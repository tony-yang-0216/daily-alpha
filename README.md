# Daily Alpha

AI-powered daily news briefing system. Uses **Gemini 2.5 Flash** with built-in **Google Search Grounding** to collect, summarize, and analyze news across technology, economy, and international topics — no RSS feeds required.

## How It Works

The system runs a **3-step pipeline**, fully automated via GitHub Actions twice a day:

```
Step 1: Collection          Step 2: Report              Step 3: Publish
──────────────────          ─────────────────           ───────────────
6 topics in                 AI selects 6-9              Scan docs/,
topics.yaml         →       most important      →       regenerate
                            articles + deep             index.md for
Gemini queries              analysis + beginner         GitHub Pages
Google, returns             notes + cross-domain
30-40 articles              trend insight
                            (~25 min read)
```

Each step writes to two locations:
- `data/` — local data files (git-ignored, for downstream use)
- `docs/` — Jekyll Markdown files (git-committed, published to GitHub Pages)

---

## Features

- **Live search** — Gemini queries Google in real time; no static feed URLs to maintain
- **Bilingual** — English titles, Traditional Chinese summaries and analysis
- **Three categories** — Technology (AI, chips, software), Economy (markets, macro), International (major events)
- **Deduplication** — same story in multiple topics is merged, keeping the highest-priority version
- **Beginner-friendly** — each article includes a "初學者筆記" with 5-6 key background concepts
- **Dual formats** — structured JSON for downstream use + Markdown for human reading
- **Rate-aware** — tracks Google Search usage against the free-tier limit (500 queries/day)
- **Auto-published** — GitHub Actions runs the pipeline and pushes to GitHub Pages

---

## Requirements

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) package manager
- Gemini API key (free tier at [Google AI Studio](https://aistudio.google.com))

---

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

For GitHub Actions, add `GEMINI_API_KEY` as a repository secret.

---

## Usage

Run the full pipeline manually in order:

```bash
# Step 1: Collect news from all topics
uv run daily-alpha

# Step 2: Generate morning report from latest collection
uv run morning-report

# Step 3: Regenerate GitHub Pages index
uv run publish
```

### Step 1 Options

```bash
uv run daily-alpha --dry-run                  # Preview without saving (shows first 8 articles)
uv run daily-alpha --topics "AI,半導體"       # Filter to specific topics (comma-separated)
uv run daily-alpha --output-dir ./my-output   # Write to a custom directory
```

### Step 2 Options

```bash
uv run morning-report --dry-run                               # Preview AI selection only, no files written
uv run morning-report --input data/raw/20260221_0830.json     # Use a specific Step 1 file (default: latest unprocessed)
```

---

## Configuration

### `config/topics.yaml` — News Collection

Controls what Step 1 searches for.

**Topic fields:**

| Field | Description |
|---|---|
| `name` | Topic label used in output headings |
| `category` | `tech` / `economy` / `world` |
| `priority` | Deduplication tie-breaking (higher wins, 1–3) |
| `max_articles` | Max articles per topic per run |
| `queries` | Keyword hints passed to Gemini for search direction |

**Gemini settings** (under `gemini` key):

| Field | Default | Description |
|---|---|---|
| `model` | `gemini-2.5-flash` | Gemini model ID |
| `temperature` | `0.2` | Lower = more consistent output |
| `max_output_tokens` | `65536` | Max tokens per API response |

**Schedule** (under `schedule` key, informational — GitHub Actions handles actual scheduling):

| Field | Default |
|---|---|
| `timezone` | `Asia/Taipei` |
| `morning` | `08:30` |
| `evening` | `20:30` |

**Default topics:**

| Topic | Category | Max Articles | Priority |
|---|---|---|---|
| AI / 人工智慧 | tech | 10 | 3 |
| 半導體 / 晶片 | tech | 8 | 3 |
| 軟體 / 新技術 | tech | 6 | 2 |
| 市場趨勢 / 行情 | economy | 8 | 3 |
| 總經 / 央行政策 | economy | 5 | 2 |
| 國際重大事件 | world | 3 | 1 |

6 topics × 2 runs/day ≈ 12 API calls/day (well within the 500 Google Search queries/day free limit).

---

### `config/report.yaml` — Report Generation

Controls what Step 2 generates.

| Field | Description |
|---|---|
| `model` | Gemini model for report generation |
| `max_output_tokens` | Max tokens for report response |
| `max_articles` | Max articles in the final report (default: 8) |
| `reader_profile` | Description of the target reader (used to calibrate AI tone) |

The `reader_profile` field shapes the AI's article selection and writing style. It currently describes a beginner investor who is interested in technology and global economics and prefers friendly explanations over jargon.

---

## Output

### Step 1 Output

Files written to:
- `data/raw/{YYYYMMDD}_{HHMM}.json` — full structured data (git-ignored)
- `docs/raw/{YYYYMMDD}_{HHMM}.md` — human-readable Markdown (published)

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
    "topics_status": {"AI / 人工智慧": "success", "半導體 / 晶片": "success"}
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
  ]
}
```

**Markdown preview** (open with `Cmd+Shift+V` in VS Code):

```
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

---

### Step 2 Output

Files written to:
- `data/report/{YYYYMMDD}_{HHMM}.json` — curated articles + full report (git-ignored)
- `docs/report/{YYYYMMDD}_{HHMM}.md` — final morning report Markdown (published)

The report includes:
1. **Article selection** — 6-9 most important articles chosen by AI based on reader profile
2. **Per-article analysis** — 200-250 word analysis (what happened, why it matters, key data, what to watch)
3. **初學者筆記** — 5-6 bullet points explaining background concepts for each article
4. **Daily Insight** — 400-500 word cross-domain trend analysis connecting multiple stories

---

### Step 3 Output

- `docs/index.md` — Jekyll landing page with chronological links to all raw collections and reports

---

## GitHub Actions Automation

Workflow: `.github/workflows/daily.yml`

**Schedule** (UTC):
- `00:00` UTC → Taiwan `08:00` (morning run)
- `12:00` UTC → Taiwan `20:00` (evening run)

**Manual trigger:** available via `workflow_dispatch` in the Actions tab.

**Jobs (run in sequence):**
1. Checkout repo, set up Python + uv
2. Run `uv run daily-alpha` (Step 1)
3. Run `uv run morning-report` (Step 2)
4. Run `uv run publish` (Step 3)
5. Commit and push changes in `docs/` with timestamp in commit message

Requires `GEMINI_API_KEY` set as a GitHub repository secret.

---

## GitHub Pages

Published at: the repo's GitHub Pages URL (configured in repository Settings → Pages → source: `docs/` folder on `main` branch).

Theme: [Just-the-Docs](https://just-the-docs.com/), configured in `docs/_config.yml`.

The `docs/` directory contains:
```
docs/
├── _config.yml           # Jekyll theme config
├── index.md              # Auto-generated landing page (Step 3)
├── raw/                  # Step 1 Markdown outputs (one file per run)
└── report/               # Step 2 morning reports (one file per run)
```

---

## Project Structure

```
daily-alpha/
├── .github/
│   └── workflows/
│       └── daily.yml           # Automated daily pipeline
├── config/
│   ├── topics.yaml             # Search topics, queries, Gemini settings
│   └── report.yaml             # Morning report configuration
├── data/                       # Local data (git-ignored)
│   ├── raw/                    # Step 1 JSON outputs
│   └── report/                 # Step 2 JSON outputs
├── docs/                       # GitHub Pages content (git-committed)
│   ├── _config.yml             # Jekyll Just-the-Docs theme config
│   ├── index.md                # Auto-generated index (Step 3)
│   ├── raw/                    # Step 1 Markdown outputs
│   └── report/                 # Step 2 morning report Markdown
├── src/
│   ├── __init__.py
│   ├── news_agent.py           # Step 1 CLI entry point (argparse + orchestration)
│   ├── collector.py            # Gemini search, JSON parsing, deduplication
│   ├── config.py               # Load topics.yaml, report.yaml, API key
│   ├── exporter.py             # Write JSON and Markdown for Steps 1 & 2
│   ├── morning_report.py       # Step 2 CLI: AI selection + deep analysis
│   └── publisher.py            # Step 3: scan docs/, generate index.md
├── .env                        # API key (git-ignored)
├── .env.example                # API key template
├── pyproject.toml              # Project metadata and entry points
└── uv.lock                     # Locked dependency versions
```

### Key Source Files

**`src/collector.py`** — Core of Step 1. Each topic = 1 Gemini API call with Google Search Grounding enabled. Handles JSON parsing, markdown fence stripping, grounding metadata extraction, and cross-topic deduplication.

**`src/morning_report.py`** — Core of Step 2. Finds the latest unprocessed Step 1 JSON, asks Gemini to select the most relevant articles, then generates deep analysis and beginner notes for each. Uses Google Search Grounding for supplementary detail.

**`src/publisher.py`** — Step 3. Scans all `.md` files in `docs/raw/` and `docs/report/`, generates a grouped-by-date `docs/index.md` with links in reverse chronological order.

**`src/exporter.py`** — Shared output writer for all steps. Handles both `data/` (JSON) and `docs/` (Markdown) destinations.

---

## License

MIT — Copyright 2026 Tony Yang
