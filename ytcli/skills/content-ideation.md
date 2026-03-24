# Content Ideation Workflow

## When to use
User wants video ideas, is brainstorming, or wants to find content gaps.

## Steps

### 1. Scan relevant channels for inspiration
```bash
ytcli scan @channel1 --limit 50
ytcli scan @channel2 --limit 50
```

### 2. Find what's working
```bash
ytcli top @channel1 --by engagement --limit 10
ytcli hooks @channel1
```

### 3. Find gaps
```bash
ytcli gaps @channel1
```

### 4. Pull comments for pain points
```bash
ytcli comments "VIDEO_URL" --sort top --limit 200
```

### 5. Generate ideas
```bash
ytcli ideas --from @channel1 --count 10
```

### 6. Generate titles for best ideas
```bash
ytcli titles "chosen topic" --count 5
```

### 7. Optional: Cross-reference with knowledge base
```bash
# Transcribe a reference video
ytcli transcript "VIDEO_URL" > /tmp/ref.txt
eureka ingest /tmp/ref.txt --brain-dir ./brain
eureka discover ./brain --count 10
```

## Tips
- Comments on top-performing videos are gold for pain points
- Gaps between two similar channels reveal underserved topics
- Cross-referencing with Eureka finds non-obvious angles
