"""
Agent 基类 - 定义所有智能体的通用接口
"""

import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional

from model.model_router import ModelRouter
from storage.context_db import ContextDB


class BaseAgent(ABC):
    """智能体抽象基类"""

    def __init__(
        self,
        agent_type: str,
        model_router: ModelRouter,
        db: ContextDB,
    ):
        """
        初始化 Agent

        Args:
            agent_type: Agent 类型标识 (frontend/backend/test/audit)
            model_router: 模型路由器实例
            db: 数据库实例
        """
        self.agent_type = agent_type
        self.model_router = model_router
        self.db = db
        self.model = self.model_router.get_model_for_agent(agent_type)
        self._output_dir: Optional[Path] = None  # 输出目录，由 Coordinator 注入
        self._usage_log: List[Dict] = []  # 每步 LLM 调用的 token 用量记录

    @abstractmethod
    def get_system_prompt(self) -> str:
        """获取系统提示词 - 子类必须实现"""
        pass

    @abstractmethod
    def execute(self, task_id: str, context: Dict) -> Dict:
        """
        执行任务 - 子类必须实现

        Args:
            task_id: 任务 ID
            context: 任务上下文（包含依赖的任务结果）

        Returns:
            执行结果字典
        """
        pass

    def _call_llm(self, user_prompt: str, temperature: float = 0.7) -> str:
        """
        调用 LLM 的通用方法

        Args:
            user_prompt: 用户提示词
            temperature: 温度参数

        Returns:
            模型生成的文本
        """
        messages = [
            {"role": "system", "content": self.get_system_prompt()},
            {"role": "user", "content": user_prompt},
        ]
        result = self.model_router.chat(
            messages=messages,
            model=self.model,
            temperature=temperature,
        )

        # 记录 token 用量
        usage = result.get("usage", {})
        if usage:
            self._usage_log.append(
                {
                    "step": len(self._usage_log) + 1,
                    "model": result.get("model", self.model),
                    "prompt_tokens": usage.get("prompt_tokens", 0),
                    "completion_tokens": usage.get("completion_tokens", 0),
                    "total_tokens": usage.get("total_tokens", 0),
                    "latency_ms": result.get("latency_ms", 0),
                }
            )

        return result["content"]

    def _check_dependencies(
        self,
        context: Dict,
        required_keys: List[str],
    ) -> bool:
        """
        检查任务依赖是否满足

        Args:
            context: 任务上下文
            required_keys: 必需的上下文键列表

        Returns:
            是否满足所有依赖
        """
        for key in required_keys:
            if key not in context:
                return False
        return True

    def _log_change(
        self,
        task_id: str,
        file_path: str,
        change_type: str,
        diff: Optional[str] = None,
    ):
        """记录代码变更到数据库"""
        self.db.log_code_change(
            task_id=task_id,
            agent_type=self.agent_type,
            file_path=file_path,
            change_type=change_type,
            diff=diff,
        )

    def _save_result(self, task_id: str, result: str):
        """保存任务结果到数据库"""
        self.db.update_task_status(
            task_id=task_id,
            status="completed",
            result=result,
        )

    # ------------------------------------------------------------------ #
    #  输出目录相关方法（由 Coordinator 注入 output_dir）
    # ------------------------------------------------------------------ #

    def _set_output_dir(self, output_dir: Path):
        """设置输出目录（由 Coordinator 在初始化后调用）"""
        self._output_dir = output_dir

    def _get_sub_dir(self) -> str:
        """
        返回当前 Agent 对应的子目录名
        子类可重写，默认使用 agent_type
        """
        return self.agent_type

    def _write_file(self, rel_path: str, content: str):
        """
        将内容写入输出目录下的指定相对路径

        仅在 _output_dir 已设置时实际写入文件系统；
        否则仅记录日志（向后兼容）。

        Args:
            rel_path: 相对路径，如 "backend/main.py"
            content:  文件内容
        """
        if self._output_dir is None:
            # 向后兼容：未设置输出目录时不写入文件
            return

        file_path = self._output_dir / rel_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")

    def _read_file(self, rel_path: str) -> str:
        """
        读取输出目录下的指定文件

        Args:
            rel_path: 相对路径

        Returns:
            文件内容；文件不存在时返回空字符串
        """
        if self._output_dir is None:
            return ""

        file_path = self._output_dir / rel_path
        if not file_path.exists():
            return ""
        return file_path.read_text(encoding="utf-8", errors="replace")

    def _collect_existing_code(self) -> str:
        """
        收集当前 Agent 对应子目录下所有已有代码，
        用于构建迭代模式的 LLM prompt 上下文

        Returns:
            格式化的代码块字符串，每个文件用 ### FILE: 标记
        """
        if self._output_dir is None:
            return ""

        sub_dir = self._output_dir / self._get_sub_dir()
        if not sub_dir.exists():
            return ""

        parts = []
        for file_path in sorted(sub_dir.rglob("*")):
            if file_path.is_file():
                rel = file_path.relative_to(self._output_dir)
                content = file_path.read_text(encoding="utf-8", errors="replace")
                parts.append(f"### FILE: {rel}\n{content}\n")
        return "\n".join(parts)

    def _save_trace(
        self,
        task_id: str,
        system_prompt: str,
        user_prompt: str,
        llm_response: str,
        parsed_result: Dict,
    ):
        """
        保存 Agent 执行 trace 到输出目录

        记录完整的 LLM 输入输出以及 token 用量，以便审计和验证 Agent 的每一步行为。

        Args:
            task_id: 任务 ID
            system_prompt: 系统提示词
            user_prompt: 发送给 LLM 的完整用户提示词
            llm_response: LLM 的原始返回
            parsed_result: 解析后的结果（files, contracts 等）
        """
        if self._output_dir is None:
            return

        from datetime import datetime

        traces_dir = self._output_dir / "traces" / self.agent_type
        traces_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{task_id}.md"
        file_path = traces_dir / filename

        # 构建 token 用量部分
        usage_lines = self._build_usage_section()

        # 构建解析结果部分
        parsed_lines = []
        if parsed_result.get("files"):
            parsed_lines.append("### 生成/修改的文件")
            for f in parsed_result["files"]:
                parsed_lines.append(f"- `{f}`")
            parsed_lines.append("")
        if parsed_result.get("contracts"):
            parsed_lines.append("### 提取的 API 契约")
            for c in parsed_result["contracts"]:
                parsed_lines.append(
                    f"- **{c.get('method', '?')} {c.get('endpoint', '?')}**"
                )
            parsed_lines.append("")
        if parsed_result.get("reports_count") is not None:
            parsed_lines.append(
                f"- 发现问题数: {parsed_result.get('reports_count', 0)}"
            )
            parsed_lines.append(f"- 高危问题: {parsed_result.get('high_severity', 0)}")
            parsed_lines.append("")
        if parsed_result.get("status"):
            parsed_lines.append(f"- 状态: {parsed_result['status']}")
            parsed_lines.append("")

        content = f"""# Agent Trace: {self.agent_type}

- **时间**: {datetime.now().isoformat()}
- **任务ID**: {task_id}
- **Agent 类型**: {self.agent_type}

---

{usage_lines}

---

## 系统提示词 (System Prompt)

{system_prompt}

---

## 用户提示词 (User Prompt, sent to LLM)

{user_prompt}

---

## LLM 原始输出 (Raw Response)

{llm_response}

---

## 解析结果 (Parsed Result)

{chr(10).join(parsed_lines) if parsed_lines else '（无解析结果）'}

---
"""
        file_path.write_text(content, encoding="utf-8")

    def _build_usage_section(self) -> str:
        """构建 token 用量报告 Markdown 段"""
        if not self._usage_log:
            return "## Token 用量\n\n（无用量数据）"

        lines = [
            "## Token 用量",
            "",
            "| Step | 模型 | Prompt Tokens | Completion Tokens | Total Tokens | 耗时(ms) |",
            "|------|------|---------------|-------------------|--------------|----------|",
        ]
        total_prompt = 0
        total_completion = 0
        total_tokens = 0
        total_latency = 0.0
        for entry in self._usage_log:
            lines.append(
                f"| {entry['step']} | {entry['model']} "
                f"| {entry['prompt_tokens']:,} "
                f"| {entry['completion_tokens']:,} "
                f"| {entry['total_tokens']:,} "
                f"| {entry['latency_ms']} |"
            )
            total_prompt += entry["prompt_tokens"]
            total_completion += entry["completion_tokens"]
            total_tokens += entry["total_tokens"]
            total_latency += entry.get("latency_ms", 0)

        lines.append(
            f"| **合计** | — "
            f"| **{total_prompt:,}** "
            f"| **{total_completion:,}** "
            f"| **{total_tokens:,}** "
            f"| **{total_latency:.0f}** |"
        )
        return "\n".join(lines)

    def get_usage_summary(self) -> Dict:
        """
        获取当前 Agent 的 token 用量汇总

        Returns:
            字典: {
                "agent_type": str,
                "steps": int,
                "total_prompt_tokens": int,
                "total_completion_tokens": int,
                "total_tokens": int,
                "total_latency_ms": float,
                "details": List[Dict],
            }
        """
        total_prompt = sum(e["prompt_tokens"] for e in self._usage_log)
        total_completion = sum(e["completion_tokens"] for e in self._usage_log)
        total_tokens = sum(e["total_tokens"] for e in self._usage_log)
        total_latency = sum(e.get("latency_ms", 0) for e in self._usage_log)

        return {
            "agent_type": self.agent_type,
            "steps": len(self._usage_log),
            "total_prompt_tokens": total_prompt,
            "total_completion_tokens": total_completion,
            "total_tokens": total_tokens,
            "total_latency_ms": round(total_latency, 1),
            "details": list(self._usage_log),
        }

    def _parse_llm_code_output(self, text: str) -> Dict[str, str]:
        """
        解析 LLM 返回内容中的文件块

        期望格式：
        ### FILE: path/to/file.py
        ```python
        # code here
        ```

        也支持无代码块包裹的纯代码（直到下一个 ### FILE: 或文件结束）。

        Returns:
            字典 {相对文件路径: 文件内容}
        """
        result: Dict[str, str] = {}
        pattern = r"### FILE:\s*(\S+)\n(.*?)(?=\n### FILE:|\Z)"
        matches = re.findall(pattern, text, re.DOTALL)

        if not matches:
            # 无法解析出多文件，整段内容作为单个文件
            return {"output.txt": text.strip()}

        for file_path, content in matches:
            # 去掉代码块标记（``` 包裹）
            cleaned = re.sub(r"```[\w]*\n?", "", content)
            cleaned = re.sub(r"```\s*$", "", cleaned)
            result[file_path.strip()] = cleaned.strip()

        return result
