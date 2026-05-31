"""
模型配置文件
定义各 Agent 使用的模型及 Fallback 策略
支持从环境变量读取敏感信息
"""

import os
from dotenv import load_dotenv

# 加载 .env 文件中的环境变量
load_dotenv(override=True)  # 允许 .env 覆盖系统环境变量


def get_env(key: str, default: str = "") -> str:
    """安全获取环境变量"""
    return os.getenv(key, default)


# 从环境变量读取敏感配置
TENCENT_API_KEY = get_env("TENCENT_API_KEY", "YOUR_TENCENT_API_KEY")
TENCENT_API_BASE = get_env(
    "TENCENT_API_BASE",
    "https://api.hunyuan.cloud.tencent.com/v1"
)
SQLITE_DB_PATH = get_env("SQLITE_DB_PATH", "./context.db")
CODEBUDDY_CLI_PATH = get_env("CODEBUDDY_CLI_PATH", "codebuddy")
CODEBUDDY_TIMEOUT = int(get_env("CODEBUDDY_TIMEOUT", "60"))

MODEL_CONFIG = {
    # 默认模型（腾讯混元，OpenAI 兼容 API）
    "default": "openai/hunyuan-lite",

    # 各 Agent 专用模型配置
    "agents": {
        "frontend": "openai/hunyuan-lite",      # 前端 Agent 使用轻量模型
        "backend":  "openai/hunyuan-standard",   # 后端 Agent 使用标准模型
        "test":     "openai/hunyuan-lite",       # 测试 Agent 使用轻量模型
        "audit":    "openai/hunyuan-pro",        # 审计 Agent 使用专业模型
    },

    # 腾讯混元 API 配置（从环境变量读取）
    "tencent": {
        "api_base": TENCENT_API_BASE,
        "api_key": TENCENT_API_KEY,
    },

    # Fallback 链式降级策略
    "fallback_chain": ["openai/hunyuan-lite", "openai/hunyuan-standard"],

    # LiteLLM 通用参数
    "litellm_settings": {
        "timeout": 60,
        "max_retries": 2,
    }
}

# 数据库配置
DATABASE_CONFIG = {
    "path": SQLITE_DB_PATH,
}

# CodeBuddy CLI 配置
CODEBUDDY_CONFIG = {
    "cli_path": CODEBUDDY_CLI_PATH,
    "timeout": CODEBUDDY_TIMEOUT,
}
