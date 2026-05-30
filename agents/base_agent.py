"""
Agent 基类 - 定义所有智能体的通用接口
"""

from abc import ABC, abstractmethod
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
        return self.model_router.chat(
            messages=messages,
            model=self.model,
            temperature=temperature,
        )

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
