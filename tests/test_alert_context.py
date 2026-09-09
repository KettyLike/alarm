import asyncio
from pathlib import Path

from app import AlertEngine
from config import Settings


def make_settings() -> Settings:
    return Settings(
        user_lat=50.4501,
        user_lon=30.5234,
        alert_radius_km=140,
        context_minutes=20,
        alert_sound=False,
        telegram_bot_token=None,
        telegram_alert_chat_ids=(),
        telegram_api_id=None,
        telegram_api_hash=None,
        telegram_session="test",
        telegram_channels=(),
        places_path=Path(__file__).parents[1] / "places_ukraine.json",
    )


def test_location_message_triggers_without_threat_word() -> None:
    engine = AlertEngine(make_settings())

    asyncio.run(engine.handle_message("test", "Рух у напрямку Бучі", 1, None))

    assert ("test", 1) in engine.messages


def test_reply_messages_are_combined_into_context() -> None:
    engine = AlertEngine(make_settings())

    asyncio.run(engine.handle_message("test", "Повітряна ціль", 1, None))
    asyncio.run(engine.handle_message("test", "на Бучу", 2, 1))

    assert ("test", 1) in engine.messages