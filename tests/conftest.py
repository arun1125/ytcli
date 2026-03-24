"""Shared test fixtures and helpers for ytcli tests."""

import json


def parse_json(output: str) -> dict:
    """Extract JSON from CLI output, skipping any non-JSON lines (progress messages)."""
    for line in output.strip().split("\n"):
        line = line.strip()
        if line.startswith("{"):
            return json.loads(line)
    raise ValueError(f"No JSON found in output: {output!r}")
