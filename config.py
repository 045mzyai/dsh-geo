import os

PROJECT_NAME = "GEO Platform"
VERSION = "0.1.0"

PORT = int(os.environ.get("GEO_PORT", "8060"))
DEBUG = os.environ.get("GEO_DEBUG", "true").lower() == "true"

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "geo.db")

MZY_API_KEY = os.environ.get("MZY_API_KEY", "")
MZY_BASE_URL = os.environ.get("MZY_BASE_URL", "https://token.mzyai.com/v1")

if not MZY_API_KEY:
    import sys
    print("[ERROR] 环境变量 MZY_API_KEY 未设置，AI功能不可用", file=sys.stderr)

AI_CONFIG = {
    "deepseek": {
        "enabled": True,
        "api_key": MZY_API_KEY,
        "model": "deepseek-v4-pro",
        "base_url": MZY_BASE_URL,
    },
    "kimi": {
        "enabled": True,
        "api_key": MZY_API_KEY,
        "model": "kimi-k3",
        "base_url": MZY_BASE_URL,
    },
    "glm": {
        "enabled": True,
        "api_key": MZY_API_KEY,
        "model": "glm-5.2",
        "base_url": MZY_BASE_URL,
    },
    "minimax": {
        "enabled": True,
        "api_key": MZY_API_KEY,
        "model": "minimax-m3",
        "base_url": MZY_BASE_URL,
    },
    "hunyuan": {
        "enabled": True,
        "api_key": MZY_API_KEY,
        "model": "hy3",
        "base_url": MZY_BASE_URL,
    },
}

# 默认用于内容生成的模型
DEFAULT_MODEL = "deepseek-v4-pro"

RUN_MODE = os.environ.get("RUN_MODE", "production")
