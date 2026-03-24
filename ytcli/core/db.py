"""SQLite database layer for ytcli."""

import os
import sqlite3
from pathlib import Path

DEFAULT_DATA_DIR = os.path.expanduser("~/.ytcli")

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS channels (
    id TEXT PRIMARY KEY,
    handle TEXT,
    name TEXT NOT NULL,
    description TEXT,
    subscriber_count INTEGER,
    video_count INTEGER,
    view_count INTEGER,
    thumbnail_url TEXT,
    custom_url TEXT,
    country TEXT,
    created_at TEXT,
    scanned_at TEXT,
    api_refreshed_at TEXT,
    is_own_channel BOOLEAN DEFAULT 0
);

CREATE TABLE IF NOT EXISTS videos (
    id TEXT PRIMARY KEY,
    channel_id TEXT NOT NULL REFERENCES channels(id),
    title TEXT NOT NULL,
    description TEXT,
    published_at TEXT,
    duration_seconds INTEGER,
    view_count INTEGER,
    like_count INTEGER,
    comment_count INTEGER,
    tags TEXT,
    category_id TEXT,
    thumbnail_url TEXT,
    has_captions BOOLEAN,
    is_short BOOLEAN,
    scraped_at TEXT,
    api_refreshed_at TEXT
);

CREATE TABLE IF NOT EXISTS comments (
    id TEXT PRIMARY KEY,
    video_id TEXT NOT NULL REFERENCES videos(id),
    author TEXT,
    text TEXT NOT NULL,
    like_count INTEGER DEFAULT 0,
    published_at TEXT,
    is_reply BOOLEAN DEFAULT 0,
    parent_id TEXT,
    scraped_at TEXT
);

CREATE TABLE IF NOT EXISTS transcripts (
    video_id TEXT PRIMARY KEY REFERENCES videos(id),
    text TEXT NOT NULL,
    language TEXT DEFAULT 'en',
    is_auto_generated BOOLEAN,
    fetched_at TEXT
);

CREATE TABLE IF NOT EXISTS downloads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id TEXT REFERENCES videos(id),
    url TEXT NOT NULL,
    format TEXT,
    output_path TEXT,
    downloaded_at TEXT
);

CREATE TABLE IF NOT EXISTS config (
    key TEXT PRIMARY KEY,
    value TEXT
);

CREATE INDEX IF NOT EXISTS idx_videos_channel ON videos(channel_id);
CREATE INDEX IF NOT EXISTS idx_videos_published ON videos(published_at);
CREATE INDEX IF NOT EXISTS idx_comments_video ON comments(video_id);
CREATE INDEX IF NOT EXISTS idx_videos_views ON videos(view_count);
"""


def get_db_path(data_dir: str = None) -> Path:
    """Return path to ytcli.db."""
    d = Path(data_dir) if data_dir else Path(DEFAULT_DATA_DIR)
    return d / "ytcli.db"


def init_db(data_dir: str = None) -> Path:
    """Create data directory and all tables. Return db path."""
    db_path = get_db_path(data_dir)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    try:
        conn.executescript(SCHEMA_SQL)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.commit()
    finally:
        conn.close()
    return db_path


def get_connection(data_dir: str = None) -> sqlite3.Connection:
    """Return a connection with Row factory and WAL mode."""
    db_path = get_db_path(data_dir)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _row_to_dict(row: sqlite3.Row) -> dict:
    """Convert a sqlite3.Row to a plain dict."""
    return dict(row)


# --- Channel CRUD ---


def upsert_channel(conn: sqlite3.Connection, channel_data: dict) -> None:
    """Insert or update a channel."""
    fields = [
        "id", "handle", "name", "description", "subscriber_count",
        "video_count", "view_count", "thumbnail_url", "custom_url",
        "country", "created_at", "scanned_at", "api_refreshed_at",
        "is_own_channel",
    ]
    present = {k: v for k, v in channel_data.items() if k in fields}
    if "id" not in present:
        raise ValueError("channel_data must include 'id'")

    cols = ", ".join(present.keys())
    placeholders = ", ".join("?" for _ in present)
    updates = ", ".join(f"{k}=excluded.{k}" for k in present if k != "id")

    sql = (
        f"INSERT INTO channels ({cols}) VALUES ({placeholders})"
        f" ON CONFLICT(id) DO UPDATE SET {updates}"
    )
    conn.execute(sql, list(present.values()))
    conn.commit()


def get_channel(conn: sqlite3.Connection, channel_id_or_handle: str) -> dict | None:
    """Look up a channel by ID or @handle."""
    row = conn.execute(
        "SELECT * FROM channels WHERE id = ? OR handle = ?",
        (channel_id_or_handle, channel_id_or_handle),
    ).fetchone()
    return _row_to_dict(row) if row else None


def get_channels(conn: sqlite3.Connection) -> list[dict]:
    """Return all tracked channels."""
    rows = conn.execute(
        "SELECT * FROM channels ORDER BY name"
    ).fetchall()
    return [_row_to_dict(r) for r in rows]


# --- Video CRUD ---


def upsert_video(conn: sqlite3.Connection, video_data: dict) -> None:
    """Insert or update a video."""
    fields = [
        "id", "channel_id", "title", "description", "published_at",
        "duration_seconds", "view_count", "like_count", "comment_count",
        "tags", "category_id", "thumbnail_url", "has_captions",
        "is_short", "scraped_at", "api_refreshed_at",
    ]
    present = {k: v for k, v in video_data.items() if k in fields}
    if "id" not in present:
        raise ValueError("video_data must include 'id'")

    cols = ", ".join(present.keys())
    placeholders = ", ".join("?" for _ in present)
    updates = ", ".join(f"{k}=excluded.{k}" for k in present if k != "id")

    sql = (
        f"INSERT INTO videos ({cols}) VALUES ({placeholders})"
        f" ON CONFLICT(id) DO UPDATE SET {updates}"
    )
    conn.execute(sql, list(present.values()))
    conn.commit()


_VIDEO_SORT_MAP = {
    "date": "published_at DESC",
    "views": "view_count DESC",
    "duration": "duration_seconds DESC",
}


def get_videos(
    conn: sqlite3.Connection,
    channel_id: str,
    sort: str = "date",
    limit: int = 50,
) -> list[dict]:
    """Return videos for a channel, sorted and limited."""
    order = _VIDEO_SORT_MAP.get(sort, "published_at DESC")
    rows = conn.execute(
        f"SELECT * FROM videos WHERE channel_id = ? ORDER BY {order} LIMIT ?",
        (channel_id, limit),
    ).fetchall()
    return [_row_to_dict(r) for r in rows]


def search_videos(
    conn: sqlite3.Connection,
    query: str,
    channel_id: str = None,
) -> list[dict]:
    """Search videos by title/description. Optional channel filter."""
    pattern = f"%{query}%"
    if channel_id:
        rows = conn.execute(
            "SELECT * FROM videos WHERE channel_id = ? "
            "AND (title LIKE ? OR description LIKE ?) "
            "ORDER BY published_at DESC",
            (channel_id, pattern, pattern),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM videos WHERE title LIKE ? OR description LIKE ? "
            "ORDER BY published_at DESC",
            (pattern, pattern),
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


# --- Config ---


def get_config(conn: sqlite3.Connection, key: str) -> str | None:
    """Get a config value."""
    row = conn.execute(
        "SELECT value FROM config WHERE key = ?", (key,)
    ).fetchone()
    return row["value"] if row else None


def set_config(conn: sqlite3.Connection, key: str, value: str) -> None:
    """Set a config value."""
    conn.execute(
        "INSERT INTO config (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )
    conn.commit()


# --- Stats ---


def get_stats(conn: sqlite3.Connection) -> dict:
    """Return summary stats about the database."""
    channel_count = conn.execute("SELECT COUNT(*) FROM channels").fetchone()[0]
    video_count = conn.execute("SELECT COUNT(*) FROM videos").fetchone()[0]
    comment_count = conn.execute("SELECT COUNT(*) FROM comments").fetchone()[0]

    db_path = conn.execute("PRAGMA database_list").fetchone()[2]
    try:
        db_size = os.path.getsize(db_path)
    except (TypeError, OSError):
        db_size = 0

    return {
        "channels": channel_count,
        "videos": video_count,
        "comments": comment_count,
        "db_size_bytes": db_size,
    }
