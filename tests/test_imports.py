"""
模型路由 / 配置 / 工具模块导入验证测试
"""

import pytest


class TestImports:
    """验证所有模块可以正常导入（不触发 LLM 调用）"""

    def test_import_utils(self):
        from utils.logger import info, debug, error, warning, get_logger, setup_logger
        from utils.config_validator import validate_config, ConfigValidator
        from utils.output_manager import OutputManager

    def test_import_model_config(self):
        """model/config.py 在 mock API key 下应能正常加载"""
        import os

        os.environ.setdefault("TENCENT_API_KEY", "sk-mock-for-test")
        from model.config import (
            MODEL_CONFIG,
            DATABASE_CONFIG,
            TENCENT_API_KEY,
            TENCENT_API_BASE,
        )

        assert isinstance(MODEL_CONFIG, dict)
        assert isinstance(DATABASE_CONFIG, dict)

    def test_import_model_router_no_llm_call(self):
        """ModelRouter 可以被导入和实例化（不调用 LLM）"""
        import os

        os.environ.setdefault("TENCENT_API_KEY", "sk-mock-for-test")
        from model.model_router import ModelRouter

        router = ModelRouter()
        assert router is not None

    def test_import_dag(self):
        from coordinator.dag import DAGScheduler

    def test_import_storage(self):
        import os

        os.environ.setdefault("TENCENT_API_KEY", "sk-mock-for-test")
        from storage.context_db import ContextDB

    def test_import_agents(self):
        """Agent 导入验证（不执行 execute）"""
        import os

        os.environ.setdefault("TENCENT_API_KEY", "sk-mock-for-test")
        from agents.base_agent import BaseAgent
        from agents.backend_agent import BackendAgent
        from agents.frontend_agent import FrontendAgent
        from agents.test_agent import TestAgent
        from agents.audit_agent import AuditAgent
