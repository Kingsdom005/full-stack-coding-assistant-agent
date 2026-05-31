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
- 每个文件用 ### FILE: 标记，格式如下：
  ### FILE: backend/main.py
  ```python
  # code here
  ```
- 代码必须可直接运行
- API 接口必须包含完整的请求/响应 Schema
- 在代码注释中标注 API 契约信息（endpoint, method, request_schema, response_schema）
"""

    def execute(self, task_id: str, context: Dict) -> Dict:
        """
        执行后端开发任务

        流程：
        1. 检查依赖
        2. 如果是迭代模式，读取已有代码注入 prompt
        3. 调用 LLM 生成后端代码
        4. 解析多文件输出并写入文件系统
        5. 提取 API 契约并保存到数据库
        6. 更新任务状态
        """
        # 1. 检查依赖
        if not self._check_dependencies(context, ["description"]):
            raise ValueError("缺少必需的任务描述")

        description = context["description"]
        requirements = context.get("requirements", "")
        is_iteration = context.get("is_iteration", False)

        # 2. 构建 prompt
        prompt = f"""请根据以下需求生成后端代码：

## 需求描述
{description}

## 详细要求
{requirements}
"""

        # 迭代模式：注入已有代码
        if is_iteration:
            existing_code = self._collect_existing_code()
            if existing_code:
                prompt += f"""
## 已有代码（请基于以下代码进行修改，不要重复生成已有文件）
{existing_code}

重要：请只输出需要新增或修改的文件，不要重复输出未修改的文件。
"""

        prompt += """
请生成完整的后端代码，每个文件用 ### FILE: 标记，格式如下：

### FILE: backend/main.py
```python
# code here
```

### FILE: backend/api.py
```python
# code here
```

在代码中用注释标注 API 契约，格式如下：
### API_CONTRACT_START
endpoint: /api/xxx
method: GET/POST/...
request_schema: {{...}}
response_schema: {{...}}
### API_CONTRACT_END
"""

        # 3. 调用 LLM 生成代码
        system_prompt = self.get_system_prompt()
        code_result = self._call_llm(prompt, temperature=0.3)

        # 4. 解析多文件输出并写入文件系统
        files = self._parse_llm_code_output(code_result)
        change_type = "update" if is_iteration else "create"
        for file_path, content in files.items():
            self._write_file(file_path, content)
            self._log_change(
                task_id=task_id,
                file_path=file_path,
                change_type=change_type,
                diff=content,
            )

        # 5. 提取 API 契约
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

        # 6. 保存结果
        result = {
            "status": "success",
            "files": list(files.keys()),
            "contracts": contracts,
        }

        # 7. 保存 Agent 执行 trace（完整 I/O 审计）
        self._save_trace(
            task_id=task_id,
            system_prompt=system_prompt,
            user_prompt=prompt,
            llm_response=code_result,
            parsed_result=result,
        )
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
