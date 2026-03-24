"""Shared utility functions for ytcli."""

import re


def extract_video_id(url_or_id: str) -> str | None:
    """Extract YouTube video ID from various URL formats, or return as-is if already an ID.

    Supports:
    - https://www.youtube.com/watch?v=VIDEO_ID
    - https://youtu.be/VIDEO_ID
    - https://www.youtube.com/embed/VIDEO_ID
    - https://www.youtube.com/v/VIDEO_ID
    - Plain VIDEO_ID

    Returns None if no valid ID can be extracted from a URL-like string.
    For non-URL strings, returns the input as-is (assumed to be a video ID).
    """
    # Try v= parameter
    m = re.search(r'[?&]v=([^&]+)', url_or_id)
    if m:
        return m.group(1)
    # Try youtu.be, embed, or /v/ paths
    m = re.search(r'(?:youtu\.be|/embed|/v)/([^?&/]+)', url_or_id)
    if m:
        return m.group(1)
    # If it looks like a URL but we couldn't extract an ID, return None
    if '/' in url_or_id or '.' in url_or_id:
        return None
    # Assume it's already a video ID
    return url_or_id
