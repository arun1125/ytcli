"""YouTube Data API v3 client — requires google-api-python-client."""

import re


def get_api_client(api_key: str):
    """Build YouTube API client. Raises ImportError if google-api-python-client not installed."""
    try:
        from googleapiclient.discovery import build
    except ImportError:
        raise ImportError("Install API dependencies: pip install ytcli[api]")
    return build("youtube", "v3", developerKey=api_key)


def get_channel_stats(client, channel_handle_or_id: str) -> dict:
    """Get channel statistics.

    Returns dict with subscriber_count, view_count, video_count,
    name, description, thumbnail_url, channel_id.
    """
    # Determine if it's a handle (@name) or channel ID (UC...)
    if channel_handle_or_id.startswith("@"):
        handle = channel_handle_or_id.lstrip("@")
        request = client.channels().list(
            part="statistics,snippet",
            forHandle=handle,
        )
    else:
        request = client.channels().list(
            part="statistics,snippet",
            id=channel_handle_or_id,
        )

    response = request.execute()
    items = response.get("items", [])
    if not items:
        raise ValueError(f"Channel not found: {channel_handle_or_id}")

    item = items[0]
    snippet = item.get("snippet", {})
    stats = item.get("statistics", {})

    return {
        "channel_id": item["id"],
        "name": snippet.get("title", ""),
        "description": snippet.get("description", ""),
        "thumbnail_url": snippet.get("thumbnails", {}).get("default", {}).get("url", ""),
        "subscriber_count": int(stats.get("subscriberCount", 0)),
        "view_count": int(stats.get("viewCount", 0)),
        "video_count": int(stats.get("videoCount", 0)),
    }


def get_video_stats(client, video_id: str) -> dict:
    """Get video statistics.

    Returns dict with view_count, like_count, comment_count,
    title, published_at, duration.
    """
    request = client.videos().list(
        part="statistics,snippet,contentDetails",
        id=video_id,
    )
    response = request.execute()
    items = response.get("items", [])
    if not items:
        raise ValueError(f"Video not found: {video_id}")

    item = items[0]
    snippet = item.get("snippet", {})
    stats = item.get("statistics", {})
    details = item.get("contentDetails", {})

    return {
        "video_id": item["id"],
        "title": snippet.get("title", ""),
        "published_at": snippet.get("publishedAt", ""),
        "duration": details.get("duration", ""),
        "view_count": int(stats.get("viewCount", 0)),
        "like_count": int(stats.get("likeCount", 0)),
        "comment_count": int(stats.get("commentCount", 0)),
    }


def get_comments(client, video_id: str, sort: str = "relevance", limit: int = 100) -> list[dict]:
    """Get video comments.

    Args:
        sort: "relevance" or "time"
        limit: max number of comments to return

    Returns list of dicts with author, text, like_count, published_at.
    """
    # Map user-friendly sort names to API values
    order = "relevance" if sort in ("relevance", "top") else "time"

    comments = []
    next_page_token = None

    while len(comments) < limit:
        max_results = min(100, limit - len(comments))
        kwargs = {
            "part": "snippet",
            "videoId": video_id,
            "order": order,
            "maxResults": max_results,
            "textFormat": "plainText",
        }
        if next_page_token:
            kwargs["pageToken"] = next_page_token

        request = client.commentThreads().list(**kwargs)
        response = request.execute()

        for item in response.get("items", []):
            top = item["snippet"]["topLevelComment"]["snippet"]
            comments.append({
                "author": top.get("authorDisplayName", ""),
                "text": top.get("textDisplay", ""),
                "like_count": int(top.get("likeCount", 0)),
                "published_at": top.get("publishedAt", ""),
            })

        next_page_token = response.get("nextPageToken")
        if not next_page_token:
            break

    return comments[:limit]


def search_youtube(client, query: str, limit: int = 10) -> list[dict]:
    """Search YouTube.

    Returns list of dicts with video_id, title, channel, published_at, thumbnail_url.
    """
    results = []
    next_page_token = None

    while len(results) < limit:
        max_results = min(50, limit - len(results))
        kwargs = {
            "part": "snippet",
            "q": query,
            "type": "video",
            "maxResults": max_results,
        }
        if next_page_token:
            kwargs["pageToken"] = next_page_token

        request = client.search().list(**kwargs)
        response = request.execute()

        for item in response.get("items", []):
            snippet = item.get("snippet", {})
            results.append({
                "video_id": item["id"].get("videoId", ""),
                "title": snippet.get("title", ""),
                "channel": snippet.get("channelTitle", ""),
                "published_at": snippet.get("publishedAt", ""),
                "thumbnail_url": snippet.get("thumbnails", {}).get("default", {}).get("url", ""),
            })

        next_page_token = response.get("nextPageToken")
        if not next_page_token:
            break

    return results[:limit]
