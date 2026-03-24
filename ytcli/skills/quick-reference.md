# ytcli Quick Reference

## Setup
```bash
ytcli init                              # Create database
ytcli config api_key YOUR_KEY           # Optional: YouTube API key
ytcli config output_dir ./downloads     # Set download directory
```

## Every command at a glance

### Download & Extract (no API key needed)
```bash
ytcli download URL [--format mp4] [--quality 1080]
ytcli audio URL [--format mp3] [--quality best]
ytcli transcript URL [--lang en]
ytcli thumbnail URL [--output PATH]
ytcli metadata URL
ytcli batch-audio FILE_OR_URL [--format mp3]
```

### Channel Tracking
```bash
ytcli scan @channel [--limit 100]
ytcli channels
ytcli videos @channel [--sort views|date|duration] [--limit 50]
ytcli search "query" [--channel @ch]
ytcli refresh [@channel]
ytcli export @channel [--format csv|json]
```

### Analytics (requires API key)
```bash
ytcli auth [--api-key KEY]
ytcli stats @channel
ytcli performance VIDEO_URL
ytcli top @channel [--by views|engagement] [--limit 10]
ytcli comments VIDEO_URL [--sort top|recent] [--limit 100]
```

### Competitive Analysis
```bash
ytcli compare @ch1 @ch2
ytcli gaps @channel
ytcli hooks @channel [--limit 20]
ytcli calendar @channel
ytcli niche "query" [--limit 10]
```

### Content Creation
```bash
ytcli ideas [--from @channel] [--count 10]
ytcli titles "topic" [--count 5]
ytcli tags VIDEO_URL|"topic"
```

### Meta
```bash
ytcli init [--dir PATH]
ytcli status
ytcli config KEY [VALUE]
ytcli serve [--port 8888]
```

## Output format
All commands return JSON to stdout:
```json
{"ok": true, "command": "scan", "data": {"channel": "MKBHD", "videos_found": 100}}
```
Errors:
```json
{"ok": false, "command": "stats", "error": "No API key configured"}
```
Progress messages go to stderr.

## Common first-time flow
```bash
ytcli init
ytcli scan @mkbhd --limit 50
ytcli hooks @mkbhd
ytcli gaps @mkbhd
ytcli ideas --from @mkbhd --count 5
```
