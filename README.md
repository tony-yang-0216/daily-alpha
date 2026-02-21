# Daily Alpha

AI-powered daily news briefing system. Uses **Gemini 2.5 Flash** with built-in **Google Search Grounding** to collect, summarize, and deduplicate news across technology, economy, and international topics — no RSS feeds required.

## Features

- **Live search** — Gemini queries Google in real time; no static feed URLs to maintain
- **Bilingual output** — English titles, Traditional Chinese summaries
- **Three categories** — Technology (AI, chips, software), Economy (markets, macro), International (major events)
- **Cross-topic deduplication** — same story appearing in multiple topics is merged, keeping the highest-priority version
- **Dual output formats** — structured JSON for downstream processing + human-readable Markdown for review
- **Rate-aware** — tracks Google Search usage against the free-tier limit (500 queries/day)

## Requirements

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) package manager
- Gemini API key (free tier available at [Google AI Studio](https://aistudio.google.com))

## Setup

```bash
# 1. Clone and enter the repo
git clone <repo-url>
cd daily-alpha

# 2. Copy and fill in the API key
cp .env.example .env
# Edit .env: GEMINI_API_KEY="your-key-here"

# 3. Install dependencies
uv sync
```

## Usage

```bash
# Collect all topics and save output files
uv run daily-alpha

# Preview results without saving (shows first 8 articles)
uv run daily-alpha --dry-run

# Only search specific topics (comma-separated)
uv run daily-alpha --topics "AI,半導體"

# Write to a custom output directory
uv run daily-alpha --output-dir ./my-output
```

## Configuration

Edit `config/topics.yaml` to adjust search topics, keywords, article counts, and Gemini model settings.

| Field | Description |
|---|---|
| `name` | Topic label used in output headings |
| `category` | `tech` / `economy` / `world` |
| `priority` | Deduplication tie-breaking (higher wins) |
| `max_articles` | Max articles to fetch per topic per run |
| `queries` | Keyword hints passed to Gemini for search |

**Gemini settings** (`gemini` key in the same file):

| Field | Default | Description |
|---|---|---|
| `model` | `gemini-2.5-flash` | Gemini model ID |
| `temperature` | `0.2` | Lower = more consistent output |
| `max_output_tokens` | `65536` | Max tokens per API response |

**Default topics and daily usage:**

| Topic | Category | Max Articles |
|---|---|---|
| AI / 人工智慧 | tech | 10 |
| 半導體 / 晶片 | tech | 8 |
| 軟體 / 新技術 | tech | 6 |
| 市場趨勢 / 行情 | economy | 8 |
| 總經 / 央行政策 | economy | 5 |
| 國際重大事件 | world | 3 |

6 topics × 2 runs/day = ~12 API calls/day (well within the 500 Google Search queries/day free limit).

## Output

Each run writes two files to `./output/` (or `--output-dir`):

```
output/
├── news_raw_YYYYMMDD_HHMM.json   # Full structured data
└── news_raw_YYYYMMDD_HHMM.md    # Human-readable report
```

**JSON structure:**

```json
{
  "meta": {
    "collected_at": "2026-02-21T16:07:00+08:00",
    "model": "gemini-2.5-flash",
    "total_articles": 36,
    "duplicates_removed": 4,
    "google_search_count": 50,
    "category_counts": {"tech": 23, "economy": 10, "world": 3},
    "topics_status": {"AI / 人工智慧": "success", ...}
  },
  "articles": [
    {
      "title": "Original English Title",
      "source": "Reuters",
      "url": "https://...",
      "summary": "繁體中文摘要，4~6 句，包含事件、影響、關鍵數據。",
      "key_entities": ["NVIDIA", "Jensen Huang", "Blackwell"],
      "relevance": "high",
      "topic": "AI / 人工智慧",
      "category": "tech",
      "priority": 3
    }
  ],
  "raw_results": [...]
}
```

**Markdown preview** (open in VS Code with `Cmd+Shift+V`):

```markdown
# 📡 Daily Alpha — 新聞收集
> 🤖 由 Gemini + Google Search 自動收集

## 🔧 科技（23 篇）
### 📌 AI / 人工智慧

**🔴 Original Article Title**
*Reuters*

繁體中文摘要...

🔗 [原文連結](https://...)
```

Relevance indicators: 🔴 high · 🟡 medium · 🟢 low

## Project Structure

```
daily-alpha/
├── config/
│   └── topics.yaml          # Search topics and Gemini settings
├── output/                  # Generated reports (git-ignored)
├── src/
│   ├── __init__.py
│   ├── news_agent.py        # CLI entry point (argparse + main)
│   ├── collector.py         # Gemini search, deduplication, orchestration
│   ├── config.py            # Config and API key loading
│   └── exporter.py          # JSON and Markdown output
├── .env.example             # API key template
├── pyproject.toml           # Project metadata and dependencies
└── uv.lock                  # Locked dependency versions
```

## License

MIT — Copyright 2026 Tony Yang
