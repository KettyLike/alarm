from __future__ import annotations

import re


THREAT_WORDS = (
    "бпла",
    "шахед",
    "ракета",
    "дрон",
    "авіація",
    "повітряна ціль",
)


def looks_like_threat_message(text: str) -> bool:
    normalized = text.lower()
    return any(word in normalized for word in THREAT_WORDS)


def contains_location_context(text: str) -> bool:
    """Залишено для сумісності: рішення приймає локальний геоіндекс."""
    return bool(text.strip())


def clean_message(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()