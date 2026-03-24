"""Standardized JSON output for agent consumption."""

import json
import click


def success(command: str, data: dict) -> None:
    """Print success JSON to stdout."""
    payload = {"ok": True, "command": command, "data": data}
    click.echo(json.dumps(payload, ensure_ascii=False))


def error(command: str, message: str, details: dict = None) -> None:
    """Print error JSON to stdout."""
    payload = {"ok": False, "command": command, "error": message}
    if details is not None:
        payload["details"] = details
    click.echo(json.dumps(payload, ensure_ascii=False))


def progress(message: str) -> None:
    """Print progress message to stderr."""
    click.echo(message, err=True)
