import os
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv

_CONFIG_PATH = Path(__file__).parent.parent / "config" / "topics.yaml"


def load_config() -> dict:
    """Load topics and Gemini settings from config/topics.yaml."""
    with _CONFIG_PATH.open(encoding="utf-8") as f:
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
