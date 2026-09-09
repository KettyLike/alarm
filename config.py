from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parent
load_dotenv(ROOT_DIR / ".env")


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"Не задано обов'язкове налаштування {name}")
    return value


def _bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "y", "так"}


@dataclass(frozen=True)
class Settings:
    user_lat: float
    user_lon: float
    alert_radius_km: float
    context_minutes: int
    alert_sound: bool
    telegram_bot_token: str | None
    telegram_alert_chat_ids: tuple[str, ...]
    telegram_api_id: int | None
    telegram_api_hash: str | None
    telegram_session: str
    telegram_channels: tuple[str, ...]
    places_path: Path


def load_settings() -> Settings:
    api_id = os.getenv("TELEGRAM_API_ID", "").strip()
    api_hash = os.getenv("TELEGRAM_API_HASH", "").strip()
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    alert_chat_ids = tuple(
        chat_id.strip()
        for chat_id in os.getenv("TELEGRAM_ALERT_CHAT_IDS", "").split(",")
        if chat_id.strip()
    )
    channels = tuple(
        channel.strip()
        for channel in os.getenv("TELEGRAM_CHANNELS", "").split(",")
        if channel.strip()
    )

    return Settings(
        user_lat=float(os.getenv("USER_LAT", "50.4501")),
        user_lon=float(os.getenv("USER_LON", "30.5234")),
        alert_radius_km=float(os.getenv("ALERT_RADIUS_KM", "40")),
        context_minutes=int(os.getenv("MESSAGE_CONTEXT_MINUTES", "20")),
        alert_sound=_bool("ALERT_SOUND", True),
        telegram_bot_token=bot_token or None,
        telegram_alert_chat_ids=alert_chat_ids,
        telegram_api_id=int(api_id) if api_id else None,
        telegram_api_hash=api_hash or None,
        telegram_session=os.getenv("TELEGRAM_SESSION", "air_alert_session"),
        telegram_channels=channels,
        places_path=ROOT_DIR / "places_ukraine.json",
    )