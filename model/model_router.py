"""
模型路由器 - 基于 LiteLLM 的统一模型接口
支持多模型切换、Fallback、流式输出
"""

import litellm
from typing import List, Dict, Optional, Generator
from model.config import MODEL_CONFIG


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
    ) -> str:
        """
        统一聊天接口（非流式）

        Args:
            messages: OpenAI 格式的消息列表
            model: 指定模型，None 则使用默认模型
            temperature: 温度参数
            max_tokens: 最大 token 数

        Returns:
            模型回复内容
        """
        model = model or self.default_model

        try:
            response = litellm.completion(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **self.config["litellm_settings"],
            )
            return response.choices[0].message.content
        except Exception as e:
            # Fallback 策略
            for fallback_model in self.fallback_chain:
                if fallback_model != model:
                    try:
                        response = litellm.completion(
                            model=fallback_model,
                            messages=messages,
                            temperature=temperature,
                            max_tokens=max_tokens,
                        )
                        return response.choices[0].message.content
                    except Exception:
                        continue
            raise RuntimeError(f"所有模型调用失败: {str(e)}")

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
