"""
morning_report.py — Step 2: AI 深度分析 + 晨報產出
=====================================================
讀取 Step 1 的 JSON → AI 精選 + 深度分析 → 產出晨報 Markdown

流程：
  1. 讀取 Step 1 最新的「尚未處理」JSON（data/raw/）
  2. AI 篩選出最重要的 6~9 篇
  3. 對精選文章做深度分析（用 Google Search 補充原文細節）
  4. 加入「初學者筆記」（背景知識補充）
  5. 產出 Daily Insight（跨領域趨勢判讀）
  6. 輸出晨報 Markdown

使用方式：
  uv run morning-report                                          # 處理最新未處理的 Step 1 JSON
  uv run morning-report --input data/raw/20260221_0830.json      # 指定檔案（即使已處理也會執行）
  uv run morning-report --dry-run                                # 只印精選結果不產出晨報
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

try:
    from google import genai
    from google.genai import types
except ImportError:
    print("❌ 找不到 google-genai 套件！")
    print("   請執行：pip install google-genai")
    sys.exit(1)

from .collector import extract_grounding_metadata, strip_markdown_fences
from .config import (
    DATA_RAW_DIR,
    DATA_REPORT_DIR,
    TZ_TAIPEI,
    get_session,
    load_api_key,
    load_prompt,
    load_report_config,
)
from .exporter import save_report_json, save_report_markdown


# ─── 讀取 Step 1 輸出 ─────────────────────────────────


def find_unprocessed_json() -> list[Path]:
    """找出 data/raw/ 裡尚未有對應 data/report/ 檔案的 JSON。"""
    raw_files = sorted(DATA_RAW_DIR.glob("*.json"))
    return [f for f in raw_files if not (DATA_REPORT_DIR / f.name).exists()]


def find_latest_json() -> Path:
    """找到 data/raw/ 裡最新的尚未處理的 JSON。"""
    unprocessed = find_unprocessed_json()
    if not unprocessed:
        all_raw = sorted(DATA_RAW_DIR.glob("*.json"))
        if not all_raw:
            print(f"❌ 在 {DATA_RAW_DIR}/ 找不到 Step 1 的 JSON 檔案！")
            print("   請先執行：uv run daily-alpha")
            sys.exit(1)
        print("ℹ️  所有 raw JSON 都已處理過，沒有新的檔案可處理。")
        sys.exit(0)

    latest = unprocessed[-1]
    print(f"📂 讀取：{latest}")
    return latest


def load_step1_data(filepath: str | Path) -> dict:
    """讀取 Step 1 的 JSON。"""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


# ─── 第一步：AI 篩選 ──────────────────────────────────
#
# 兩階段設計的原因：
#   Step A（select_top_articles）— 「不開 Google Search」
#     只讓 Gemini 看已有的摘要文字，做純文字比較和排序。
#     不需要 Search，速度快，用 temperature=0.1（幾乎確定性輸出，確保篩選穩定）。
#
#   Step B（generate_report）— 「開啟 Google Search」
#     對精選文章做深度分析時，讓 Gemini 自行搜尋補充原文細節、具體數據。
#     用 temperature=0.3（略高，讓文字更自然流暢）。
#
# 這樣拆分可以避免在「比較 30 篇文章」的時候花費大量 Google Search 配額。


def select_top_articles(client, articles: list[dict], config: dict) -> list[dict]:
    """從 30~40 篇中精選最重要的文章（不帶 Google Search）。"""
    model = config.get("model", "gemini-3-flash-preview")
    max_select = config.get("max_articles_in_report", 8)
    reader_profile = config.get("reader_profile", "")

    articles_text = ""
    for i, a in enumerate(articles):
        articles_text += (
            f"\n[{i}] 標題: {a.get('title', 'N/A')}\n"
            f"來源: {a.get('source', 'N/A')} | 主題: {a.get('topic', 'N/A')} "
            f"| 優先級: {a.get('priority', 1)} | 重要性: {a.get('relevance', 'N/A')}\n"
            f"摘要: {a.get('summary', 'N/A')}\n"
            f"關鍵實體: {', '.join(a.get('key_entities', []))}\n"
            f"連結: {a.get('url', 'N/A')}\n"
        )

    prompt = load_prompt(
        "select_articles",
        reader_profile=reader_profile,
        article_count=len(articles),
        articles_text=articles_text,
        max_select=max_select,
    )

    print(f"🔍 AI 篩選中（{len(articles)} 篇 → {max_select} 篇）...")

    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.1,
            max_output_tokens=config.get("max_output_tokens", 65536),
        ),
    )

    selections = json.loads(strip_markdown_fences(response.text.strip()))

    selected = []
    for sel in selections:
        idx = sel.get("index", -1)
        if 0 <= idx < len(articles):
            article = articles[idx].copy()
            article["selection_reason"] = sel.get("reason", "")
            selected.append(article)

    print(f"   ✅ 精選 {len(selected)} 篇")
    for i, s in enumerate(selected, 1):
        print(f"   {i}. [{s.get('topic', '?')}] {s.get('title', '?')[:50]}...")

    return selected


# ─── 第二步：深度分析 + 初學者筆記 ─────────────────────


def generate_report(client, selected_articles: list[dict], config: dict) -> str:
    """對精選文章做深度分析，產出完整晨報（啟用 Google Search Grounding）。"""
    model = config.get("model", "gemini-3-flash-preview")
    reader_profile = config.get("reader_profile", "")

    articles_text = ""
    for i, a in enumerate(selected_articles, 1):
        articles_text += (
            f"\n--- 第 {i} 篇 ---\n"
            f"標題: {a.get('title', 'N/A')}\n"
            f"來源: {a.get('source', 'N/A')}\n"
            f"連結: {a.get('url', 'N/A')}\n"
            f"主題: {a.get('topic', 'N/A')} | 分類: {a.get('category', 'N/A')}\n"
            f"摘要: {a.get('summary', 'N/A')}\n"
            f"關鍵實體: {', '.join(a.get('key_entities', []))}\n"
            f"入選理由: {a.get('selection_reason', 'N/A')}\n"
        )

    today = datetime.now(TZ_TAIPEI).strftime("%Y 年 %m 月 %d 日")
    _, session = get_session()

    prompt = load_prompt(
        "generate_report",
        reader_profile=reader_profile,
        article_count=len(selected_articles),
        articles_text=articles_text,
        today=today,
        session=session,
    )

    print("📝 正在產出晨報（Gemini 2.5 Flash + Google Search）...")

    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())],
            temperature=0.3,
            max_output_tokens=config.get("max_output_tokens", 65536),
        ),
    )

    sources, search_queries = extract_grounding_metadata(response)
    print(f"   🔍 引用了 {len(sources)} 個來源，搜尋了 {len(search_queries)} 次")

    report_text = response.text.strip()
    print(f"   ✅ 晨報產出完成（{len(report_text)} 字）")
    return report_text


# ─── 主流程 ───────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="Daily Alpha — 晨報產出器")
    parser.add_argument(
        "--input",
        type=str,
        default=None,
        help="指定 Step 1 的 JSON 檔案路徑（預設：自動找最新未處理的）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只做篩選，不產出完整晨報",
    )
    args = parser.parse_args()

    config = load_report_config()
    client = genai.Client(api_key=load_api_key())

    print()
    print("=" * 55)
    print("📰 Daily Alpha — 晨報產出器")
    print(f"   模型：{config.get('model', 'gemini-2.5-flash')}")
    print(f"   時間：{datetime.now(TZ_TAIPEI).strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 55)
    print()

    if args.input:
        json_path = Path(args.input)
        timestamp = json_path.stem
        report_json = DATA_REPORT_DIR / f"{timestamp}.json"
        if report_json.exists():
            print(f"⚠️  警告：{report_json} 已存在，將覆蓋。")
    else:
        json_path = find_latest_json()
        timestamp = json_path.stem

    step1_data = load_step1_data(json_path)
    articles = step1_data.get("articles", [])
    print(f"   共 {len(articles)} 篇待篩選")
    print()

    selected = select_top_articles(client, articles, config)

    if args.dry_run:
        print("\n🏃 Dry run 模式，不產出晨報")
        return

    print()
    time.sleep(3)  # 禮貌性延遲，避免連續 API 請求

    report_text = generate_report(client, selected, config)

    print()
    report_path = save_report_markdown(report_text, timestamp)
    save_report_json(selected, report_text, timestamp)

    print()
    print("=" * 55)
    print("✅ 晨報完成！")
    print(f"   📄 {report_path}")
    print("   用 VS Code 打開，按 Cmd+Shift+V 預覽")
    print("=" * 55)


if __name__ == "__main__":
    main()
