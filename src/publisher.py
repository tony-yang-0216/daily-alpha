"""
publisher.py — GitHub Pages 索引產生器
========================================
掃描 docs/raw/ + docs/report/ 裡所有 .md，
按日期（新→舊）列出連結，產生 docs/index.md。

使用方式：
  uv run publish          # 重新產生 index.md
"""

from datetime import datetime
from pathlib import Path

DOCS_DIR = Path("docs")
DOCS_RAW_DIR = DOCS_DIR / "raw"
DOCS_REPORT_DIR = DOCS_DIR / "report"
INDEX_PATH = DOCS_DIR / "index.md"


def _parse_ts(stem: str) -> datetime | None:
    """將檔名 YYYYMMDD_HHMM 解析為 datetime；解析失敗回傳 None。"""
    try:
        return datetime.strptime(stem, "%Y%m%d_%H%M")
    except ValueError:
        return None


def _format_date(dt: datetime) -> str:
    return dt.strftime("%Y 年 %m 月 %d 日")


def _format_time(dt: datetime) -> str:
    return dt.strftime("%H:%M")


def generate_index() -> str:
    """掃描 docs/ 並產生 index.md 內容。"""
    raw_stems = {f.stem for f in DOCS_RAW_DIR.glob("*.md")} if DOCS_RAW_DIR.exists() else set()
    report_stems = {f.stem for f in DOCS_REPORT_DIR.glob("*.md")} if DOCS_REPORT_DIR.exists() else set()

    all_stems = sorted(raw_stems | report_stems, reverse=True)

    lines = [
        "---",
        'title: "Daily Alpha — 每日 AI 新聞報告"',
        "nav_order: 1",
        "---",
        "",
        "# Daily Alpha",
        "",
        "> 每日 AI 新聞收集與深度分析報告，由 Gemini + Google Search 自動產出。",
        "",
        "---",
        "",
    ]

    if not all_stems:
        lines.append("*尚無報告，請先執行 `uv run daily-alpha` 與 `uv run morning-report`。*")
        lines.append("")
    else:
        # Group stems by date (YYYYMMDD) for the section header
        by_date: dict[str, list[str]] = {}
        for stem in all_stems:
            date_key = stem[:8]  # YYYYMMDD
            by_date.setdefault(date_key, []).append(stem)

        for date_key in sorted(by_date.keys(), reverse=True):
            dt_date = datetime.strptime(date_key, "%Y%m%d")
            lines.append(f"## {_format_date(dt_date)}")
            lines.append("")

            for stem in by_date[date_key]:
                dt = _parse_ts(stem)
                time_label = f"（{_format_time(dt)}）" if dt else ""

                if stem in report_stems:
                    lines.append(f"- 📰 [晨報{time_label}](report/{stem}.md)")
                if stem in raw_stems:
                    lines.append(f"- 📡 [原始收集{time_label}](raw/{stem}.md)")

            lines.append("")

    lines += [
        "---",
        "",
        "> 📊 本站由 [Daily Alpha](https://github.com) 自動產出，內容僅供參考，不構成投資建議。",
        "",
    ]

    return "\n".join(lines)


def main():
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    content = generate_index()
    INDEX_PATH.write_text(content, encoding="utf-8")

    raw_count = len(list(DOCS_RAW_DIR.glob("*.md"))) if DOCS_RAW_DIR.exists() else 0
    report_count = len(list(DOCS_REPORT_DIR.glob("*.md"))) if DOCS_REPORT_DIR.exists() else 0

    print(f"✅ {INDEX_PATH} 已更新")
    print(f"   📡 原始收集：{raw_count} 份")
    print(f"   📰 晨報：{report_count} 份")


if __name__ == "__main__":
    main()
