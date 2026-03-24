"""Local computation — patterns, gaps, hooks analysis."""

from __future__ import annotations

import re
from collections import Counter
from datetime import datetime, timedelta

STOPWORDS = frozenset({
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "it", "its", "this", "that", "was",
    "are", "be", "been", "being", "have", "has", "had", "do", "does", "did",
    "will", "would", "could", "should", "may", "might", "can", "not", "no",
    "so", "if", "as", "up", "out", "about", "into", "over", "after", "how",
    "what", "when", "where", "who", "why", "which", "all", "each", "every",
    "both", "more", "most", "other", "some", "such", "than", "too", "very",
    "just", "i", "me", "my", "we", "our", "you", "your", "he", "she", "they",
    "them", "his", "her", "us", "am", "were", "get", "got",
})

MIN_KEYWORD_LEN = 3


def _extract_keywords(text: str) -> list[str]:
    """Split text into lowercase keywords, removing stopwords and short words."""
    words = re.findall(r"[a-zA-Z0-9]+", text.lower())
    return [w for w in words if w not in STOPWORDS and len(w) >= MIN_KEYWORD_LEN]


def _safe_mean(values: list[float | int]) -> float:
    """Return mean of values, or 0.0 if empty."""
    if not values:
        return 0.0
    return sum(values) / len(values)


def _parse_date(date_str: str | None) -> datetime | None:
    """Try to parse a date string. Returns None on failure."""
    if not date_str:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y%m%d"):
        try:
            return datetime.strptime(date_str, fmt)
        except (ValueError, TypeError):
            continue
    return None


def _channel_stats(videos: list[dict], info: dict) -> dict:
    """Compute per-channel stats."""
    durations = [v["duration_seconds"] for v in videos if v.get("duration_seconds")]
    views = [v["view_count"] for v in videos if v.get("view_count") is not None]
    titles = [v["title"] for v in videos if v.get("title")]

    dates = sorted(
        [d for v in videos if (d := _parse_date(v.get("published_at")))]
    )
    if len(dates) >= 2:
        span_weeks = max((dates[-1] - dates[0]).days / 7.0, 1e-9)
        upload_frequency = len(dates) / span_weeks
    else:
        upload_frequency = 0.0

    return {
        "name": info.get("name", ""),
        "total_videos": len(videos),
        "upload_frequency_per_week": round(upload_frequency, 2),
        "avg_duration_seconds": round(_safe_mean(durations), 1),
        "avg_views": round(_safe_mean(views), 1),
        "avg_title_length": round(_safe_mean([len(t) for t in titles]), 1),
    }


def compare_channels(
    ch1_videos: list[dict],
    ch2_videos: list[dict],
    ch1_info: dict,
    ch2_info: dict,
) -> dict:
    """Compare two channels side-by-side.

    Returns dict with channel_1 stats, channel_2 stats, and topic_overlap (Jaccard).
    """
    ch1_stats = _channel_stats(ch1_videos, ch1_info)
    ch2_stats = _channel_stats(ch2_videos, ch2_info)

    # Topic overlap via Jaccard similarity on title keywords
    kw1 = set()
    for v in ch1_videos:
        if v.get("title"):
            kw1.update(_extract_keywords(v["title"]))

    kw2 = set()
    for v in ch2_videos:
        if v.get("title"):
            kw2.update(_extract_keywords(v["title"]))

    if kw1 or kw2:
        intersection = kw1 & kw2
        union = kw1 | kw2
        topic_overlap = len(intersection) / len(union) if union else 0.0
    else:
        topic_overlap = 0.0

    return {
        "channel_1": ch1_stats,
        "channel_2": ch2_stats,
        "topic_overlap": round(topic_overlap, 4),
    }


def analyze_hooks(videos: list[dict]) -> dict:
    """Analyze title patterns across videos.

    Returns stats on title length, common words, question/number/bracket/caps usage.
    """
    titles = [v["title"] for v in videos if v.get("title")]

    if not titles:
        return {
            "total_titles": 0,
            "avg_title_length": 0.0,
            "max_title_length": 0,
            "min_title_length": 0,
            "common_words": [],
            "question_title_pct": 0.0,
            "number_in_title_pct": 0.0,
            "bracket_pct": 0.0,
            "caps_word_pct": 0.0,
            "top_patterns": [],
        }

    lengths = [len(t) for t in titles]
    n = len(titles)

    # Common words (excluding stopwords)
    word_counts: Counter = Counter()
    for t in titles:
        word_counts.update(_extract_keywords(t))
    common_words = [{"word": w, "count": c} for w, c in word_counts.most_common(20)]

    # Pattern percentages
    question_count = sum(1 for t in titles if t.rstrip().endswith("?"))
    number_count = sum(1 for t in titles if re.search(r"\d", t))
    bracket_count = sum(1 for t in titles if re.search(r"[\[\]\(\)]", t))
    caps_count = sum(
        1 for t in titles if any(
            w.isupper() and len(w) >= 2 for w in t.split()
        )
    )

    # Top patterns: collect the detected pattern types sorted by prevalence
    patterns = []
    if question_count:
        patterns.append({"pattern": "question", "count": question_count, "pct": round(question_count / n * 100, 1)})
    if number_count:
        patterns.append({"pattern": "number", "count": number_count, "pct": round(number_count / n * 100, 1)})
    if bracket_count:
        patterns.append({"pattern": "bracket", "count": bracket_count, "pct": round(bracket_count / n * 100, 1)})
    if caps_count:
        patterns.append({"pattern": "all_caps_word", "count": caps_count, "pct": round(caps_count / n * 100, 1)})
    patterns.sort(key=lambda p: p["count"], reverse=True)

    return {
        "total_titles": n,
        "avg_title_length": round(_safe_mean(lengths), 1),
        "max_title_length": max(lengths),
        "min_title_length": min(lengths),
        "common_words": common_words,
        "question_title_pct": round(question_count / n * 100, 1),
        "number_in_title_pct": round(number_count / n * 100, 1),
        "bracket_pct": round(bracket_count / n * 100, 1),
        "caps_word_pct": round(caps_count / n * 100, 1),
        "top_patterns": patterns,
    }


def analyze_upload_schedule(videos: list[dict]) -> dict:
    """Analyze upload timing patterns.

    Returns day-of-week distribution, videos/week, longest streak, longest gap.
    """
    dates = sorted(
        [d for v in videos if (d := _parse_date(v.get("published_at")))]
    )

    if not dates:
        return {
            "total_videos": 0,
            "day_of_week": {},
            "videos_per_week": 0.0,
            "longest_streak_weeks": 0,
            "longest_gap_days": 0,
        }

    # Day-of-week distribution
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    day_counts: Counter = Counter()
    for d in dates:
        day_counts[day_names[d.weekday()]] += 1
    day_of_week = {name: day_counts.get(name, 0) for name in day_names}

    # Videos per week
    if len(dates) >= 2:
        span_weeks = max((dates[-1] - dates[0]).days / 7.0, 1e-9)
        videos_per_week = len(dates) / span_weeks
    else:
        videos_per_week = 0.0

    # Longest gap (days between consecutive uploads)
    gaps_days = []
    for i in range(1, len(dates)):
        gap = (dates[i] - dates[i - 1]).days
        gaps_days.append(gap)
    longest_gap = max(gaps_days) if gaps_days else 0

    # Longest streak: consecutive ISO weeks with at least one upload
    if dates:
        week_numbers = sorted(set(
            d.isocalendar()[0] * 100 + d.isocalendar()[1] for d in dates
        ))
        # Convert to (year, week) tuples for proper consecutive check
        weeks = []
        for wn in week_numbers:
            weeks.append((wn // 100, wn % 100))

        best_streak = 1
        current_streak = 1
        for i in range(1, len(weeks)):
            prev_y, prev_w = weeks[i - 1]
            cur_y, cur_w = weeks[i]
            # Check if consecutive week
            prev_date = datetime.strptime(f"{prev_y}-W{prev_w:02d}-1", "%Y-W%W-%w")
            cur_date = datetime.strptime(f"{cur_y}-W{cur_w:02d}-1", "%Y-W%W-%w")
            if (cur_date - prev_date).days == 7:
                current_streak += 1
            else:
                best_streak = max(best_streak, current_streak)
                current_streak = 1
        best_streak = max(best_streak, current_streak)
    else:
        best_streak = 0

    return {
        "total_videos": len(dates),
        "day_of_week": day_of_week,
        "videos_per_week": round(videos_per_week, 2),
        "longest_streak_weeks": best_streak,
        "longest_gap_days": longest_gap,
    }


def find_content_gaps(
    videos: list[dict],
    reference_topics: list[str] | None = None,
) -> dict:
    """Find content gaps: underrepresented and uncovered topics.

    Extracts keywords from titles, finds low-frequency ones (1-2 mentions),
    and if reference_topics given, finds which are not covered.
    """
    # Extract all keywords from titles
    topic_counts: Counter = Counter()
    for v in videos:
        if v.get("title"):
            topic_counts.update(_extract_keywords(v["title"]))

    total_topics = len(topic_counts)

    # Low-frequency topics (mentioned only 1-2 times)
    low_frequency = sorted(
        [t for t, c in topic_counts.items() if c <= 2]
    )

    result: dict = {
        "total_topics": total_topics,
        "low_frequency_topics": low_frequency,
    }

    # Uncovered topics from reference list
    if reference_topics is not None:
        existing = set(topic_counts.keys())
        uncovered = [
            t for t in reference_topics
            if t.lower() not in existing
        ]
        result["uncovered_topics"] = uncovered

    return result
