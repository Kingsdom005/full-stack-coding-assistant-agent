"""
前端专家智能体
负责生成前端组件代码，并根据后端 API 契约调整接口调用
"""

from typing import Dict, List
from agents.base_agent import BaseAgent


class FrontendAgent(BaseAgent):
    """前端专家 Agent"""

    def get_system_prompt(self) -> str:
        return """你是一位资深前端开发专家，精通 React/Vue/Angular 等主流框架。
你的职责是：
1. 根据 UI 需求生成高质量的前端组件代码
2. 编写类型安全的 TypeScript 代码
3. 实现响应式布局和交互逻辑
4. 根据后端 API 契约生成接口调用代码

输出要求：
- 使用函数式组件和 Hooks
- 包含完整的 TypeScript 类型定义
- 代码必须可直接运行
"""

    def execute(self, task_id: str, context: Dict) -> Dict:
        """
        执行前端开发任务

        流程：
        1. 获取后端 API 契约（如果有）
        2. 调用 LLM 生成前端代码
        3. 根据 API 契约生成接口调用层
        4. 记录代码变更
        """
        # 1. 获取 API 契约
        api_contracts = self.db.get_api_contracts(task_id)
        contracts_str = ""
        if api_contracts:
            contracts_str = "\n## 后端 API 契约（必须严格按照此契约调用接口）\n"
            for contract in api_contracts:
                contracts_str += f"""
### {contract['method']} {contract['endpoint']}
- 请求 Schema: {contract.get('request_schema', '无')}
- 响应 Schema: {contract.get('response_schema', '无')}
"""

        # 2. 调用 LLM 生成代码
        description = context.get("description", "")
        requirements = context.get("requirements", "")

        prompt = f"""请根据以下需求生成前端代码：

## 需求描述
{description}

## 详细要求
{requirements}
{contracts_str}

请生成完整的前端代码，包括：
1. 组件定义（使用 React + TypeScript）
2. 状态管理
3. API 接口调用函数（根据上面的 API 契约）
4. 样式（使用 Tailwind CSS）

代码要求：
- 使用函数式组件和 Hooks
- 完整的 TypeScript 类型定义
- 包含错误处理和加载状态
"""

        code_result = self._call_llm(prompt, temperature=0.3)

        # 3. 记录代码变更
        self._log_change(
            task_id=task_id,
            file_path="frontend/generated_component.tsx",
            change_type="create",
            diff=code_result,
        )

        # 4. 保存结果
        result = {
            "status": "success",
            "code": code_result,
            "api_contracts_used": len(api_contracts),
        }
        self._save_result(task_id, str(result))

        return result
