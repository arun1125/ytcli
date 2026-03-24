# ytcli

YouTube CLI for AI agents and creators. Read `SPEC.md` for full command map and DB schema.

## Quick Reference

```bash
pip install -e .          # Install in dev mode
ytcli --help              # All commands
ytcli init                # Create ~/.ytcli/ and database
ytcli status              # What's tracked
pytest                    # Run tests
```

## Architecture

- **CLI:** Click-based, one file per command group in `ytcli/commands/`
- **DB:** SQLite at `~/.ytcli/ytcli.db` (schema in SPEC.md)
- **Output:** All commands emit JSON to stdout, progress to stderr
- **Scraping:** yt-dlp via subprocess (no library import)
- **API:** YouTube Data API v3 (optional, requires API key)
- **Dashboard:** Single HTML file served by `ytcli serve`

## Adding a New Command

1. Pick the right command group file in `ytcli/commands/`
2. Add a Click command function with `@group.command()`
3. Use `core/output.py` for JSON output
4. Use `core/db.py` for database operations
5. Use `core/scraper.py` for yt-dlp calls
6. Add tests in `tests/test_<group>.py`
7. Update SPEC.md command table

## Rules

- JSON stdout, progress stderr. No exceptions.
- yt-dlp via subprocess, not library import (yt-dlp API is unstable)
- Tests before features. Reproduce before fixing.
- One command per logical unit. Don't merge concerns.
- `trash` not `rm -rf`

## Dependencies

- `click` — CLI framework
- `yt-dlp` — YouTube scraping/downloading (subprocess)
- `google-api-python-client` — YouTube Data API (optional)
- `google-auth-oauthlib` — OAuth for API (optional)

## Data Directory

Default: `~/.ytcli/`
```
~/.ytcli/
├── ytcli.db          # SQLite database
├── downloads/        # Downloaded files
└── cache/            # Thumbnail cache, temp files
```
