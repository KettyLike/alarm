from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Place:
    name: str
    lat: float
    lon: float
    matched_alias: str


class LocalPlaceIndex:
    def __init__(self, json_path: str | Path) -> None:
        path = Path(json_path)
        with path.open("r", encoding="utf-8") as file:
            raw_places = json.load(file)

        self._places: dict[str, dict[str, object]] = raw_places
        self._aliases: dict[str, str] = {}
        for name, data in raw_places.items():
            for alias in {name, *data.get("aliases", [])}:
                self._aliases[self.normalize(alias)] = name

    @staticmethod
    def normalize(value: str) -> str:
        value = value.lower().replace("’", "'")
        value = re.sub(r"[^a-zа-яіїєґ0-9' -]", " ", value)
        return re.sub(r"\s+", " ", value).strip()

    def find_in_text(self, text: str) -> list[Place]:
        normalized_text = self.normalize(text)
        result: list[Place] = []
        found_names: set[str] = set()

        for alias in sorted(self._aliases, key=len, reverse=True):
            pattern = rf"(?<![\wа-яіїєґ]){re.escape(alias)}(?![\wа-яіїєґ])"
            if not re.search(pattern, normalized_text):
                continue

            name = self._aliases[alias]
            if name in found_names:
                continue
            data = self._places[name]
            result.append(
                Place(
                    name=name,
                    lat=float(data["lat"]),
                    lon=float(data["lon"]),
                    matched_alias=alias,
                ))
            found_names.add(name)
            
        return result