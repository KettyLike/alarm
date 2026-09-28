import asyncio

from telegram_bot import TelegramBotClient


def test_authorized_shared_location_updates_center(monkeypatch) -> None:
    locations: list[tuple[str, float, float]] = []
    sent_messages: list[dict[str, object]] = []
    bot = TelegramBotClient(
        "token",
        ("123",),
        lambda chat_id, lat, lon: locations.append((chat_id, lat, lon)),
    )

    async def capture_request(method: str, payload: dict[str, object]) -> dict:
        sent_messages.append(payload)
        return {"ok": True}

    monkeypatch.setattr(bot, "_request", capture_request)
    asyncio.run(
        bot.process_update(
            {
                "message": {
                    "chat": {"id": 123},
                    "location": {"latitude": 50.45, "longitude": 30.52},
                }
            }
        )
    )

    assert locations == [("123", 50.45, 30.52)]
    assert sent_messages[0]["chat_id"] == 123


def test_location_from_unlisted_chat_is_ignored(monkeypatch) -> None:
    locations: list[tuple[float, float]] = []
    bot = TelegramBotClient(
        "token",
        ("123",),
        lambda chat_id, lat, lon: locations.append((lat, lon)),
    )

    async def unexpected_request(method: str, payload: dict[str, object]) -> dict:
        raise AssertionError("Unauthorized chat must not trigger a Bot API request")

    monkeypatch.setattr(bot, "_request", unexpected_request)
    asyncio.run(
        bot.process_update(
            {
                "message": {
                    "chat": {"id": 456},
                    "location": {"latitude": 50.45, "longitude": 30.52},
                }
            }
        )
    )

    assert locations == []


def test_start_shows_location_request_button(monkeypatch) -> None:
    requests: list[tuple[str, dict[str, object]]] = []
    bot = TelegramBotClient("token", ("123",), lambda chat_id, lat, lon: None)

    async def capture_request(method: str, payload: dict[str, object]) -> dict:
        requests.append((method, payload))
        return {"ok": True}

    monkeypatch.setattr(bot, "_request", capture_request)
    asyncio.run(
        bot.process_update(
            {"message": {"chat": {"id": 123}, "text": "/start"}}
        )
    )

    assert requests[0][0] == "sendMessage"
    keyboard = requests[0][1]["reply_markup"]["keyboard"]
    assert keyboard[0][0]["request_location"] is True