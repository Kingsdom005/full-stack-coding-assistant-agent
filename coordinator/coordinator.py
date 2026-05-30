"""
主协调器 - 负责任务拆解、调度和上下文管理
"""

import uuid
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

    def __init__(self, config_path: str = "config.yaml"):
        # 初始化核心组件
        self.model_router = ModelRouter()
        self.db = ContextDB()
        self.dag = DAGScheduler()

        # 初始化 Agents
        self.agents = {
            "frontend": FrontendAgent("frontend", self.model_router, self.db),
            "backend": BackendAgent("backend", self.model_router, self.db),
            "test": TestAgent("test", self.model_router, self.db),
            "audit": AuditAgent("audit", self.model_router, self.db),
        }

    def submit_task(self, description: str, requirements: str = "") -> str:
        """
        提交任务 - 拆解任务并添加到 DAG

        Args:
            description: 任务描述
            requirements: 详细需求

        Returns:
            主任务 ID
        """
        # 生成主任务 ID
        main_task_id = f"task_{uuid.uuid4().hex[:8]}"

        # 创建主任务
        self.db.create_task(main_task_id, description)

        # 拆解子任务并添加到 DAG
        # 1. 后端任务（无依赖）
        backend_task_id = f"{main_task_id}_backend"
        self.db.create_task(backend_task_id, f"{description} - 后端开发")
        self.dag.add_task(
            backend_task_id,
            agent_type="backend",
            dependencies=[],
            context={"description": description, "requirements": requirements},
        )

        # 2. 前端任务（依赖后端完成，以获取 API 契约）
        frontend_task_id = f"{main_task_id}_frontend"
        self.db.create_task(frontend_task_id, f"{description} - 前端开发")
        self.dag.add_task(
            frontend_task_id,
            agent_type="frontend",
            dependencies=[backend_task_id],
            context={"description": description, "requirements": requirements},
        )

        # 3. 测试任务（依赖前后端完成）
        test_task_id = f"{main_task_id}_test"
        self.db.create_task(test_task_id, f"{description} - 测试")
        self.dag.add_task(
            test_task_id,
            agent_type="test",
            dependencies=[backend_task_id, frontend_task_id],
            context={"description": description},
        )

        # 4. 审计任务（异步，依赖所有任务完成）
        audit_task_id = f"{main_task_id}_audit"
        self.db.create_task(audit_task_id, f"{description} - 审计")
        self.dag.add_task(
            audit_task_id,
            agent_type="audit",
            dependencies=[backend_task_id, frontend_task_id, test_task_id],
            context={"description": description},
        )

        return main_task_id

    def run(self, main_task_id: str) -> Dict:
        """
        主运行循环 - DAG 调度执行

        Returns:
            所有任务的执行结果
        """
        results = {}
        task_mapping = {
            f"{main_task_id}_backend": "backend",
            f"{main_task_id}_frontend": "frontend",
            f"{main_task_id}_test": "test",
            f"{main_task_id}_audit": "audit",
        }

        # DAG 调度循环
        while not self.dag.is_completed():
            runnable = self.dag.get_runnable_tasks()

            if not runnable:
                # 检查是否有失败的任务阻塞了流程
                if not self.dag.is_completed():
                    raise RuntimeError("任务调度死锁：没有可运行任务但 DAG 未完成")
                break

            for task_id in runnable:
                agent_type = self.dag.tasks[task_id]["agent_type"]
                agent = self.agents.get(agent_type)

                if not agent:
                    self.dag.mark_failed(task_id)
                    continue

                # 获取任务上下文（包含依赖的结果）
                context = self.dag.get_task_context(task_id)

                try:
                    # 执行任务
                    result = agent.execute(task_id, context)

                    # 保存结果到 DAG（供下游任务使用）
                    self.dag.tasks[task_id]["result"] = result

                    # 标记完成
                    self.dag.mark_done(task_id)
                    results[task_id] = result

                except Exception as e:
                    # 标记失败
                    self.dag.mark_failed(task_id)
                    self.db.update_task_status(task_id, "failed", error=str(e))
                    results[task_id] = {"status": "failed", "error": str(e)}

        return results

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
