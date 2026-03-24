"""Tests for scaffold: CLI loads, meta commands work, DB layer works."""

import json
import os
import tempfile

import pytest
from click.testing import CliRunner

from ytcli.cli import cli
from ytcli.core import db


@pytest.fixture
def tmp_data_dir(tmp_path):
    """Provide a temporary data directory."""
    return str(tmp_path / "ytcli_test")


@pytest.fixture
def runner():
    return CliRunner()


# --- CLI loads ---


class TestCLIHelp:
    def test_help_exits_zero(self, runner):
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0

    def test_help_lists_all_commands(self, runner):
        result = runner.invoke(cli, ["--help"])
        expected = [
            "audio", "auth", "batch-audio", "calendar", "channels",
            "comments", "compare", "config", "download", "export",
            "gaps", "hooks", "ideas", "init", "metadata", "niche",
            "performance", "refresh", "scan", "search", "serve",
            "stats", "status", "tags", "thumbnail", "titles",
            "top", "transcript", "videos",
        ]
        for cmd in expected:
            assert cmd in result.output, f"Missing command: {cmd}"

    def test_version(self, runner):
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output


# --- Init ---


class TestInit:
    def test_init_creates_db(self, runner, tmp_data_dir):
        result = runner.invoke(cli, ["--data-dir", tmp_data_dir, "init"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["ok"] is True
        assert os.path.exists(data["data"]["db_path"])

    def test_init_idempotent(self, runner, tmp_data_dir):
        runner.invoke(cli, ["--data-dir", tmp_data_dir, "init"])
        result = runner.invoke(cli, ["--data-dir", tmp_data_dir, "init"])
        assert result.exit_code == 0


# --- Status ---


class TestStatus:
    def test_status_on_empty_db(self, runner, tmp_data_dir):
        runner.invoke(cli, ["--data-dir", tmp_data_dir, "init"])
        result = runner.invoke(cli, ["--data-dir", tmp_data_dir, "status"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["data"]["channels"] == 0
        assert data["data"]["videos"] == 0

    def test_status_fails_without_init(self, runner, tmp_data_dir):
        result = runner.invoke(cli, ["--data-dir", tmp_data_dir, "status"])
        assert result.exit_code == 1


# --- Config ---


class TestConfig:
    def test_config_set_and_get(self, runner, tmp_data_dir):
        runner.invoke(cli, ["--data-dir", tmp_data_dir, "init"])
        runner.invoke(cli, ["--data-dir", tmp_data_dir, "config", "api_key", "test123"])
        result = runner.invoke(cli, ["--data-dir", tmp_data_dir, "config", "api_key"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["data"]["value"] == "test123"

    def test_config_get_missing_key(self, runner, tmp_data_dir):
        runner.invoke(cli, ["--data-dir", tmp_data_dir, "init"])
        result = runner.invoke(cli, ["--data-dir", tmp_data_dir, "config", "nonexistent"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["data"]["value"] is None


# --- DB layer ---


class TestDB:
    def test_init_db_creates_tables(self, tmp_data_dir):
        db.init_db(tmp_data_dir)
        conn = db.get_connection(tmp_data_dir)
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()]
        conn.close()
        assert "channels" in tables
        assert "videos" in tables
        assert "comments" in tables
        assert "transcripts" in tables
        assert "downloads" in tables
        assert "config" in tables

    def test_upsert_and_get_channel(self, tmp_data_dir):
        db.init_db(tmp_data_dir)
        conn = db.get_connection(tmp_data_dir)
        db.upsert_channel(conn, {
            "id": "UC123",
            "handle": "@testchannel",
            "name": "Test Channel",
        })
        ch = db.get_channel(conn, "UC123")
        assert ch["name"] == "Test Channel"
        ch2 = db.get_channel(conn, "@testchannel")
        assert ch2["id"] == "UC123"
        conn.close()

    def test_upsert_and_get_videos(self, tmp_data_dir):
        db.init_db(tmp_data_dir)
        conn = db.get_connection(tmp_data_dir)
        db.upsert_channel(conn, {"id": "UC123", "name": "Test"})
        db.upsert_video(conn, {
            "id": "v1", "channel_id": "UC123", "title": "First Video",
            "published_at": "2024-01-01", "view_count": 100,
        })
        db.upsert_video(conn, {
            "id": "v2", "channel_id": "UC123", "title": "Second Video",
            "published_at": "2024-02-01", "view_count": 500,
        })
        vids = db.get_videos(conn, "UC123", sort="views")
        assert len(vids) == 2
        assert vids[0]["view_count"] == 500
        conn.close()

    def test_search_videos(self, tmp_data_dir):
        db.init_db(tmp_data_dir)
        conn = db.get_connection(tmp_data_dir)
        db.upsert_channel(conn, {"id": "UC123", "name": "Test"})
        db.upsert_video(conn, {
            "id": "v1", "channel_id": "UC123",
            "title": "Python Tutorial for Beginners",
        })
        db.upsert_video(conn, {
            "id": "v2", "channel_id": "UC123",
            "title": "JavaScript Deep Dive",
        })
        results = db.search_videos(conn, "Python")
        assert len(results) == 1
        assert results[0]["id"] == "v1"
        conn.close()

    def test_config_round_trip(self, tmp_data_dir):
        db.init_db(tmp_data_dir)
        conn = db.get_connection(tmp_data_dir)
        assert db.get_config(conn, "foo") is None
        db.set_config(conn, "foo", "bar")
        assert db.get_config(conn, "foo") == "bar"
        db.set_config(conn, "foo", "baz")
        assert db.get_config(conn, "foo") == "baz"
        conn.close()

    def test_get_stats(self, tmp_data_dir):
        db.init_db(tmp_data_dir)
        conn = db.get_connection(tmp_data_dir)
        stats = db.get_stats(conn)
        assert stats["channels"] == 0
        assert stats["videos"] == 0
        assert stats["db_size_bytes"] > 0
        conn.close()


class TestGetConnectionMissingDB:
    def test_get_connection_raises_on_missing_db(self, tmp_data_dir):
        """get_connection should raise FileNotFoundError if DB doesn't exist."""
        with pytest.raises(FileNotFoundError, match="Database not initialized"):
            db.get_connection(tmp_data_dir)

    def test_get_connection_works_after_init(self, tmp_data_dir):
        """get_connection should work after init_db creates the DB."""
        db.init_db(tmp_data_dir)
        conn = db.get_connection(tmp_data_dir)
        assert conn is not None
        conn.close()


# --- All Tier 5 stubs have been implemented (tags, batch-audio, export) ---
