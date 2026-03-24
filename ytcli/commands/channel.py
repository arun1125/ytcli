"""Tier 2: Channel Intelligence commands (yt-dlp scraping -> SQLite)."""

import click
from datetime import datetime, timezone

from ytcli.core import scraper
from ytcli.core.output import success, error, progress


def _resolve_channel_url(channel: str) -> tuple[str, str]:
    """Convert channel arg to (url, handle).

    Handles both '@mkbhd' and 'https://www.youtube.com/@mkbhd'.
    Returns (url, handle) where handle is '@mkbhd' format.
    """
    if channel.startswith("http"):
        url = channel
        # Extract handle from URL
        handle = channel.rstrip("/").split("/")[-1]
        if not handle.startswith("@"):
            handle = None
    else:
        handle = channel if channel.startswith("@") else f"@{channel}"
        url = f"https://www.youtube.com/{handle}"
    return url, handle


def _upload_date_to_iso(upload_date: str) -> str | None:
    """Convert yt-dlp upload_date (YYYYMMDD) to ISO date string."""
    if not upload_date:
        return None
    try:
        return f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:8]}"
    except (IndexError, TypeError):
        return None


@click.command()
@click.argument("channel")
@click.option("--limit", default=None, type=int, help="Max videos to scrape.")
@click.pass_context
def scan(ctx, channel, limit):
    """Scrape channel video metadata into DB."""
    from ytcli.core.db import init_db, get_connection, upsert_channel, upsert_video

    data_dir = ctx.obj.get("data_dir")

    url, handle = _resolve_channel_url(channel)

    try:
        progress(f"Scanning {channel}...")
        video_list = scraper.get_channel_videos(url, limit=limit)
    except Exception as e:
        error("scan", f"Failed to scrape channel: {e}")
        raise SystemExit(1)

    if not video_list:
        error("scan", f"No videos found for {channel}")
        raise SystemExit(1)

    # Extract channel info from first video entry
    first = video_list[0]
    channel_id = first.get("channel_id", "")
    channel_name = first.get("channel", "") or channel

    # Ensure DB exists
    init_db(data_dir)
    conn = get_connection(data_dir)

    now = datetime.now(timezone.utc).isoformat()

    try:
        # Upsert channel
        upsert_channel(conn, {
            "id": channel_id,
            "handle": handle,
            "name": channel_name,
            "scanned_at": now,
            "video_count": len(video_list),
        })

        # Upsert each video
        for v in video_list:
            upsert_video(conn, {
                "id": v.get("id", ""),
                "channel_id": channel_id,
                "title": v.get("title", ""),
                "duration_seconds": v.get("duration"),
                "view_count": v.get("view_count"),
                "published_at": _upload_date_to_iso(v.get("upload_date")),
                "scraped_at": now,
            })

        success("scan", {
            "channel": channel_name,
            "handle": handle,
            "channel_id": channel_id,
            "videos_found": len(video_list),
        })
    except Exception as e:
        error("scan", f"Database error: {e}")
        raise SystemExit(1)
    finally:
        conn.close()


@click.command()
@click.pass_context
def channels(ctx):
    """List all tracked channels."""
    from ytcli.core.db import get_connection, get_channels as db_get_channels

    data_dir = ctx.obj.get("data_dir")
    try:
        conn = get_connection(data_dir)
        rows = db_get_channels(conn)
        conn.close()
        success("channels", {"channels": rows})
    except Exception as e:
        error("channels", str(e))
        raise SystemExit(1)


@click.command()
@click.argument("channel")
@click.option("--sort", "sort_by", default="date", type=click.Choice(["date", "views", "duration"]), help="Sort order.")
@click.option("--limit", default=None, type=int, help="Max videos to show.")
@click.pass_context
def videos(ctx, channel, sort_by, limit):
    """List channel videos."""
    from ytcli.core.db import get_connection, get_channel, get_videos as db_get_videos

    data_dir = ctx.obj.get("data_dir")
    try:
        conn = get_connection(data_dir)
        ch = get_channel(conn, channel)
        if ch is None:
            conn.close()
            error("videos", f"Channel not found: {channel}")
            raise SystemExit(1)
        vid_limit = limit if limit is not None else 50
        rows = db_get_videos(conn, ch["id"], sort=sort_by, limit=vid_limit)
        conn.close()
        success("videos", {
            "channel": ch["name"],
            "videos": rows,
            "count": len(rows),
        })
    except Exception as e:
        error("videos", str(e))
        raise SystemExit(1)


@click.command()
@click.argument("query")
@click.option("--channel", default=None, help="Restrict search to a channel.")
@click.pass_context
def search(ctx, query, channel):
    """Full-text search across stored videos."""
    from ytcli.core.db import get_connection, get_channel, search_videos as db_search_videos

    data_dir = ctx.obj.get("data_dir")
    try:
        conn = get_connection(data_dir)
        channel_id = None
        if channel:
            ch = get_channel(conn, channel)
            if ch is None:
                conn.close()
                error("search", f"Channel not found: {channel}")
                raise SystemExit(1)
            channel_id = ch["id"]
        results = db_search_videos(conn, query, channel_id=channel_id)
        conn.close()
        success("search", {
            "query": query,
            "results": results,
            "count": len(results),
        })
    except Exception as e:
        error("search", str(e))
        raise SystemExit(1)


@click.command()
@click.argument("channel", required=False)
@click.pass_context
def refresh(ctx, channel):
    """Re-scan for new uploads since last scan."""
    from ytcli.core.db import init_db, get_connection, get_channel, get_channels as db_get_channels, upsert_video, upsert_channel

    data_dir = ctx.obj.get("data_dir")
    init_db(data_dir)
    conn = get_connection(data_dir)

    try:
        # Determine which channels to refresh
        if channel:
            ch = get_channel(conn, channel)
            if ch is None:
                error("refresh", f"Channel not found: {channel}")
                raise SystemExit(1)
            channels_to_refresh = [ch]
        else:
            channels_to_refresh = db_get_channels(conn)
            if not channels_to_refresh:
                error("refresh", "No channels tracked. Use 'scan' to add a channel first.")
                raise SystemExit(1)

        now = datetime.now(timezone.utc).isoformat()
        total_new = 0
        total_updated = 0
        total_refreshed = 0

        for ch in channels_to_refresh:
            handle = ch.get("handle")
            if handle:
                url = f"https://www.youtube.com/{handle}"
            elif ch.get("custom_url"):
                url = ch["custom_url"]
            else:
                progress(f"Skipping channel {ch['name']}: no handle or custom_url")
                continue

            try:
                progress(f"Refreshing {ch['name']}...")
                video_list = scraper.get_channel_videos(url)
            except Exception as e:
                progress(f"Error refreshing {ch['name']}: {e}")
                continue

            # Get existing video IDs for this channel
            existing_ids = {
                row[0] for row in conn.execute(
                    "SELECT id FROM videos WHERE channel_id = ?", (ch["id"],)
                ).fetchall()
            }

            new_count = 0
            updated_count = 0
            for v in video_list:
                vid_id = v.get("id", "")
                if vid_id in existing_ids:
                    updated_count += 1
                else:
                    new_count += 1

                upsert_video(conn, {
                    "id": vid_id,
                    "channel_id": ch["id"],
                    "title": v.get("title", ""),
                    "duration_seconds": v.get("duration"),
                    "view_count": v.get("view_count"),
                    "published_at": _upload_date_to_iso(v.get("upload_date")),
                    "scraped_at": now,
                })

            upsert_channel(conn, {
                "id": ch["id"],
                "name": ch["name"],
                "scanned_at": now,
            })

            total_new += new_count
            total_updated += updated_count
            total_refreshed += 1

        success("refresh", {
            "channels_refreshed": total_refreshed,
            "new_videos": total_new,
            "updated_videos": total_updated,
        })
    except Exception as e:
        error("refresh", f"Refresh failed: {e}")
        raise SystemExit(1)
    finally:
        conn.close()
