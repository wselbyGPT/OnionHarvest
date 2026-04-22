from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


class StoreError(RuntimeError):
    """Raised when persisting harvested artifacts fails."""


def _ensure_sqlite_schema(conn: sqlite3.Connection) -> None:
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
        CREATE TABLE IF NOT EXISTS harvest_url_status (
            url TEXT PRIMARY KEY,
            status TEXT NOT NULL CHECK (status IN ('pending', 'success', 'error')),
            error_message TEXT
        )
        """
    )


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
            _ensure_sqlite_schema(conn)
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


def initialize_batch_status(urls: list[str], output_path: str | Path) -> Path:
    path = Path(output_path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(path) as conn:
            _ensure_sqlite_schema(conn)
            conn.executemany(
                """
                INSERT OR IGNORE INTO harvest_url_status (url, status, error_message)
                VALUES (?, 'pending', NULL)
                """,
                ((url,) for url in urls),
            )
    except sqlite3.Error as exc:
        raise StoreError(f"Store failed: unable to initialize batch status in '{path}'.") from exc
    return path


def get_urls_requiring_processing(urls: list[str], output_path: str | Path) -> list[str]:
    path = Path(output_path)
    try:
        with sqlite3.connect(path) as conn:
            _ensure_sqlite_schema(conn)
            rows = conn.execute(
                """
                SELECT url, status
                FROM harvest_url_status
                WHERE url IN ({placeholders})
                """.format(placeholders=", ".join("?" for _ in urls)),
                urls,
            ).fetchall()
    except sqlite3.Error as exc:
        raise StoreError(f"Store failed: unable to read batch status from '{path}'.") from exc

    status_by_url = {url: status for url, status in rows}
    return [url for url in urls if status_by_url.get(url) != "success"]


def update_url_status(
    url: str,
    status: str,
    output_path: str | Path,
    error_message: str | None = None,
) -> Path:
    path = Path(output_path)
    try:
        with sqlite3.connect(path) as conn:
            _ensure_sqlite_schema(conn)
            conn.execute(
                """
                INSERT INTO harvest_url_status (url, status, error_message)
                VALUES (?, ?, ?)
                ON CONFLICT(url) DO UPDATE SET
                    status = excluded.status,
                    error_message = excluded.error_message
                """,
                (url, status, error_message),
            )
    except sqlite3.Error as exc:
        raise StoreError(f"Store failed: unable to update status for URL '{url}' in '{path}'.") from exc
    return path
