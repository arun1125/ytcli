"""Tests for Tier 2: Channel Intelligence commands."""

import json
import subprocess

import pytest
from click.testing import CliRunner
from unittest.mock import patch

from ytcli.cli import cli
from ytcli.core import db


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def tmp_data_dir(tmp_path):
    d = str(tmp_path / "ytcli_test")
    db.init_db(d)
    return d


def parse_json(output: str) -> dict:
    """Extract JSON from CLI output, skipping any non-JSON lines."""
    for line in output.strip().split("\n"):
        line = line.strip()
        if line.startswith("{"):
            return json.loads(line)
    raise ValueError(f"No JSON found in output: {output!r}")


FAKE_CHANNEL_VIDEOS = [
    {
        "id": "vid001",
        "title": "Best Phones 2025",
        "url": "https://www.youtube.com/watch?v=vid001",
        "duration": 720,
        "view_count": 5000000,
        "channel": "MKBHD",
        "channel_id": "UCBJycsmduvYEL83R_U4JriQ",
        "upload_date": "20250301",
    },
    {
        "id": "vid002",
        "title": "Galaxy S25 Ultra Review",
        "url": "https://www.youtube.com/watch?v=vid002",
        "duration": 960,
        "view_count": 8000000,
        "channel": "MKBHD",
        "channel_id": "UCBJycsmduvYEL83R_U4JriQ",
        "upload_date": "20250215",
    },
    {
        "id": "vid003",
        "title": "iPhone 17 Pro — What to Expect",
        "url": "https://www.youtube.com/watch?v=vid003",
        "duration": 540,
        "view_count": 12000000,
        "channel": "MKBHD",
        "channel_id": "UCBJycsmduvYEL83R_U4JriQ",
        "upload_date": "20250110",
    },
]


class TestScan:
    @patch("ytcli.commands.channel.scraper")
    def test_scan_creates_channel_and_videos(self, mock_scraper, runner, tmp_data_dir):
        """scan command creates channel record and video records in DB."""
        mock_scraper.get_channel_videos.return_value = FAKE_CHANNEL_VIDEOS
        result = runner.invoke(cli, ["--data-dir", tmp_data_dir, "scan", "@mkbhd"])
        assert result.exit_code == 0, f"output: {result.output}"
        data = parse_json(result.output)
        assert data["ok"] is True
        assert data["command"] == "scan"
        assert data["data"]["channel"] == "MKBHD"
        assert data["data"]["videos_found"] == 3
        assert data["data"]["channel_id"] == "UCBJycsmduvYEL83R_U4JriQ"
        assert data["data"]["handle"] == "@mkbhd"

        # Verify DB records
        conn = db.get_connection(tmp_data_dir)
        ch = conn.execute(
            "SELECT * FROM channels WHERE id = ?", ("UCBJycsmduvYEL83R_U4JriQ",)
        ).fetchone()
        assert ch is not None
        assert ch["name"] == "MKBHD"
        assert ch["handle"] == "@mkbhd"
        assert ch["scanned_at"] is not None

        vids = conn.execute(
            "SELECT * FROM videos WHERE channel_id = ?", ("UCBJycsmduvYEL83R_U4JriQ",)
        ).fetchall()
        assert len(vids) == 3
        conn.close()

    @patch("ytcli.commands.channel.scraper")
    def test_scan_with_limit(self, mock_scraper, runner, tmp_data_dir):
        """scan --limit passes through to scraper."""
        mock_scraper.get_channel_videos.return_value = FAKE_CHANNEL_VIDEOS[:1]
        result = runner.invoke(
            cli, ["--data-dir", tmp_data_dir, "scan", "--limit", "1", "@mkbhd"]
        )
        assert result.exit_code == 0
        data = parse_json(result.output)
        assert data["ok"] is True
        assert data["data"]["videos_found"] == 1
        mock_scraper.get_channel_videos.assert_called_once_with(
            "https://www.youtube.com/@mkbhd", limit=1
        )

    @patch("ytcli.commands.channel.scraper")
    def test_scan_handles_full_url(self, mock_scraper, runner, tmp_data_dir):
        """scan accepts a full URL instead of just a handle."""
        mock_scraper.get_channel_videos.return_value = FAKE_CHANNEL_VIDEOS[:1]
        url = "https://www.youtube.com/@mkbhd"
        result = runner.invoke(cli, ["--data-dir", tmp_data_dir, "scan", url])
        assert result.exit_code == 0
        mock_scraper.get_channel_videos.assert_called_once_with(url, limit=None)

    @patch("ytcli.commands.channel.scraper")
    def test_scan_error_on_scraper_failure(self, mock_scraper, runner, tmp_data_dir):
        """scan returns error JSON when scraper fails."""
        mock_scraper.get_channel_videos.side_effect = subprocess.CalledProcessError(
            1, "yt-dlp", stderr="ERROR: Unable to download channel page"
        )
        result = runner.invoke(cli, ["--data-dir", tmp_data_dir, "scan", "@nonexistent"])
        data = parse_json(result.output)
        assert data["ok"] is False
        assert data["command"] == "scan"
        assert "error" in data

    @patch("ytcli.commands.channel.scraper")
    def test_scan_error_on_empty_result(self, mock_scraper, runner, tmp_data_dir):
        """scan returns error when scraper returns empty list."""
        mock_scraper.get_channel_videos.return_value = []
        result = runner.invoke(
            cli, ["--data-dir", tmp_data_dir, "scan", "@emptychannel"]
        )
        data = parse_json(result.output)
        assert data["ok"] is False
        assert data["command"] == "scan"

    @patch("ytcli.commands.channel.scraper")
    def test_scan_upserts_on_rescan(self, mock_scraper, runner, tmp_data_dir):
        """scan upserts records — rescanning same channel updates, doesn't duplicate."""
        mock_scraper.get_channel_videos.return_value = FAKE_CHANNEL_VIDEOS
        runner.invoke(cli, ["--data-dir", tmp_data_dir, "scan", "@mkbhd"])
        runner.invoke(cli, ["--data-dir", tmp_data_dir, "scan", "@mkbhd"])

        conn = db.get_connection(tmp_data_dir)
        channels_count = conn.execute("SELECT COUNT(*) FROM channels").fetchone()[0]
        videos_count = conn.execute("SELECT COUNT(*) FROM videos").fetchone()[0]
        assert channels_count == 1
        assert videos_count == 3
        conn.close()

    @patch("ytcli.commands.channel.scraper")
    def test_scan_video_fields_stored(self, mock_scraper, runner, tmp_data_dir):
        """scan stores duration, view_count, published_at from flat-playlist."""
        mock_scraper.get_channel_videos.return_value = FAKE_CHANNEL_VIDEOS[:1]
        runner.invoke(cli, ["--data-dir", tmp_data_dir, "scan", "@mkbhd"])

        conn = db.get_connection(tmp_data_dir)
        vid = conn.execute(
            "SELECT * FROM videos WHERE id = ?", ("vid001",)
        ).fetchone()
        assert vid["title"] == "Best Phones 2025"
        assert vid["duration_seconds"] == 720
        assert vid["view_count"] == 5000000
        assert vid["published_at"] is not None
        conn.close()


class TestSearch:
    """Tests for the search command."""

    def _seed_db(self, data_dir):
        """Seed DB with two channels and 3 videos with different titles/descriptions."""
        conn = db.get_connection(data_dir)
        db.upsert_channel(conn, {"id": "UC_AAA", "handle": "@alpha", "name": "Alpha Channel"})
        db.upsert_channel(conn, {"id": "UC_BBB", "handle": "@beta", "name": "Beta Channel"})
        db.upsert_video(conn, {
            "id": "v1", "channel_id": "UC_AAA", "title": "Python Tutorial",
            "description": "Learn Python basics", "published_at": "2025-01-01",
        })
        db.upsert_video(conn, {
            "id": "v2", "channel_id": "UC_AAA", "title": "JavaScript Guide",
            "description": "Deep dive into JS", "published_at": "2025-02-01",
        })
        db.upsert_video(conn, {
            "id": "v3", "channel_id": "UC_BBB", "title": "Rust for Beginners",
            "description": "Python vs Rust comparison", "published_at": "2025-03-01",
        })
        conn.close()

    def test_search_finds_matching_title(self, runner, tmp_data_dir):
        """search returns videos matching title text."""
        self._seed_db(tmp_data_dir)
        result = runner.invoke(cli, ["--data-dir", tmp_data_dir, "search", "JavaScript"])
        assert result.exit_code == 0
        data = parse_json(result.output)
        assert data["ok"] is True
        assert data["command"] == "search"
        assert data["data"]["count"] == 1
        assert data["data"]["results"][0]["id"] == "v2"

    def test_search_finds_matching_description(self, runner, tmp_data_dir):
        """search matches on description text too."""
        self._seed_db(tmp_data_dir)
        # "Python" appears in v1 title and v3 description
        result = runner.invoke(cli, ["--data-dir", tmp_data_dir, "search", "Python"])
        data = parse_json(result.output)
        assert data["ok"] is True
        assert data["data"]["count"] == 2
        ids = {r["id"] for r in data["data"]["results"]}
        assert ids == {"v1", "v3"}

    def test_search_channel_filter(self, runner, tmp_data_dir):
        """search --channel restricts results to one channel."""
        self._seed_db(tmp_data_dir)
        # "Python" matches v1 (UC_AAA) and v3 (UC_BBB), but filter to @alpha
        result = runner.invoke(
            cli, ["--data-dir", tmp_data_dir, "search", "Python", "--channel", "@alpha"]
        )
        data = parse_json(result.output)
        assert data["ok"] is True
        assert data["data"]["count"] == 1
        assert data["data"]["results"][0]["id"] == "v1"

    def test_search_no_results(self, runner, tmp_data_dir):
        """search returns empty list when no videos match."""
        self._seed_db(tmp_data_dir)
        result = runner.invoke(cli, ["--data-dir", tmp_data_dir, "search", "Haskell"])
        data = parse_json(result.output)
        assert data["ok"] is True
        assert data["data"]["count"] == 0
        assert data["data"]["results"] == []

    def test_search_channel_not_found(self, runner, tmp_data_dir):
        """search --channel with unknown channel returns error."""
        self._seed_db(tmp_data_dir)
        result = runner.invoke(
            cli, ["--data-dir", tmp_data_dir, "search", "Python", "--channel", "@nonexistent"]
        )
        data = parse_json(result.output)
        assert data["ok"] is False
        assert "not found" in data["error"].lower()


class TestRefresh:
    """Tests for the refresh command — re-scan channels for new uploads."""

    def _seed_channel_and_videos(self, data_dir):
        """Seed DB with a channel and 2 existing videos with old scanned_at."""
        conn = db.get_connection(data_dir)
        db.upsert_channel(conn, {
            "id": "UCBJycsmduvYEL83R_U4JriQ",
            "handle": "@mkbhd",
            "name": "MKBHD",
            "scanned_at": "2025-01-01T00:00:00+00:00",
        })
        db.upsert_video(conn, {
            "id": "vid001",
            "channel_id": "UCBJycsmduvYEL83R_U4JriQ",
            "title": "Best Phones 2025",
            "view_count": 5000000,
            "scraped_at": "2025-01-01T00:00:00+00:00",
        })
        db.upsert_video(conn, {
            "id": "vid002",
            "channel_id": "UCBJycsmduvYEL83R_U4JriQ",
            "title": "Galaxy S25 Ultra Review",
            "view_count": 8000000,
            "scraped_at": "2025-01-01T00:00:00+00:00",
        })
        conn.close()

    @patch("ytcli.commands.channel.scraper")
    def test_refresh_specific_channel(self, mock_scraper, runner, tmp_data_dir):
        """refresh CHANNEL re-scans that channel and adds new videos."""
        self._seed_channel_and_videos(tmp_data_dir)

        mock_scraper.get_channel_videos.return_value = FAKE_CHANNEL_VIDEOS
        result = runner.invoke(cli, ["--data-dir", tmp_data_dir, "refresh", "@mkbhd"])
        assert result.exit_code == 0, f"output: {result.output}"
        data = parse_json(result.output)
        assert data["ok"] is True
        assert data["command"] == "refresh"
        assert data["data"]["channels_refreshed"] == 1
        assert data["data"]["new_videos"] == 1
        assert data["data"]["updated_videos"] == 2

        # Verify new video in DB
        conn = db.get_connection(tmp_data_dir)
        vid = conn.execute("SELECT * FROM videos WHERE id = ?", ("vid003",)).fetchone()
        assert vid is not None
        assert vid["title"] == "iPhone 17 Pro — What to Expect"

        # Verify scanned_at updated
        ch = conn.execute(
            "SELECT * FROM channels WHERE id = ?", ("UCBJycsmduvYEL83R_U4JriQ",)
        ).fetchone()
        assert ch["scanned_at"] > "2025-01-01T00:00:00+00:00"
        conn.close()

    @patch("ytcli.commands.channel.scraper")
    def test_refresh_all_channels(self, mock_scraper, runner, tmp_data_dir):
        """refresh with no argument refreshes all tracked channels."""
        self._seed_channel_and_videos(tmp_data_dir)

        # Add a second channel
        conn = db.get_connection(tmp_data_dir)
        db.upsert_channel(conn, {
            "id": "UC_second",
            "handle": "@dave2d",
            "name": "Dave2D",
            "scanned_at": "2025-01-01T00:00:00+00:00",
        })
        db.upsert_video(conn, {
            "id": "dvid001",
            "channel_id": "UC_second",
            "title": "Old Dave Video",
            "view_count": 100,
            "scraped_at": "2025-01-01T00:00:00+00:00",
        })
        conn.close()

        dave_videos = [{
            "id": "dvid001",
            "title": "Old Dave Video",
            "url": "https://www.youtube.com/watch?v=dvid001",
            "duration": 300,
            "view_count": 200,
            "channel": "Dave2D",
            "channel_id": "UC_second",
            "upload_date": "20250301",
        }, {
            "id": "dvid002",
            "title": "New Dave Video",
            "url": "https://www.youtube.com/watch?v=dvid002",
            "duration": 600,
            "view_count": 500,
            "channel": "Dave2D",
            "channel_id": "UC_second",
            "upload_date": "20250315",
        }]
        # db.get_channels() returns ordered by name: Dave2D < MKBHD
        mock_scraper.get_channel_videos.side_effect = [dave_videos, FAKE_CHANNEL_VIDEOS]

        result = runner.invoke(cli, ["--data-dir", tmp_data_dir, "refresh"])
        assert result.exit_code == 0, f"output: {result.output}"
        data = parse_json(result.output)
        assert data["ok"] is True
        assert data["data"]["channels_refreshed"] == 2
        # Dave2D: 1 new (dvid002) + MKBHD: 1 new (vid003) = 2 new
        assert data["data"]["new_videos"] == 2

    @patch("ytcli.commands.channel.scraper")
    def test_refresh_existing_videos_updated(self, mock_scraper, runner, tmp_data_dir):
        """refresh updates view_count on existing videos."""
        self._seed_channel_and_videos(tmp_data_dir)

        updated_videos = [
            {**FAKE_CHANNEL_VIDEOS[0], "view_count": 6000000},
            {**FAKE_CHANNEL_VIDEOS[1], "view_count": 9000000},
        ]
        mock_scraper.get_channel_videos.return_value = updated_videos

        runner.invoke(cli, ["--data-dir", tmp_data_dir, "refresh", "@mkbhd"])

        conn = db.get_connection(tmp_data_dir)
        vid = conn.execute("SELECT * FROM videos WHERE id = ?", ("vid001",)).fetchone()
        assert vid["view_count"] == 6000000
        conn.close()

    def test_refresh_error_no_channels(self, runner, tmp_data_dir):
        """refresh with no channels tracked returns error."""
        result = runner.invoke(cli, ["--data-dir", tmp_data_dir, "refresh"])
        data = parse_json(result.output)
        assert data["ok"] is False
        assert data["command"] == "refresh"

    @patch("ytcli.commands.channel.scraper")
    def test_refresh_updates_scanned_at(self, mock_scraper, runner, tmp_data_dir):
        """refresh updates scanned_at timestamp on channel."""
        self._seed_channel_and_videos(tmp_data_dir)
        mock_scraper.get_channel_videos.return_value = FAKE_CHANNEL_VIDEOS[:2]

        runner.invoke(cli, ["--data-dir", tmp_data_dir, "refresh", "@mkbhd"])

        conn = db.get_connection(tmp_data_dir)
        ch = conn.execute(
            "SELECT * FROM channels WHERE id = ?", ("UCBJycsmduvYEL83R_U4JriQ",)
        ).fetchone()
        assert ch["scanned_at"] > "2025-01-01T00:00:00+00:00"
        conn.close()
