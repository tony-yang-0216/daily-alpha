"""
collector.py — 新聞收集核心模組（Step 1）
==========================================
這是整個系統最核心的檔案，負責實作「Gemini + Google Search Grounding」的新聞收集流程。

主要職責：
  1. 對每個 topic，呼叫一次 Gemini API（帶 Google Search 工具）
  2. Gemini 自動決定搜尋 query、搜 Google、讀取結果、整理成 JSON
  3. 解析 Gemini 回傳的 JSON，提取 grounding metadata（引用來源、搜尋次數）
  4. 對所有 topic 的結果做跨主題去重
  5. 回傳完整的結構化資料給 exporter.py 存檔

呼叫關係：
  news_agent.py → collect_all() → search_topic()（每個 topic 一次）
                                → deduplicate_articles()
"""

import json
import sys
import time
from datetime import datetime
from typing import Any

try:
    from google import genai
    from google.genai import types
except ImportError:
    print("❌ 找不到 google-genai 套件！")
    print("   請執行：pip install google-genai")
    print()
    print("   💡 注意：套件名稱是 google-genai（不是 google-generativeai）")
    print("      新版 SDK 從 2025 年開始統一用 google-genai")
    sys.exit(1)

from .config import load_api_key, load_config, load_prompt

# Tool 物件可重複使用（無狀態），在 module 層級建立一次即可，
# 每次 API 呼叫都傳入同一個 instance。
_SEARCH_TOOL = types.Tool(google_search=types.GoogleSearch())


def strip_markdown_fences(text: str) -> str:
    """Remove markdown code fences that Gemini sometimes wraps around JSON."""
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()
    if text.startswith("json"):
        text = text[4:].strip()
    return text


def extract_grounding_metadata(response: Any) -> tuple[list[dict], list[str]]:
    """
    Extract grounding sources and search queries from a Gemini response.

    💡 知識補給站：
       grounding_metadata 包含：
       - grounding_chunks: 引用的來源網頁（附帶 title 和 uri）
       - web_search_queries: 實際執行的搜尋 query
    """
    if not (hasattr(response, "candidates") and response.candidates):
        return [], []

    candidate = response.candidates[0]
    gm = getattr(candidate, "grounding_metadata", None)
    if gm is None:
        return [], []

    sources = []
    for chunk in getattr(gm, "grounding_chunks", []) or []:
        web = getattr(chunk, "web", None)
        if web:
            sources.append({
                "title": getattr(web, "title", ""),
                "uri": getattr(web, "uri", ""),
            })

    queries = list(getattr(gm, "web_search_queries", []) or [])
    return sources, queries


def search_topic(client: Any, model: str, topic: dict, gemini_config: dict) -> dict:
    """
    Search a single topic using Gemini with Google Search Grounding.

    💡 知識補給站：
       tools=[_SEARCH_TOOL] 告訴 Gemini 可以用 Google Search 回答。
       Gemini 會自動：
       1. 把問題轉成搜尋 query
       2. 去 Google 搜
       3. 讀搜尋結果
       4. 整理成指定的 JSON 格式
       5. 附上來源連結（grounding_metadata）
    """
    topic_name = topic["name"]
    prompt = load_prompt(
        "collect_news",
        topic_name=topic_name,
        queries_hint=" / ".join(topic["queries"]),
        max_articles=topic.get("max_articles", 5),
    )

    raw_text = ""
    try:
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[_SEARCH_TOOL],
                temperature=gemini_config.get("temperature", 0.2),
                max_output_tokens=gemini_config.get("max_output_tokens", 60000),
            ),
        )

        raw_text = strip_markdown_fences(response.text.strip())
        articles: list[dict] = json.loads(raw_text)
        grounding_sources, search_queries = extract_grounding_metadata(response)

        for article in articles:
            article["topic"] = topic_name
            article["category"] = topic.get("category", "tech")
            article["priority"] = topic.get("priority", 1)

        return {
            "topic": topic_name,
            "category": topic.get("category", "tech"),
            "articles": articles,
            "grounding_sources": grounding_sources,
            "search_queries": search_queries,
            "status": "success",
        }

    except json.JSONDecodeError as e:
        print("  ⚠️  JSON 解析失敗，嘗試擷取部分結果...")
        return {
            "topic": topic_name,
            "category": topic.get("category", "tech"),
            "articles": [],
            "raw_response": raw_text[:500],
            "error": f"JSON parse error: {e}",
            "status": "partial",
        }

    except Exception as e:
        return {
            "topic": topic_name,
            "category": topic.get("category", "tech"),
            "articles": [],
            "error": str(e),
            "status": "error",
        }


def deduplicate_articles(articles: list[dict]) -> list[dict]:
    """
    Remove duplicate articles across topics.

    💡 知識補給站：
       同一則新聞可能出現在多個主題中。
       先按 priority 排序，讓高優先級的版本優先保留。
       URL 完全相同 → 去重；標題完全相同（不分大小寫）→ 去重。
    """
    seen_urls: set[str] = set()
    seen_titles: set[str] = set()
    unique: list[dict] = []

    for article in sorted(articles, key=lambda a: -a.get("priority", 1)):
        url = article.get("url", "")
        title = article.get("title", "").lower().strip()

        if url and url in seen_urls:
            continue
        if title and title in seen_titles:
            continue

        seen_urls.add(url)
        seen_titles.add(title)
        unique.append(article)

    return unique


def collect_all(topic_filter: str | None = None) -> dict:
    """
    Collect news from all configured topics.

    Args:
        topic_filter: Comma-separated topic names to include. None collects all.
    """
    config = load_config()
    api_key = load_api_key()
    topics: list[dict] = config.get("topics", [])
    gemini_config: dict = config.get("gemini", {})
    model: str = gemini_config.get("model", "gemini-2.5-flash")

    client = genai.Client(api_key=api_key)

    if topic_filter:
        filter_names = [t.strip() for t in topic_filter.split(",")]
        topics = [t for t in topics if any(fn in t["name"] for fn in filter_names)]

    print()
    print(f"{'=' * 55}")
    print("🤖 Daily Alpha — AI Agent 新聞收集器")
    print(f"   模型：{model}")
    print(f"   主題：{len(topics)} 個")
    print(f"   時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'=' * 55}")
    print()

    all_articles: list[dict] = []
    topic_results: list[dict] = []
    total_search_queries = 0

    for i, topic in enumerate(topics, 1):
        print(f"📡 [{i}/{len(topics)}] 搜尋：{topic['name']}...")

        result = search_topic(client, model, topic, gemini_config)
        topic_results.append(result)

        if result["status"] == "success":
            count = len(result["articles"])
            queries = len(result.get("search_queries", []))
            total_search_queries += queries
            print(f"   ✅ {count} 篇文章（Google 搜了 {queries} 次）")
            all_articles.extend(result["articles"])
        elif result["status"] == "partial":
            print(f"   ⚠️  部分成功：{result.get('error', '')}")
        else:
            print(f"   ❌ 失敗：{result.get('error', '')}")

        if i < len(topics):
            # 對 API 的禮貌性延遲：避免在短時間內送出太多請求，
            # 也讓 Google Search Grounding 的配額消耗更穩定。
            time.sleep(1)

    print()
    print(f"{'─' * 55}")

    unique_articles = deduplicate_articles(all_articles)
    dedup_removed = len(all_articles) - len(unique_articles)

    print(f"📊 原始文章：{len(all_articles)} 篇")
    print(f"🧹 去重移除：{dedup_removed} 篇")
    print(f"✅ 最終文章：{len(unique_articles)} 篇")
    print(f"🔍 Google 搜尋次數：{total_search_queries} 次（免費額度 500/天）")

    cat_counts: dict[str, int] = {}
    for article in unique_articles:
        cat = article.get("category", "unknown")
        cat_counts[cat] = cat_counts.get(cat, 0) + 1
    print(f"📂 分類分布：{cat_counts}")

    return {
        "meta": {
            "collected_at": datetime.now().astimezone().isoformat(),
            "model": model,
            "total_articles": len(unique_articles),
            "duplicates_removed": dedup_removed,
            "google_search_count": total_search_queries,
            "category_counts": cat_counts,
            "topics_status": {r["topic"]: r["status"] for r in topic_results},
        },
        "articles": unique_articles,
        "raw_results": topic_results,
    }
