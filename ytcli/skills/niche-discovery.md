# Niche Discovery

## When to use
- "What channels are in this niche?"
- "Who's making content about X?"
- "Find competitors in my space"
- "Map out a YouTube niche"

## Prerequisites
- API key required: `ytcli config api_key YOUR_KEY`

## Workflow

### Step 1: Search the niche
```bash
ytcli niche "productivity apps for developers" --limit 10
```
Searches YouTube, groups results by channel, ranks by frequency. Returns channels that appear most often for that query — the key players.

### Step 2: Scan top channels
```bash
ytcli scan @channel1 --limit 100
ytcli scan @channel2 --limit 100
ytcli scan @channel3 --limit 100
```

### Step 3: Compare the landscape
```bash
ytcli compare @channel1 @channel2
ytcli compare @channel1 @channel3
```
Reveals: who posts more, who gets more views, how much topic overlap exists.

### Step 4: Find the gaps
```bash
ytcli gaps @channel1
ytcli gaps @channel2
```
Low-frequency topics across multiple channels = underserved niche.

### Step 5: Study what wins
```bash
ytcli hooks @channel1 --limit 50
ytcli top @channel1 --by views --limit 10
```
Learn what title patterns and topics get views in this niche.

## Interpreting niche search results

| Pattern | Meaning |
|---------|---------|
| Few channels, high views | Underserved niche with demand |
| Many channels, low views | Saturated, hard to break in |
| One dominant channel | Room for alternatives/differentiation |
| Fragmented (many small channels) | No clear leader — opportunity |

## Quick version
```bash
ytcli niche "your topic" --limit 5
# Then scan the top 2-3 results
```
