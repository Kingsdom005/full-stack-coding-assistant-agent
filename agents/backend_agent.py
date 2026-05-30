"""
后端专家智能体
负责生成后端代码、API 接口，并提取 API 契约供前端使用
"""

import json
import re
from typing import Dict, List, Optional
from agents.base_agent import BaseAgent


class BackendAgent(BaseAgent):
    """后端专家 Agent"""

    def get_system_prompt(self) -> str:
        return """你是一位资深后端开发专家，精通 Python/Java/Node.js 后端开发。
你的职责是：
1. 根据需求生成高质量的后端代码
2. 设计 RESTful API 接口
3. 编写数据库模型和数据访问层
4. 确保代码的安全性、性能和可维护性

输出格式要求：
- 代码必须可直接运行
- API 接口必须包含完整的请求/响应 Schema
- 在代码注释中标注 API 契约信息（endpoint, method, request_schema, response_schema）
"""

    def execute(self, task_id: str, context: Dict) -> Dict:
        """
        执行后端开发任务

        流程：
        1. 检查依赖（可能需要前端 Agent 的 UI 需求）
        2. 调用 LLM 生成后端代码
        3. 提取 API 契约并保存到数据库
        4. 更新任务状态
        5. 通知审计 Agent（异步）
        """
        # 1. 检查依赖
        if not self._check_dependencies(context, ["description"]):
            raise ValueError("缺少必需的任务描述")

        description = context["description"]
        requirements = context.get("requirements", "")

        # 2. 调用 LLM 生成代码
        prompt = f"""请根据以下需求生成后端代码：

## 需求描述
{description}

## 详细要求
{requirements}

请生成完整的后端代码，包括：
1. API 路由定义
2. 数据模型
3. 业务逻辑
4. 错误处理

在代码中用注释标注 API 契约，格式如下：
### API_CONTRACT_START
endpoint: /api/xxx
method: GET/POST/...
request_schema: {{...}}
response_schema: {{...}}
### API_CONTRACT_END
"""
        code_result = self._call_llm(prompt, temperature=0.3)

        # 3. 提取 API 契约
        contracts = self._extract_api_contracts(code_result)
        for contract in contracts:
            self.db.save_api_contract(
                task_id=task_id,
                endpoint=contract["endpoint"],
                method=contract["method"],
                request_schema=contract.get("request_schema"),
                response_schema=contract.get("response_schema"),
                created_by="backend",
            )

        # 4. 记录代码变更
        self._log_change(
            task_id=task_id,
            file_path="backend/generated_code.py",
            change_type="create",
            diff=code_result,
        )

        # 5. 保存结果
        result = {
            "status": "success",
            "code": code_result,
            "contracts": contracts,
        }
        self._save_result(task_id, json.dumps(result))

        return result

    def _extract_api_contracts(self, code: str) -> List[Dict]:
        """
        从生成的代码中提取 API 契约

        匹配格式：
        ### API_CONTRACT_START
        endpoint: /api/xxx
        method: GET
        request_schema: {...}
        response_schema: {...}
        ### API_CONTRACT_END
        """
        contracts = []
        pattern = r"### API_CONTRACT_START(.*?)### API_CONTRACT_END"
        matches = re.findall(pattern, code, re.DOTALL)

        for match in matches:
            contract = {}
            lines = match.strip().split("\n")
            for line in lines:
                if ":" in line:
                    key, value = line.split(":", 1)
                    key = key.strip()
                    value = value.strip()
                    if key in ["endpoint", "method"]:
                        contract[key] = value
                    elif key in ["request_schema", "response_schema"]:
                        try:
                            contract[key] = json.loads(value)
                        except json.JSONDecodeError:
                            contract[key] = {"raw": value}
            if "endpoint" in contract and "method" in contract:
                contracts.append(contract)

        return contracts
