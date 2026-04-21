from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


class StoreError(RuntimeError):
    """Raised when persisting harvested artifacts fails."""


def store_json_record(record: dict[str, Any], output_path: str | Path) -> Path:
    path = Path(output_path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
    except OSError as exc:
        raise StoreError(f"Store failed: unable to write JSON artifact to '{path}'.") from exc
    return path


def store_sqlite_record(record: dict[str, Any], output_path: str | Path) -> Path:
    path = Path(output_path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS harvest_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT NOT NULL,
                    fetched_via TEXT NOT NULL,
                    title TEXT,
                    description TEXT,
                    links_count INTEGER,
                    text_preview TEXT
                )
                """
            )
            conn.execute(
                """
                INSERT INTO harvest_records (url, fetched_via, title, description, links_count, text_preview)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    record.get("url"),
                    record.get("fetched_via"),
                    record.get("title"),
                    record.get("description"),
                    int(record.get("links_count", 0)),
                    record.get("text_preview"),
                ),
            )
    except sqlite3.Error as exc:
        raise StoreError(f"Store failed: unable to write SQLite artifact to '{path}'.") from exc
    return path
