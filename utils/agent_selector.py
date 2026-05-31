"""
Agent 智能选择器 - 基于 LLM 分析用户需求，判断需要运行哪些 Agent
"""

import json
import re
from typing import Dict, List, Optional

from model.model_router import ModelRouter
from utils.logger import info, warning, error


class AgentSelector:
    """
    智能选择需要运行的 Agent

    使用轻量模型分析用户需求，输出需要运行的 Agent 列表。
    同时处理依赖修正（如选中 frontend 时必须也选中 backend）。
    """

    # 所有可用的 Agent 类型
    ALL_AGENTS = ["backend", "frontend", "test", "audit"]

    # Agent 中文描述（用于 prompt）
    AGENT_DESCRIPTIONS = {
        "backend": "后端开发（生成/修改 API 接口、数据库、业务逻辑）",
        "frontend": "前端开发（生成/修改 UI 组件、页面、样式）",
        "test": "测试（生成/修改单元测试、集成测试、E2E 测试）",
        "audit": "代码审计（检查代码质量、安全漏洞、性能问题）",
    }

    def __init__(self, model_router: ModelRouter):
        """
        初始化选择器

        Args:
            model_router: 模型路由器实例（使用轻量模型以节省成本）
        """
        self.model_router = model_router
        # 使用轻量模型进行 Agent 选择
        self.model = model_router.get_model_for_agent("frontend")  # frontend 用轻量模型

    def select_agents(
        self,
        user_input: str,
        existing_code_summary: str = "",
    ) -> Dict:
        """
        分析用户需求，返回需要运行的 Agent 列表

        Args:
            user_input: 用户输入的需求描述
            existing_code_summary: 已有代码的摘要（可选）

        Returns:
            字典 {
                "agents": ["backend", "frontend"],
                "reason": "需要修改登录接口和登录页面"
            }
        """
        prompt = self._build_prompt(user_input, existing_code_summary)

        try:
            messages = [
                {"role": "system", "content": self._get_system_prompt()},
                {"role": "user", "content": prompt},
            ]
            response = self.model_router.chat(
                messages=messages,
                model=self.model,
                temperature=0.1,  # 低温度，确保输出稳定
                max_tokens=512,
            )

            result = self._parse_response(response["content"])
            result = self._fix_dependencies(result)
            return result

        except Exception as e:
            error(f"Agent 选择失败，使用默认全部 Agent: {e}")
            return {
                "agents": self.ALL_AGENTS,
                "reason": f"LLM 调用失败，默认运行全部 Agent: {e}",
            }

    def _get_system_prompt(self) -> str:
        """获取系统提示词"""
        return """你是一个智能任务分析器。你的任务是分析用户的需求描述，判断需要运行哪些智能体（Agent）来完成任务。

请以严格的 JSON 格式输出结果，不要输出任何 JSON 以外的内容。"""

    def _build_prompt(self, user_input: str, existing_code_summary: str) -> str:
        """构建用户提示词"""
        agent_list = "\n".join(
            f"- {name}: {desc}" for name, desc in self.AGENT_DESCRIPTIONS.items()
        )

        prompt = f"""分析以下用户需求，判断需要运行哪些智能体（Agent）：

## 用户需求
{user_input}

## 可选 Agent
{agent_list}

## 输出要求
请以以下 JSON 格式输出（只输出 JSON，不要有任何其他文字）：
```json
{{
    "agents": ["backend", "frontend"],
    "reason": "需要修改登录接口和登录页面"
}}
```

## 选择规则
1. 如果需求涉及后端逻辑、API、数据库，选择 backend
2. 如果需求涉及前端页面、UI、交互，选择 frontend
3. 如果需求明确提到测试、测试用例，选择 test
4. 如果需求提到代码审查、安全检查、性能优化，选择 audit
5. 如果不确定，选择全部 Agent
6. frontend 依赖 backend 的输出（API 契约），如果选中 frontend 建议也选中 backend
7. test 依赖 backend 和 frontend 的代码，如果选中 test 建议也选中 backend 和 frontend
"""

        if existing_code_summary:
            prompt += f"\n## 已有代码摘要\n{existing_code_summary}\n"

        prompt += "\n请只输出 JSON，不要有任何其他文字：\n"
        return prompt

    def _parse_response(self, response: str) -> Dict:
        """
        解析 LLM 返回的 JSON

        Args:
            response: LLM 返回的文本

        Returns:
            解析后的字典，失败时返回默认全部 Agent
        """
        if not response:
            warning("Agent 选择器收到空响应，使用默认全部 Agent")
            return {
                "agents": self.ALL_AGENTS,
                "reason": "LLM 返回空响应",
            }

        # 尝试提取 JSON（可能被 ```json ``` 包裹）
        json_match = re.search(r"\{.*\}", response, re.DOTALL)
        if not json_match:
            warning(f"无法从响应中解析 JSON: {response[:200]}")
            return {
                "agents": self.ALL_AGENTS,
                "reason": "无法解析 LLM 响应，默认运行全部 Agent",
            }

        try:
            data = json.loads(json_match.group())

            # 验证 agents 字段
            agents = data.get("agents", [])
            if not isinstance(agents, list) or len(agents) == 0:
                warning(f"agents 字段无效: {agents}")
                agents = self.ALL_AGENTS

            # 过滤掉未知的 Agent 类型
            agents = [a for a in agents if a in self.ALL_AGENTS]
            if not agents:
                agents = self.ALL_AGENTS

            return {
                "agents": agents,
                "reason": data.get("reason", "用户需求涉及多个方面"),
            }

        except json.JSONDecodeError as e:
            warning(f"JSON 解析失败: {e}, 响应: {response[:200]}")
            return {
                "agents": self.ALL_AGENTS,
                "reason": f"JSON 解析失败，默认运行全部 Agent",
            }

    def _fix_dependencies(self, result: Dict) -> Dict:
        """
        修正依赖关系：
        - 如果选中 frontend 但未选中 backend，自动添加 backend
        - 如果选中 test 但未选中 backend/frontend，自动添加
        - 如果选中 audit 但未选中其他，也添加（audit 需要代码来审计）
        """
        agents = set(result["agents"])

        # frontend 依赖 backend（需要 API 契约）
        if "frontend" in agents and "backend" not in agents:
            info("依赖修正: frontend 需要 backend，自动添加 backend")
            agents.add("backend")

        # test 依赖 backend 和 frontend
        if "test" in agents:
            if "backend" not in agents:
                info("依赖修正: test 需要 backend，自动添加 backend")
                agents.add("backend")
            if "frontend" not in agents:
                info("依赖修正: test 需要 frontend，自动添加 frontend")
                agents.add("frontend")

        # audit 需要代码来审计
        if "audit" in agents and len(agents) == 1:
            info("依赖修正: audit 需要代码来审计，自动添加 backend 和 frontend")
            agents.add("backend")
            agents.add("frontend")

        result["agents"] = sorted(agents)
        return result

    @staticmethod
    def format_existing_code_summary(output_dir: Optional[str]) -> str:
        """
        生成已有代码的简短摘要（用于注入到选择器的 prompt）

        Args:
            output_dir: 输出目录路径

        Returns:
            代码摘要字符串（文件名列表）
        """
        if not output_dir:
            return ""

        from pathlib import Path

        path = Path(output_dir)
        if not path.exists():
            return ""

        parts = []
        for sub_dir in ["backend", "frontend", "tests"]:
            target = path / sub_dir
            if target.exists():
                files = [f.name for f in target.iterdir() if f.is_file()]
                if files:
                    parts.append(f"{sub_dir}: {', '.join(files[:5])}")

        return "\n".join(parts)
