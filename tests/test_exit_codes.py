"""Tests for consistent exit codes — all error paths must exit non-zero."""

import json

import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock

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


# Parametrized test: each tuple is (command_args, description)
# All should produce exit_code != 0 and ok=False in JSON output.
CHANNEL_NOT_FOUND_CASES = [
    # Tier 2: channel.py
    (["videos", "@ghost"], "videos: channel not found"),
    (["search", "query", "--channel", "@ghost"], "search: channel not found"),
    (["refresh", "@ghost"], "refresh: channel not found"),
    # Tier 4: compete.py
    (["compare", "@ghost1", "@ghost2"], "compare: first channel not found"),
    (["gaps", "@ghost"], "gaps: channel not found"),
    (["hooks", "@ghost"], "hooks: channel not found"),
    (["calendar", "@ghost"], "calendar: channel not found"),
    # Tier 5: create.py
    (["export", "@ghost"], "export: channel not found"),
]


@pytest.mark.parametrize("cmd_args,desc", CHANNEL_NOT_FOUND_CASES)
def test_error_exit_code_nonzero(runner, tmp_data_dir, cmd_args, desc):
    """Error conditions must produce exit_code != 0."""
    result = runner.invoke(cli, ["--data-dir", tmp_data_dir] + cmd_args)
    assert result.exit_code != 0, f"{desc}: expected non-zero exit code, got {result.exit_code}\noutput: {result.output}"
    data = parse_json(result.output)
    assert data["ok"] is False, f"{desc}: expected ok=False"


def test_scan_empty_result_exits_nonzero(runner, tmp_data_dir):
    """scan with empty scraper result must exit non-zero."""
    with patch("ytcli.commands.channel.scraper") as mock_scraper:
        mock_scraper.get_channel_videos.return_value = []
        result = runner.invoke(cli, ["--data-dir", tmp_data_dir, "scan", "@empty"])
        assert result.exit_code != 0
        data = parse_json(result.output)
        assert data["ok"] is False


def test_niche_missing_api_key_exits_nonzero(runner, tmp_data_dir):
    """niche without API key must exit non-zero."""
    result = runner.invoke(cli, ["--data-dir", tmp_data_dir, "niche", "python"])
    assert result.exit_code != 0
    data = parse_json(result.output)
    assert data["ok"] is False


def test_ideas_no_videos_exits_nonzero(runner, tmp_data_dir):
    """ideas with no videos in DB must exit non-zero."""
    result = runner.invoke(cli, ["--data-dir", tmp_data_dir, "ideas"])
    assert result.exit_code != 0
    data = parse_json(result.output)
    assert data["ok"] is False


def test_refresh_no_channels_exits_nonzero(runner, tmp_data_dir):
    """refresh with no tracked channels must exit non-zero."""
    result = runner.invoke(cli, ["--data-dir", tmp_data_dir, "refresh"])
    assert result.exit_code != 0
    data = parse_json(result.output)
    assert data["ok"] is False
