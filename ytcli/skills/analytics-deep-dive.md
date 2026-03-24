# Analytics Deep Dive

## When to use
- "How's this video performing?"
- "What are my best videos?"
- "Show me engagement rates"
- "Pull comments from this video"

## Prerequisites
- API key required: `ytcli config api_key YOUR_KEY`
- Channel should be scanned first for `top` command

## Single video performance
```bash
ytcli performance "https://youtube.com/watch?v=VIDEO_ID"
```
Returns:
- `view_count` — total views
- `like_count` — total likes
- `comment_count` — total comments
- `engagement_rate` — (likes + comments) / views * 100

## Best performing videos
```bash
ytcli top @channel --by views --limit 10
ytcli top @channel --by engagement --limit 10
```
- `--by views` — sorts by view count (from DB, no API needed if scanned)
- `--by engagement` — enriches with API data, computes engagement rate, re-sorts

## Channel stats
```bash
ytcli stats @channel
```
Returns: subscriber count, total views, video count. Updates DB with fresh data.

## Comments
```bash
ytcli comments "VIDEO_URL" --sort top --limit 100
ytcli comments "VIDEO_URL" --sort recent --limit 50
```
- `--sort top` — most liked comments first (best for understanding audience sentiment)
- `--sort recent` — newest first (best for recent feedback)

Comments are stored in DB for later search/analysis.

## Workflow: Understand what's working

```bash
# 1. Scan your channel
ytcli scan @your_channel --limit 200

# 2. Find your hits
ytcli top @your_channel --by views --limit 10

# 3. Analyze what those hits have in common
ytcli hooks @your_channel --limit 50

# 4. Deep-dive your best video
ytcli performance "YOUR_BEST_VIDEO_URL"
ytcli comments "YOUR_BEST_VIDEO_URL" --sort top --limit 200

# 5. Compare with a competitor's hits
ytcli top @competitor --by views --limit 10
ytcli compare @your_channel @competitor
```

## Tips
- Engagement rate > 5% is strong, > 10% is exceptional
- Comments sorted by "top" reveal what resonates most
- Run `stats` periodically to track subscriber growth
- `top --by engagement` is more useful than `--by views` for finding underrated content
