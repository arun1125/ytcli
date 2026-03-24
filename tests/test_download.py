"""Tests for Tier 1: Download & Extract commands."""

import json
import subprocess

import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock

from ytcli.cli import cli
from tests.conftest import parse_json


@pytest.fixture
def runner():
    return CliRunner()


FAKE_METADATA = {
    "id": "dQw4w9WgXcQ",
    "title": "Rick Astley - Never Gonna Give You Up",
    "description": "The official video for Rick Astley's hit single.",
    "channel": "Rick Astley",
    "channel_id": "UCuAXFkgsw1L7xaCfnd5JJOw",
    "duration": 212,
    "view_count": 1500000000,
    "like_count": 15000000,
    "comment_count": 3000000,
    "upload_date": "20091025",
    "tags": ["rick astley", "never gonna give you up", "80s"],
    "thumbnail": "https://i.ytimg.com/vi/dQw4w9WgXcQ/maxresdefault.jpg",
    "subtitles": {"en": [{"ext": "srt"}]},
    "automatic_captions": {},
}


class TestMetadata:
    @patch("ytcli.commands.download.scraper")
    def test_metadata_returns_key_fields(self, mock_scraper, runner):
        """metadata command returns title/description/duration/view_count/published_at."""
        mock_scraper.get_video_metadata.return_value = FAKE_METADATA
        result = runner.invoke(cli, ["metadata", "https://youtube.com/watch?v=dQw4w9WgXcQ"])
        assert result.exit_code == 0, f"stderr: {result.output}"
        data = parse_json(result.output)
        assert data["ok"] is True
        assert data["command"] == "metadata"
        d = data["data"]
        assert d["id"] == "dQw4w9WgXcQ"
        assert d["title"] == "Rick Astley - Never Gonna Give You Up"
        assert d["description"] == "The official video for Rick Astley's hit single."
        assert d["duration"] == 212
        assert d["view_count"] == 1500000000
        assert "published_at" in d

    @patch("ytcli.commands.download.scraper")
    def test_metadata_includes_optional_fields(self, mock_scraper, runner):
        """metadata command includes like_count, comment_count, tags, thumbnail_url, has_captions."""
        mock_scraper.get_video_metadata.return_value = FAKE_METADATA
        result = runner.invoke(cli, ["metadata", "https://youtube.com/watch?v=dQw4w9WgXcQ"])
        data = parse_json(result.output)
        d = data["data"]
        assert d["like_count"] == 15000000
        assert d["comment_count"] == 3000000
        assert d["tags"] == ["rick astley", "never gonna give you up", "80s"]
        assert d["thumbnail_url"] == "https://i.ytimg.com/vi/dQw4w9WgXcQ/maxresdefault.jpg"
        assert d["has_captions"] is True
        assert d["channel"] == "Rick Astley"

    @patch("ytcli.commands.download.scraper")
    def test_metadata_error_on_invalid_url(self, mock_scraper, runner):
        """metadata command returns error JSON for invalid URL."""
        mock_scraper.get_video_metadata.side_effect = subprocess.CalledProcessError(
            1, "yt-dlp", stderr="ERROR: Incomplete YouTube ID"
        )
        result = runner.invoke(cli, ["metadata", "not-a-valid-url"])
        data = parse_json(result.output)
        assert data["ok"] is False
        assert data["command"] == "metadata"
        assert "error" in data

    @patch("ytcli.commands.download.scraper")
    def test_metadata_handles_missing_optional_fields(self, mock_scraper, runner):
        """metadata command handles yt-dlp response missing optional fields gracefully."""
        sparse_metadata = {
            "id": "abc123",
            "title": "Minimal Video",
            "upload_date": "20240101",
        }
        mock_scraper.get_video_metadata.return_value = sparse_metadata
        result = runner.invoke(cli, ["metadata", "https://youtube.com/watch?v=abc123"])
        data = parse_json(result.output)
        assert data["ok"] is True
        d = data["data"]
        assert d["id"] == "abc123"
        assert d["title"] == "Minimal Video"
        assert d["description"] is None
        assert d["view_count"] is None
        assert d["like_count"] is None
        assert d["has_captions"] is False

    def test_metadata_requires_url_argument(self, runner):
        """metadata command fails with exit code 2 if no URL provided."""
        result = runner.invoke(cli, ["metadata"])
        assert result.exit_code == 2


class TestDownload:
    @patch("ytcli.commands.download.scraper")
    def test_download_returns_output_path(self, mock_scraper, runner, tmp_path):
        """download command returns output_path in JSON data."""
        fake_path = str(tmp_path / "Rick Astley - Never Gonna Give You Up.mp4")
        mock_scraper.download_video.return_value = fake_path
        result = runner.invoke(
            cli, ["download", "https://youtube.com/watch?v=dQw4w9WgXcQ"]
        )
        assert result.exit_code == 0, f"output: {result.output}"
        data = parse_json(result.output)
        assert data["ok"] is True
        assert data["command"] == "download"
        assert data["data"]["output_path"] == fake_path

    @patch("ytcli.commands.download.scraper")
    def test_download_default_format_and_quality(self, mock_scraper, runner, tmp_path):
        """download command uses mp4 format and 1080 quality by default."""
        fake_path = str(tmp_path / "video.mp4")
        mock_scraper.download_video.return_value = fake_path
        runner.invoke(
            cli, ["download", "https://youtube.com/watch?v=dQw4w9WgXcQ"]
        )
        mock_scraper.download_video.assert_called_once()
        call_kwargs = mock_scraper.download_video.call_args
        assert call_kwargs[1].get("format", call_kwargs[0][2] if len(call_kwargs[0]) > 2 else None) == "mp4" or \
            "mp4" in str(call_kwargs)

    @patch("ytcli.commands.download.scraper")
    def test_download_custom_format_and_quality(self, mock_scraper, runner, tmp_path):
        """download command passes custom format and quality to scraper."""
        fake_path = str(tmp_path / "video.webm")
        mock_scraper.download_video.return_value = fake_path
        result = runner.invoke(
            cli,
            ["download", "--format", "webm", "--quality", "720",
             "https://youtube.com/watch?v=dQw4w9WgXcQ"],
        )
        assert result.exit_code == 0
        data = parse_json(result.output)
        assert data["ok"] is True
        # Verify scraper was called with custom args
        args, kwargs = mock_scraper.download_video.call_args
        assert "webm" in args or kwargs.get("format") == "webm"
        assert "720" in args or kwargs.get("quality") == "720"

    @patch("ytcli.commands.download.scraper")
    def test_download_error_handling(self, mock_scraper, runner):
        """download command returns error JSON on scraper failure."""
        mock_scraper.download_video.side_effect = subprocess.CalledProcessError(
            1, "yt-dlp", stderr="ERROR: Video unavailable"
        )
        result = runner.invoke(
            cli, ["download", "https://youtube.com/watch?v=invalid"]
        )
        data = parse_json(result.output)
        assert data["ok"] is False
        assert data["command"] == "download"
        assert "error" in data

    @patch("ytcli.commands.download.scraper")
    def test_download_records_in_db(self, mock_scraper, runner, tmp_path):
        """download command records download in DB when DB exists."""
        data_dir = str(tmp_path / "ytcli_data")
        # Init DB first
        runner.invoke(cli, ["--data-dir", data_dir, "init"])
        fake_path = str(tmp_path / "video.mp4")
        mock_scraper.download_video.return_value = fake_path
        result = runner.invoke(
            cli,
            ["--data-dir", data_dir, "download",
             "https://youtube.com/watch?v=dQw4w9WgXcQ"],
        )
        assert result.exit_code == 0
        # Check DB has the download record
        from ytcli.core.db import get_connection
        conn = get_connection(data_dir)
        row = conn.execute("SELECT * FROM downloads").fetchone()
        conn.close()
        assert row is not None
        assert row["url"] == "https://youtube.com/watch?v=dQw4w9WgXcQ"
        assert row["output_path"] == fake_path
        assert row["format"] == "mp4"

    def test_download_requires_url_argument(self, runner):
        """download command fails with exit code 2 if no URL provided."""
        result = runner.invoke(cli, ["download"])
        assert result.exit_code == 2


class TestAudio:
    @patch("ytcli.commands.download.scraper")
    def test_audio_returns_output_path(self, mock_scraper, runner):
        """audio command returns output_path in JSON on success."""
        mock_scraper.download_audio.return_value = "/tmp/downloads/Song.mp3"
        result = runner.invoke(cli, ["audio", "https://youtube.com/watch?v=dQw4w9WgXcQ"])
        assert result.exit_code == 0, f"output: {result.output}"
        data = parse_json(result.output)
        assert data["ok"] is True
        assert data["command"] == "audio"
        assert data["data"]["output_path"] == "/tmp/downloads/Song.mp3"

    @patch("ytcli.commands.download.scraper")
    def test_audio_default_format_mp3(self, mock_scraper, runner):
        """audio command defaults to mp3 format."""
        mock_scraper.download_audio.return_value = "/tmp/downloads/Song.mp3"
        runner.invoke(cli, ["audio", "https://youtube.com/watch?v=dQw4w9WgXcQ"])
        call_args = mock_scraper.download_audio.call_args
        assert "mp3" in str(call_args)

    @patch("ytcli.commands.download.scraper")
    def test_audio_custom_format_wav(self, mock_scraper, runner):
        """audio command respects --format wav option."""
        mock_scraper.download_audio.return_value = "/tmp/downloads/Song.wav"
        result = runner.invoke(cli, ["audio", "--format", "wav", "https://youtube.com/watch?v=dQw4w9WgXcQ"])
        assert result.exit_code == 0
        data = parse_json(result.output)
        assert data["ok"] is True
        assert data["data"]["output_path"] == "/tmp/downloads/Song.wav"
        call_args = mock_scraper.download_audio.call_args
        assert "wav" in str(call_args)

    @patch("ytcli.commands.download.scraper")
    def test_audio_custom_quality(self, mock_scraper, runner):
        """audio command passes quality option to scraper."""
        mock_scraper.download_audio.return_value = "/tmp/downloads/Song.mp3"
        runner.invoke(cli, ["audio", "--quality", "128", "https://youtube.com/watch?v=dQw4w9WgXcQ"])
        call_args = mock_scraper.download_audio.call_args
        assert "128" in str(call_args)

    @patch("ytcli.commands.download.scraper")
    def test_audio_error_handling(self, mock_scraper, runner):
        """audio command returns error JSON when scraper fails."""
        mock_scraper.download_audio.side_effect = subprocess.CalledProcessError(
            1, "yt-dlp", stderr="ERROR: Video unavailable"
        )
        result = runner.invoke(cli, ["audio", "https://youtube.com/watch?v=bad"])
        data = parse_json(result.output)
        assert data["ok"] is False
        assert data["command"] == "audio"
        assert "error" in data

    def test_audio_requires_url_argument(self, runner):
        """audio command fails with exit code 2 if no URL provided."""
        result = runner.invoke(cli, ["audio"])
        assert result.exit_code == 2

    @patch("ytcli.commands.download.scraper")
    def test_audio_records_download_in_db(self, mock_scraper, runner, tmp_path):
        """audio command records download in DB when data_dir exists."""
        from ytcli.core.db import init_db, get_connection
        data_dir = str(tmp_path / "ytcli_test")
        init_db(data_dir)
        mock_scraper.download_audio.return_value = "/tmp/downloads/Song.mp3"
        result = runner.invoke(cli, [
            "--data-dir", data_dir,
            "audio", "https://youtube.com/watch?v=dQw4w9WgXcQ",
        ])
        assert result.exit_code == 0
        data = parse_json(result.output)
        assert data["ok"] is True
        conn = get_connection(data_dir)
        row = conn.execute("SELECT * FROM downloads WHERE url = ?",
                           ("https://youtube.com/watch?v=dQw4w9WgXcQ",)).fetchone()
        assert row is not None
        assert row["format"] == "mp3"
        assert row["output_path"] == "/tmp/downloads/Song.mp3"
        conn.close()

    @patch("ytcli.commands.download.scraper")
    def test_audio_uses_config_default_format(self, mock_scraper, runner, tmp_path):
        """audio command uses default_audio_format from config when no --format given."""
        from ytcli.core.db import init_db, get_connection, set_config
        data_dir = str(tmp_path / "ytcli_test")
        init_db(data_dir)
        conn = get_connection(data_dir)
        set_config(conn, "default_audio_format", "wav")
        conn.close()
        mock_scraper.download_audio.return_value = "/tmp/downloads/Song.wav"
        result = runner.invoke(cli, [
            "--data-dir", data_dir,
            "audio", "https://youtube.com/watch?v=dQw4w9WgXcQ",
        ])
        assert result.exit_code == 0
        call_args = mock_scraper.download_audio.call_args
        assert "wav" in str(call_args)


class TestThumbnail:
    @patch("ytcli.commands.download.scraper")
    def test_thumbnail_returns_output_path(self, mock_scraper, runner):
        """thumbnail command returns output_path in JSON on success."""
        mock_scraper.download_thumbnail.return_value = "/tmp/downloads/Rick Astley.webp"
        result = runner.invoke(cli, ["thumbnail", "https://youtube.com/watch?v=dQw4w9WgXcQ"])
        assert result.exit_code == 0, f"output: {result.output}"
        data = parse_json(result.output)
        assert data["ok"] is True
        assert data["command"] == "thumbnail"
        assert data["data"]["output_path"] == "/tmp/downloads/Rick Astley.webp"

    @patch("ytcli.commands.download.scraper")
    def test_thumbnail_custom_output_path(self, mock_scraper, runner, tmp_path):
        """thumbnail command passes custom --output path to scraper."""
        custom_path = str(tmp_path / "my_thumb.jpg")
        mock_scraper.download_thumbnail.return_value = custom_path
        result = runner.invoke(cli, [
            "thumbnail", "--output", custom_path,
            "https://youtube.com/watch?v=dQw4w9WgXcQ",
        ])
        assert result.exit_code == 0
        data = parse_json(result.output)
        assert data["ok"] is True
        assert data["data"]["output_path"] == custom_path

    @patch("ytcli.commands.download.scraper")
    def test_thumbnail_error_handling(self, mock_scraper, runner):
        """thumbnail command returns error JSON when scraper fails."""
        mock_scraper.download_thumbnail.side_effect = subprocess.CalledProcessError(
            1, "yt-dlp", stderr="ERROR: Video unavailable"
        )
        result = runner.invoke(cli, ["thumbnail", "https://youtube.com/watch?v=bad"])
        data = parse_json(result.output)
        assert data["ok"] is False
        assert data["command"] == "thumbnail"
        assert "error" in data

    @patch("ytcli.commands.download.scraper")
    def test_thumbnail_url_in_response(self, mock_scraper, runner):
        """thumbnail command includes the source URL in response data."""
        mock_scraper.download_thumbnail.return_value = "/tmp/downloads/thumb.webp"
        result = runner.invoke(cli, ["thumbnail", "https://youtube.com/watch?v=dQw4w9WgXcQ"])
        data = parse_json(result.output)
        assert data["data"]["url"] == "https://youtube.com/watch?v=dQw4w9WgXcQ"

    def test_thumbnail_requires_url_argument(self, runner):
        """thumbnail command fails with exit code 2 if no URL provided."""
        result = runner.invoke(cli, ["thumbnail"])
        assert result.exit_code == 2


class TestTranscript:
    @patch("ytcli.commands.download.scraper")
    def test_transcript_returns_clean_text(self, mock_scraper, runner):
        """transcript command returns clean text in JSON data field."""
        mock_scraper.get_transcript.return_value = "Hello world this is a transcript of the video"
        result = runner.invoke(cli, ["transcript", "https://youtube.com/watch?v=dQw4w9WgXcQ"])
        assert result.exit_code == 0, f"output: {result.output}"
        data = parse_json(result.output)
        assert data["ok"] is True
        assert data["command"] == "transcript"
        assert data["data"]["text"] == "Hello world this is a transcript of the video"
        assert data["data"]["url"] == "https://youtube.com/watch?v=dQw4w9WgXcQ"

    @patch("ytcli.commands.download.scraper")
    def test_transcript_default_language_en(self, mock_scraper, runner):
        """transcript command defaults to English language."""
        mock_scraper.get_transcript.return_value = "English transcript text"
        result = runner.invoke(cli, ["transcript", "https://youtube.com/watch?v=dQw4w9WgXcQ"])
        assert result.exit_code == 0
        data = parse_json(result.output)
        assert data["data"]["language"] == "en"
        mock_scraper.get_transcript.assert_called_once_with(
            "https://youtube.com/watch?v=dQw4w9WgXcQ", lang="en"
        )

    @patch("ytcli.commands.download.scraper")
    def test_transcript_custom_language(self, mock_scraper, runner):
        """transcript command respects --lang option."""
        mock_scraper.get_transcript.return_value = "Texto en espanol"
        result = runner.invoke(cli, [
            "transcript", "--lang", "es",
            "https://youtube.com/watch?v=dQw4w9WgXcQ",
        ])
        assert result.exit_code == 0
        data = parse_json(result.output)
        assert data["data"]["language"] == "es"
        mock_scraper.get_transcript.assert_called_once_with(
            "https://youtube.com/watch?v=dQw4w9WgXcQ", lang="es"
        )

    @patch("ytcli.commands.download.scraper")
    def test_transcript_error_no_subtitles(self, mock_scraper, runner):
        """transcript command returns error JSON when no subtitles found."""
        mock_scraper.get_transcript.side_effect = FileNotFoundError(
            "No subtitles found for https://youtube.com/watch?v=nosubs in language en"
        )
        result = runner.invoke(cli, ["transcript", "https://youtube.com/watch?v=nosubs"])
        data = parse_json(result.output)
        assert data["ok"] is False
        assert data["command"] == "transcript"
        assert "No subtitles found" in data["error"]

    @patch("ytcli.commands.download.scraper")
    def test_transcript_error_on_scraper_failure(self, mock_scraper, runner):
        """transcript command returns error JSON on scraper exception."""
        mock_scraper.get_transcript.side_effect = subprocess.CalledProcessError(
            1, "yt-dlp", stderr="ERROR: Video unavailable"
        )
        result = runner.invoke(cli, ["transcript", "https://youtube.com/watch?v=bad"])
        data = parse_json(result.output)
        assert data["ok"] is False
        assert data["command"] == "transcript"

    def test_transcript_requires_url_argument(self, runner):
        """transcript command fails with exit code 2 if no URL provided."""
        result = runner.invoke(cli, ["transcript"])
        assert result.exit_code == 2

    @patch("ytcli.commands.download.scraper")
    def test_transcript_stores_in_db(self, mock_scraper, runner, tmp_path):
        """transcript command stores transcript in DB when video exists."""
        from ytcli.core.db import init_db, get_connection, upsert_channel, upsert_video
        data_dir = str(tmp_path / "ytcli_test")
        init_db(data_dir)
        # Pre-seed video record so transcript storage works (no phantom records)
        conn = get_connection(data_dir)
        upsert_channel(conn, {"id": "UC_test", "name": "Test Channel"})
        upsert_video(conn, {"id": "dQw4w9WgXcQ", "channel_id": "UC_test", "title": "Test"})
        conn.close()
        mock_scraper.get_transcript.return_value = "Stored transcript text"
        result = runner.invoke(cli, [
            "--data-dir", data_dir,
            "transcript", "https://youtube.com/watch?v=dQw4w9WgXcQ",
        ])
        assert result.exit_code == 0
        data = parse_json(result.output)
        assert data["ok"] is True
        conn = get_connection(data_dir)
        row = conn.execute(
            "SELECT * FROM transcripts WHERE video_id = ?", ("dQw4w9WgXcQ",)
        ).fetchone()
        conn.close()
        assert row is not None
        assert row["text"] == "Stored transcript text"
        assert row["language"] == "en"

    @patch("ytcli.commands.download.scraper")
    def test_transcript_updates_existing_db_record(self, mock_scraper, runner, tmp_path):
        """transcript command upserts if transcript already exists in DB."""
        from ytcli.core.db import init_db, get_connection, upsert_channel, upsert_video
        data_dir = str(tmp_path / "ytcli_test")
        init_db(data_dir)
        # Pre-seed video record so transcript storage works
        conn = get_connection(data_dir)
        upsert_channel(conn, {"id": "UC_test", "name": "Test Channel"})
        upsert_video(conn, {"id": "dQw4w9WgXcQ", "channel_id": "UC_test", "title": "Test"})
        conn.close()
        # First call
        mock_scraper.get_transcript.return_value = "First version"
        runner.invoke(cli, [
            "--data-dir", data_dir,
            "transcript", "https://youtube.com/watch?v=dQw4w9WgXcQ",
        ])
        # Second call with updated text
        mock_scraper.get_transcript.return_value = "Updated version"
        runner.invoke(cli, [
            "--data-dir", data_dir,
            "transcript", "https://youtube.com/watch?v=dQw4w9WgXcQ",
        ])
        conn = get_connection(data_dir)
        row = conn.execute(
            "SELECT * FROM transcripts WHERE video_id = ?", ("dQw4w9WgXcQ",)
        ).fetchone()
        conn.close()
        assert row["text"] == "Updated version"

    @patch("ytcli.commands.download.scraper")
    def test_transcript_no_phantom_channel(self, mock_scraper, runner, tmp_path):
        """transcript command must not create phantom channel/video records."""
        from ytcli.core.db import init_db, get_connection
        data_dir = str(tmp_path / "ytcli_test")
        init_db(data_dir)
        mock_scraper.get_transcript.return_value = "Transcript text"
        result = runner.invoke(cli, [
            "--data-dir", data_dir,
            "transcript", "https://youtube.com/watch?v=dQw4w9WgXcQ",
        ])
        assert result.exit_code == 0
        data = parse_json(result.output)
        assert data["ok"] is True
        # Verify no phantom channel or video records were created
        conn = get_connection(data_dir)
        channels = conn.execute("SELECT COUNT(*) FROM channels").fetchone()[0]
        videos = conn.execute("SELECT COUNT(*) FROM videos").fetchone()[0]
        transcripts = conn.execute("SELECT COUNT(*) FROM transcripts").fetchone()[0]
        conn.close()
        assert channels == 0, "Should not create phantom channel"
        assert videos == 0, "Should not create phantom video"
        assert transcripts == 0, "Should not store transcript without real video"
