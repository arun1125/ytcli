"""Tests for Tier 5: Creation Assist commands (ideas, titles)."""

import json

import pytest
from click.testing import CliRunner

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


def seed_channel_with_videos(data_dir: str):
    """Seed DB with 1 channel and diverse videos for idea generation."""
    conn = db.get_connection(data_dir)
    db.upsert_channel(conn, {
        "id": "UC_AAA",
        "handle": "@alpha",
        "name": "Alpha Channel",
        "subscriber_count": 100000,
    })
    videos = [
        ("v1", "10 Python Tips You NEED to Know", 50000, 600),
        ("v2", "Why I Quit My Job (Story Time)", 120000, 900),
        ("v3", "How to Build a CLI?", 30000, 1200),
        ("v4", "React Tutorial for Beginners [2025]", 80000, 480),
        ("v5", "5 Mistakes Every Developer Makes", 60000, 720),
        ("v6", "Rust vs Go — Which Should You Learn?", 95000, 840),
        ("v7", "Python Automation Projects", 110000, 1500),
    ]
    for i, (vid_id, title, views, dur) in enumerate(videos):
        db.upsert_video(conn, {
            "id": vid_id,
            "channel_id": "UC_AAA",
            "title": title,
            "view_count": views,
            "duration_seconds": dur,
            "published_at": f"2025-01-{10 + i:02d}",
        })
    conn.close()


def seed_two_channels(data_dir: str):
    """Seed DB with 2 channels for --from filter testing."""
    conn = db.get_connection(data_dir)
    db.upsert_channel(conn, {
        "id": "UC_AAA",
        "handle": "@alpha",
        "name": "Alpha Channel",
    })
    db.upsert_channel(conn, {
        "id": "UC_BBB",
        "handle": "@beta",
        "name": "Beta Channel",
    })
    alpha_videos = [
        ("a1", "10 Python Tips", 50000),
        ("a2", "Advanced Python Tricks", 80000),
        ("a3", "Python for Data Science", 120000),
    ]
    for i, (vid_id, title, views) in enumerate(alpha_videos):
        db.upsert_video(conn, {
            "id": vid_id,
            "channel_id": "UC_AAA",
            "title": title,
            "view_count": views,
            "published_at": f"2025-01-{10 + i:02d}",
        })
    beta_videos = [
        ("b1", "JavaScript Crash Course", 90000),
        ("b2", "React vs Angular", 70000),
    ]
    for i, (vid_id, title, views) in enumerate(beta_videos):
        db.upsert_video(conn, {
            "id": vid_id,
            "channel_id": "UC_BBB",
            "title": title,
            "view_count": views,
            "published_at": f"2025-02-{5 + i:02d}",
        })
    conn.close()


# --- Ideas command ---


class TestIdeas:
    def test_ideas_returns_idea_list(self, runner, tmp_data_dir):
        """ideas returns JSON with idea list containing topic, reasoning, inspired_by."""
        seed_channel_with_videos(tmp_data_dir)

        result = runner.invoke(cli, [
            "--data-dir", tmp_data_dir, "ideas",
        ])
        assert result.exit_code == 0, f"output: {result.output}"
        data = parse_json(result.output)
        assert data["ok"] is True
        assert data["command"] == "ideas"
        assert "ideas" in data["data"]
        assert "count" in data["data"]

        ideas = data["data"]["ideas"]
        assert len(ideas) > 0
        for idea in ideas:
            assert "topic" in idea
            assert "reasoning" in idea
            assert "inspired_by" in idea
            assert isinstance(idea["inspired_by"], list)

    def test_ideas_from_channel_filter(self, runner, tmp_data_dir):
        """ideas --from filters to a specific channel's videos."""
        seed_two_channels(tmp_data_dir)

        result = runner.invoke(cli, [
            "--data-dir", tmp_data_dir, "ideas", "--from", "@alpha",
        ])
        assert result.exit_code == 0, f"output: {result.output}"
        data = parse_json(result.output)
        assert data["ok"] is True
        ideas = data["data"]["ideas"]
        # Ideas should be derived from alpha channel's python-heavy content
        assert len(ideas) > 0

    def test_ideas_count_flag(self, runner, tmp_data_dir):
        """ideas --count limits the number of ideas returned."""
        seed_channel_with_videos(tmp_data_dir)

        result = runner.invoke(cli, [
            "--data-dir", tmp_data_dir, "ideas", "--count", "3",
        ])
        assert result.exit_code == 0, f"output: {result.output}"
        data = parse_json(result.output)
        assert data["ok"] is True
        assert len(data["data"]["ideas"]) <= 3
        assert data["data"]["count"] <= 3

    def test_ideas_no_channels_error(self, runner, tmp_data_dir):
        """ideas with no channels in DB returns error."""
        result = runner.invoke(cli, [
            "--data-dir", tmp_data_dir, "ideas",
        ])
        data = parse_json(result.output)
        assert data["ok"] is False
        assert "no video" in data["error"].lower() or "no channel" in data["error"].lower()

    def test_ideas_from_nonexistent_channel(self, runner, tmp_data_dir):
        """ideas --from with nonexistent channel returns error."""
        result = runner.invoke(cli, [
            "--data-dir", tmp_data_dir, "ideas", "--from", "@nonexistent",
        ])
        data = parse_json(result.output)
        assert data["ok"] is False
        assert "not found" in data["error"].lower()


# --- Titles command ---


class TestTitles:
    def test_titles_returns_variations(self, runner, tmp_data_dir):
        """titles returns JSON with title variations."""
        seed_channel_with_videos(tmp_data_dir)

        result = runner.invoke(cli, [
            "--data-dir", tmp_data_dir, "titles", "python automation",
        ])
        assert result.exit_code == 0, f"output: {result.output}"
        data = parse_json(result.output)
        assert data["ok"] is True
        assert data["command"] == "titles"
        assert "titles" in data["data"]
        assert "count" in data["data"]
        assert "topic" in data["data"]
        assert data["data"]["topic"] == "python automation"

        titles = data["data"]["titles"]
        assert len(titles) > 0
        for t in titles:
            assert "title" in t
            assert "pattern" in t

    def test_titles_count_flag(self, runner, tmp_data_dir):
        """titles --count limits the number of variations."""
        seed_channel_with_videos(tmp_data_dir)

        result = runner.invoke(cli, [
            "--data-dir", tmp_data_dir, "titles", "python", "--count", "3",
        ])
        assert result.exit_code == 0, f"output: {result.output}"
        data = parse_json(result.output)
        assert data["ok"] is True
        assert len(data["data"]["titles"]) <= 3
        assert data["data"]["count"] <= 3

    def test_titles_has_various_patterns(self, runner, tmp_data_dir):
        """titles generates question, number, how-to, and bracket patterns."""
        seed_channel_with_videos(tmp_data_dir)

        result = runner.invoke(cli, [
            "--data-dir", tmp_data_dir, "titles", "machine learning", "--count", "20",
        ])
        assert result.exit_code == 0, f"output: {result.output}"
        data = parse_json(result.output)
        titles = data["data"]["titles"]
        patterns = {t["pattern"] for t in titles}
        # Should have at least 3 different pattern types
        assert len(patterns) >= 3, f"Only got patterns: {patterns}"
        expected_patterns = {"question", "number", "how-to", "bracket"}
        assert patterns.issubset(expected_patterns), f"Unexpected patterns: {patterns - expected_patterns}"

    def test_titles_no_db_still_works(self, runner, tmp_data_dir):
        """titles generates titles even with no videos in DB (pure generation)."""
        result = runner.invoke(cli, [
            "--data-dir", tmp_data_dir, "titles", "cooking tips",
        ])
        assert result.exit_code == 0, f"output: {result.output}"
        data = parse_json(result.output)
        assert data["ok"] is True
        assert len(data["data"]["titles"]) > 0

    def test_titles_incorporates_db_patterns(self, runner, tmp_data_dir):
        """titles includes db_patterns info when similar videos exist."""
        seed_channel_with_videos(tmp_data_dir)

        result = runner.invoke(cli, [
            "--data-dir", tmp_data_dir, "titles", "python",
        ])
        data = parse_json(result.output)
        assert data["ok"] is True
        # When videos exist, db_patterns should be populated
        assert "db_patterns" in data["data"]


# --- Tags command ---


class TestTags:
    def test_tags_from_url(self, runner, tmp_data_dir):
        """URL input calls scraper.get_video_metadata() and returns video tags."""
        with pytest.MonkeyPatch.context() as mp:
            import ytcli.commands.create as create_mod
            from unittest.mock import MagicMock
            mock_scraper = MagicMock()
            mock_scraper.get_video_metadata.return_value = {
                "id": "abc123",
                "title": "Test Video",
                "tags": ["python", "tutorial", "coding"],
            }
            mp.setattr(create_mod, "scraper", mock_scraper)

            result = runner.invoke(cli, [
                "--data-dir", tmp_data_dir,
                "tags", "https://youtube.com/watch?v=abc123",
            ])
            data = parse_json(result.output)
            assert data["ok"] is True
            assert data["data"]["source"] == "video"
            assert "python" in data["data"]["tags"]
            assert "tutorial" in data["data"]["tags"]
            mock_scraper.get_video_metadata.assert_called_once()

    def test_tags_from_youtu_be_url(self, runner, tmp_data_dir):
        """Short youtu.be URL should also be treated as video URL."""
        with pytest.MonkeyPatch.context() as mp:
            import ytcli.commands.create as create_mod
            from unittest.mock import MagicMock
            mock_scraper = MagicMock()
            mock_scraper.get_video_metadata.return_value = {
                "id": "xyz",
                "title": "Short Link Video",
                "tags": ["music", "chill"],
            }
            mp.setattr(create_mod, "scraper", mock_scraper)

            result = runner.invoke(cli, [
                "--data-dir", tmp_data_dir,
                "tags", "https://youtu.be/xyz",
            ])
            data = parse_json(result.output)
            assert data["ok"] is True
            assert data["data"]["source"] == "video"
            assert "music" in data["data"]["tags"]

    def test_tags_from_topic_search(self, runner, tmp_data_dir):
        """Topic input searches DB and aggregates common tags."""
        conn = db.get_connection(tmp_data_dir)
        db.upsert_channel(conn, {"id": "UC1", "name": "Test Channel"})
        db.upsert_video(conn, {
            "id": "v1", "channel_id": "UC1", "title": "Python Tutorial",
            "tags": json.dumps(["python", "tutorial", "beginner"]),
        })
        db.upsert_video(conn, {
            "id": "v2", "channel_id": "UC1", "title": "Python Advanced",
            "tags": json.dumps(["python", "advanced", "tutorial"]),
        })
        db.upsert_video(conn, {
            "id": "v3", "channel_id": "UC1", "title": "Python Data Science",
            "tags": json.dumps(["python", "data science", "pandas"]),
        })
        conn.close()

        result = runner.invoke(cli, [
            "--data-dir", tmp_data_dir, "tags", "Python",
        ])
        data = parse_json(result.output)
        assert data["ok"] is True
        assert data["data"]["source"] == "search"
        tags = data["data"]["tags"]
        # "python" appears in all 3 videos, should be first
        assert tags[0] == "python"

    def test_tags_no_results(self, runner, tmp_data_dir):
        """Topic with no matching videos returns empty tags."""
        result = runner.invoke(cli, [
            "--data-dir", tmp_data_dir, "tags", "xyznonexistenttopic",
        ])
        data = parse_json(result.output)
        assert data["ok"] is True
        assert data["data"]["tags"] == []


# --- Batch Audio command ---


class TestBatchAudio:
    def test_batch_audio_from_file(self, runner, tmp_data_dir, tmp_path):
        """File with 3 URLs downloads all 3."""
        url_file = tmp_path / "urls.txt"
        url_file.write_text(
            "https://youtube.com/watch?v=aaa\n"
            "https://youtube.com/watch?v=bbb\n"
            "https://youtube.com/watch?v=ccc\n"
        )

        with pytest.MonkeyPatch.context() as mp:
            import ytcli.commands.create as create_mod
            from unittest.mock import MagicMock
            mock_scraper = MagicMock()
            mock_scraper.download_audio.side_effect = [
                "/tmp/audio1.mp3",
                "/tmp/audio2.mp3",
                "/tmp/audio3.mp3",
            ]
            mp.setattr(create_mod, "scraper", mock_scraper)

            result = runner.invoke(cli, [
                "--data-dir", tmp_data_dir,
                "batch-audio", str(url_file),
            ])
            data = parse_json(result.output)
            assert data["ok"] is True
            assert data["data"]["total"] == 3
            assert data["data"]["succeeded"] == 3
            assert data["data"]["failed"] == 0
            assert len(data["data"]["downloads"]) == 3

    def test_batch_audio_partial_failure(self, runner, tmp_data_dir, tmp_path):
        """One failing URL does not block others."""
        url_file = tmp_path / "urls.txt"
        url_file.write_text(
            "https://youtube.com/watch?v=aaa\n"
            "https://youtube.com/watch?v=bbb\n"
            "https://youtube.com/watch?v=ccc\n"
        )

        with pytest.MonkeyPatch.context() as mp:
            import ytcli.commands.create as create_mod
            from unittest.mock import MagicMock
            mock_scraper = MagicMock()
            mock_scraper.download_audio.side_effect = [
                "/tmp/audio1.mp3",
                Exception("Network error"),
                "/tmp/audio3.mp3",
            ]
            mp.setattr(create_mod, "scraper", mock_scraper)

            result = runner.invoke(cli, [
                "--data-dir", tmp_data_dir,
                "batch-audio", str(url_file),
            ])
            data = parse_json(result.output)
            assert data["ok"] is True
            assert data["data"]["total"] == 3
            assert data["data"]["succeeded"] == 2
            assert data["data"]["failed"] == 1

    def test_batch_audio_format_flag(self, runner, tmp_data_dir, tmp_path):
        """--format flag passes through to download_audio."""
        url_file = tmp_path / "urls.txt"
        url_file.write_text("https://youtube.com/watch?v=aaa\n")

        with pytest.MonkeyPatch.context() as mp:
            import ytcli.commands.create as create_mod
            from unittest.mock import MagicMock
            mock_scraper = MagicMock()
            mock_scraper.download_audio.return_value = "/tmp/audio1.wav"
            mp.setattr(create_mod, "scraper", mock_scraper)

            result = runner.invoke(cli, [
                "--data-dir", tmp_data_dir,
                "batch-audio", str(url_file), "--format", "wav",
            ])
            data = parse_json(result.output)
            assert data["ok"] is True
            # Verify wav format was passed
            call_kwargs = mock_scraper.download_audio.call_args
            assert "wav" in str(call_kwargs)

    def test_batch_audio_single_url(self, runner, tmp_data_dir):
        """Single URL (not a file) treated as playlist URL."""
        with pytest.MonkeyPatch.context() as mp:
            import ytcli.commands.create as create_mod
            from unittest.mock import MagicMock
            mock_scraper = MagicMock()
            mock_scraper.download_audio.return_value = "/tmp/playlist_audio.mp3"
            mp.setattr(create_mod, "scraper", mock_scraper)

            result = runner.invoke(cli, [
                "--data-dir", tmp_data_dir,
                "batch-audio", "https://youtube.com/playlist?list=PLxyz",
            ])
            data = parse_json(result.output)
            assert data["ok"] is True
            mock_scraper.download_audio.assert_called_once()

    def test_batch_audio_skips_empty_lines_and_comments(self, runner, tmp_data_dir, tmp_path):
        """Empty lines and # comments are skipped."""
        url_file = tmp_path / "urls.txt"
        url_file.write_text(
            "# This is a comment\n"
            "\n"
            "https://youtube.com/watch?v=aaa\n"
            "  \n"
            "# Another comment\n"
            "https://youtube.com/watch?v=bbb\n"
        )

        with pytest.MonkeyPatch.context() as mp:
            import ytcli.commands.create as create_mod
            from unittest.mock import MagicMock
            mock_scraper = MagicMock()
            mock_scraper.download_audio.side_effect = [
                "/tmp/audio1.mp3",
                "/tmp/audio2.mp3",
            ]
            mp.setattr(create_mod, "scraper", mock_scraper)

            result = runner.invoke(cli, [
                "--data-dir", tmp_data_dir,
                "batch-audio", str(url_file),
            ])
            data = parse_json(result.output)
            assert data["ok"] is True
            assert data["data"]["total"] == 2
            assert data["data"]["succeeded"] == 2


# --- Export command ---


class TestExport:
    def _seed(self, data_dir):
        conn = db.get_connection(data_dir)
        db.upsert_channel(conn, {
            "id": "UC1", "handle": "@testch", "name": "Test Channel",
        })
        for i in range(3):
            db.upsert_video(conn, {
                "id": f"v{i}",
                "channel_id": "UC1",
                "title": f"Video {i}",
                "published_at": f"2025-01-0{i + 1}",
                "duration_seconds": 300 + i * 60,
                "view_count": 1000 * (i + 1),
                "like_count": 50 * (i + 1),
            })
        conn.close()

    def test_export_json(self, runner, tmp_data_dir):
        """--format json outputs video list as JSON."""
        self._seed(tmp_data_dir)
        result = runner.invoke(cli, [
            "--data-dir", tmp_data_dir,
            "export", "@testch", "--format", "json",
        ])
        data = parse_json(result.output)
        assert data["ok"] is True
        assert data["data"]["channel"] == "Test Channel"
        assert data["data"]["format"] == "json"
        assert data["data"]["count"] == 3
        assert len(data["data"]["data"]) == 3

    def test_export_csv(self, runner, tmp_data_dir):
        """--format csv outputs CSV string in data."""
        self._seed(tmp_data_dir)
        result = runner.invoke(cli, [
            "--data-dir", tmp_data_dir,
            "export", "@testch", "--format", "csv",
        ])
        data = parse_json(result.output)
        assert data["ok"] is True
        assert data["data"]["format"] == "csv"
        assert data["data"]["count"] == 3
        csv_str = data["data"]["csv"]
        import csv as csv_mod
        import io
        reader = csv_mod.reader(io.StringIO(csv_str))
        rows = list(reader)
        # Header + 3 data rows
        assert len(rows) == 4
        assert "title" in rows[0]

    def test_export_channel_not_found(self, runner, tmp_data_dir):
        """Non-existent channel returns error."""
        result = runner.invoke(cli, [
            "--data-dir", tmp_data_dir,
            "export", "@nonexistent",
        ])
        data = parse_json(result.output)
        assert data["ok"] is False
