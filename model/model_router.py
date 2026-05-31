"""
模型路由器 - 基于 LiteLLM 的统一模型接口
支持多模型切换、Fallback、流式输出、Token 用量追踪
"""

import time
from typing import Dict, Generator, List, Optional

import litellm

from model.config import MODEL_CONFIG


def _extract_usage(response) -> Dict:
    """安全提取 LiteLLM response 中的 usage 信息"""
    try:
        usage = response.usage
        if usage is None:
            return {}
        return {
            "prompt_tokens": getattr(usage, "prompt_tokens", 0) or 0,
            "completion_tokens": getattr(usage, "completion_tokens", 0) or 0,
            "total_tokens": getattr(usage, "total_tokens", 0) or 0,
        }
    except Exception:
        return {}


class ModelRouter:
    """LiteLLM 封装，提供统一的模型调用接口"""

    def __init__(self):
        self.config = MODEL_CONFIG
        self.default_model = self.config["default"]
        self.fallback_chain = self.config["fallback_chain"]

        # 配置 LiteLLM
        litellm.api_key = self.config["tencent"]["api_key"]
        litellm.api_base = self.config["tencent"]["api_base"]

    def chat(
        self,
        messages: List[Dict],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> Dict:
        """
        统一聊天接口（非流式）

        Args:
            messages: OpenAI 格式的消息列表
            model: 指定模型，None 则使用默认模型
            temperature: 温度参数
            max_tokens: 最大 token 数

        Returns:
            字典 {"content": str, "usage": dict, "model": str, "latency_ms": float}
            usage 包含 prompt_tokens / completion_tokens / total_tokens
        """
        model = model or self.default_model

        def _make_empty_result(content: str) -> Dict:
            return {
                "content": content,
                "usage": {},
                "model": model,
                "latency_ms": 0,
            }

        try:
            t0 = time.time()
            response = litellm.completion(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **self.config["litellm_settings"],
            )
            latency = (time.time() - t0) * 1000
            return {
                "content": response.choices[0].message.content or "",
                "usage": _extract_usage(response),
                "model": model,
                "latency_ms": round(latency, 1),
            }
        except Exception as e:
            import logging

            logger = logging.getLogger("coding_agent")
            logger.error(f"LLM 调用失败 (model={model}): {e}")
            # Fallback 策略
            for fallback_model in self.fallback_chain:
                if fallback_model != model:
                    try:
                        logger.warning(f"尝试 Fallback 模型: {fallback_model}")
                        t0 = time.time()
                        response = litellm.completion(
                            model=fallback_model,
                            messages=messages,
                            temperature=temperature,
                            max_tokens=max_tokens,
                        )
                        latency = (time.time() - t0) * 1000
                        return {
                            "content": response.choices[0].message.content or "",
                            "usage": _extract_usage(response),
                            "model": fallback_model,
                            "latency_ms": round(latency, 1),
                        }
                    except Exception as fe:
                        logger.warning(f"Fallback 模型 {fallback_model} 也失败: {fe}")
                        continue
            raise RuntimeError(
                f"所有模型调用失败 (model={model}, fallback={self.fallback_chain}): {str(e)}"
            )

    def stream_chat(
        self,
        messages: List[Dict],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> Generator[str, None, None]:
        """
        流式聊天接口

        Yields:
            流式输出的文本片段
        """
        model = model or self.default_model

        try:
            response = litellm.completion(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )
            for chunk in response:
                content = chunk.choices[0].delta.content
                if content:
                    yield content
        except Exception as e:
            yield f"[ERROR] 模型调用失败: {str(e)}"

    def get_model_for_agent(self, agent_type: str) -> str:
        """获取指定 Agent 类型的模型"""
        return self.config["agents"].get(agent_type, self.default_model)
