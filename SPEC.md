# ytcli — Specification

## Philosophy

CLI tools are the new API layer for AI agents. The human expresses intent → their agent picks the right `ytcli` subcommand → the CLI does the work. The localhost dashboard is the human's window into the same data.

All output goes to stdout as JSON: `{"ok": bool, "command": str, "data": {...}}`.
All progress/errors go to stderr.
Exit codes: 0=success, 1=failure, 2=usage error.

## Architecture

```
ytcli/
├── cli.py              # Click entry point, group registration
├── commands/
│   ├── __init__.py
│   ├── download.py     # Tier 1: download, audio, transcript, thumbnail, metadata
│   ├── channel.py      # Tier 2: scan, channels, videos, search, refresh
│   ├── analytics.py    # Tier 3: auth, stats, performance, top, comments
│   ├── compete.py      # Tier 4: compare, gaps, hooks, calendar, niche
│   └── create.py       # Tier 5: ideas, titles, tags, batch-audio, export
├── core/
│   ├── __init__.py
│   ├── db.py           # SQLite schema, migrations, CRUD
│   ├── scraper.py      # yt-dlp wrapper (subprocess calls)
│   ├── api.py          # YouTube Data API v3 client
│   ├── analyzer.py     # Local computation (patterns, gaps, hooks)
│   └── output.py       # JSON output formatting
├── dashboard/
│   └── index.html      # Single-file localhost dashboard
└── skills/             # Premade agent workflow files
    ├── competitor-analysis.md
    ├── content-ideation.md
    └── download-pipeline.md
```

## Database Schema (SQLite)

```sql
-- Core tables
CREATE TABLE channels (
    id TEXT PRIMARY KEY,              -- YouTube channel ID (UC...)
    handle TEXT,                       -- @handle
    name TEXT NOT NULL,
    description TEXT,
    subscriber_count INTEGER,
    video_count INTEGER,
    view_count INTEGER,
    thumbnail_url TEXT,
    custom_url TEXT,
    country TEXT,
    created_at TEXT,                   -- channel creation date
    scanned_at TEXT,                   -- last scan timestamp
    api_refreshed_at TEXT,             -- last API data pull
    is_own_channel BOOLEAN DEFAULT 0
);

CREATE TABLE videos (
    id TEXT PRIMARY KEY,              -- YouTube video ID
    channel_id TEXT NOT NULL REFERENCES channels(id),
    title TEXT NOT NULL,
    description TEXT,
    published_at TEXT,
    duration_seconds INTEGER,
    view_count INTEGER,
    like_count INTEGER,
    comment_count INTEGER,
    tags TEXT,                         -- JSON array
    category_id TEXT,
    thumbnail_url TEXT,
    has_captions BOOLEAN,
    is_short BOOLEAN,
    scraped_at TEXT,
    api_refreshed_at TEXT
);

CREATE TABLE comments (
    id TEXT PRIMARY KEY,
    video_id TEXT NOT NULL REFERENCES videos(id),
    author TEXT,
    text TEXT NOT NULL,
    like_count INTEGER DEFAULT 0,
    published_at TEXT,
    is_reply BOOLEAN DEFAULT 0,
    parent_id TEXT,
    scraped_at TEXT
);

CREATE TABLE transcripts (
    video_id TEXT PRIMARY KEY REFERENCES videos(id),
    text TEXT NOT NULL,
    language TEXT DEFAULT 'en',
    is_auto_generated BOOLEAN,
    fetched_at TEXT
);

CREATE TABLE downloads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id TEXT REFERENCES videos(id),
    url TEXT NOT NULL,
    format TEXT,                       -- mp3, mp4, wav, etc.
    output_path TEXT,
    downloaded_at TEXT
);

-- Config
CREATE TABLE config (
    key TEXT PRIMARY KEY,
    value TEXT
);

-- Indexes
CREATE INDEX idx_videos_channel ON videos(channel_id);
CREATE INDEX idx_videos_published ON videos(published_at);
CREATE INDEX idx_comments_video ON comments(video_id);
CREATE INDEX idx_videos_views ON videos(view_count);
```

## Command Reference

### Meta Commands

| Command | Description |
|---------|-------------|
| `ytcli init [--dir PATH]` | Create data directory (~/.ytcli/) and database |
| `ytcli status` | Tracked channels, video count, DB size, last refreshes |
| `ytcli config KEY [VALUE]` | Get/set config (api_key, output_dir, default_format) |
| `ytcli serve [--port 8888]` | Launch localhost dashboard |

### Tier 1: Download & Extract (yt-dlp, no API key)

| Command | Description |
|---------|-------------|
| `ytcli download URL [--format mp4] [--quality 1080]` | Download video |
| `ytcli audio URL [--format mp3] [--quality best]` | Extract audio only |
| `ytcli transcript URL [--lang en]` | Get subtitles as clean text |
| `ytcli thumbnail URL [--output PATH]` | Download thumbnail image |
| `ytcli metadata URL` | Dump video metadata JSON |

### Tier 2: Channel Intelligence (yt-dlp scraping → SQLite)

| Command | Description |
|---------|-------------|
| `ytcli scan CHANNEL [--limit N]` | Scrape channel video metadata → DB |
| `ytcli channels` | List all tracked channels |
| `ytcli videos CHANNEL [--sort date\|views\|duration] [--limit N]` | List channel videos |
| `ytcli search QUERY [--channel CH]` | Full-text search across stored videos |
| `ytcli refresh [CHANNEL]` | Re-scan for new uploads since last scan |

### Tier 3: Analytics (YouTube Data API v3, requires API key)

| Command | Description |
|---------|-------------|
| `ytcli auth [--api-key KEY]` | Set up API authentication |
| `ytcli stats CHANNEL` | Subscriber count, views, growth |
| `ytcli performance VIDEO_URL` | Views, likes, engagement metrics |
| `ytcli top CHANNEL [--by views\|engagement\|growth] [--limit 10]` | Best performing videos |
| `ytcli comments VIDEO_URL [--sort top\|recent] [--limit 100]` | Pull video comments |

### Tier 4: Competitive Analysis (local computation)

| Command | Description |
|---------|-------------|
| `ytcli compare CH1 CH2` | Side-by-side: frequency, duration, topics, patterns |
| `ytcli gaps CHANNEL` | Content topics they haven't covered |
| `ytcli hooks CHANNEL [--limit 20]` | Title/thumbnail pattern analysis |
| `ytcli calendar CHANNEL` | Upload schedule and frequency trends |
| `ytcli niche QUERY [--limit 10]` | Find channels in a niche |

### Tier 5: Creation Assist

| Command | Description |
|---------|-------------|
| `ytcli ideas [--from CHANNEL] [--count 10]` | Generate video ideas from gaps/trends |
| `ytcli titles TOPIC [--count 5]` | Generate title variations from patterns |
| `ytcli tags VIDEO_URL\|TOPIC` | Suggest tags based on similar content |
| `ytcli batch-audio FILE\|PLAYLIST_URL [--format mp3]` | Bulk audio download |
| `ytcli export CHANNEL [--format csv\|json]` | Export channel data |

## Config Keys

| Key | Default | Description |
|-----|---------|-------------|
| `api_key` | None | YouTube Data API v3 key |
| `output_dir` | `./downloads` | Default download directory |
| `default_format` | `mp4` | Default video format |
| `default_audio_format` | `mp3` | Default audio format |
| `data_dir` | `~/.ytcli` | Database and cache location |

## Agent Integration

Agents call `ytcli` subcommands and parse JSON stdout. Example workflows:

**Competitor analysis:**
```bash
ytcli scan @mkbhd --limit 50
ytcli scan @dave2d --limit 50
ytcli compare @mkbhd @dave2d
ytcli hooks @mkbhd
ytcli gaps @mkbhd
```

**Content ideation (with Eureka):**
```bash
ytcli transcript "https://youtube.com/watch?v=..." > /tmp/transcript.txt
eureka ingest /tmp/transcript.txt --brain-dir ./brain
eureka discover ./brain --count 10
```

**Audio extraction for video production:**
```bash
ytcli batch-audio playlist.txt --format mp3
```

## Build Order

Session 1: ~~Scaffold + init/status/config + DB + output + tests~~ DONE
Session 2: ~~Tier 1 (download commands — yt-dlp wrappers)~~ DONE
Session 3: ~~Tier 2 (channel intelligence — scraping + SQLite)~~ DONE
Session 4: ~~Tier 3 (analytics — YouTube API)~~ DONE
Session 5: ~~Tier 4 (competitive analysis — local computation)~~ DONE
Session 6: ~~Tier 5 (creation assist)~~ DONE
Session 7: Dashboard (localhost) ← NEXT
Session 8: Agent skills + Eureka bridge workflows

## Session 2: Tier 1 Implementation Tasks

All commands use `core/scraper.py` (yt-dlp subprocess wrapper). All output JSON to stdout via `core/output.py`.
Tests must mock yt-dlp subprocess calls — never hit real YouTube in tests.
Working directory: `/Users/arun/Desktop/00_Organized/Agents/work/ytcli/`

### Tasks

- [x] Write tests for `metadata` command in `tests/test_download.py` — mock `scraper.get_video_metadata()`, assert JSON output contains title/description/duration/view_count/published_at. Test error handling for invalid URL.
- [x] Implement `metadata` command — wire `commands/download.py::metadata` to `core/scraper.get_video_metadata()`. Parse yt-dlp JSON, extract key fields (id, title, description, channel, duration, view_count, like_count, comment_count, published_at, tags, thumbnail_url, has_captions), output via `success()`.
- [x] Write tests for `download` command — mock `scraper.download_video()`, assert JSON output contains output_path. Test default format/quality and custom options.
- [x] Implement `download` command — wire to `core/scraper.download_video()`. Use config `output_dir` as default. Record download in DB `downloads` table. Output path in JSON.
- [x] Write tests for `audio` command — mock `scraper.download_audio()`, assert JSON output. Test mp3/wav format options.
- [x] Implement `audio` command — wire to `core/scraper.download_audio()`. Use config `default_audio_format` as fallback. Record in `downloads` table. Output path in JSON.
- [x] Write tests for `transcript` command — mock `scraper.get_transcript()`, assert clean text output in JSON data field. Test language option.
- [x] Implement `transcript` command — wire to `core/scraper.get_transcript()`. Store in `transcripts` table. Output text in JSON. Also upsert the video record if we have its metadata.
- [x] Write tests for `thumbnail` command — mock `scraper.download_thumbnail()`, assert output_path in JSON.
- [x] Implement `thumbnail` command — wire to `core/scraper.download_thumbnail()`. Output path in JSON.

## Session 3: Tier 2 Implementation Tasks (Channel Intelligence)

These commands scrape channel data via yt-dlp and store in SQLite. All output JSON to stdout.
Tests must mock `scraper` functions — never hit real YouTube.
Working directory: `/Users/arun/Desktop/00_Organized/Agents/work/ytcli/`

### Context for implementers
- `core/scraper.py` has `get_channel_videos(channel_url, limit)` which returns list of dicts from `yt-dlp --dump-json --flat-playlist`
- `core/scraper.py` has `get_video_metadata(url)` for full video detail
- `core/db.py` has `upsert_channel()`, `upsert_video()`, `get_channel()`, `get_channels()`, `get_videos()`, `search_videos()`
- Channel handles like `@mkbhd` need to be converted to `https://www.youtube.com/@mkbhd` for yt-dlp
- yt-dlp flat-playlist returns minimal fields (id, title, url). For full metadata, need a second `get_video_metadata()` call per video — but for scan, flat-playlist fields + duration/view_count from the flat entry are enough for v1.
- The `scan` command should: resolve channel handle → scrape video list → upsert channel record → upsert each video → report count

### Tasks

- [x] Write tests for `scan` command in `tests/test_channel.py` — mock `scraper.get_channel_videos()`, assert channel and videos stored in DB. Test `--limit` flag. Test error handling for invalid channel.
- [x] Implement `scan` command — resolve channel handle to URL, call `scraper.get_channel_videos()`, upsert channel + videos in DB, output JSON with channel name and video count. Must init DB if needed.
- [x] Write tests for `channels` command — seed DB with 2 channels, assert JSON lists both with name/handle/video_count/scanned_at.
- [x] Implement `channels` command — call `db.get_channels()`, output JSON list.
- [x] Write tests for `videos` command — seed DB with channel + videos, test `--sort` (date/views/duration) and `--limit` flags.
- [x] Implement `videos` command — resolve channel arg to channel_id, call `db.get_videos()`, output JSON list.
- [x] Write tests for `search` command — seed DB with videos, assert text search finds matches. Test `--channel` filter.
- [x] Implement `search` command — call `db.search_videos()`, output JSON results.
- [x] Write tests for `refresh` command — mock scraper, seed DB with channel scanned_at in the past, assert only new videos added.
- [x] Implement `refresh` command — for each tracked channel (or specified one), re-scan and upsert only new videos. Update scanned_at timestamp.

## Session 4: Tier 3 Implementation Tasks (Analytics — YouTube API)

These commands use the YouTube Data API v3. Requires API key stored via `ytcli config api_key KEY`.
All commands must check for API key first and return clear error if missing.
Tests mock the API client — never hit real YouTube API.
Working directory: `/Users/arun/Desktop/00_Organized/Agents/work/ytcli/`

### Context for implementers
- `core/api.py` needs to be built — wrap `googleapiclient.discovery.build("youtube", "v3", developerKey=key)`
- API key is stored in DB config table: `db.get_config(conn, "api_key")`
- YouTube Data API v3 endpoints needed:
  - `youtube.channels().list(part="statistics,snippet", forHandle=handle)` — channel stats
  - `youtube.videos().list(part="statistics,snippet", id=video_id)` — video stats
  - `youtube.commentThreads().list(part="snippet", videoId=id)` — comments
  - `youtube.search().list(part="snippet", q=query, type="video")` — search
- The API is optional — `google-api-python-client` is in `[project.optional-dependencies]`
- If the import fails, commands should error with "Install API dependencies: pip install ytcli[api]"

### Tasks

- [x] Build `core/api.py` — YouTube API client wrapper with functions: `get_api_client(api_key)`, `get_channel_stats(client, channel_handle_or_id)`, `get_video_stats(client, video_id)`, `get_comments(client, video_id, sort, limit)`, `search_youtube(client, query, limit)`. Each returns plain dicts. Write tests in `tests/test_api.py` mocking `googleapiclient`.
- [x] Write tests for `auth` command in `tests/test_analytics.py` — test that `auth --api-key KEY` stores key in config, test that `auth` without key shows current status.
- [x] Implement `auth` command — store API key in DB config, verify it works with a test API call (mock in tests), output success/failure.
- [x] Write tests for `stats` command — mock `api.get_channel_stats()`, assert JSON output with subscriber_count, view_count, video_count. Test missing API key error.
- [x] Implement `stats` command — get API key from config, call `api.get_channel_stats()`, also update channel record in DB with fresh stats. Output JSON.
- [x] Write tests for `performance` command — mock `api.get_video_stats()`, assert JSON with views, likes, comments, engagement rate.
- [x] Implement `performance` command — extract video ID from URL, call `api.get_video_stats()`, compute engagement rate, output JSON.
- [x] Write tests for `top` command — seed DB with channel videos, mock API to enrich with stats, assert sorted output. Test `--by` flag and `--limit`.
- [x] Implement `top` command — get videos from DB for channel, enrich with API stats, sort by views/engagement/growth, output top N.
- [x] Write tests for `comments` command — mock `api.get_comments()`, assert JSON list with author, text, likes. Test `--sort` and `--limit`.
- [x] Implement `comments` command — extract video ID, call `api.get_comments()`, store in DB comments table, output JSON.

## Session 5: Tier 4 Implementation Tasks (Competitive Analysis)

Local computation over stored data. These commands read from SQLite and compute patterns/comparisons.
No API calls needed (data must be scanned first). Tests seed the DB directly.
Working directory: `/Users/arun/Desktop/00_Organized/Agents/work/ytcli/`

### Context for implementers
- `core/analyzer.py` needs to be built — pure functions that take video/channel data and return analysis
- All data comes from `core/db.py` — channels and videos tables
- `commands/compete.py` has stub commands for: compare, gaps, hooks, calendar, niche

### Tasks

- [x] Build `core/analyzer.py` with analysis functions, write tests in `tests/test_analyzer.py`:
  - `compare_channels(ch1_videos, ch2_videos, ch1_info, ch2_info)` — returns dict with upload_frequency, avg_duration, avg_views, topic_overlap, title_length stats for each
  - `analyze_hooks(videos)` — extract title patterns: avg length, common words (excluding stopwords), question titles %, number usage %, bracket/parenthesis usage %
  - `analyze_upload_schedule(videos)` — day-of-week distribution, time-of-day distribution (if available), frequency (videos/week), streak/gap analysis
  - `find_content_gaps(videos, reference_topics=None)` — extract topics from titles/descriptions via keyword extraction, find underrepresented topics
- [x] Write tests for `compare` command in `tests/test_compete.py` — seed 2 channels with videos, assert comparison JSON has both channels' stats side-by-side.
- [x] Implement `compare` command — resolve both channels, get their videos, call `analyzer.compare_channels()`, output JSON.
- [x] Write tests for `hooks` command — seed channel with videos with various title patterns, assert analysis JSON.
- [x] Implement `hooks` command — resolve channel, get videos, call `analyzer.analyze_hooks()`, output JSON.
- [x] Write tests for `gaps` command — seed channel with videos, assert gap analysis JSON.
- [x] Implement `gaps` command — resolve channel, get videos, call `analyzer.find_content_gaps()`, output JSON.
- [x] Write tests for `calendar` command — seed channel with videos at various dates, assert schedule analysis JSON.
- [x] Implement `calendar` command — resolve channel, get videos, call `analyzer.analyze_upload_schedule()`, output JSON.
- [x] Write tests for `niche` command — mock `api.search_youtube()`, assert channel discovery JSON. Test `--limit`.
- [x] Implement `niche` command — search YouTube for query, group results by channel, rank by frequency/views, output top channels.

## Session 6: Tier 5 Implementation Tasks (Creation Assist)

These commands help with content creation — idea generation, title optimization, tagging, bulk downloads, and data export.
Working directory: `/Users/arun/Desktop/00_Organized/Agents/work/ytcli/`

### Tasks

- [x] Write tests for `ideas` command in `tests/test_create.py` — seed DB with channel videos, assert JSON output with idea list. Test `--from` channel filter and `--count` flag.
- [x] Implement `ideas` command — combine gap analysis + hook analysis + high-performing topics to generate video idea suggestions. Use `analyzer.find_content_gaps()` and `analyzer.analyze_hooks()` on stored data. Each idea: topic, reasoning, inspired_by (source videos). Output JSON list.
- [x] Write tests for `titles` command — assert JSON output with title variations. Test `--count` flag.
- [x] Implement `titles` command — take TOPIC arg, search DB for similar videos, extract title patterns from high-view videos, generate variations using the patterns (question format, number format, bracket format, how-to format). Pure string manipulation, no LLM. Output JSON list of title suggestions.
- [x] Write tests for `tags` command — test with URL (extract video tags) and with topic string (suggest from DB). Assert JSON output.
- [x] Implement `tags` command — if input looks like URL, get video metadata and return its tags. If topic string, search DB for similar videos and aggregate their most common tags. Output JSON.
- [x] Write tests for `batch-audio` command — mock `scraper.download_audio()`, test with playlist URL and with file path containing URLs. Assert JSON with download results.
- [x] Implement `batch-audio` command — if input is URL, treat as playlist. If file path, read URLs from file (one per line). Download each via `scraper.download_audio()`. Record in DB. Output JSON summary.
- [x] Write tests for `export` command — seed DB with channel + videos, test CSV and JSON format output. Test `--format` flag.
- [x] Implement `export` command — resolve channel, get all videos, format as CSV or JSON, write to file or stdout. Output JSON with file path or inline data.
