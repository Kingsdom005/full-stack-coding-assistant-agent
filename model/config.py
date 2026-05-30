"""
模型配置文件
定义各 Agent 使用的模型及 Fallback 策略
"""

MODEL_CONFIG = {
    # 默认模型（腾讯混元免费模型）
    "default": "hunyuan-lite",

    # 各 Agent 专用模型配置
    "agents": {
        "frontend": "hunyuan-lite",      # 前端 Agent 使用轻量模型
        "backend":  "hunyuan-standard",   # 后端 Agent 使用标准模型
        "test":     "hunyuan-lite",       # 测试 Agent 使用轻量模型
        "audit":    "hunyuan-pro",        # 审计 Agent 使用专业模型
    },

    # 腾讯混元 API 配置
    "tencent": {
        "api_base": "https://api.hunyuan.cloud.tencent.com/hyllm/v1",
        "api_key": "YOUR_TENCENT_API_KEY",  # 请替换为实际 API Key
    },

    # Fallback 链式降级策略
    "fallback_chain": ["hunyuan-lite", "hunyuan-standard"],

    # LiteLLM 通用参数
    "litellm_settings": {
        "timeout": 60,
        "max_retries": 2,
    }
}
