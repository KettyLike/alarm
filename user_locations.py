from __future__ import annotations

import sqlite3
from pathlib import Path


class UserLocationStore:
    def __init__(self, database_path: str | Path) -> None:
        path = str(database_path)
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path)
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS user_locations (
                chat_id TEXT PRIMARY KEY,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL
            )
            """
        )
        self.connection.commit()

    def set(self, chat_id: str, latitude: float, longitude: float) -> None:
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO user_locations (chat_id, latitude, longitude)
                VALUES (?, ?, ?)
                ON CONFLICT(chat_id) DO UPDATE SET
                    latitude = excluded.latitude,
                    longitude = excluded.longitude
                """,
                (str(chat_id), latitude, longitude),
            )

    def get(self, chat_id: str) -> tuple[float, float] | None:
        row = self.connection.execute(
            "SELECT latitude, longitude FROM user_locations WHERE chat_id = ?",
            (str(chat_id),),
        ).fetchone()
        return (float(row[0]), float(row[1])) if row else None