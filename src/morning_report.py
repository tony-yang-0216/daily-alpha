"""
morning_report.py — Step 2: AI 深度分析 + 晨報產出
=====================================================
讀取 Step 1 的 JSON → AI 精選 + 深度分析 → 產出晨報 Markdown

流程：
  1. 讀取 Step 1 最新的 JSON（40 篇 summary）
  2. AI 篩選出最重要的 6~9 篇
  3. 對精選文章做深度分析（用 Google Search 補充原文細節）
  4. 加入「初學者筆記」（背景知識補充）
  5. 產出 Daily Insight（跨領域趨勢判讀）
  6. 輸出晨報 Markdown

使用方式：
  uv run python src/morning_report.py                        # 讀取最新的 Step 1 JSON
  uv run python src/morning_report.py --input output/news_raw_20260221_0830.json
  uv run python src/morning_report.py --dry-run              # 只印精選結果不產出晨報
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
from .config import load_api_key, load_report_config
from .exporter import save_report_json, save_report_markdown


# ─── 讀取 Step 1 輸出 ─────────────────────────────────


def find_latest_json(output_dir: str = "./output") -> Path:
    """找到 output/ 裡最新的 news_raw_*.json。"""
    files = sorted(Path(output_dir).glob("news_raw_*.json"))
    if not files:
        print(f"❌ 在 {output_dir}/ 找不到 Step 1 的 JSON 檔案！")
        print("   請先執行：uv run python src/news_agent.py")
        sys.exit(1)
    latest = files[-1]
    print(f"📂 讀取：{latest}")
    return latest


def load_step1_data(filepath: str | Path) -> dict:
    """讀取 Step 1 的 JSON。"""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


# ─── 第一步：AI 篩選 ──────────────────────────────────


def select_top_articles(client, articles: list[dict], config: dict) -> list[dict]:
    """從 30~40 篇中精選最重要的文章（不帶 Google Search）。"""
    model = config.get("model", "gemini-2.5-flash")
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

    prompt = f"""你是一位資深新聞編輯，正在為以下讀者篩選今日最重要的新聞：

讀者背景：{reader_profile}

以下是今日收集到的 {len(articles)} 篇新聞摘要：
{articles_text}

請從中選出最重要的 {max_select} 篇，選擇標準：
1. 科技（AI、半導體、新技術）權重最高
2. 經濟（市場趨勢、行情、重大財報）次之
3. 國際只選真正的重大事件
4. 優先選擇有具體數據、影響範圍廣的新聞
5. 避免選擇過於相似的新聞（同一事件只選最重要的一篇）
6. 考慮讀者是初學者，選擇能幫助建立世界觀的新聞

請回覆 JSON 陣列，包含選中文章的索引號碼和選擇理由：
[
  {{
    "index": 0,
    "reason": "為什麼選這篇（一句話）"
  }}
]

只回覆 JSON 陣列，不要有其他文字。"""

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
    model = config.get("model", "gemini-2.5-flash")
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

    today = datetime.now().strftime("%Y 年 %m 月 %d 日")
    session = "早報" if datetime.now().hour < 15 else "晚報"

    prompt = f"""你是「Daily Alpha」的主編，負責為讀者產出每日新聞晨報。

## 讀者背景
{reader_profile}

## 今日精選（共 {len(selected_articles)} 篇）
{articles_text}

## 你的任務

請產出一份完整的繁體中文晨報，格式如下：

### 格式要求

```
# Daily Alpha {session}｜{today}

> 一句話總結今天最重要的事

---

## 📌 [新聞 1 的繁體中文標題]
**來源**：媒體名稱 ｜ **分類**：科技/經濟/國際

[深度分析，200~250 字]
分析內容必須包含：
- 發生了什麼事（清楚描述事件）
- 為什麼重要（對產業、市場、或技術趨勢的影響）
- 關鍵數據或引述（如果有的話）
- 後續值得觀察什麼

💡 **初學者筆記**
用 5~6個要點解釋這則新聞涉及的背景知識。幫助完整了解這則新聞的意義和影響。
假設讀者完全不懂這個領域，用最白話的方式解釋。
例如：
- 「法說會」是什麼？為什麼投資人在意？
- 「HBM」是什麼？跟 AI 有什麼關係？
- 「升息/降息」怎麼影響科技股？

🔗 [原文連結](URL)

---

（重複以上格式，每篇都要有深度分析 + 初學者筆記）

---

## 🔭 Daily Insight｜今日趨勢觀察

[400~500 字趨勢分析]
如果可以把今天的新聞串連起來，就找出背後的共同趨勢或矛盾。
例如：「台積電法說提到 AI 晶片需求超預期」+「Fed 暗示維持利率」
→ 這兩件事合在一起代表什麼？對科技投資者意味著什麼？

---

（重複以上格式，不同領域的深度分析或者不同領域但是可以經過判斷是相關的）

---

寫作風格：像一位有經驗的朋友在跟你聊天，不是在寫論文。
讓初學者讀完能理解「今天的世界發生了什麼、為什麼重要、我該關注什麼」。

---

> 📊 本報告由 AI 自動產出，資料來源經 Google Search 驗證。
> 投資決策請自行研究判斷，本報告不構成投資建議。
```

## 重要指示
1. 請使用 Google Search 搜尋每篇新聞的原文連結，補充摘要中缺少的具體數據和細節
2. 所有內容必須是繁體中文（標題也翻譯成中文）
3. 初學者筆記是這份報告最重要的特色，請認真寫，不要敷衍
4. Daily Insight 必須跨領域串連，不要只是重複各篇摘要
5. 控制總長度在 25 分鐘閱讀量（約 4000~5000 字）
6. 不要虛構任何數據，如果搜不到就不要寫"""

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
        help="指定 Step 1 的 JSON 檔案路徑（預設：自動找最新的）",
    )
    parser.add_argument(
        "--output-dir",
        default="./output",
        help="輸出目錄（預設：./output）",
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
    print(f"   時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 55)
    print()

    json_path = args.input or find_latest_json(args.output_dir)
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
    report_path = save_report_markdown(report_text, args.output_dir)
    save_report_json(selected, report_text, args.output_dir)

    print()
    print("=" * 55)
    print("✅ 晨報完成！")
    print(f"   📄 {report_path}")
    print("   用 VS Code 打開，按 Cmd+Shift+V 預覽")
    print("=" * 55)


if __name__ == "__main__":
    main()
