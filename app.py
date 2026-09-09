from __future__ import annotations

import argparse
import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from config import Settings, load_settings
from distance import haversine_distance_km
from geocoder import LocalPlaceIndex
from notifier import notify_local
from parser import clean_message


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class StoredMessage:
    text: str
    message_id: int
    reply_to_id: int | None
    received_at: datetime


class AlertEngine:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.place_index = LocalPlaceIndex(settings.places_path)
        self.messages: dict[tuple[str, int], StoredMessage] = {}

    def _context_text(
        self,
        channel: str,
        message_id: int,
        text: str,
        reply_to_id: int | None,
        now: datetime,
    ) -> str:
        parts = [text]
        current_reply_id = reply_to_id
        max_age = timedelta(minutes=self.settings.context_minutes)

        for _ in range(10):
            if current_reply_id is None:
                break
            parent = self.messages.get((channel, current_reply_id))
            if parent is None or now - parent.received_at > max_age:
                break
            parts.append(parent.text)
            current_reply_id = parent.reply_to_id

        return " ".join(reversed(parts))

    async def handle_message(
        self,
        channel: str,
        text: str,
        message_id: int = 0,
        reply_to_id: int | None = None,
    ) -> None:
        text = clean_message(text)
        now = datetime.now(timezone.utc)
        if message_id:
            self.messages[(channel, message_id)] = StoredMessage(
                text=text,
                message_id=message_id,
                reply_to_id=reply_to_id,
                received_at=now,
            )

        combined_text = self._context_text(
            channel,
            message_id,
            text,
            reply_to_id,
            now,
        )
        found_places = self.place_index.find_in_text(combined_text)
        if not found_places:
            logger.info("Локацію не знайдено, повідомлення збережено в контексті")
            return

        for place in found_places:
            distance_km = haversine_distance_km(
                self.settings.user_lat,
                self.settings.user_lon,
                place.lat,
                place.lon,
            )
            logger.info("%s: %s, %.1f км", channel, place.name, distance_km)

            if distance_km > self.settings.alert_radius_km:
                continue

            await notify_local(
                f"Можлива небезпека біля {place.name}: {distance_km:.1f} км. "
                f"Контекст: {combined_text}",
                self.settings.alert_sound,
                self.settings.telegram_bot_token,
                self.settings.telegram_alert_chat_ids,
            )


async def run(settings: Settings, test_message: str | None) -> None:
    logger.info("Запуск моніторингу. Радіус: %.1f км", settings.alert_radius_km)
    engine = AlertEngine(settings)
    if test_message:
        await engine.handle_message("test", test_message, message_id=1)
        return

    if not settings.telegram_api_id or not settings.telegram_api_hash:
        raise ValueError("Для live-режиму заповніть TELEGRAM_API_ID і TELEGRAM_API_HASH у .env")
    if not settings.telegram_channels:
        raise ValueError("Для live-режиму заповніть TELEGRAM_CHANNELS у .env")

    from telegram_client import TelegramChannelClient

    client = TelegramChannelClient(
        settings.telegram_api_id,
        settings.telegram_api_hash,
        settings.telegram_session,
        settings.telegram_channels,
        engine.handle_message,
    )
    await client.run()


def main() -> None:
    parser = argparse.ArgumentParser(description="Моніторинг географічно близьких повітряних загроз")
    parser.add_argument("--test-message", help="Перевірити обробку одного повідомлення без Telegram")
    args = parser.parse_args()
    asyncio.run(run(load_settings(), args.test_message))


if __name__ == "__main__":
    main()