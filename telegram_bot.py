from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Callable
from urllib.error import HTTPError
from urllib.request import Request, urlopen


logger = logging.getLogger(__name__)
LocationHandler = Callable[[str, float, float], None]


def _request_telegram(token: str, method: str, payload: dict[str, object]) -> dict:
    request = Request(
        f"https://api.telegram.org/bot{token}/{method}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=40) as response:
            result = json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Telegram Bot API HTTP {error.code}: {body}") from error

    if not result.get("ok"):
        raise RuntimeError(result.get("description", "Telegram Bot API error"))
    return result


class TelegramBotClient:
    def __init__(
        self,
        token: str,
        allowed_chat_ids: tuple[str, ...],
        location_handler: LocationHandler,
    ) -> None:
        self.token = token
        self.allowed_chat_ids = {str(chat_id) for chat_id in allowed_chat_ids}
        self.location_handler = location_handler
        self.offset = 0

    async def _request(self, method: str, payload: dict[str, object]) -> dict:
        return await asyncio.to_thread(_request_telegram, self.token, method, payload)

    async def _send_location_request(self, chat_id: int) -> None:
        await self._request(
            "sendMessage",
            {
                "chat_id": chat_id,
                "text": "Надішліть свою локацію, щоб встановити центр моніторингу.",
                "reply_markup": {
                    "keyboard": [[{"text": "Надіслати локацію", "request_location": True}]],
                    "resize_keyboard": True,
                    "one_time_keyboard": True,
                },
            },
        )

    async def process_update(self, update: dict[str, object]) -> None:
        message = update.get("message")
        if not isinstance(message, dict):
            return
        chat = message.get("chat")
        if not isinstance(chat, dict):
            return
        chat_id = chat.get("id")
        if chat_id is None:
            return
        if str(chat_id) not in self.allowed_chat_ids:
            logger.warning("Ігнорую повідомлення бота з неавторизованого чату %s", chat_id)
            return

        text = message.get("text", "")
        if isinstance(text, str):
            command = text.split()[0].split("@", 1)[0] if text.split() else ""
            if command in ("/start", "/location"):
                await self._send_location_request(int(chat_id))
                return

        location = message.get("location")
        if not isinstance(location, dict):
            return
        try:
            latitude = float(location["latitude"])
            longitude = float(location["longitude"])
        except (KeyError, TypeError, ValueError):
            return
        if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
            return

        self.location_handler(str(chat_id), latitude, longitude)
        await self._request(
            "sendMessage",
            {
                "chat_id": chat_id,
                "text": f"Локацію оновлено: {latitude:.5f}, {longitude:.5f}.",
                "reply_markup": {"remove_keyboard": True},
            },
        )
        logger.info("Отримано нову локацію з Telegram-чату %s", chat_id)

    async def run(self) -> None:
        logger.info("Telegram-бот запущений для отримання локації")
        while True:
            try:
                result = await self._request(
                    "getUpdates",
                    {
                        "offset": self.offset,
                        "timeout": 30,
                        "allowed_updates": ["message"],
                    },
                )
                for update in result.get("result", []):
                    self.offset = int(update["update_id"]) + 1
                    await self.process_update(update)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Помилка отримання оновлень Telegram-бота")
                await asyncio.sleep(5)