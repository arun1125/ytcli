"""Tier 3: Analytics commands (YouTube Data API v3, requires API key)."""

import re

import click

from ytcli.core import api
from ytcli.core.output import success, error


def _get_api_key(data_dir):
    """Get API key from DB config. Returns key or None."""
    from ytcli.core.db import get_connection, get_config
    conn = get_connection(data_dir)
    key = get_config(conn, "api_key")
    conn.close()
    return key


def _extract_video_id(url_or_id: str) -> str:
    """Extract video ID from a YouTube URL or return as-is if already an ID.

    Supports:
    - https://www.youtube.com/watch?v=VIDEO_ID
    - https://youtu.be/VIDEO_ID
    - https://www.youtube.com/embed/VIDEO_ID
    - Plain VIDEO_ID
    """
    # Try v= parameter
    m = re.search(r'[?&]v=([^&]+)', url_or_id)
    if m:
        return m.group(1)
    # Try youtu.be or embed
    m = re.search(r'(?:youtu\.be|/embed)/([^?&/]+)', url_or_id)
    if m:
        return m.group(1)
    # Assume it's already a video ID
    return url_or_id


@click.command()
@click.option("--api-key", default=None, help="YouTube Data API v3 key.")
@click.pass_context
def auth(ctx, api_key):
    """Set up API authentication."""
    from ytcli.core.db import get_connection, get_config, set_config, init_db

    data_dir = ctx.obj.get("data_dir")
    try:
        init_db(data_dir)
        conn = get_connection(data_dir)

        if api_key:
            set_config(conn, "api_key", api_key)
            conn.close()
            success("auth", {
                "api_key_set": True,
                "status": "API key stored successfully.",
            })
        else:
            existing = get_config(conn, "api_key")
            conn.close()
            if existing:
                masked = existing[:4] + "***" + existing[-2:] if len(existing) > 6 else "***"
                success("auth", {
                    "api_key_set": True,
                    "status": f"API key configured: {masked}",
                })
            else:
                success("auth", {
                    "api_key_set": False,
                    "status": "No API key configured. Use: ytcli auth --api-key YOUR_KEY",
                })
    except Exception as e:
        error("auth", str(e))
        raise SystemExit(1)


@click.command()
@click.argument("channel")
@click.pass_context
def stats(ctx, channel):
    """Subscriber count, views, growth."""
    from ytcli.core.db import get_connection, init_db, upsert_channel

    data_dir = ctx.obj.get("data_dir")
    try:
        init_db(data_dir)
        api_key = _get_api_key(data_dir)
        if not api_key:
            error("stats", "No API key configured. Use: ytcli auth --api-key YOUR_KEY")
            raise SystemExit(1)

        client = api.get_api_client(api_key)
        channel_data = api.get_channel_stats(client, channel)

        # Update channel record in DB
        from datetime import datetime, timezone
        conn = get_connection(data_dir)
        upsert_channel(conn, {
            "id": channel_data["channel_id"],
            "name": channel_data["name"],
            "description": channel_data.get("description", ""),
            "thumbnail_url": channel_data.get("thumbnail_url", ""),
            "subscriber_count": channel_data["subscriber_count"],
            "view_count": channel_data["view_count"],
            "video_count": channel_data["video_count"],
            "api_refreshed_at": datetime.now(timezone.utc).isoformat(),
        })
        conn.close()

        success("stats", channel_data)
    except SystemExit:
        raise
    except ValueError as e:
        error("stats", str(e))
        raise SystemExit(1)
    except Exception as e:
        error("stats", str(e))
        raise SystemExit(1)


@click.command()
@click.argument("video_url")
@click.pass_context
def performance(ctx, video_url):
    """Views, likes, engagement metrics."""
    data_dir = ctx.obj.get("data_dir")
    try:
        from ytcli.core.db import init_db
        init_db(data_dir)

        api_key = _get_api_key(data_dir)
        if not api_key:
            error("performance", "No API key configured. Use: ytcli auth --api-key YOUR_KEY")
            raise SystemExit(1)

        video_id = _extract_video_id(video_url)
        client = api.get_api_client(api_key)
        video_data = api.get_video_stats(client, video_id)

        # Compute engagement rate
        views = video_data["view_count"]
        likes = video_data["like_count"]
        comments = video_data["comment_count"]
        if views > 0:
            engagement_rate = round((likes + comments) / views * 100, 2)
        else:
            engagement_rate = 0.0

        video_data["engagement_rate"] = engagement_rate
        success("performance", video_data)
    except SystemExit:
        raise
    except ValueError as e:
        error("performance", str(e))
        raise SystemExit(1)
    except Exception as e:
        error("performance", str(e))
        raise SystemExit(1)


@click.command()
@click.argument("channel")
@click.option("--by", "sort_by", default="views", type=click.Choice(["views", "engagement", "growth"]), help="Sort metric.")
@click.option("--limit", default=10, type=int, help="Number of results.")
@click.pass_context
def top(ctx, channel, sort_by, limit):
    """Best performing videos."""
    from ytcli.core.db import get_connection, get_channel, get_videos, init_db

    data_dir = ctx.obj.get("data_dir")
    try:
        init_db(data_dir)
        conn = get_connection(data_dir)
        ch = get_channel(conn, channel)
        if not ch:
            conn.close()
            error("top", f"Channel not found: {channel}")
            raise SystemExit(1)

        channel_id = ch["id"]
        channel_name = ch["name"]

        if sort_by == "views":
            # Sort by views from DB data (already stored from scan)
            vids = get_videos(conn, channel_id, sort="views", limit=limit)
            conn.close()
            video_list = [
                {
                    "id": v["id"],
                    "title": v["title"],
                    "view_count": v["view_count"] or 0,
                    "published_at": v["published_at"],
                }
                for v in vids
            ]
        elif sort_by == "engagement":
            # Need API to get like/comment counts for engagement calculation
            api_key = _get_api_key(data_dir)
            if not api_key:
                conn.close()
                error("top", "No API key configured. Engagement sort requires API. Use: ytcli auth --api-key YOUR_KEY")
                raise SystemExit(1)

            # Get all videos from DB, then enrich with API stats
            vids = get_videos(conn, channel_id, sort="views", limit=200)
            conn.close()
            client = api.get_api_client(api_key)

            enriched = []
            for v in vids:
                try:
                    stats_data = api.get_video_stats(client, v["id"])
                    views = stats_data["view_count"]
                    likes = stats_data["like_count"]
                    comment_count = stats_data["comment_count"]
                    eng_rate = round((likes + comment_count) / views * 100, 2) if views > 0 else 0.0
                    enriched.append({
                        "id": v["id"],
                        "title": stats_data.get("title", v["title"]),
                        "view_count": views,
                        "like_count": likes,
                        "comment_count": comment_count,
                        "engagement_rate": eng_rate,
                        "published_at": v["published_at"],
                    })
                except Exception:
                    continue

            enriched.sort(key=lambda x: x["engagement_rate"], reverse=True)
            video_list = enriched[:limit]
        else:
            # growth — fall back to views for now
            vids = get_videos(conn, channel_id, sort="views", limit=limit)
            conn.close()
            video_list = [
                {
                    "id": v["id"],
                    "title": v["title"],
                    "view_count": v["view_count"] or 0,
                    "published_at": v["published_at"],
                }
                for v in vids
            ]

        success("top", {
            "channel": channel_name,
            "sort_by": sort_by,
            "videos": video_list,
            "count": len(video_list),
        })
    except SystemExit:
        raise
    except Exception as e:
        error("top", str(e))
        raise SystemExit(1)


@click.command()
@click.argument("video_url")
@click.option("--sort", "sort_by", default="top", type=click.Choice(["top", "recent"]), help="Sort order.")
@click.option("--limit", default=100, type=int, help="Max comments to pull.")
@click.pass_context
def comments(ctx, video_url, sort_by, limit):
    """Pull video comments."""
    from datetime import datetime, timezone
    from ytcli.core.db import get_connection, init_db

    data_dir = ctx.obj.get("data_dir")
    try:
        init_db(data_dir)
        api_key = _get_api_key(data_dir)
        if not api_key:
            error("comments", "No API key configured. Use: ytcli auth --api-key YOUR_KEY")
            raise SystemExit(1)

        video_id = _extract_video_id(video_url)
        client = api.get_api_client(api_key)
        comment_list = api.get_comments(client, video_id, sort_by, limit)

        # Store comments in DB (skip if video not in DB due to FK constraint)
        conn = get_connection(data_dir)
        now = datetime.now(timezone.utc).isoformat()
        try:
            for i, c in enumerate(comment_list):
                comment_id = f"{video_id}_{i}_{hash(c['text']) % 100000}"
                conn.execute(
                    "INSERT OR REPLACE INTO comments (id, video_id, author, text, like_count, published_at, scraped_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (comment_id, video_id, c["author"], c["text"], c["like_count"], c.get("published_at", ""), now),
                )
            conn.commit()
        except Exception:
            # FK constraint fails if video not in DB — still return the data
            pass
        finally:
            conn.close()

        success("comments", {
            "video_id": video_id,
            "comments": comment_list,
            "count": len(comment_list),
        })
    except SystemExit:
        raise
    except Exception as e:
        error("comments", str(e))
        raise SystemExit(1)
