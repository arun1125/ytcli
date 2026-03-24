# Channel Tracking

## When to use
- "Track this channel"
- "What channels am I following?"
- "Show me their latest videos"
- "What's new on @channel?"
- "Export channel data"

## Setup
```bash
ytcli init    # One-time setup
```

## Add a channel
```bash
ytcli scan @mkbhd --limit 100
```
Scrapes video metadata into local DB. Use `--limit` to control how far back to go.

Accepts:
- `@handle` format: `@mkbhd`
- Full URL: `https://youtube.com/@mkbhd`

## List tracked channels
```bash
ytcli channels
```
Returns all channels in DB with name, handle, video count, last scanned date.

## Browse a channel's videos
```bash
ytcli videos @mkbhd --sort views --limit 20
```
Sort options: `date` (newest first), `views` (most viewed), `duration` (longest first).

## Search across all channels
```bash
ytcli search "python tutorial"
ytcli search "machine learning" --channel @mkbhd
```
Full-text search on titles and descriptions. Optional channel filter.

## Check for new uploads
```bash
ytcli refresh              # Refresh all tracked channels
ytcli refresh @mkbhd       # Refresh one channel
```
Adds new videos since last scan, updates existing video data, updates `scanned_at` timestamp.

## Export data
```bash
ytcli export @mkbhd --format json
ytcli export @mkbhd --format csv
```
Exports all video data for a channel. CSV includes: id, title, published_at, duration, views, likes.

## Check status
```bash
ytcli status
```
Returns: total channels, total videos, total comments, database size.

## Tips
- Scan channels you want to analyze before running any analysis commands
- `ytcli refresh` is cheap — run it before analysis to get latest data
- Export to CSV for spreadsheet analysis or sharing
