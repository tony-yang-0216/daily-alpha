"""
config.py — 設定載入模組
==========================
集中處理所有外部設定的讀取，讓其他模組只需 import 函式，不用直接碰 YAML 或環境變數。

職責：
  - load_config()        → config/topics.yaml（search topics、Gemini 模型設定）
  - load_report_config() → config/report.yaml（晨報產出設定）
  - load_api_key()       → .env 或系統環境變數中的 GEMINI_API_KEY
"""

import os
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv

# __file__ 是本檔案（src/config.py）的絕對路徑。
# .parent     → src/
# .parent.parent → daily-alpha/（專案根目錄）
# / "config"  → daily-alpha/config/
# 這樣不管從哪個目錄執行 uv run，路徑都能正確解析。
_CONFIG_DIR = Path(__file__).parent.parent / "config"
_CONFIG_PATH = _CONFIG_DIR / "topics.yaml"


def load_config() -> dict:
    """Load topics and Gemini settings from config/topics.yaml."""
    with _CONFIG_PATH.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_report_config() -> dict:
    """Load morning-report settings from config/report.yaml."""
    with (_CONFIG_DIR / "report.yaml").open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_api_key() -> str:
    """
    Load GEMINI_API_KEY from .env file or environment variables.

    💡 知識補給站：
       使用 python-dotenv 自動載入 .env 檔案。
       讀取順序：
       1. load_dotenv() 把 .env 的內容載入環境變數
       2. os.environ.get() 讀取環境變數
       在 Terminal 直接 export 也行，用 .env 檔案也行。
    """
    load_dotenv()
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if key:
        return key

    print("❌ 找不到 Gemini API Key！")
    print()
    print("   設定方式（擇一）：")
    print("   方法 1: cp .env.example .env → 編輯 .env 填入 Key")
    print("   方法 2: export GEMINI_API_KEY=你的Key")
    print()
    print("   取得 API Key: https://aistudio.google.com → Get API key")
    sys.exit(1)
