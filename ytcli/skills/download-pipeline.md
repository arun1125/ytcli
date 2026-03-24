# Download Pipeline Workflow

## When to use
User wants to download videos, extract audio, get transcripts, or grab thumbnails.

## Single video

### Download video
```bash
ytcli download "VIDEO_URL" --format mp4 --quality 1080
```

### Extract audio (for music, samples, b-roll)
```bash
ytcli audio "VIDEO_URL" --format mp3 --quality best
```

### Get transcript
```bash
ytcli transcript "VIDEO_URL" --lang en
```

### Get thumbnail
```bash
ytcli thumbnail "VIDEO_URL"
```

### Get metadata
```bash
ytcli metadata "VIDEO_URL"
```

## Bulk operations

### Batch audio from playlist
```bash
ytcli batch-audio "PLAYLIST_URL" --format mp3
```

### Batch audio from file (one URL per line)
```bash
ytcli batch-audio urls.txt --format wav
```

## Common patterns

### Transcribe for Eureka ingestion
```bash
ytcli transcript "VIDEO_URL" > /tmp/transcript.txt
eureka ingest /tmp/transcript.txt --brain-dir ./brain
```

### Download audio for video production
```bash
ytcli audio "VIDEO_URL" --format wav --quality best
# wav for editing, mp3 for final
```

### Get all metadata without downloading
```bash
ytcli metadata "VIDEO_URL"
# Returns: title, description, duration, view count, tags, upload date
```
