from __future__ import annotations

import asyncio
import json
import logging
from urllib.parse import urlencode
from urllib.request import HTTPError, Request, urlopen


logger = logging.getLogger(__name__)


def _send_telegram_message(token: str, chat_id: str, message: str) -> None:
    payload = urlencode(
        {
            "chat_id": chat_id,
            "text": message[:4096],
            "disable_web_page_preview": "true",
        }
    ).encode("utf-8")
    request = Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=15) as response:
            result = json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        error_body = error.read().decode("utf-8", errors="replace")
        try:
            api_error = json.loads(error_body)
            description = api_error.get("description", error_body)
        except json.JSONDecodeError:
            description = error_body
        raise RuntimeError(
            f"Telegram Bot API HTTP {error.code}: {description}"
        ) from error

    if not result.get("ok"):
        raise RuntimeError(result.get("description", "Telegram Bot API error"))


async def notify_local(
    message: str,
    sound: bool = True,
    bot_token: str | None = None,
    alert_chat_ids: tuple[str, ...] = (),
) -> None:
    logger.warning("ALERT: %s", message)
    if bot_token:
        for chat_id in alert_chat_ids:
            try:
                await asyncio.to_thread(
                    _send_telegram_message,
                    bot_token,
                    chat_id,
                    message,
                )
                logger.info("Telegram-сповіщення надіслано в чат %s", chat_id)
            except Exception:
                logger.exception(
                    "Не вдалося надіслати Telegram-сповіщення в чат %s",
                    chat_id,
                )

    if not sound:
        return

    try:
        import winsound

        for _ in range(3):
            winsound.Beep(1200, 600)
    except (ImportError, RuntimeError):
        print("\a" * 3, end="", flush=True)