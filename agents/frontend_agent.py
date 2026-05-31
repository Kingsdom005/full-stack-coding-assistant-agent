"""
前端专家智能体
负责生成前端组件代码，并根据后端 API 契约调整接口调用
"""

from typing import Dict

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

输出格式要求：
- 每个文件用 ### FILE: 标记，格式如下：
  ### FILE: frontend/App.tsx
  ```tsx
  // code here
  ```
- 使用函数式组件和 Hooks
- 包含完整的 TypeScript 类型定义
- 代码必须可直接运行

【重要】必须同时生成前端项目的工程配置文件，让项目可以 npm install && npm start 直接运行：
- frontend/package.json（含 react、react-dom、react-scripts 等必要依赖）
- frontend/tsconfig.json
- frontend/public/index.html（入口 HTML）
"""

    def execute(self, task_id: str, context: Dict) -> Dict:
        """
        执行前端开发任务

        流程：
        1. 获取后端 API 契约（如果有）
        2. 如果是迭代模式，读取已有代码注入 prompt
        3. 调用 LLM 生成前端代码
        4. 解析多文件输出并写入文件系统
        5. 记录代码变更
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

        description = context.get("description", "")
        requirements = context.get("requirements", "")
        is_iteration = context.get("is_iteration", False)

        # 2. 构建 prompt
        prompt = f"""请根据以下需求生成前端代码：

## 需求描述
{description}

## 详细要求
{requirements}
{contracts_str}
"""

        # 迭代模式：注入已有代码
        if is_iteration:
            existing_code = self._collect_existing_code()
            if existing_code:
                prompt += f"""
## 已有代码（请基于以下代码进行修改，不要重复生成未修改的文件）
{existing_code}
"""

        prompt += """
请生成完整的前端代码，每个文件用 ### FILE: 标记，格式如下：

### FILE: frontend/App.tsx
```tsx
// code here
```

### FILE: frontend/components/Login.tsx
```tsx
// code here
```

代码要求：
- 使用函数式组件和 Hooks
- 完整的 TypeScript 类型定义
- 包含错误处理和加载状态
- 使用 Tailwind CSS 做样式

【必须生成以下工程配置文件，否则项目无法运行】：
### FILE: frontend/package.json
包含完整的 dependencies（react, react-dom, react-scripts 等）和 scripts（start, build, test）

### FILE: frontend/tsconfig.json
TypeScript 配置，target 为 ES2020，jsx 为 react-jsx，strict 模式

### FILE: frontend/public/index.html
React 入口 HTML 文件
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

        # 5. 保存结果
        result = {
            "status": "success",
            "files": list(files.keys()),
            "api_contracts_used": len(api_contracts),
        }

        # 6. 保存 Agent 执行 trace（完整 I/O 审计）
        self._save_trace(
            task_id=task_id,
            system_prompt=system_prompt,
            user_prompt=prompt,
            llm_response=code_result,
            parsed_result=result,
        )
        self._save_result(task_id, str(result))

        return result
