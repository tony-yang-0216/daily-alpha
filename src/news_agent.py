"""
Daily Alpha — AI Agent 新聞收集器
==================================
Gemini 2.5 Flash + Google Search Grounding 取代 RSS。

使用方式：
  uv run daily-alpha                           # 正常執行
  uv run daily-alpha --dry-run                 # 只印結果不存檔
  uv run daily-alpha --topics "AI,半導體"       # 只搜特定主題

💡 知識補給站：
   Google Search Grounding 是 Gemini 的內建功能。
   在 API 呼叫加上 tools=[google_search] 後，
   Gemini 會自動去 Google 搜尋並附帶來源連結。
"""

import argparse
from datetime import datetime

from .collector import collect_all
from .exporter import save_json, save_markdown


def main() -> None:
    parser = argparse.ArgumentParser(
        description="🤖 Daily Alpha — AI Agent 新聞收集器",
    )
    parser.add_argument(
        "--topics",
        type=str,
        default=None,
        help="只搜特定主題（逗號分隔），例如：--topics 'AI,半導體'",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只顯示結果，不存檔",
    )
    args = parser.parse_args()

    result = collect_all(topic_filter=args.topics)

    print()

    if args.dry_run:
        print("🏃 Dry run 模式")
        print()
        for i, article in enumerate(result["articles"][:8], 1):
            rel = article.get("relevance", "?")
            print(f"  {i}. [{rel}] [{article.get('source', '?')}] {article.get('title', '?')}")
            print(f"     {article.get('summary', '')[:80]}...")
            print()
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    save_json(result, timestamp)
    save_markdown(result, timestamp)

    print()
    print(f"{'=' * 55}")
    print("✅ Step 1 完成！")
    print("   VS Code 打開 docs/raw/ 查看 Markdown 結果")
    print("   .md 檔按 Cmd+Shift+V 預覽")
    print(f"{'=' * 55}")


if __name__ == "__main__":
    main()
