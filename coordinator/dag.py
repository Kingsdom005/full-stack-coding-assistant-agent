"""
DAG 调度器 - 管理任务依赖关系
实现有向无环图的任务编排
"""

from typing import Dict, List, Set, Optional
from collections import defaultdict, deque


class DAGScheduler:
    """有向无环图任务调度器"""

    def __init__(self):
        # 邻接表：task_id -> [依赖它的下游任务]
        self.graph: Dict[str, List[str]] = defaultdict(list)
        # 入度：task_id -> 依赖数量
        self.in_degree: Dict[str, int] = defaultdict(int)
        # 任务信息存储
        self.tasks: Dict[str, Dict] = {}
        # 任务状态
        self.status: Dict[str, str] = defaultdict(lambda: "pending")

    def add_task(
        self,
        task_id: str,
        agent_type: str,
        dependencies: Optional[List[str]] = None,
        context: Optional[Dict] = None,
    ):
        """
        添加任务到 DAG

        Args:
            task_id: 任务 ID
            agent_type: Agent 类型
            dependencies: 依赖的任务 ID 列表
            context: 任务上下文
        """
        dependencies = dependencies or []
        self.tasks[task_id] = {
            "agent_type": agent_type,
            "dependencies": dependencies,
            "context": context or {},
        }

        # 更新入度和邻接表
        self.in_degree[task_id] = len(dependencies)
        for dep in dependencies:
            self.graph[dep].append(task_id)

    def get_runnable_tasks(self) -> List[str]:
        """
        获取当前可运行的任务（所有依赖已完成）

        Returns:
            可运行任务 ID 列表
        """
        runnable = []
        for task_id, deg in self.in_degree.items():
            if deg == 0 and self.status[task_id] == "pending":
                # 检查所有依赖是否都已完成
                deps = self.tasks[task_id]["dependencies"]
                if all(self.status[d] == "completed" for d in deps):
                    runnable.append(task_id)
        return runnable

    def mark_done(self, task_id: str):
        """标记任务完成，并更新下游任务的入度"""
        self.status[task_id] = "completed"

        # 更新下游任务的入度
        for downstream in self.graph[task_id]:
            self.in_degree[downstream] -= 1

    def mark_failed(self, task_id: str):
        """标记任务失败，并级联标记所有下游任务为失败"""
        self.status[task_id] = "failed"
        # 级联标记所有下游任务为失败，避免死锁
        self._cascade_failure(task_id)

    def _cascade_failure(self, task_id: str):
        """递归标记所有下游任务为失败（BFS 遍历）"""
        from collections import deque
        queue = deque([task_id])
        while queue:
            current = queue.popleft()
            for downstream in self.graph.get(current, []):
                if self.status[downstream] not in ("completed", "failed"):
                    self.status[downstream] = "failed"
                    queue.append(downstream)

    def is_completed(self) -> bool:
        """检查所有任务是否已完成"""
        return all(
            self.status[task_id] in ("completed", "failed")
            for task_id in self.tasks
        )

    def get_task_context(self, task_id: str) -> Dict:
        """
        获取任务的完整上下文（包括依赖任务的结果）

        Returns:
            合并了所有依赖任务结果的上下文
        """
        context = self.tasks[task_id]["context"].copy()

        # 合并依赖任务的结果
        for dep_id in self.tasks[task_id]["dependencies"]:
            dep_result = self.tasks[dep_id].get("result", {})
            context[f"{self.tasks[dep_id]['agent_type']}_result"] = dep_result

        return context

    def topological_sort(self) -> List[str]:
        """
        拓扑排序（用于获取执行顺序）

        Returns:
            拓扑排序后的任务 ID 列表
        """
        in_deg = self.in_degree.copy()
        queue = deque([t for t, d in in_deg.items() if d == 0])
        order = []

        while queue:
            task = queue.popleft()
            order.append(task)
            for downstream in self.graph[task]:
                in_deg[downstream] -= 1
                if in_deg[downstream] == 0:
                    queue.append(downstream)

        return order

    def reset(self):
        """
        清空 DAG 所有状态，用于迭代模式下重新提交任务

        保留已完成的任务结果不清除（由 Coordinator 管理上下文），
        此处仅清空调度相关状态。
        """
        self.graph.clear()
        self.in_degree.clear()
        self.tasks.clear()
        # status 使用 defaultdict，清空需要重新初始化
        self.status = defaultdict(lambda: "pending")
