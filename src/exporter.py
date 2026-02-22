import json
import os
from datetime import datetime
from pathlib import Path

DATA_RAW_DIR = Path("data/raw")
DATA_REPORT_DIR = Path("data/report")
DOCS_RAW_DIR = Path("docs/raw")
DOCS_REPORT_DIR = Path("docs/report")

_CATEGORY_LABELS: dict[str, str] = {
    "tech": "🔧 科技",
    "economy": "💰 總經",
    "world": "🌍 國際",
}

_RELEVANCE_EMOJI: dict[str, str] = {
    "high": "🔴",
    "medium": "🟡",
    "low": "🟢",
}


def save_json(result: dict, timestamp: str) -> str:
    """Serialize the collection result to a timestamped JSON file."""
    DATA_RAW_DIR.mkdir(parents=True, exist_ok=True)
    filepath = DATA_RAW_DIR / f"{timestamp}.json"

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2, default=str)

    size_kb = os.path.getsize(filepath) / 1024
    print(f"💾 JSON：{filepath} ({size_kb:.1f} KB)")
    return str(filepath)


def save_markdown(result: dict, timestamp: str) -> str:
    """Render the collection result to a human-readable Markdown file."""
    DOCS_RAW_DIR.mkdir(parents=True, exist_ok=True)
    filepath = DOCS_RAW_DIR / f"{timestamp}.md"

    meta = result["meta"]
    articles: list[dict] = result["articles"]

    lines: list[str] = [
        "# 📡 Daily Alpha — 新聞收集",
        "> 🤖 由 Gemini + Google Search 自動收集",
        f"> 📅 {meta['collected_at']}",
        f"> 📊 共 {meta['total_articles']} 篇 | 🔍 搜尋 {meta['google_search_count']} 次",
        "",
    ]

    for cat in ("tech", "economy", "world"):
        cat_articles = [a for a in articles if a.get("category") == cat]
        if not cat_articles:
            continue

        label = _CATEGORY_LABELS.get(cat, cat)
        lines += [f"## {label}（{len(cat_articles)} 篇）", ""]

        topics_in_cat: dict[str, list[dict]] = {}
        for article in cat_articles:
            topic = article.get("topic", "其他")
            topics_in_cat.setdefault(topic, []).append(article)

        for topic_name, topic_articles in topics_in_cat.items():
            lines += [f"### 📌 {topic_name}", ""]

            for article in topic_articles:
                relevance = article.get("relevance", "medium")
                emoji = _RELEVANCE_EMOJI.get(relevance, "⚪")

                lines += [
                    f"**{emoji} {article.get('title', 'No title')}**",
                    f"*{article.get('source', '未知來源')}*",
                    "",
                    article.get("summary", "無摘要"),
                    "",
                ]
                if article.get("url"):
                    lines.append(f"🔗 [原文連結]({article['url']})")
                lines += ["", "---", ""]

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    size_kb = os.path.getsize(filepath) / 1024
    print(f"📄 Markdown：{filepath} ({size_kb:.1f} KB)")
    return str(filepath)


# ─── Step 2: Report outputs ───────────────────────────


def save_report_json(selected_articles: list[dict], report_text: str, timestamp: str) -> str:
    """Persist selected articles and the rendered report as a JSON file."""
    DATA_REPORT_DIR.mkdir(parents=True, exist_ok=True)
    filepath = DATA_REPORT_DIR / f"{timestamp}.json"

    session = "morning" if datetime.now().hour < 15 else "evening"
    data = {
        "meta": {
            "generated_at": datetime.now().astimezone().isoformat(),
            "session": session,
            "articles_analyzed": len(selected_articles),
            "report_length": len(report_text),
        },
        "selected_articles": selected_articles,
        "report_markdown": report_text,
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)

    return str(filepath)


def save_report_markdown(report_text: str, timestamp: str) -> str:
    """Write the final report Markdown to a timestamped file."""
    DOCS_REPORT_DIR.mkdir(parents=True, exist_ok=True)
    filepath = DOCS_REPORT_DIR / f"{timestamp}.md"

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(report_text)

    size_kb = os.path.getsize(filepath) / 1024
    print(f"📄 晨報已存檔：{filepath} ({size_kb:.1f} KB)")
    return str(filepath)
