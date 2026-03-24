# Download Pipeline

## When to use
- "Download this video"
- "Get me the audio from this"
- "Transcribe this video"
- "I need background music from this playlist"
- "Get the thumbnail"

## No setup needed
Download commands work immediately — no `ytcli init` or API key required (uses yt-dlp).

## Single video

### Download video
```bash
ytcli download "https://youtube.com/watch?v=VIDEO_ID" --format mp4 --quality 1080
```
Options: `--format` (mp4, webm), `--quality` (1080, 720, 480, best)

### Extract audio
```bash
ytcli audio "URL" --format mp3 --quality best
```
Options: `--format` (mp3, wav, m4a, flac), `--quality` (best, 0-9)

Use **wav** for editing, **mp3** for final delivery.

### Get transcript
```bash
ytcli transcript "URL" --lang en
```
Returns clean text (timestamps and formatting stripped). Stores in DB if initialized.

### Get thumbnail
```bash
ytcli thumbnail "URL" --output ./thumbnails/
```

### Get metadata (no download)
```bash
ytcli metadata "URL"
```
Returns: title, description, duration, view count, likes, comments, tags, channel, publish date.

## Bulk operations

### Batch audio from a file
Create `urls.txt` with one URL per line:
```
https://youtube.com/watch?v=VIDEO1
https://youtube.com/watch?v=VIDEO2
https://youtube.com/watch?v=VIDEO3
```
```bash
ytcli batch-audio urls.txt --format mp3
```
Returns summary: total, succeeded, failed, with paths for each.

### Batch audio from a playlist
```bash
ytcli batch-audio "https://youtube.com/playlist?list=PLAYLIST_ID" --format mp3
```

## Common patterns

### Transcribe for research
```bash
ytcli transcript "URL" > /tmp/transcript.txt
# Now the agent can read, summarize, or ingest the transcript
```

### Download audio for video production
```bash
ytcli audio "URL" --format wav --quality best
# wav for editing software (DaVinci, Premiere)
```

### Quick metadata check
```bash
ytcli metadata "URL"
# Returns JSON — agent can check duration, view count, tags before deciding to download
```

## Output
All commands return JSON to stdout:
```json
{"ok": true, "command": "audio", "data": {"output_path": "/path/to/file.mp3", "url": "...", "format": "mp3"}}
```
Downloads are recorded in the database if `ytcli init` has been run.
