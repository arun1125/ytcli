"""Tests for Tier 3 analytics commands."""

import json

import pytest
from click.testing import CliRunner

from ytcli.cli import cli


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def tmp_data_dir(tmp_path):
    return str(tmp_path / "ytcli_test")


@pytest.fixture
def init_db(runner, tmp_data_dir):
    """Initialize DB before tests that need it."""
    runner.invoke(cli, ["--data-dir", tmp_data_dir, "init"])
    return tmp_data_dir


class TestAuth:
    def test_auth_set_api_key(self, runner, init_db):
        result = runner.invoke(cli, ["--data-dir", init_db, "auth", "--api-key", "TESTKEY123"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["ok"] is True
        assert data["command"] == "auth"
        assert data["data"]["api_key_set"] is True

        # Verify it's stored: retrieve via config
        result2 = runner.invoke(cli, ["--data-dir", init_db, "config", "api_key"])
        data2 = json.loads(result2.output)
        assert data2["data"]["value"] == "TESTKEY123"

    def test_auth_no_key_configured(self, runner, init_db):
        """auth without args and no key stored shows 'no API key configured'."""
        result = runner.invoke(cli, ["--data-dir", init_db, "auth"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["ok"] is True
        assert data["data"]["api_key_set"] is False
        assert "no api key configured" in data["data"]["status"].lower()

    def test_auth_shows_status_when_key_exists(self, runner, init_db):
        """auth without args but key exists shows status."""
        runner.invoke(cli, ["--data-dir", init_db, "auth", "--api-key", "MYKEY456"])
        result = runner.invoke(cli, ["--data-dir", init_db, "auth"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["ok"] is True
        assert data["data"]["api_key_set"] is True
        # Should show masked key
        assert "***" in data["data"]["status"]
        assert "MYKEY456" not in data["data"]["status"]


class TestStats:
    def test_stats_returns_channel_data(self, runner, init_db):
        """Mock api.get_channel_stats(), assert JSON has subscriber_count, view_count, video_count, name."""
        from unittest.mock import patch

        # Set API key first
        runner.invoke(cli, ["--data-dir", init_db, "auth", "--api-key", "TESTKEY"])

        mock_stats = {
            "channel_id": "UC123",
            "name": "Test Channel",
            "description": "A test channel",
            "thumbnail_url": "https://example.com/thumb.jpg",
            "subscriber_count": 10000,
            "view_count": 500000,
            "video_count": 42,
        }

        with patch("ytcli.commands.analytics.api.get_api_client") as mock_client, \
             patch("ytcli.commands.analytics.api.get_channel_stats", return_value=mock_stats):
            result = runner.invoke(cli, ["--data-dir", init_db, "stats", "@testchannel"])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["ok"] is True
        assert data["command"] == "stats"
        assert data["data"]["subscriber_count"] == 10000
        assert data["data"]["view_count"] == 500000
        assert data["data"]["video_count"] == 42
        assert data["data"]["name"] == "Test Channel"

    def test_stats_missing_api_key(self, runner, init_db):
        """Test missing API key returns clear error."""
        result = runner.invoke(cli, ["--data-dir", init_db, "stats", "@testchannel"])
        data = json.loads(result.output)
        assert data["ok"] is False
        assert "api" in data["error"].lower() or "key" in data["error"].lower()

    def test_stats_channel_not_found(self, runner, init_db):
        """Test channel not found error."""
        from unittest.mock import patch

        runner.invoke(cli, ["--data-dir", init_db, "auth", "--api-key", "TESTKEY"])

        with patch("ytcli.commands.analytics.api.get_api_client"), \
             patch("ytcli.commands.analytics.api.get_channel_stats",
                   side_effect=ValueError("Channel not found: @nonexistent")):
            result = runner.invoke(cli, ["--data-dir", init_db, "stats", "@nonexistent"])

        data = json.loads(result.output)
        assert data["ok"] is False
        assert "not found" in data["error"].lower()

    def test_stats_upserts_channel_in_db(self, runner, init_db):
        """Stats command should update the channel record in DB."""
        from unittest.mock import patch
        from ytcli.core.db import get_connection, get_channel

        runner.invoke(cli, ["--data-dir", init_db, "auth", "--api-key", "TESTKEY"])

        mock_stats = {
            "channel_id": "UC123",
            "name": "Test Channel",
            "description": "A test channel",
            "thumbnail_url": "https://example.com/thumb.jpg",
            "subscriber_count": 10000,
            "view_count": 500000,
            "video_count": 42,
        }

        with patch("ytcli.commands.analytics.api.get_api_client"), \
             patch("ytcli.commands.analytics.api.get_channel_stats", return_value=mock_stats):
            runner.invoke(cli, ["--data-dir", init_db, "stats", "@testchannel"])

        conn = get_connection(init_db)
        ch = get_channel(conn, "UC123")
        conn.close()
        assert ch is not None
        assert ch["name"] == "Test Channel"
        assert ch["subscriber_count"] == 10000


class TestPerformance:
    def test_performance_returns_video_data(self, runner, init_db):
        """Mock api.get_video_stats(), assert JSON has views, likes, comments, engagement_rate."""
        from unittest.mock import patch

        runner.invoke(cli, ["--data-dir", init_db, "auth", "--api-key", "TESTKEY"])

        mock_stats = {
            "video_id": "dQw4w9WgXcQ",
            "title": "Test Video",
            "published_at": "2024-01-01T00:00:00Z",
            "duration": "PT4M30S",
            "view_count": 1000,
            "like_count": 80,
            "comment_count": 20,
        }

        with patch("ytcli.commands.analytics.api.get_api_client"), \
             patch("ytcli.commands.analytics.api.get_video_stats", return_value=mock_stats):
            result = runner.invoke(cli, [
                "--data-dir", init_db, "performance",
                "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            ])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["ok"] is True
        assert data["command"] == "performance"
        assert data["data"]["view_count"] == 1000
        assert data["data"]["like_count"] == 80
        assert data["data"]["comment_count"] == 20
        assert "engagement_rate" in data["data"]

    def test_engagement_rate_calculation(self, runner, init_db):
        """engagement_rate = (likes + comments) / views * 100."""
        from unittest.mock import patch

        runner.invoke(cli, ["--data-dir", init_db, "auth", "--api-key", "TESTKEY"])

        mock_stats = {
            "video_id": "abc123",
            "title": "Test",
            "published_at": "2024-01-01",
            "duration": "PT5M",
            "view_count": 1000,
            "like_count": 80,
            "comment_count": 20,
        }

        with patch("ytcli.commands.analytics.api.get_api_client"), \
             patch("ytcli.commands.analytics.api.get_video_stats", return_value=mock_stats):
            result = runner.invoke(cli, [
                "--data-dir", init_db, "performance",
                "https://www.youtube.com/watch?v=abc123",
            ])

        data = json.loads(result.output)
        # (80 + 20) / 1000 * 100 = 10.0
        assert data["data"]["engagement_rate"] == 10.0

    def test_engagement_rate_zero_views(self, runner, init_db):
        """Zero views should not cause division by zero."""
        from unittest.mock import patch

        runner.invoke(cli, ["--data-dir", init_db, "auth", "--api-key", "TESTKEY"])

        mock_stats = {
            "video_id": "abc123",
            "title": "Test",
            "published_at": "2024-01-01",
            "duration": "PT5M",
            "view_count": 0,
            "like_count": 0,
            "comment_count": 0,
        }

        with patch("ytcli.commands.analytics.api.get_api_client"), \
             patch("ytcli.commands.analytics.api.get_video_stats", return_value=mock_stats):
            result = runner.invoke(cli, [
                "--data-dir", init_db, "performance",
                "https://www.youtube.com/watch?v=abc123",
            ])

        data = json.loads(result.output)
        assert data["data"]["engagement_rate"] == 0.0

    def test_performance_missing_api_key(self, runner, init_db):
        """Test missing API key returns clear error."""
        result = runner.invoke(cli, [
            "--data-dir", init_db, "performance",
            "https://www.youtube.com/watch?v=test123",
        ])
        data = json.loads(result.output)
        assert data["ok"] is False
        assert "api" in data["error"].lower() or "key" in data["error"].lower()

    def test_performance_video_not_found(self, runner, init_db):
        """Test video not found error."""
        from unittest.mock import patch

        runner.invoke(cli, ["--data-dir", init_db, "auth", "--api-key", "TESTKEY"])

        with patch("ytcli.commands.analytics.api.get_api_client"), \
             patch("ytcli.commands.analytics.api.get_video_stats",
                   side_effect=ValueError("Video not found: nonexistent")):
            result = runner.invoke(cli, [
                "--data-dir", init_db, "performance",
                "https://www.youtube.com/watch?v=nonexistent",
            ])

        data = json.loads(result.output)
        assert data["ok"] is False
        assert "not found" in data["error"].lower()

    def test_performance_extracts_video_id_from_short_url(self, runner, init_db):
        """Test extraction of video ID from youtu.be short URLs."""
        from unittest.mock import patch

        runner.invoke(cli, ["--data-dir", init_db, "auth", "--api-key", "TESTKEY"])

        mock_stats = {
            "video_id": "dQw4w9WgXcQ",
            "title": "Test",
            "published_at": "2024-01-01",
            "duration": "PT5M",
            "view_count": 100,
            "like_count": 10,
            "comment_count": 5,
        }

        with patch("ytcli.commands.analytics.api.get_api_client"), \
             patch("ytcli.commands.analytics.api.get_video_stats", return_value=mock_stats) as mock_get:
            result = runner.invoke(cli, [
                "--data-dir", init_db, "performance",
                "https://youtu.be/dQw4w9WgXcQ",
            ])

        assert result.exit_code == 0
        mock_get.assert_called_once()
        # The video_id passed to get_video_stats should be dQw4w9WgXcQ
        assert mock_get.call_args[0][1] == "dQw4w9WgXcQ"


class TestTop:
    """Tests for the top command."""

    @pytest.fixture
    def seeded_db(self, runner, init_db):
        """Seed DB with a channel and 3 videos with different view counts."""
        from ytcli.core.db import get_connection, upsert_channel, upsert_video, set_config

        conn = get_connection(init_db)
        set_config(conn, "api_key", "TESTKEY")
        upsert_channel(conn, {
            "id": "UC123",
            "handle": "@testchannel",
            "name": "Test Channel",
        })
        upsert_video(conn, {
            "id": "v1", "channel_id": "UC123", "title": "Low Views",
            "view_count": 100, "published_at": "2024-01-01",
        })
        upsert_video(conn, {
            "id": "v2", "channel_id": "UC123", "title": "Mid Views",
            "view_count": 500, "published_at": "2024-02-01",
        })
        upsert_video(conn, {
            "id": "v3", "channel_id": "UC123", "title": "High Views",
            "view_count": 1000, "published_at": "2024-03-01",
        })
        conn.close()
        return init_db

    def test_top_by_views(self, runner, seeded_db):
        result = runner.invoke(cli, ["--data-dir", seeded_db, "top", "@testchannel", "--by", "views"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["ok"] is True
        assert data["command"] == "top"
        videos = data["data"]["videos"]
        assert len(videos) == 3
        assert videos[0]["title"] == "High Views"
        assert videos[0]["view_count"] == 1000
        assert videos[1]["view_count"] == 500
        assert videos[2]["view_count"] == 100

    def test_top_by_engagement(self, runner, seeded_db):
        """Mock api.get_video_stats for engagement sort."""
        from unittest.mock import patch, MagicMock

        def mock_get_video_stats(client, video_id):
            stats_map = {
                "v1": {"video_id": "v1", "title": "Low Views", "view_count": 100, "like_count": 50, "comment_count": 10, "published_at": "2024-01-01", "duration": "PT5M"},
                "v2": {"video_id": "v2", "title": "Mid Views", "view_count": 500, "like_count": 20, "comment_count": 5, "published_at": "2024-02-01", "duration": "PT10M"},
                "v3": {"video_id": "v3", "title": "High Views", "view_count": 1000, "like_count": 30, "comment_count": 10, "published_at": "2024-03-01", "duration": "PT15M"},
            }
            return stats_map[video_id]

        with patch("ytcli.commands.analytics.api.get_video_stats", side_effect=mock_get_video_stats):
            with patch("ytcli.commands.analytics.api.get_api_client", return_value=MagicMock()):
                result = runner.invoke(cli, ["--data-dir", seeded_db, "top", "@testchannel", "--by", "engagement"])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["ok"] is True
        videos = data["data"]["videos"]
        # v1: (50+10)/100 = 60%, v2: (20+5)/500 = 5%, v3: (30+10)/1000 = 4%
        assert videos[0]["title"] == "Low Views"
        assert videos[0]["engagement_rate"] > videos[1]["engagement_rate"]

    def test_top_limit(self, runner, seeded_db):
        result = runner.invoke(cli, ["--data-dir", seeded_db, "top", "@testchannel", "--by", "views", "--limit", "2"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data["data"]["videos"]) == 2

    def test_top_missing_channel(self, runner, init_db):
        from ytcli.core.db import get_connection, set_config
        conn = get_connection(init_db)
        set_config(conn, "api_key", "TESTKEY")
        conn.close()

        result = runner.invoke(cli, ["--data-dir", init_db, "top", "@nonexistent"])
        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["ok"] is False


class TestComments:
    """Tests for the comments command."""

    def test_comments_basic(self, runner, init_db):
        from unittest.mock import patch, MagicMock
        from ytcli.core.db import get_connection, set_config, upsert_channel, upsert_video

        conn = get_connection(init_db)
        set_config(conn, "api_key", "TESTKEY")
        upsert_channel(conn, {"id": "UC123", "name": "Test"})
        upsert_video(conn, {"id": "abc123", "channel_id": "UC123", "title": "Test Video"})
        conn.close()

        mock_comments = [
            {"author": "User1", "text": "Great video!", "like_count": 10, "published_at": "2024-01-01T00:00:00Z"},
            {"author": "User2", "text": "Thanks for sharing", "like_count": 5, "published_at": "2024-01-02T00:00:00Z"},
        ]

        with patch("ytcli.commands.analytics.api.get_comments", return_value=mock_comments):
            with patch("ytcli.commands.analytics.api.get_api_client", return_value=MagicMock()):
                result = runner.invoke(cli, ["--data-dir", init_db, "comments", "https://youtube.com/watch?v=abc123"])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["ok"] is True
        assert data["command"] == "comments"
        assert data["data"]["video_id"] == "abc123"
        assert len(data["data"]["comments"]) == 2
        assert data["data"]["comments"][0]["author"] == "User1"
        assert data["data"]["comments"][0]["text"] == "Great video!"
        assert data["data"]["comments"][0]["like_count"] == 10

    def test_comments_sort_top(self, runner, init_db):
        from unittest.mock import patch, MagicMock
        from ytcli.core.db import get_connection, set_config

        conn = get_connection(init_db)
        set_config(conn, "api_key", "TESTKEY")
        conn.close()

        with patch("ytcli.commands.analytics.api.get_comments", return_value=[]) as mock_get:
            with patch("ytcli.commands.analytics.api.get_api_client", return_value=MagicMock()):
                runner.invoke(cli, ["--data-dir", init_db, "comments", "https://youtube.com/watch?v=abc123", "--sort", "top"])
                # Verify get_comments was called with sort="top"
                call_args = mock_get.call_args
                assert call_args[0][2] == "top" or call_args[1].get("sort") == "top"

    def test_comments_sort_recent(self, runner, init_db):
        from unittest.mock import patch, MagicMock
        from ytcli.core.db import get_connection, set_config

        conn = get_connection(init_db)
        set_config(conn, "api_key", "TESTKEY")
        conn.close()

        with patch("ytcli.commands.analytics.api.get_comments", return_value=[]) as mock_get:
            with patch("ytcli.commands.analytics.api.get_api_client", return_value=MagicMock()):
                runner.invoke(cli, ["--data-dir", init_db, "comments", "https://youtube.com/watch?v=abc123", "--sort", "recent"])
                call_args = mock_get.call_args
                assert call_args[0][2] == "recent" or call_args[1].get("sort") == "recent"

    def test_comments_limit(self, runner, init_db):
        from unittest.mock import patch, MagicMock
        from ytcli.core.db import get_connection, set_config

        conn = get_connection(init_db)
        set_config(conn, "api_key", "TESTKEY")
        conn.close()

        mock_comments = [{"author": f"User{i}", "text": f"Comment {i}", "like_count": i, "published_at": "2024-01-01T00:00:00Z"} for i in range(3)]

        with patch("ytcli.commands.analytics.api.get_comments", return_value=mock_comments):
            with patch("ytcli.commands.analytics.api.get_api_client", return_value=MagicMock()):
                result = runner.invoke(cli, ["--data-dir", init_db, "comments", "https://youtube.com/watch?v=abc123", "--limit", "3"])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["data"]["count"] == 3

    def test_comments_missing_api_key(self, runner, init_db):
        result = runner.invoke(cli, ["--data-dir", init_db, "comments", "https://youtube.com/watch?v=abc123"])
        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["ok"] is False

    def test_comments_stored_in_db(self, runner, init_db):
        from unittest.mock import patch, MagicMock
        from ytcli.core.db import get_connection, set_config, upsert_channel, upsert_video

        conn = get_connection(init_db)
        set_config(conn, "api_key", "TESTKEY")
        upsert_channel(conn, {"id": "UC123", "name": "Test"})
        upsert_video(conn, {"id": "abc123", "channel_id": "UC123", "title": "Test Video"})
        conn.close()

        mock_comments = [
            {"author": "User1", "text": "Stored comment", "like_count": 3, "published_at": "2024-01-01T00:00:00Z"},
        ]

        with patch("ytcli.commands.analytics.api.get_comments", return_value=mock_comments):
            with patch("ytcli.commands.analytics.api.get_api_client", return_value=MagicMock()):
                runner.invoke(cli, ["--data-dir", init_db, "comments", "https://youtube.com/watch?v=abc123"])

        conn = get_connection(init_db)
        rows = conn.execute("SELECT * FROM comments WHERE video_id = 'abc123'").fetchall()
        conn.close()
        assert len(rows) == 1
        assert rows[0]["text"] == "Stored comment"
