from __future__ import annotations

import argparse
import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from config import Settings, load_settings
from distance import haversine_distance_km
from geocoder import LocalPlaceIndex
from notifier import notify_local
from parser import clean_message
from user_locations import UserLocationStore


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
        self.user_locations = UserLocationStore(settings.user_locations_path)
        self.place_index = LocalPlaceIndex(settings.places_path)
        self.messages: dict[tuple[str, int], StoredMessage] = {}

    def set_location(self, chat_id: str, latitude: float, longitude: float) -> None:
        if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
            raise ValueError("Координати мають бути в межах широти ±90° і довготи ±180°")
        self.user_locations.set(chat_id, latitude, longitude)
        logger.info("Центр моніторингу оновлено для чату %s", chat_id)

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

        found_places = self.place_index.find_in_text(text)
        if not found_places:
            logger.info("Локацію не знайдено, повідомлення збережено в контексті")
            return

        place = found_places[0]
        recipients = self.settings.telegram_alert_chat_ids or (None,)
        for chat_id in recipients:
            saved_location = (
                self.user_locations.get(chat_id) if chat_id is not None else None
            )
            latitude, longitude = saved_location or (
                self.settings.user_lat,
                self.settings.user_lon,
            )
            distance_km = haversine_distance_km(
                latitude,
                longitude,
                place.lat,
                place.lon,
            )
            logger.info(
                "%s: %s, %.1f км для чату %s",
                channel,
                place.name,
                distance_km,
                chat_id,
            )

            if distance_km > self.settings.alert_radius_km:
                continue

            await notify_local(
                f"Можлива небезпека біля {place.name}: {distance_km:.1f} км. "
                f"Повідомлення: {text}",
                self.settings.telegram_bot_token,
                (chat_id,) if chat_id is not None else (),
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
    if settings.telegram_bot_token:
        from telegram_bot import TelegramBotClient

        bot = TelegramBotClient(
            settings.telegram_bot_token,
            settings.telegram_alert_chat_ids,
            engine.set_location,
        )
        await asyncio.gather(client.run(), bot.run())
    else:
        await client.run()


def main() -> None:
    parser = argparse.ArgumentParser(description="Моніторинг географічно близьких повітряних загроз")
    parser.add_argument("--test-message", help="Перевірити обробку одного повідомлення без Telegram")
    args = parser.parse_args()
    asyncio.run(run(load_settings(), args.test_message))


if __name__ == "__main__":
    main()