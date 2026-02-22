"""
exporter.py — 輸出模組（Step 1 & 2）
======================================
所有檔案 I/O 集中在這裡，其他模組只呼叫 save_*() 函式。

雙目錄輸出設計：
  每次產出都寫入兩個地方：
  ┌─ data/raw/       ─── 本機原始資料（.gitignore 排除，不上傳）
  │   data/report/       用於 Step 2 讀取、或本機除錯
  │
  └─ docs/raw/       ─── GitHub Pages 來源（git 追蹤，推送後自動發佈）
      docs/report/       Jekyll 渲染成公開網頁

  這樣設計的原因：
  - data/ 保留完整 JSON（包含 raw_results），方便本機查閱或程式讀取
  - docs/ 只放 Markdown，讓 GitHub Pages 能渲染成網頁
  - 兩者時間戳相同（YYYYMMDD_HHMM），Step 2 用時間戳配對 raw ↔ report
"""

import json
import os
from datetime import datetime
from pathlib import Path

from .config import (
    DATA_RAW_DIR,
    DATA_REPORT_DIR,
    DOCS_RAW_DIR,
    DOCS_REPORT_DIR,
    TZ_TAIPEI,
    get_session,
    load_report_config,
)


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

    report_config = load_report_config()
    category_labels: dict[str, str] = report_config.get("category_labels", {
        "tech": "🔧 科技",
        "economy": "💰 總經",
        "world": "🌍 國際",
    })
    relevance_emoji: dict[str, str] = report_config.get("relevance_emoji", {
        "high": "🔴",
        "medium": "🟡",
        "low": "🟢",
    })

    meta = result["meta"]
    articles: list[dict] = result["articles"]

    lines: list[str] = [
        "---",
        f'title: "Daily Alpha 新聞收集 {timestamp}"',
        "nav_exclude: true",
        "---",
        "",
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

        label = category_labels.get(cat, cat)
        lines += [f"## {label}（{len(cat_articles)} 篇）", ""]

        topics_in_cat: dict[str, list[dict]] = {}
        for article in cat_articles:
            topic = article.get("topic", "其他")
            topics_in_cat.setdefault(topic, []).append(article)

        for topic_name, topic_articles in topics_in_cat.items():
            lines += [f"### 📌 {topic_name}", ""]

            for article in topic_articles:
                relevance = article.get("relevance", "medium")
                emoji = relevance_emoji.get(relevance, "⚪")

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

    # 以 15:00 為界區分早報/晚報：GitHub Actions 分別在 08:00 和 20:00 台灣時間觸發，
    # 15:00 是兩者的中間點，用來自動判斷當次是哪個 session。
    session, _ = get_session()
    data = {
        "meta": {
            "generated_at": datetime.now(TZ_TAIPEI).isoformat(),
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

    front_matter = f"---\ntitle: \"Daily Alpha 晨報 {timestamp}\"\nnav_exclude: true\n---\n\n"
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(front_matter + report_text)

    size_kb = os.path.getsize(filepath) / 1024
    print(f"📄 晨報已存檔：{filepath} ({size_kb:.1f} KB)")
    return str(filepath)
