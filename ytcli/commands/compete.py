"""Tier 4: Competitive Analysis commands (local computation)."""

from collections import defaultdict

import click

from ytcli.core import analyzer, api
from ytcli.core.output import success, error


@click.command()
@click.argument("ch1")
@click.argument("ch2")
@click.pass_context
def compare(ctx, ch1, ch2):
    """Side-by-side: frequency, duration, topics, patterns."""
    from ytcli.core.db import get_connection, get_channel, get_videos

    data_dir = ctx.obj.get("data_dir")
    try:
        conn = get_connection(data_dir)

        ch1_info = get_channel(conn, ch1)
        if not ch1_info:
            error("compare", f"Channel '{ch1}' not found. Run 'ytcli scan {ch1}' first.")
            raise SystemExit(1)

        ch2_info = get_channel(conn, ch2)
        if not ch2_info:
            error("compare", f"Channel '{ch2}' not found. Run 'ytcli scan {ch2}' first.")
            raise SystemExit(1)

        ch1_videos = get_videos(conn, ch1_info["id"], limit=500)
        ch2_videos = get_videos(conn, ch2_info["id"], limit=500)
        conn.close()

        result = analyzer.compare_channels(ch1_videos, ch2_videos, ch1_info, ch2_info)
        success("compare", result)
    except Exception as e:
        error("compare", str(e))
        raise SystemExit(1)


@click.command()
@click.argument("channel")
@click.pass_context
def gaps(ctx, channel):
    """Content topics they haven't covered."""
    from ytcli.core.db import get_connection, get_channel, get_videos

    data_dir = ctx.obj.get("data_dir")
    try:
        conn = get_connection(data_dir)

        ch_info = get_channel(conn, channel)
        if not ch_info:
            error("gaps", f"Channel '{channel}' not found. Run 'ytcli scan {channel}' first.")
            raise SystemExit(1)

        videos = get_videos(conn, ch_info["id"], limit=500)
        conn.close()

        result = analyzer.find_content_gaps(videos)
        success("gaps", result)
    except Exception as e:
        error("gaps", str(e))
        raise SystemExit(1)


@click.command()
@click.argument("channel")
@click.option("--limit", default=20, type=int, help="Number of hooks to analyze.")
@click.pass_context
def hooks(ctx, channel, limit):
    """Title/thumbnail pattern analysis."""
    from ytcli.core.db import get_connection, get_channel, get_videos

    data_dir = ctx.obj.get("data_dir")
    try:
        conn = get_connection(data_dir)

        ch_info = get_channel(conn, channel)
        if not ch_info:
            error("hooks", f"Channel '{channel}' not found. Run 'ytcli scan {channel}' first.")
            raise SystemExit(1)

        videos = get_videos(conn, ch_info["id"], limit=limit)
        conn.close()

        result = analyzer.analyze_hooks(videos)
        success("hooks", result)
    except Exception as e:
        error("hooks", str(e))
        raise SystemExit(1)


@click.command()
@click.argument("channel")
@click.pass_context
def calendar(ctx, channel):
    """Upload schedule and frequency trends."""
    from ytcli.core.db import get_connection, get_channel, get_videos

    data_dir = ctx.obj.get("data_dir")
    try:
        conn = get_connection(data_dir)

        ch_info = get_channel(conn, channel)
        if not ch_info:
            error("calendar", f"Channel '{channel}' not found. Run 'ytcli scan {channel}' first.")
            raise SystemExit(1)

        videos = get_videos(conn, ch_info["id"], limit=500)
        conn.close()

        result = analyzer.analyze_upload_schedule(videos)
        success("calendar", result)
    except Exception as e:
        error("calendar", str(e))
        raise SystemExit(1)


@click.command()
@click.argument("query")
@click.option("--limit", default=10, type=int, help="Max channels to find.")
@click.pass_context
def niche(ctx, query, limit):
    """Find channels in a niche."""
    from ytcli.core.db import get_connection, get_config

    data_dir = ctx.obj.get("data_dir")
    try:
        conn = get_connection(data_dir)
        api_key = get_config(conn, "api_key")
        conn.close()

        if not api_key:
            error("niche", "No API key configured. Run 'ytcli config api_key YOUR_KEY' first.")
            raise SystemExit(1)

        client = api.get_api_client(api_key)
        results = api.search_youtube(client, query, limit=50)

        # Group by channel name
        by_channel = defaultdict(list)
        for r in results:
            by_channel[r["channel"]].append(r["title"])

        # Rank by number of videos (more = more relevant to niche)
        ranked = sorted(by_channel.items(), key=lambda x: len(x[1]), reverse=True)

        channels = [
            {
                "name": name,
                "video_count": len(titles),
                "sample_videos": titles,
            }
            for name, titles in ranked[:limit]
        ]

        success("niche", {
            "query": query,
            "channels": channels,
            "count": len(channels),
        })
    except Exception as e:
        error("niche", str(e))
        raise SystemExit(1)
