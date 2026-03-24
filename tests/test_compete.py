"""Tests for Tier 4: Competitive Analysis commands (compare, hooks)."""

import json

import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock

from ytcli.cli import cli
from ytcli.core import db
from tests.conftest import parse_json


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def tmp_data_dir(tmp_path):
    d = str(tmp_path / "ytcli_test")
    db.init_db(d)
    return d


def seed_two_channels(data_dir: str):
    """Seed DB with 2 channels and videos for each."""
    conn = db.get_connection(data_dir)
    db.upsert_channel(conn, {
        "id": "UC_AAA",
        "handle": "@alpha",
        "name": "Alpha Channel",
        "subscriber_count": 100000,
        "video_count": 3,
    })
    db.upsert_channel(conn, {
        "id": "UC_BBB",
        "handle": "@beta",
        "name": "Beta Channel",
        "subscriber_count": 50000,
        "video_count": 2,
    })
    for i, (vid_id, title, views, dur) in enumerate([
        ("a1", "10 Python Tips You Need", 50000, 600),
        ("a2", "Why I Switched to Rust", 120000, 900),
        ("a3", "How to Build a CLI (Tutorial)", 30000, 1200),
    ]):
        db.upsert_video(conn, {
            "id": vid_id,
            "channel_id": "UC_AAA",
            "title": title,
            "view_count": views,
            "duration_seconds": dur,
            "published_at": f"2025-01-{10 + i:02d}",
        })
    for i, (vid_id, title, views, dur) in enumerate([
        ("b1", "JavaScript in 2025", 80000, 480),
        ("b2", "React vs Vue — Which Is Better?", 200000, 720),
    ]):
        db.upsert_video(conn, {
            "id": vid_id,
            "channel_id": "UC_BBB",
            "title": title,
            "view_count": views,
            "duration_seconds": dur,
            "published_at": f"2025-02-{5 + i:02d}",
        })
    conn.close()


def seed_one_channel(data_dir: str):
    """Seed DB with 1 channel and videos with varied title patterns."""
    conn = db.get_connection(data_dir)
    db.upsert_channel(conn, {
        "id": "UC_AAA",
        "handle": "@alpha",
        "name": "Alpha Channel",
    })
    videos = [
        ("v1", "10 Python Tips You NEED to Know", 50000),
        ("v2", "Why I Quit My Job (Story Time)", 120000),
        ("v3", "How to Build a CLI?", 30000),
        ("v4", "React Tutorial for Beginners [2025]", 80000),
        ("v5", "5 Mistakes Every Developer Makes", 60000),
    ]
    for i, (vid_id, title, views) in enumerate(videos):
        db.upsert_video(conn, {
            "id": vid_id,
            "channel_id": "UC_AAA",
            "title": title,
            "view_count": views,
            "published_at": f"2025-01-{10 + i:02d}",
        })
    conn.close()


# --- Compare command ---


FAKE_COMPARISON = {
    "channel_1": {
        "name": "Alpha Channel",
        "avg_views": 66666,
        "avg_duration": 900,
        "upload_frequency": 1.5,
        "title_avg_length": 28,
    },
    "channel_2": {
        "name": "Beta Channel",
        "avg_views": 140000,
        "avg_duration": 600,
        "upload_frequency": 2.0,
        "title_avg_length": 25,
    },
    "topic_overlap": 0.15,
}


class TestCompare:
    @patch("ytcli.commands.compete.analyzer")
    def test_compare_returns_both_channels(self, mock_analyzer, runner, tmp_data_dir):
        """compare returns JSON with comparison data for both channels."""
        seed_two_channels(tmp_data_dir)
        mock_analyzer.compare_channels.return_value = FAKE_COMPARISON

        result = runner.invoke(cli, [
            "--data-dir", tmp_data_dir, "compare", "@alpha", "@beta",
        ])
        assert result.exit_code == 0, f"output: {result.output}"
        data = parse_json(result.output)
        assert data["ok"] is True
        assert data["command"] == "compare"
        assert "channel_1" in data["data"]
        assert "channel_2" in data["data"]
        assert data["data"]["channel_1"]["name"] == "Alpha Channel"
        assert data["data"]["channel_2"]["name"] == "Beta Channel"

    @patch("ytcli.commands.compete.analyzer")
    def test_compare_calls_analyzer_with_correct_args(self, mock_analyzer, runner, tmp_data_dir):
        """compare passes videos and channel info to analyzer."""
        seed_two_channels(tmp_data_dir)
        mock_analyzer.compare_channels.return_value = FAKE_COMPARISON

        runner.invoke(cli, [
            "--data-dir", tmp_data_dir, "compare", "@alpha", "@beta",
        ])

        mock_analyzer.compare_channels.assert_called_once()
        args = mock_analyzer.compare_channels.call_args
        ch1_vids, ch2_vids, ch1_info, ch2_info = args[0]
        assert len(ch1_vids) == 3
        assert len(ch2_vids) == 2
        assert ch1_info["handle"] == "@alpha"
        assert ch2_info["handle"] == "@beta"

    @patch("ytcli.commands.compete.analyzer")
    def test_compare_channel_not_found(self, mock_analyzer, runner, tmp_data_dir):
        """compare errors when a channel is not in the DB."""
        seed_two_channels(tmp_data_dir)

        result = runner.invoke(cli, [
            "--data-dir", tmp_data_dir, "compare", "@alpha", "@nonexistent",
        ])
        data = parse_json(result.output)
        assert data["ok"] is False
        assert "not found" in data["error"].lower()

    @patch("ytcli.commands.compete.analyzer")
    def test_compare_first_channel_not_found(self, mock_analyzer, runner, tmp_data_dir):
        """compare errors when the first channel is not in the DB."""
        result = runner.invoke(cli, [
            "--data-dir", tmp_data_dir, "compare", "@ghost", "@beta",
        ])
        data = parse_json(result.output)
        assert data["ok"] is False
        assert "not found" in data["error"].lower()


# --- Hooks command ---


FAKE_HOOKS_ANALYSIS = {
    "total_videos": 5,
    "avg_title_length": 32,
    "question_titles_pct": 20.0,
    "number_usage_pct": 40.0,
    "bracket_usage_pct": 20.0,
    "parenthesis_usage_pct": 20.0,
    "common_words": ["python", "build", "tutorial"],
}


class TestHooks:
    @patch("ytcli.commands.compete.analyzer")
    def test_hooks_returns_analysis(self, mock_analyzer, runner, tmp_data_dir):
        """hooks returns JSON with hook analysis data."""
        seed_one_channel(tmp_data_dir)
        mock_analyzer.analyze_hooks.return_value = FAKE_HOOKS_ANALYSIS

        result = runner.invoke(cli, [
            "--data-dir", tmp_data_dir, "hooks", "@alpha",
        ])
        assert result.exit_code == 0, f"output: {result.output}"
        data = parse_json(result.output)
        assert data["ok"] is True
        assert data["command"] == "hooks"
        assert data["data"]["total_videos"] == 5
        assert data["data"]["avg_title_length"] == 32
        assert "common_words" in data["data"]

    @patch("ytcli.commands.compete.analyzer")
    def test_hooks_limit_flag(self, mock_analyzer, runner, tmp_data_dir):
        """hooks --limit restricts videos passed to analyzer."""
        seed_one_channel(tmp_data_dir)
        mock_analyzer.analyze_hooks.return_value = FAKE_HOOKS_ANALYSIS

        runner.invoke(cli, [
            "--data-dir", tmp_data_dir, "hooks", "@alpha", "--limit", "3",
        ])

        mock_analyzer.analyze_hooks.assert_called_once()
        videos_arg = mock_analyzer.analyze_hooks.call_args[0][0]
        assert len(videos_arg) == 3

    @patch("ytcli.commands.compete.analyzer")
    def test_hooks_default_limit(self, mock_analyzer, runner, tmp_data_dir):
        """hooks default limit is 20 (all 5 videos returned since < 20)."""
        seed_one_channel(tmp_data_dir)
        mock_analyzer.analyze_hooks.return_value = FAKE_HOOKS_ANALYSIS

        runner.invoke(cli, [
            "--data-dir", tmp_data_dir, "hooks", "@alpha",
        ])

        videos_arg = mock_analyzer.analyze_hooks.call_args[0][0]
        assert len(videos_arg) == 5  # all 5, since 5 < default 20

    @patch("ytcli.commands.compete.analyzer")
    def test_hooks_channel_not_found(self, mock_analyzer, runner, tmp_data_dir):
        """hooks errors when channel is not in the DB."""
        result = runner.invoke(cli, [
            "--data-dir", tmp_data_dir, "hooks", "@nonexistent",
        ])
        data = parse_json(result.output)
        assert data["ok"] is False
        assert "not found" in data["error"].lower()


# --- Gaps command ---


FAKE_GAPS_ANALYSIS = {
    "total_topics": 15,
    "low_frequency_topics": ["rust", "cli", "tutorial"],
}


class TestGaps:
    @patch("ytcli.commands.compete.analyzer")
    def test_gaps_returns_analysis(self, mock_analyzer, runner, tmp_data_dir):
        """gaps returns JSON with content gap analysis."""
        seed_one_channel(tmp_data_dir)
        mock_analyzer.find_content_gaps.return_value = FAKE_GAPS_ANALYSIS

        result = runner.invoke(cli, [
            "--data-dir", tmp_data_dir, "gaps", "@alpha",
        ])
        assert result.exit_code == 0, f"output: {result.output}"
        data = parse_json(result.output)
        assert data["ok"] is True
        assert data["command"] == "gaps"
        assert data["data"]["total_topics"] == 15
        assert "low_frequency_topics" in data["data"]

    @patch("ytcli.commands.compete.analyzer")
    def test_gaps_passes_videos_to_analyzer(self, mock_analyzer, runner, tmp_data_dir):
        """gaps passes all channel videos to analyzer.find_content_gaps."""
        seed_one_channel(tmp_data_dir)
        mock_analyzer.find_content_gaps.return_value = FAKE_GAPS_ANALYSIS

        runner.invoke(cli, [
            "--data-dir", tmp_data_dir, "gaps", "@alpha",
        ])

        mock_analyzer.find_content_gaps.assert_called_once()
        videos_arg = mock_analyzer.find_content_gaps.call_args[0][0]
        assert len(videos_arg) == 5

    @patch("ytcli.commands.compete.analyzer")
    def test_gaps_channel_not_found(self, mock_analyzer, runner, tmp_data_dir):
        """gaps errors when channel is not in the DB."""
        result = runner.invoke(cli, [
            "--data-dir", tmp_data_dir, "gaps", "@nonexistent",
        ])
        data = parse_json(result.output)
        assert data["ok"] is False
        assert "not found" in data["error"].lower()


# --- Calendar command ---


def seed_channel_with_dates(data_dir: str):
    """Seed DB with 1 channel and videos across different dates/days."""
    conn = db.get_connection(data_dir)
    db.upsert_channel(conn, {
        "id": "UC_CCC",
        "handle": "@gamma",
        "name": "Gamma Channel",
    })
    dates = [
        "2025-01-06T10:00:00Z",  # Monday
        "2025-01-08T14:00:00Z",  # Wednesday
        "2025-01-13T09:00:00Z",  # Monday
        "2025-01-15T16:00:00Z",  # Wednesday
        "2025-01-20T11:00:00Z",  # Monday
        "2025-02-03T12:00:00Z",  # Monday (gap)
    ]
    for i, date in enumerate(dates):
        db.upsert_video(conn, {
            "id": f"c{i}",
            "channel_id": "UC_CCC",
            "title": f"Video {i + 1}",
            "published_at": date,
            "view_count": 1000 * (i + 1),
        })
    conn.close()


FAKE_SCHEDULE_ANALYSIS = {
    "total_videos": 6,
    "day_of_week": {
        "Monday": 4, "Tuesday": 0, "Wednesday": 2,
        "Thursday": 0, "Friday": 0, "Saturday": 0, "Sunday": 0,
    },
    "videos_per_week": 1.5,
    "longest_streak_weeks": 3,
    "longest_gap_days": 14,
}


class TestCalendar:
    @patch("ytcli.commands.compete.analyzer")
    def test_calendar_returns_schedule(self, mock_analyzer, runner, tmp_data_dir):
        """calendar returns JSON with upload schedule analysis."""
        seed_channel_with_dates(tmp_data_dir)
        mock_analyzer.analyze_upload_schedule.return_value = FAKE_SCHEDULE_ANALYSIS

        result = runner.invoke(cli, [
            "--data-dir", tmp_data_dir, "calendar", "@gamma",
        ])
        assert result.exit_code == 0, f"output: {result.output}"
        data = parse_json(result.output)
        assert data["ok"] is True
        assert data["command"] == "calendar"
        assert data["data"]["total_videos"] == 6
        assert "day_of_week" in data["data"]
        assert data["data"]["videos_per_week"] == 1.5
        assert data["data"]["longest_gap_days"] == 14

    @patch("ytcli.commands.compete.analyzer")
    def test_calendar_passes_videos_to_analyzer(self, mock_analyzer, runner, tmp_data_dir):
        """calendar passes channel videos to analyzer.analyze_upload_schedule."""
        seed_channel_with_dates(tmp_data_dir)
        mock_analyzer.analyze_upload_schedule.return_value = FAKE_SCHEDULE_ANALYSIS

        runner.invoke(cli, [
            "--data-dir", tmp_data_dir, "calendar", "@gamma",
        ])

        mock_analyzer.analyze_upload_schedule.assert_called_once()
        videos_arg = mock_analyzer.analyze_upload_schedule.call_args[0][0]
        assert len(videos_arg) == 6

    @patch("ytcli.commands.compete.analyzer")
    def test_calendar_channel_not_found(self, mock_analyzer, runner, tmp_data_dir):
        """calendar errors when channel is not in the DB."""
        result = runner.invoke(cli, [
            "--data-dir", tmp_data_dir, "calendar", "@nonexistent",
        ])
        data = parse_json(result.output)
        assert data["ok"] is False
        assert "not found" in data["error"].lower()


# --- Niche command ---


FAKE_SEARCH_RESULTS = [
    {"video_id": "v1", "title": "Python Tips", "channel": "CodePro", "published_at": "2025-01-01", "thumbnail_url": ""},
    {"video_id": "v2", "title": "Python Tricks", "channel": "CodePro", "published_at": "2025-01-05", "thumbnail_url": ""},
    {"video_id": "v3", "title": "Python Basics", "channel": "CodePro", "published_at": "2025-01-10", "thumbnail_url": ""},
    {"video_id": "v4", "title": "Learn Python Fast", "channel": "DevGuru", "published_at": "2025-02-01", "thumbnail_url": ""},
    {"video_id": "v5", "title": "Python for Data Science", "channel": "DevGuru", "published_at": "2025-02-05", "thumbnail_url": ""},
    {"video_id": "v6", "title": "Python Tutorial", "channel": "TechNerd", "published_at": "2025-03-01", "thumbnail_url": ""},
]


class TestNiche:
    @patch("ytcli.commands.compete.api")
    def test_niche_groups_by_channel_and_ranks(self, mock_api, runner, tmp_data_dir):
        """niche groups search results by channel and ranks by frequency."""
        conn = db.get_connection(tmp_data_dir)
        db.set_config(conn, "api_key", "fake-key-123")
        conn.close()

        mock_client = MagicMock()
        mock_api.get_api_client.return_value = mock_client
        mock_api.search_youtube.return_value = FAKE_SEARCH_RESULTS

        result = runner.invoke(cli, [
            "--data-dir", tmp_data_dir, "niche", "python tutorial",
        ])
        assert result.exit_code == 0, f"output: {result.output}"
        data = parse_json(result.output)
        assert data["ok"] is True
        assert data["command"] == "niche"
        assert data["data"]["query"] == "python tutorial"

        channels = data["data"]["channels"]
        # CodePro has 3 videos, DevGuru has 2, TechNerd has 1 — ranked by frequency
        assert channels[0]["name"] == "CodePro"
        assert channels[0]["video_count"] == 3
        assert channels[1]["name"] == "DevGuru"
        assert channels[1]["video_count"] == 2
        assert channels[2]["name"] == "TechNerd"
        assert channels[2]["video_count"] == 1

        # Each channel should have sample_videos
        assert len(channels[0]["sample_videos"]) == 3
        assert "Python Tips" in channels[0]["sample_videos"]

    @patch("ytcli.commands.compete.api")
    def test_niche_limit_flag(self, mock_api, runner, tmp_data_dir):
        """niche --limit restricts number of channels returned."""
        conn = db.get_connection(tmp_data_dir)
        db.set_config(conn, "api_key", "fake-key-123")
        conn.close()

        mock_client = MagicMock()
        mock_api.get_api_client.return_value = mock_client
        mock_api.search_youtube.return_value = FAKE_SEARCH_RESULTS

        result = runner.invoke(cli, [
            "--data-dir", tmp_data_dir, "niche", "python tutorial", "--limit", "2",
        ])
        data = parse_json(result.output)
        assert data["ok"] is True
        assert len(data["data"]["channels"]) == 2
        assert data["data"]["count"] == 2

    @patch("ytcli.commands.compete.api")
    def test_niche_missing_api_key(self, mock_api, runner, tmp_data_dir):
        """niche errors when no API key is configured."""
        # No api_key set in config
        result = runner.invoke(cli, [
            "--data-dir", tmp_data_dir, "niche", "python tutorial",
        ])
        data = parse_json(result.output)
        assert data["ok"] is False
        assert "api" in data["error"].lower() or "key" in data["error"].lower()
