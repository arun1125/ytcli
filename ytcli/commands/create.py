"""Tier 5: Creation Assist commands."""

import click

from ytcli.core import analyzer, scraper
from ytcli.core.output import success, error


def _generate_title_variations(topic: str) -> list[dict]:
    """Generate title variations using common YouTube patterns.

    Returns list of dicts with 'title' and 'pattern' keys.
    """
    # Capitalize topic for titles
    topic_cap = topic.title()
    topic_lower = topic.lower()

    variations = []

    # Question patterns
    variations.append({"title": f"What Is {topic_cap} and Why Should You Care?", "pattern": "question"})
    variations.append({"title": f"Why Does {topic_cap} Matter?", "pattern": "question"})
    variations.append({"title": f"Is {topic_cap} Worth Learning in 2025?", "pattern": "question"})
    variations.append({"title": f"What Nobody Tells You About {topic_cap}?", "pattern": "question"})

    # Number patterns
    variations.append({"title": f"7 {topic_cap} Tips That Actually Work", "pattern": "number"})
    variations.append({"title": f"Top 5 {topic_cap} Mistakes to Avoid", "pattern": "number"})
    variations.append({"title": f"10 {topic_cap} Tricks You Didn't Know", "pattern": "number"})
    variations.append({"title": f"3 {topic_cap} Secrets From the Pros", "pattern": "number"})

    # How-to patterns
    variations.append({"title": f"How to {topic_cap} (Step by Step)", "pattern": "how-to"})
    variations.append({"title": f"The Complete Guide to {topic_cap}", "pattern": "how-to"})
    variations.append({"title": f"How to Master {topic_cap} in 30 Days", "pattern": "how-to"})
    variations.append({"title": f"{topic_cap} for Beginners — Start Here", "pattern": "how-to"})

    # Bracket patterns
    variations.append({"title": f"{topic_cap} [2025 Guide]", "pattern": "bracket"})
    variations.append({"title": f"{topic_cap} (You Won't Believe This)", "pattern": "bracket"})
    variations.append({"title": f"I Tried {topic_cap} [Honest Review]", "pattern": "bracket"})
    variations.append({"title": f"{topic_cap} (What I Wish I Knew Earlier)", "pattern": "bracket"})

    return variations


@click.command()
@click.option("--from", "from_channel", default=None, help="Source channel for ideas.")
@click.option("--count", default=10, type=int, help="Number of ideas to generate.")
@click.pass_context
def ideas(ctx, from_channel, count):
    """Generate video ideas from gaps/trends."""
    from ytcli.core.db import get_connection, get_channel, get_channels, get_videos

    data_dir = ctx.obj.get("data_dir")
    try:
        conn = get_connection(data_dir)

        # Get videos: from specific channel or all channels
        if from_channel:
            ch = get_channel(conn, from_channel)
            if not ch:
                error("ideas", f"Channel '{from_channel}' not found. Run 'ytcli scan {from_channel}' first.")
                conn.close()
                return
            all_videos = get_videos(conn, ch["id"], limit=500)
        else:
            channels = get_channels(conn)
            all_videos = []
            for ch in channels:
                all_videos.extend(get_videos(conn, ch["id"], limit=500))

        conn.close()

        if not all_videos:
            error("ideas", "No videos in database. Run 'ytcli scan CHANNEL' first.")
            return

        # Run analysis
        gaps = analyzer.find_content_gaps(all_videos)
        hooks = analyzer.analyze_hooks(all_videos)

        # Extract trending words from hooks analysis
        trending_words = [w["word"] for w in hooks.get("common_words", [])[:10]]

        # Extract high-view video topics (top 25% by views)
        sorted_by_views = sorted(
            [v for v in all_videos if v.get("view_count")],
            key=lambda v: v["view_count"],
            reverse=True,
        )
        top_quartile = sorted_by_views[:max(1, len(sorted_by_views) // 4)]

        # Build idea list
        idea_list = []

        # 1. Gap-based ideas: low-frequency topics combined with trending words
        low_freq = gaps.get("low_frequency_topics", [])
        for topic in low_freq:
            if len(idea_list) >= count:
                break
            # Find which videos mentioned this topic
            inspired = [
                v["title"] for v in all_videos
                if v.get("title") and topic.lower() in v["title"].lower()
            ][:3]
            # Combine with a trending word for relevance
            trending_hint = f" (trending: {trending_words[0]})" if trending_words else ""
            idea_list.append({
                "topic": topic,
                "reasoning": f"Low-frequency topic with room for more content{trending_hint}",
                "inspired_by": inspired,
            })

        # 2. High-performer ideas: topics from top-viewed videos
        for v in top_quartile:
            if len(idea_list) >= count:
                break
            title = v.get("title", "")
            keywords = analyzer._extract_keywords(title)
            if keywords:
                topic = " ".join(keywords[:3])
                # Check not already suggested
                existing_topics = {i["topic"] for i in idea_list}
                if topic not in existing_topics:
                    idea_list.append({
                        "topic": topic,
                        "reasoning": f"Derived from high-performing video ({v.get('view_count', 0):,} views)",
                        "inspired_by": [title],
                    })

        # Trim to count
        idea_list = idea_list[:count]

        success("ideas", {
            "ideas": idea_list,
            "count": len(idea_list),
        })
    except Exception as e:
        error("ideas", str(e))


@click.command()
@click.argument("topic")
@click.option("--count", default=5, type=int, help="Number of title variations.")
@click.pass_context
def titles(ctx, topic, count):
    """Generate title variations from patterns."""
    from ytcli.core.db import get_connection, search_videos

    data_dir = ctx.obj.get("data_dir")
    try:
        conn = get_connection(data_dir)

        # Search DB for similar videos
        similar = search_videos(conn, topic)
        conn.close()

        # Generate base variations
        all_variations = _generate_title_variations(topic)

        # If DB has similar videos, analyze their patterns and note them
        db_patterns = None
        if similar:
            hooks_data = analyzer.analyze_hooks(similar)
            db_patterns = {
                "similar_video_count": len(similar),
                "question_pct": hooks_data.get("question_title_pct", 0),
                "number_pct": hooks_data.get("number_in_title_pct", 0),
                "bracket_pct": hooks_data.get("bracket_pct", 0),
            }

            # Prioritize patterns that match what works in DB
            # Sort: patterns with higher DB prevalence first
            pattern_score = {
                "question": hooks_data.get("question_title_pct", 0),
                "number": hooks_data.get("number_in_title_pct", 0),
                "bracket": hooks_data.get("bracket_pct", 0),
                "how-to": 50.0,  # default mid-priority
            }
            all_variations.sort(
                key=lambda v: pattern_score.get(v["pattern"], 0),
                reverse=True,
            )

        # Trim to count
        result_titles = all_variations[:count]

        result_data = {
            "topic": topic,
            "titles": result_titles,
            "count": len(result_titles),
        }
        if db_patterns:
            result_data["db_patterns"] = db_patterns

        success("titles", result_data)
    except Exception as e:
        error("titles", str(e))


@click.command()
@click.argument("source")
@click.pass_context
def tags(ctx, source):
    """Suggest tags based on similar content."""
    import json as _json
    from collections import Counter
    from ytcli.core.db import get_connection, search_videos

    data_dir = ctx.obj.get("data_dir")
    try:
        # URL input: extract tags from the video directly
        if "youtube.com" in source or "youtu.be" in source:
            meta = scraper.get_video_metadata(source)
            tag_list = meta.get("tags") or []
            success("tags", {
                "input": source,
                "tags": tag_list,
                "source": "video",
            })
            return

        # Topic input: search DB and aggregate tags
        conn = get_connection(data_dir)
        results = search_videos(conn, source)
        conn.close()

        tag_counter = Counter()
        for v in results:
            raw = v.get("tags")
            if not raw:
                continue
            try:
                parsed = _json.loads(raw)
                if isinstance(parsed, list):
                    for t in parsed:
                        if isinstance(t, str):
                            tag_counter[t] += 1
            except (_json.JSONDecodeError, TypeError):
                pass

        sorted_tags = [t for t, _ in tag_counter.most_common()]

        success("tags", {
            "input": source,
            "tags": sorted_tags,
            "source": "search",
        })
    except Exception as e:
        error("tags", str(e))


@click.command("batch-audio")
@click.argument("source")
@click.option("--format", "fmt", default="mp3", help="Audio format (default: mp3).")
@click.pass_context
def batch_audio(ctx, source, fmt):
    """Bulk audio download from file or playlist URL."""
    import os
    from ytcli.core.db import get_connection, get_config
    from ytcli.core.output import progress

    data_dir = ctx.obj.get("data_dir")
    try:
        conn = get_connection(data_dir)
        output_dir = get_config(conn, "output_dir") or "./downloads"
        conn.close()

        # Determine if source is a file or a URL
        if os.path.isfile(source):
            # Read URLs from file
            with open(source) as f:
                urls = []
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    urls.append(line)
        else:
            # Treat as single playlist/video URL
            urls = [source]

        downloads = []
        succeeded = 0
        failed = 0

        for url in urls:
            try:
                progress(f"Downloading: {url}")
                path = scraper.download_audio(url, output_dir, format=fmt)
                downloads.append({"url": url, "path": path})
                succeeded += 1
            except Exception as e:
                downloads.append({"url": url, "error": str(e)})
                failed += 1

        success("batch-audio", {
            "total": len(urls),
            "succeeded": succeeded,
            "failed": failed,
            "downloads": downloads,
        })
    except Exception as e:
        error("batch-audio", str(e))


@click.command()
@click.argument("channel")
@click.option("--format", "fmt", default="json", type=click.Choice(["csv", "json"]), help="Export format.")
@click.pass_context
def export(ctx, channel, fmt):
    """Export channel data."""
    import csv
    import io
    from ytcli.core.db import get_connection, get_channel, get_videos

    data_dir = ctx.obj.get("data_dir")
    try:
        conn = get_connection(data_dir)
        ch = get_channel(conn, channel)
        if not ch:
            error("export", f"Channel '{channel}' not found. Run 'ytcli scan {channel}' first.")
            conn.close()
            return

        videos = get_videos(conn, ch["id"], limit=10000)
        conn.close()

        csv_fields = ["id", "title", "published_at", "duration_seconds", "view_count", "like_count"]

        if fmt == "csv":
            buf = io.StringIO()
            writer = csv.DictWriter(buf, fieldnames=csv_fields, extrasaction="ignore")
            writer.writeheader()
            for v in videos:
                writer.writerow(v)
            csv_str = buf.getvalue()

            success("export", {
                "channel": ch["name"],
                "format": "csv",
                "count": len(videos),
                "csv": csv_str,
            })
        else:
            # JSON format — include only key fields per video
            clean_videos = []
            for v in videos:
                clean_videos.append({k: v.get(k) for k in csv_fields})

            success("export", {
                "channel": ch["name"],
                "format": "json",
                "count": len(videos),
                "data": clean_videos,
            })
    except Exception as e:
        error("export", str(e))
