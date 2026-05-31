"""
主协调器 - 负责任务拆解、调度和上下文管理
"""

import json
import uuid
from pathlib import Path
from typing import Dict, List, Optional

from coordinator.dag import DAGScheduler
from model.model_router import ModelRouter
from storage.context_db import ContextDB
from agents.frontend_agent import FrontendAgent
from agents.backend_agent import BackendAgent
from agents.test_agent import TestAgent
from agents.audit_agent import AuditAgent


class Coordinator:
    """主协调器"""

    def __init__(
        self,
        config_path: str = "config.yaml",
        db_path: Optional[str] = None,
        output_dir: Optional[Path] = None,
    ):
        """
        初始化协调器

        Args:
            config_path: 配置文件路径
            db_path: 数据库路径，None 则使用配置文件中的默认值
            output_dir: 输出目录 Path，None 则不写入文件系统
        """
        # 初始化核心组件
        self.model_router = ModelRouter()
        self.db = ContextDB(db_path)
        self.dag = DAGScheduler()
        self.config_path = config_path
        self.output_dir = output_dir

        # 初始化 Agents
        self.agents = {
            "frontend": FrontendAgent("frontend", self.model_router, self.db),
            "backend": BackendAgent("backend", self.model_router, self.db),
            "test": TestAgent("test", self.model_router, self.db),
            "audit": AuditAgent("audit", self.model_router, self.db),
        }

        # 将 output_dir 注入到所有 Agent
        if output_dir is not None:
            for agent in self.agents.values():
                agent._set_output_dir(output_dir)

    def reset_dag(self):
        """
        重置 DAG 调度器，用于迭代模式

        清空 DAG 的任务和状态，但保留 Agent 和数据库连接。
        每次新的迭代前调用此方法。
        """
        self.dag.reset()

    def submit_iteration_task(
        self,
        description: str,
        requirements: str = "",
        agent_types: Optional[List[str]] = None,
    ) -> str:
        """
        提交迭代任务，只创建指定的 Agent 任务

        与 submit_task() 不同，此方法允许只运行部分 Agent，
        用于交互模式下的智能 Agent 选择。

        Args:
            description: 任务描述（用户的新需求）
            requirements: 详细需求
            agent_types: Agent 类型列表，None 则运行全部

        Returns:
            主任务 ID
        """
        agent_types = agent_types or ["backend", "frontend", "test", "audit"]
        agent_types_set = set(agent_types)

        main_task_id = f"task_{uuid.uuid4().hex[:8]}"
        self.db.create_task(main_task_id, description)

        # 基础 context（所有任务共享）
        base_context = {
            "description": description,
            "requirements": requirements,
            "is_iteration": True,
        }

        # 收集已有代码上下文（从 output_dir 读取）
        if self.output_dir is not None:
            base_context["existing_backend_code"] = self._read_generated_code("backend")
            base_context["existing_frontend_code"] = self._read_generated_code(
                "frontend"
            )
            base_context["existing_test_code"] = self._read_generated_code("tests")

        created_tasks: Dict[str, str] = {}  # suffix -> task_id

        def _add_task(suffix: str, agent_type: str, deps: List[str]):
            """添加任务到 DAG，记录到 created_tasks"""
            task_id = f"{main_task_id}_{suffix}"
            self.db.create_task(task_id, f"{description} - {suffix}")
            self.dag.add_task(
                task_id,
                agent_type=agent_type,
                dependencies=deps,
                context={**base_context},
            )
            created_tasks[suffix] = task_id
            return task_id

        # 1. 后端任务（无依赖，如果选中）
        if "backend" in agent_types_set:
            _add_task("backend", "backend", [])

        # 2. 前端任务（依赖 backend，如果选中）
        if "frontend" in agent_types_set:
            deps = [created_tasks["backend"]] if "backend" in created_tasks else []
            _add_task("frontend", "frontend", deps)

        # 3. 测试任务（依赖 backend + frontend，如果选中）
        if "test" in agent_types_set:
            deps = []
            if "backend" in created_tasks:
                deps.append(created_tasks["backend"])
            if "frontend" in created_tasks:
                deps.append(created_tasks["frontend"])
            _add_task("test", "test", deps)

        # 4. 审计任务（依赖所有其他任务，如果选中）
        if "audit" in agent_types_set:
            deps = []
            for suffix in ["backend", "frontend", "test"]:
                if suffix in created_tasks:
                    deps.append(created_tasks[suffix])
            _add_task("audit", "audit", deps)

        self._main_task_id = main_task_id
        return main_task_id

    def submit_task(
        self,
        description: str,
        requirements: str = "",
        is_iteration: bool = False,
        existing_context: Optional[Dict] = None,
    ) -> str:
        """
        提交任务 - 拆解任务并添加到 DAG

        Args:
            description: 任务描述
            requirements: 详细需求
            is_iteration: 是否为迭代模式
            existing_context: 已有项目上下文（迭代模式时使用）

        Returns:
            主任务 ID
        """
        main_task_id = f"task_{uuid.uuid4().hex[:8]}"
        self.db.create_task(main_task_id, description)

        # 基础 context（所有任务共享）
        base_context = {
            "description": description,
            "requirements": requirements,
            "is_iteration": is_iteration,
        }

        # 迭代模式：注入已有代码上下文
        if is_iteration and existing_context:
            base_context["existing_backend_code"] = existing_context.get(
                "backend_code", ""
            )
            base_context["existing_frontend_code"] = existing_context.get(
                "frontend_code", ""
            )
            base_context["existing_test_code"] = existing_context.get("test_code", "")

        # 1. 后端任务（无依赖）
        backend_task_id = f"{main_task_id}_backend"
        self.db.create_task(backend_task_id, f"{description} - 后端开发")
        self.dag.add_task(
            backend_task_id,
            agent_type="backend",
            dependencies=[],
            context={**base_context},
        )

        # 2. 前端任务（依赖后端完成，以获取 API 契约）
        frontend_task_id = f"{main_task_id}_frontend"
        self.db.create_task(frontend_task_id, f"{description} - 前端开发")
        self.dag.add_task(
            frontend_task_id,
            agent_type="frontend",
            dependencies=[backend_task_id],
            context={**base_context},
        )

        # 3. 测试任务（依赖前后端完成）
        test_task_id = f"{main_task_id}_test"
        self.db.create_task(test_task_id, f"{description} - 测试")
        self.dag.add_task(
            test_task_id,
            agent_type="test",
            dependencies=[backend_task_id, frontend_task_id],
            context={
                **base_context,
                "frontend_code": "",
                "backend_code": "",
            },
        )

        # 4. 审计任务（异步，依赖所有任务完成）
        audit_task_id = f"{main_task_id}_audit"
        self.db.create_task(audit_task_id, f"{description} - 审计")
        self.dag.add_task(
            audit_task_id,
            agent_type="audit",
            dependencies=[backend_task_id, frontend_task_id, test_task_id],
            context={**base_context},
        )

        # 保存 main_task_id 供 run() 使用
        self._main_task_id = main_task_id
        return main_task_id

    def run(self, main_task_id: str) -> Dict:
        """
        主运行循环 - DAG 调度执行

        Returns:
            所有任务的执行结果，包含 token 用量汇总
        """
        results = {}

        while not self.dag.is_completed():
            runnable = self.dag.get_runnable_tasks()

            if not runnable:
                if not self.dag.is_completed():
                    raise RuntimeError("任务调度死锁：没有可运行任务但 DAG 未完成")
                break

            for task_id in runnable:
                agent_type = self.dag.tasks[task_id]["agent_type"]
                agent = self.agents.get(agent_type)

                if not agent:
                    self.dag.mark_failed(task_id)
                    continue

                # 获取任务上下文
                context = self.dag.get_task_context(task_id)

                # 为测试任务注入前后端代码
                if agent_type == "test":
                    context["frontend_code"] = self._read_generated_code("frontend")
                    context["backend_code"] = self._read_generated_code("backend")

                # 为审计任务注入待审计代码
                if agent_type == "audit":
                    context["code"] = (
                        self._read_generated_code("backend")
                        + "\n"
                        + self._read_generated_code("frontend")
                    )
                    context["file_path"] = str(self.output_dir or "unknown")
                    context["agent_type"] = agent_type

                try:
                    result = agent.execute(task_id, context)
                    self.dag.tasks[task_id]["result"] = result
                    self.dag.mark_done(task_id)
                    results[task_id] = result

                except Exception as e:
                    import traceback
                    from utils.logger import error as log_error

                    error_detail = traceback.format_exc()
                    log_error(f"任务 [{task_id}] 执行失败 (agent={agent_type}): {e}")
                    log_error(f"详细堆栈:\n{error_detail}")
                    self.dag.mark_failed(task_id)
                    self.db.update_task_status(task_id, "failed", error=str(e))
                    # 同步更新被级联标记失败的下游任务到数据库
                    for tid, info in self.dag.tasks.items():
                        if self.dag.status.get(tid) == "failed" and tid != task_id:
                            self.db.update_task_status(
                                tid,
                                "failed",
                                error=f"上游任务 {task_id} 失败，本级联取消",
                            )
                    results[task_id] = {
                        "status": "failed",
                        "error": str(e),
                        "traceback": error_detail,
                    }

        # 收集并汇总所有 Agent 的 token 用量
        usage_summary = self._collect_usage_summary()
        results["_usage_summary"] = usage_summary

        # 打印用量汇总
        self._print_usage_summary(usage_summary)

        # 保存用量汇总文件
        self._save_usage_summary(usage_summary)

        return results

    def _collect_usage_summary(self) -> List[Dict]:
        """收集所有 Agent 的 token 用量"""
        summaries = []
        for agent_type, agent in self.agents.items():
            summary = agent.get_usage_summary()
            if summary["total_tokens"] > 0:
                summaries.append(summary)
        return summaries

    def _print_usage_summary(self, summaries: List[Dict]):
        """打印 token 用量汇总表"""
        if not summaries:
            return

        from utils.logger import info as log_info

        total_tokens = sum(s["total_tokens"] for s in summaries)
        total_latency = sum(s["total_latency_ms"] for s in summaries)

        log_info("=" * 72)
        log_info("📊 Token 用量汇总")
        log_info(
            f"{'Agent':<12} {'Steps':<8} {'Prompt':<12} {'Completion':<14} {'Total':<12} {'耗时(ms)'}"
        )
        log_info("-" * 72)
        for s in summaries:
            log_info(
                f"{s['agent_type']:<12} "
                f"{s['steps']:<8} "
                f"{s['total_prompt_tokens']:<12,} "
                f"{s['total_completion_tokens']:<14,} "
                f"{s['total_tokens']:<12,} "
                f"{s['total_latency_ms']:.0f}"
            )
        log_info("-" * 72)
        log_info(
            f"{'合计':<12} {'—':<8} {'—':<12} {'—':<14} {total_tokens:<12,} {total_latency:.0f}"
        )
        log_info("=" * 72)

    def _save_usage_summary(self, summaries: List[Dict]):
        """保存 token 用量汇总到文件"""
        if not summaries or self.output_dir is None:
            return

        total_tokens = sum(s["total_tokens"] for s in summaries)
        total_latency = sum(s["total_latency_ms"] for s in summaries)

        lines = [
            "# Token 用量汇总",
            "",
            f"- **总 Token 数**: {total_tokens:,}",
            f"- **总耗时**: {total_latency:.0f} ms",
            "",
            "## 各 Agent 明细",
            "",
            "| Agent | 调用次数 | Prompt Tokens | Completion Tokens | Total Tokens | 耗时(ms) |",
            "|-------|---------|---------------|-------------------|--------------|----------|",
        ]
        for s in summaries:
            lines.append(
                f"| {s['agent_type']} "
                f"| {s['steps']} "
                f"| {s['total_prompt_tokens']:,} "
                f"| {s['total_completion_tokens']:,} "
                f"| {s['total_tokens']:,} "
                f"| {s['total_latency_ms']:.0f} |"
            )
        lines.append(
            f"| **合计** | — | — | — | **{total_tokens:,}** | **{total_latency:.0f}** |"
        )
        lines.append("")
        lines.append("## 每步明细")
        lines.append("")

        for s in summaries:
            lines.append(f"### {s['agent_type']}")
            lines.append("")
            lines.append("| Step | 模型 | Prompt | Completion | Total | 耗时(ms) |")
            lines.append("|------|------|--------|------------|-------|----------|")
            for d in s.get("details", []):
                lines.append(
                    f"| {d['step']} | {d['model']} "
                    f"| {d['prompt_tokens']:,} "
                    f"| {d['completion_tokens']:,} "
                    f"| {d['total_tokens']:,} "
                    f"| {d['latency_ms']} |"
                )
            lines.append("")

        (self.output_dir / "usage_summary.md").write_text(
            "\n".join(lines), encoding="utf-8"
        )

    def _read_generated_code(self, sub_dir: str) -> str:
        """
        读取输出目录下指定子目录的所有代码，
        用于注入到下游 Agent 的 context
        """
        if self.output_dir is None:
            return ""
        target_dir = self.output_dir / sub_dir
        if not target_dir.exists():
            return ""

        parts = []
        for file_path in sorted(target_dir.rglob("*")):
            if file_path.is_file():
                rel = file_path.relative_to(self.output_dir)
                content = file_path.read_text(encoding="utf-8", errors="replace")
                parts.append(f"### FILE: {rel}\n{content}\n")
        return "\n".join(parts)

    def get_task_status(self, main_task_id: str) -> Dict:
        """获取任务执行状态"""
        status = {
            "main_task_id": main_task_id,
            "tasks": {},
        }

        for suffix in ["_backend", "_frontend", "_test", "_audit"]:
            task_id = f"{main_task_id}{suffix}"
            task_info = self.db.get_task(task_id)
            if task_info:
                status["tasks"][suffix[1:]] = {
                    "task_id": task_id,
                    "status": task_info["status"],
                    "result": task_info.get("result"),
                    "error": task_info.get("error"),
                }

        return status
