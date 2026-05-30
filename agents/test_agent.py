"""
测试专家智能体
负责生成单元测试、集成测试代码
"""

from typing import Dict
from agents.base_agent import BaseAgent


class TestAgent(BaseAgent):
    """测试专家 Agent"""

    def get_system_prompt(self) -> str:
        return """你是一位资深测试开发专家，精通单元测试、集成测试和 E2E 测试。
你的职责是：
1. 为前端组件生成单元测试（Jest + React Testing Library）
2. 为后端 API 生成集成测试
3. 编写测试用例覆盖正常和异常场景
4. 确保测试代码的可维护性和可读性

输出要求：
- 测试用例必须完整覆盖主要逻辑分支
- 包含 Mock 数据和方法
- 测试代码必须可直接运行
"""

    def execute(self, task_id: str, context: Dict) -> Dict:
        """
        执行测试生成任务

        流程：
        1. 获取前后端代码
        2. 调用 LLM 生成测试代码
        3. 记录代码变更
        """
        # 1. 获取前后端代码
        frontend_code = context.get("frontend_code", "")
        backend_code = context.get("backend_code", "")

        # 2. 调用 LLM 生成测试
        prompt = f"""请为以下代码生成完整的测试：

## 前端代码
```tsx
{frontend_code}
```

## 后端代码
```python
{backend_code}
```

请生成：
1. 前端单元测试（使用 Jest + React Testing Library）
2. 后端 API 集成测试（使用 pytest）
3. Mock 数据和辅助函数

测试要求：
- 覆盖正常流程和异常流程
- 包含边界条件测试
- 测试代码可直接运行
"""

        test_code = self._call_llm(prompt, temperature=0.3)

        # 3. 记录代码变更
        self._log_change(
            task_id=task_id,
            file_path="tests/generated_tests.py",
            change_type="create",
            diff=test_code,
        )

        # 4. 保存结果
        result = {
            "status": "success",
            "test_code": test_code,
        }
        self._save_result(task_id, str(result))

        return result
