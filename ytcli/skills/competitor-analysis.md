# Competitor Analysis

## When to use
- "Analyze this channel"
- "What's @channel doing?"
- "Compare these two channels"
- "What content gaps does @channel have?"

## Prerequisites
- `ytcli init` (run once)
- Channels must be scanned first — all analysis reads from local DB
- API key optional but recommended for stats: `ytcli config api_key YOUR_KEY`

## Full workflow

### Step 1: Scan target channels
```bash
ytcli scan @competitor --limit 100
```
This scrapes all video metadata (titles, dates, durations, views) into the local database. Takes 10-30 seconds depending on channel size.

### Step 2: Get live stats (requires API key)
```bash
ytcli stats @competitor
```
Returns: subscriber count, total views, video count. Updates the DB record.

### Step 3: Analyze their title patterns
```bash
ytcli hooks @competitor --limit 50
```
Returns:
- `avg_title_length` — how long their titles are
- `common_words` — top 20 words they use (stopwords excluded)
- `question_title_pct` — % of titles that are questions
- `number_in_title_pct` — % with numbers ("7 Tips", "Top 10")
- `bracket_pct` — % with brackets ("[2024]", "(Full Guide)")
- `caps_word_pct` — % with ALL CAPS words
- `top_patterns` — ranked list of which patterns they use most

### Step 4: Analyze their upload schedule
```bash
ytcli calendar @competitor
```
Returns: day-of-week distribution, videos/week, longest streak, longest gap.

### Step 5: Find their best content
```bash
ytcli top @competitor --by views --limit 20
```
Shows their highest-performing videos. Use `--by engagement` if API key is set.

### Step 6: Find content gaps
```bash
ytcli gaps @competitor
```
Returns topics they've only covered 1-2 times (low-frequency) — potential opportunities.

### Step 7: Compare two channels
```bash
ytcli compare @channel1 @channel2
```
Side-by-side: upload frequency, avg duration, avg views, avg title length, topic overlap (Jaccard similarity).

### Step 8: Mine comments for pain points
```bash
ytcli comments "https://youtube.com/watch?v=THEIR_TOP_VIDEO" --sort top --limit 200
```
Top comments reveal what the audience wants more of.

## Interpreting results

| Signal | What it means |
|--------|--------------|
| High topic overlap + lower views | You're competing head-on, need differentiation |
| Low topic overlap | Different niches, gaps are opportunities |
| High question_title_pct | Their audience responds to curiosity-driven titles |
| High number_in_title_pct | Listicle format works in this niche |
| Low upload frequency + high views | Quality over quantity niche |
| Consistent calendar | Algorithm-friendly, audience expects schedule |

## Quick version (3 commands)
```bash
ytcli scan @competitor --limit 50
ytcli hooks @competitor
ytcli gaps @competitor
```
