# Content Ideation

## When to use
- "Give me video ideas"
- "What should I make next?"
- "Find me content gaps"
- "What topics are underserved?"

## Prerequisites
- At least one channel scanned: `ytcli scan @channel --limit 100`
- More scanned channels = better ideas

## Full workflow

### Step 1: Scan inspiration channels
```bash
ytcli scan @inspiration1 --limit 100
ytcli scan @inspiration2 --limit 100
```

### Step 2: Generate ideas from gaps and patterns
```bash
ytcli ideas --from @inspiration1 --count 10
```
Returns ideas combining:
- Gap-based: topics the channel barely covers (low-frequency keywords)
- High-performer: topics from their most-viewed videos
- Each idea includes: `topic`, `reasoning`, `inspired_by` (source videos)

### Step 3: Generate title variations
```bash
ytcli titles "chosen topic" --count 10
```
Generates titles in 4 patterns:
- Question: "What Is X?" / "Why Does X Matter?"
- Number: "7 X Tips" / "Top 5 X Mistakes"
- How-to: "How to X (Step by Step)"
- Bracket: "X [Complete Guide]" / "X (You Won't Believe This)"

If similar videos exist in DB, patterns are weighted by what works in your niche.

### Step 4: Get tags
```bash
ytcli tags "chosen topic"
```
Aggregates tags from similar videos in DB, ranked by frequency.

### Step 5: Study what works in the niche
```bash
ytcli hooks @inspiration1 --limit 50
ytcli top @inspiration1 --by views --limit 10
```

### Step 6: Mine comments for requests
```bash
ytcli comments "TOP_VIDEO_URL" --sort top --limit 200
```
Look for: "Can you make a video about...", "I wish someone would explain...", repeated questions.

## Quick version (2 commands)
```bash
ytcli ideas --count 10
ytcli titles "best idea" --count 5
```

## Tips
- Scan 3-5 channels in your niche for better gap detection
- Comments on top videos are the highest-signal source of ideas
- `ytcli gaps` finds what's underserved; `ytcli hooks` tells you how to package it
