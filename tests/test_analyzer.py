"""Tests for core/analyzer.py — local computation functions."""

import pytest

from ytcli.core.analyzer import (
    analyze_hooks,
    analyze_upload_schedule,
    compare_channels,
    find_content_gaps,
)


# --- Fixtures ---

def _make_videos(titles_and_dates, channel_id="UC_test"):
    """Helper: build video dicts from (title, published_at, duration, views) tuples."""
    videos = []
    for i, item in enumerate(titles_and_dates):
        if len(item) == 4:
            title, pub, dur, views = item
        elif len(item) == 2:
            title, pub = item
            dur, views = 600, 1000
        else:
            raise ValueError(f"Expected 2 or 4 elements, got {len(item)}")
        videos.append({
            "id": f"vid_{i}",
            "channel_id": channel_id,
            "title": title,
            "published_at": pub,
            "duration_seconds": dur,
            "view_count": views,
        })
    return videos


CH1_VIDEOS = _make_videos([
    ("How to Build a PC in 2024", "2024-01-07T12:00:00Z", 900, 50000),
    ("Best GPUs for Gaming [2024]", "2024-01-14T12:00:00Z", 720, 80000),
    ("Is AMD Better Than Intel?", "2024-01-21T12:00:00Z", 600, 30000),
    ("TOP 10 Tech Gadgets", "2024-01-28T12:00:00Z", 480, 120000),
])

CH2_VIDEOS = _make_videos([
    ("Building My Dream Setup", "2024-01-05T10:00:00Z", 1200, 40000),
    ("Tech Review: New Laptop (2024)", "2024-01-12T10:00:00Z", 800, 60000),
    ("Best Monitors for Coding", "2024-01-19T10:00:00Z", 500, 25000),
], channel_id="UC_other")

CH1_INFO = {"name": "TechChannel", "id": "UC_test"}
CH2_INFO = {"name": "SetupChannel", "id": "UC_other"}


# ===== compare_channels =====

class TestCompareChannels:
    def test_basic_comparison(self):
        result = compare_channels(CH1_VIDEOS, CH2_VIDEOS, CH1_INFO, CH2_INFO)
        assert result["channel_1"]["name"] == "TechChannel"
        assert result["channel_2"]["name"] == "SetupChannel"
        assert result["channel_1"]["total_videos"] == 4
        assert result["channel_2"]["total_videos"] == 3
        assert result["channel_1"]["upload_frequency_per_week"] > 0
        assert result["channel_2"]["avg_duration_seconds"] > 0
        assert 0.0 <= result["topic_overlap"] <= 1.0

    def test_topic_overlap_is_jaccard(self):
        # Same videos should give overlap = 1.0
        result = compare_channels(CH1_VIDEOS, CH1_VIDEOS, CH1_INFO, CH1_INFO)
        assert result["topic_overlap"] == 1.0

    def test_empty_channel(self):
        result = compare_channels([], CH2_VIDEOS, CH1_INFO, CH2_INFO)
        assert result["channel_1"]["total_videos"] == 0
        assert result["channel_1"]["avg_views"] == 0.0
        assert result["channel_1"]["upload_frequency_per_week"] == 0.0
        assert result["topic_overlap"] == 0.0

    def test_both_empty(self):
        result = compare_channels([], [], CH1_INFO, CH2_INFO)
        assert result["channel_1"]["total_videos"] == 0
        assert result["channel_2"]["total_videos"] == 0
        assert result["topic_overlap"] == 0.0


# ===== analyze_hooks =====

class TestAnalyzeHooks:
    def test_basic_hooks(self):
        result = analyze_hooks(CH1_VIDEOS)
        assert result["total_titles"] == 4
        assert result["avg_title_length"] > 0
        assert result["max_title_length"] >= result["min_title_length"]
        # "Is AMD Better Than Intel?" ends with ?
        assert result["question_title_pct"] > 0
        # "2024" and "10" contain digits
        assert result["number_in_title_pct"] > 0
        # "[2024]" has brackets
        assert result["bracket_pct"] > 0
        # "TOP" is all caps
        assert result["caps_word_pct"] > 0

    def test_common_words_excludes_stopwords(self):
        result = analyze_hooks(CH1_VIDEOS)
        words = [w["word"] for w in result["common_words"]]
        # "the", "a", "in", "for" should not appear
        for sw in ["the", "in", "for", "is"]:
            assert sw not in words

    def test_empty_videos(self):
        result = analyze_hooks([])
        assert result["total_titles"] == 0
        assert result["avg_title_length"] == 0.0
        assert result["common_words"] == []
        assert result["top_patterns"] == []

    def test_missing_title_field(self):
        videos = [{"id": "v1"}, {"id": "v2", "title": "Hello World Test"}]
        result = analyze_hooks(videos)
        assert result["total_titles"] == 1

    def test_patterns_sorted_by_count(self):
        # All titles have numbers, only some have questions
        videos = _make_videos([
            ("Top 10 Things", "2024-01-01"),
            ("5 Best Tips", "2024-01-02"),
            ("Why 3 Matters?", "2024-01-03"),
        ])
        result = analyze_hooks(videos)
        assert result["number_in_title_pct"] == 100.0
        # number pattern should be first in top_patterns
        assert result["top_patterns"][0]["pattern"] == "number"


# ===== analyze_upload_schedule =====

class TestAnalyzeUploadSchedule:
    def test_basic_schedule(self):
        result = analyze_upload_schedule(CH1_VIDEOS)
        assert result["total_videos"] == 4
        assert result["videos_per_week"] > 0
        assert sum(result["day_of_week"].values()) == 4
        assert "Monday" in result["day_of_week"]

    def test_longest_gap(self):
        videos = _make_videos([
            ("Video 1", "2024-01-01"),
            ("Video 2", "2024-01-03"),
            ("Video 3", "2024-02-01"),  # 29-day gap
        ])
        result = analyze_upload_schedule(videos)
        assert result["longest_gap_days"] == 29

    def test_streak_consecutive_weeks(self):
        # 4 consecutive weeks
        videos = _make_videos([
            ("W1", "2024-01-01"),
            ("W2", "2024-01-08"),
            ("W3", "2024-01-15"),
            ("W4", "2024-01-22"),
        ])
        result = analyze_upload_schedule(videos)
        assert result["longest_streak_weeks"] >= 4

    def test_streak_across_year_boundary(self):
        """ISO week streak must work across Dec→Jan year boundary.

        This is the regression test for the strptime→fromisocalendar fix.
        Dec 23 2024 = ISO week 2024-W52, Dec 30 2024 = ISO week 2025-W01,
        Jan 6 2025 = ISO week 2025-W02.
        """
        videos = _make_videos([
            ("Dec week", "2024-12-23"),   # ISO 2024-W52
            ("Year boundary", "2024-12-30"),  # ISO 2025-W01
            ("Jan week", "2025-01-06"),   # ISO 2025-W02
            ("Jan week 2", "2025-01-13"), # ISO 2025-W03
        ])
        result = analyze_upload_schedule(videos)
        # All 4 weeks are consecutive ISO weeks
        assert result["longest_streak_weeks"] == 4

    def test_empty_videos(self):
        result = analyze_upload_schedule([])
        assert result["total_videos"] == 0
        assert result["videos_per_week"] == 0.0
        assert result["longest_gap_days"] == 0
        assert result["longest_streak_weeks"] == 0

    def test_single_video(self):
        videos = _make_videos([("Solo", "2024-06-15")])
        result = analyze_upload_schedule(videos)
        assert result["total_videos"] == 1
        assert result["videos_per_week"] == 0.0
        assert result["longest_gap_days"] == 0
        assert result["longest_streak_weeks"] == 1

    def test_missing_date_field(self):
        videos = [
            {"id": "v1", "title": "A"},
            {"id": "v2", "title": "B", "published_at": "2024-01-10T00:00:00Z"},
        ]
        result = analyze_upload_schedule(videos)
        assert result["total_videos"] == 1


# ===== find_content_gaps =====

class TestFindContentGaps:
    def test_basic_gaps(self):
        result = find_content_gaps(CH1_VIDEOS)
        assert result["total_topics"] > 0
        assert isinstance(result["low_frequency_topics"], list)
        assert "uncovered_topics" not in result  # no reference given

    def test_with_reference_topics(self):
        reference = ["gaming", "streaming", "keyboards", "networking"]
        result = find_content_gaps(CH1_VIDEOS, reference_topics=reference)
        assert "uncovered_topics" in result
        # "gaming" appears in "Best GPUs for Gaming"
        assert "gaming" not in result["uncovered_topics"]
        # "keyboards" and "networking" are not in any title
        assert "keyboards" in result["uncovered_topics"]
        assert "networking" in result["uncovered_topics"]

    def test_empty_videos(self):
        result = find_content_gaps([])
        assert result["total_topics"] == 0
        assert result["low_frequency_topics"] == []

    def test_empty_videos_with_reference(self):
        result = find_content_gaps([], reference_topics=["python", "rust"])
        assert result["uncovered_topics"] == ["python", "rust"]

    def test_low_frequency_detection(self):
        videos = _make_videos([
            ("Python Tutorial Basics", "2024-01-01"),
            ("Python Advanced Guide", "2024-01-02"),
            ("Python Web Framework", "2024-01-03"),
            ("Rust Getting Started", "2024-01-04"),  # rust appears once
        ])
        result = find_content_gaps(videos)
        # "rust" mentioned once = low frequency
        assert "rust" in result["low_frequency_topics"]
        # "python" mentioned 3 times = not low frequency
        assert "python" not in result["low_frequency_topics"]
