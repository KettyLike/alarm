from __future__ import annotations

import base64
from collections.abc import Awaitable, Callable
import logging
import os
from pathlib import Path
import sqlite3
from urllib.parse import urlparse

from telethon import TelegramClient, events
from telethon.sessions import StringSession


MessageHandler = Callable[[str, str, int, int | None], Awaitable[None]]
logger = logging.getLogger(__name__)


class TelegramChannelClient:
    def __init__(
        self,
        api_id: int,
        api_hash: str,
        session_name: str,
        channels: tuple[str, ...],
        message_handler: MessageHandler,
    ) -> None:
        string_session = os.getenv("TELEGRAM_STRING_SESSION", "").strip()
        session = StringSession(string_session) if string_session else session_name
        self.client = TelegramClient(session, api_id, api_hash)
        self.channels = channels
        self.message_handler = message_handler

    @staticmethod
    def normalize_channel_reference(reference: str) -> str | int:
        reference = reference.strip()
        if reference.startswith("https://") or reference.startswith("http://"):
            parsed = urlparse(reference)
            reference = parsed.path.strip("/").split("/")[0]
        reference = reference.removeprefix("@")

        try:
            return int(reference)
        except ValueError:
            return reference

    async def resolve_channels(self) -> list[object]:
        resolved_channels: list[object] = []
        for reference in self.channels:
            normalized_reference = self.normalize_channel_reference(reference)
            try:
                resolved_channels.append(
                    await self.client.get_input_entity(normalized_reference)
                )
            except ValueError as error:
                raise ValueError(
                    f'Не вдалося знайти Telegram-канал "{reference}". '
                    "У TELEGRAM_CHANNELS вкажіть username (наприклад @channel), "
                    "посилання https://t.me/channel або numeric ID. "
                    "Назва каналу з заголовка, наприклад 'Kyiv AirDefense', не підходить."
                ) from error
            logger.info("Канал підключено: %s", reference)
        return resolved_channels

    def register_handlers(self, resolved_channels: list[object]) -> None:
        @self.client.on(events.NewMessage(chats=resolved_channels))
        async def on_new_message(event) -> None:
            text = (event.raw_text or "").strip()
            if text:
                logger.info("Отримано повідомлення: %s", text[:200])
                reply_to = event.message.reply_to_msg_id
                await self.message_handler(
                    str(event.chat_id),
                    text,
                    event.message.id,
                    reply_to,
                )

    def restore_session_from_environment(self) -> None:
        if os.getenv("TELEGRAM_STRING_SESSION", "").strip():
            return

        encoded_session = os.getenv("TELEGRAM_SESSION_BASE64", "").strip()
        if not encoded_session:
            chunks: list[str] = []
            chunk_index = 1
            while chunk := os.getenv(
                f"TELEGRAM_SESSION_BASE64_{chunk_index}", ""
            ).strip():
                chunks.append(chunk)
                chunk_index += 1
            encoded_session = "".join(chunks)

        if not encoded_session:
            return

        session_path = Path(f"{self.client.session.filename}.session")
        if session_path.exists():
            return

        try:
            session_data = base64.b64decode(encoded_session, validate=True)
        except ValueError as error:
            raise ValueError(
                "TELEGRAM_SESSION_BASE64 має містити коректний Base64 session-файл."
            ) from error

        session_path.parent.mkdir(parents=True, exist_ok=True)
        session_path.write_bytes(session_data)
        logger.info("Telegram session відновлено у %s", session_path)

    async def run(self) -> None:
        try:
            self.restore_session_from_environment()
            await self.client.start()
        except sqlite3.OperationalError as error:
            if "locked" not in str(error).lower():
                raise
            raise RuntimeError(
                "Telegram session заблокована іншим процесом. "
                "Зупиніть інший запуск app.py, видаліть файл "
                "air_alert_session.session-journal і запустіть програму один раз."
            ) from error
        resolved_channels = await self.resolve_channels()
        self.register_handlers(resolved_channels)
        print("Telegram-клієнт запущений. Очікування повідомлень...")
        await self.client.run_until_disconnected()