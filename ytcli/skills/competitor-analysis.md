# Competitor Analysis Workflow

## When to use
User wants to analyze a YouTube channel, compare channels, or find content gaps.

## Steps

### 1. Scan the channel(s)
```bash
ytcli scan @competitor_channel --limit 100
```

### 2. Get channel stats (requires API key)
```bash
ytcli stats @competitor_channel
```

### 3. Find their best content
```bash
ytcli top @competitor_channel --by views --limit 20
```

### 4. Analyze their patterns
```bash
ytcli hooks @competitor_channel --limit 20
ytcli calendar @competitor_channel
```

### 5. Compare with own channel (if applicable)
```bash
ytcli compare @my_channel @competitor_channel
ytcli gaps @competitor_channel
```

### 6. Optional: Feed insights to Eureka
```bash
ytcli export @competitor_channel --format json > /tmp/competitor.json
# Agent can summarize and pipe to eureka dump
```

## Output interpretation
- `hooks` shows title patterns, common words, avg title length
- `gaps` shows topics with search demand but no coverage
- `compare` gives side-by-side metrics
- `calendar` shows posting schedule and consistency
