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

输出格式要求：
- 每个文件用 ### FILE: 标记，格式如下：
  ### FILE: tests/test_api.py
  ```python
  # code here
  ```
- 测试用例必须完整覆盖主要逻辑分支
- 包含 Mock 数据和方法
- 测试代码必须可直接运行

【重要】如果生成了前端测试（.tsx/.ts 文件），也必须生成测试运行所需的配置文件：
- frontend/jest.config.js（或 package.json 中的 jest 配置节）
- frontend/src/setupTests.ts（Jest setup 文件，导入 @testing-library/jest-dom）
"""

    def execute(self, task_id: str, context: Dict) -> Dict:
        """
        执行测试生成任务

        流程：
        1. 获取前后端代码
        2. 如果是迭代模式，读取已有测试代码注入 prompt
        3. 调用 LLM 生成测试代码
        4. 解析多文件输出并写入文件系统
        5. 记录代码变更
        """
        # 1. 获取前后端代码
        frontend_code = context.get("frontend_code", "")
        backend_code = context.get("backend_code", "")
        is_iteration = context.get("is_iteration", False)

        # 2. 构建 prompt
        prompt = f"""请为以下代码生成完整的测试：

## 前端代码
```tsx
{frontend_code}
```

## 后端代码
```python
{backend_code}
```
"""

        # 迭代模式：注入已有测试代码
        if is_iteration:
            existing_code = self._collect_existing_code()
            if existing_code:
                prompt += f"""
## 已有测试代码（请基于以下代码进行补充或修改）
{existing_code}
"""

        prompt += """
请生成：
1. 前端单元测试（使用 Jest + React Testing Library）——注意放在 frontend/src/ 下
2. 后端 API 集成测试（使用 pytest）
3. Mock 数据和辅助函数
4. 测试运行所需的配置文件（如 jest.config.js、setupTests.ts）

每个文件用 ### FILE: 标记，格式如下：

后端测试（放在 tests/ 目录）：
### FILE: tests/test_api.py
```python
# code here
```

前端测试（放在 frontend/src/ 目录，文件名以 .test.tsx 结尾以匹配 CRA/Jest 约定）：
### FILE: frontend/src/__tests__/ComponentName.test.tsx
```tsx
// code here
```

或直接放在 frontend/src/ 下：
### FILE: frontend/src/components.test.tsx
```tsx
// code here
```

【如果生成了前端测试，必须同时生成以下配置文件】：
### FILE: frontend/jest.config.js
```js
module.exports = {
  testEnvironment: 'jsdom',
  setupFilesAfterSetup: ['<rootDir>/src/setupTests.ts'],
};
```

### FILE: frontend/src/setupTests.ts
```ts
import '@testing-library/jest-dom';
```

测试要求：
- 覆盖正常流程和异常流程
- 包含边界条件测试
- 测试代码可直接运行
"""

        # 3. 调用 LLM 生成测试
        system_prompt = self.get_system_prompt()
        test_code = self._call_llm(prompt, temperature=0.3)

        # 4. 解析多文件输出并写入文件系统
        files = self._parse_llm_code_output(test_code)
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
        }

        # 6. 保存 Agent 执行 trace（完整 I/O 审计）
        self._save_trace(
            task_id=task_id,
            system_prompt=system_prompt,
            user_prompt=prompt,
            llm_response=test_code,
            parsed_result=result,
        )
        self._save_result(task_id, str(result))

        return result
