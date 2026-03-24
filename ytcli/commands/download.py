"""Tier 1: Download & Extract commands (yt-dlp, no API key)."""

import click

from ytcli.core import scraper
from ytcli.core.output import success, error, progress


@click.command()
@click.argument("url")
@click.option("--format", "fmt", default="mp4", help="Video format (default: mp4).")
@click.option("--quality", default="1080", help="Video quality (default: 1080).")
@click.pass_context
def download(ctx, url, fmt, quality):
    """Download video."""
    import os
    from datetime import datetime, timezone

    data_dir = ctx.obj.get("data_dir") if ctx.obj else None

    # Determine output directory: config output_dir > ./downloads
    output_dir = os.path.join(".", "downloads")
    try:
        from ytcli.core.db import get_connection, get_config
        conn = get_connection(data_dir)
        configured_dir = get_config(conn, "output_dir")
        if configured_dir:
            output_dir = configured_dir
        conn.close()
    except Exception:
        pass  # DB may not exist yet, use default

    os.makedirs(output_dir, exist_ok=True)

    try:
        progress(f"Downloading {url} as {fmt} ({quality}p)...")
        output_path = scraper.download_video(url, output_dir, format=fmt, quality=quality)

        # Record in DB if available
        try:
            from ytcli.core.db import get_connection
            conn = get_connection(data_dir)
            conn.execute(
                "INSERT INTO downloads (url, format, output_path, downloaded_at) VALUES (?, ?, ?, ?)",
                (url, fmt, output_path, datetime.now(timezone.utc).isoformat()),
            )
            conn.commit()
            conn.close()
        except Exception:
            pass  # DB not initialized, skip recording

        success("download", {
            "output_path": output_path,
            "format": fmt,
            "quality": quality,
            "url": url,
        })
    except Exception as e:
        error("download", str(e))
        raise SystemExit(1)


@click.command()
@click.argument("url")
@click.option("--format", "fmt", default=None, help="Audio format (default: mp3).")
@click.option("--quality", default="best", help="Audio quality (default: best).")
@click.pass_context
def audio(ctx, url, fmt, quality):
    """Extract audio only."""
    import os
    from datetime import datetime, timezone

    data_dir = ctx.obj.get("data_dir") if ctx.obj else None

    # Resolve format: CLI flag > config default_audio_format > mp3
    if fmt is None:
        try:
            from ytcli.core.db import get_connection, get_config
            conn = get_connection(data_dir)
            configured_fmt = get_config(conn, "default_audio_format")
            conn.close()
            if configured_fmt:
                fmt = configured_fmt
        except Exception:
            pass
        if fmt is None:
            fmt = "mp3"

    # Determine output directory: config output_dir > ./downloads
    output_dir = os.path.join(".", "downloads")
    try:
        from ytcli.core.db import get_connection, get_config
        conn = get_connection(data_dir)
        configured_dir = get_config(conn, "output_dir")
        if configured_dir:
            output_dir = configured_dir
        conn.close()
    except Exception:
        pass

    os.makedirs(output_dir, exist_ok=True)

    try:
        progress(f"Extracting audio from {url} as {fmt}...")
        output_path = scraper.download_audio(url, output_dir, format=fmt, quality=quality)

        # Record in DB if available
        try:
            from ytcli.core.db import get_connection
            conn = get_connection(data_dir)
            conn.execute(
                "INSERT INTO downloads (url, format, output_path, downloaded_at) VALUES (?, ?, ?, ?)",
                (url, fmt, output_path, datetime.now(timezone.utc).isoformat()),
            )
            conn.commit()
            conn.close()
        except Exception:
            pass

        success("audio", {
            "output_path": output_path,
            "format": fmt,
            "quality": quality,
            "url": url,
        })
    except Exception as e:
        error("audio", str(e))
        raise SystemExit(1)


@click.command()
@click.argument("url")
@click.option("--lang", default="en", help="Subtitle language (default: en).")
@click.pass_context
def transcript(ctx, url, lang):
    """Get subtitles as clean text."""
    from datetime import datetime, timezone

    data_dir = ctx.obj.get("data_dir") if ctx.obj else None

    try:
        progress(f"Fetching transcript for {url} (lang={lang})...")
        text = scraper.get_transcript(url, lang=lang)

        # Store in DB if available
        try:
            from ytcli.core.db import get_connection
            conn = get_connection(data_dir)
            # Extract video ID from URL for DB storage
            video_id = _extract_video_id(url)
            if video_id:
                # Ensure video record exists (FK constraint requires channel → video → transcript)
                conn.execute(
                    "INSERT INTO channels (id, name) VALUES (?, ?) ON CONFLICT(id) DO NOTHING",
                    ("unknown", "unknown"),
                )
                conn.execute(
                    "INSERT INTO videos (id, channel_id, title) "
                    "VALUES (?, ?, ?) ON CONFLICT(id) DO NOTHING",
                    (video_id, "unknown", "unknown"),
                )
                conn.execute(
                    "INSERT INTO transcripts (video_id, text, language, fetched_at) "
                    "VALUES (?, ?, ?, ?) "
                    "ON CONFLICT(video_id) DO UPDATE SET text=excluded.text, "
                    "language=excluded.language, fetched_at=excluded.fetched_at",
                    (video_id, text, lang, datetime.now(timezone.utc).isoformat()),
                )
                conn.commit()
            conn.close()
        except Exception:
            pass  # DB not initialized, skip recording

        success("transcript", {
            "text": text,
            "language": lang,
            "url": url,
        })
    except Exception as e:
        error("transcript", str(e))
        raise SystemExit(1)


def _extract_video_id(url: str) -> str | None:
    """Extract YouTube video ID from various URL formats."""
    import re
    patterns = [
        r'(?:v=|/v/|youtu\.be/)([a-zA-Z0-9_-]{11})',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


@click.command()
@click.argument("url")
@click.option("--output", "output_path", default=None, help="Output file path.")
@click.pass_context
def thumbnail(ctx, url, output_path):
    """Download thumbnail image."""
    import os

    data_dir = ctx.obj.get("data_dir") if ctx.obj else None

    # Determine output directory
    if output_path:
        output_dir = os.path.dirname(output_path) or "."
    else:
        output_dir = os.path.join(".", "downloads")
        try:
            from ytcli.core.db import get_connection, get_config
            conn = get_connection(data_dir)
            configured_dir = get_config(conn, "output_dir")
            if configured_dir:
                output_dir = configured_dir
            conn.close()
        except Exception:
            pass

    os.makedirs(output_dir, exist_ok=True)

    try:
        progress(f"Downloading thumbnail for {url}...")
        result_path = scraper.download_thumbnail(url, output_dir)

        success("thumbnail", {
            "output_path": result_path,
            "url": url,
        })
    except Exception as e:
        error("thumbnail", str(e))
        raise SystemExit(1)


@click.command()
@click.argument("url")
@click.pass_context
def metadata(ctx, url):
    """Dump video metadata JSON."""
    try:
        raw = scraper.get_video_metadata(url)
        has_captions = bool(raw.get("subtitles") or raw.get("automatic_captions"))
        data = {
            "id": raw.get("id"),
            "title": raw.get("title"),
            "description": raw.get("description"),
            "channel": raw.get("channel"),
            "channel_id": raw.get("channel_id"),
            "duration": raw.get("duration"),
            "view_count": raw.get("view_count"),
            "like_count": raw.get("like_count"),
            "comment_count": raw.get("comment_count"),
            "published_at": raw.get("upload_date"),
            "tags": raw.get("tags"),
            "thumbnail_url": raw.get("thumbnail"),
            "has_captions": has_captions,
        }
        success("metadata", data)
    except Exception as e:
        error("metadata", str(e))
        raise SystemExit(1)
