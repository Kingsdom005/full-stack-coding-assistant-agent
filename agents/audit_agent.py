"""
代码审计智能体
异步执行安全扫描、代码质量检查
"""

import re
from typing import Dict, List
from agents.base_agent import BaseAgent


class AuditAgent(BaseAgent):
    """代码审计专家 Agent"""

    def get_system_prompt(self) -> str:
        return """你是一位资深代码安全审计专家，精通 OWASP Top 10、代码质量分析。
你的职责是：
1. 检查代码安全漏洞（SQL 注入、XSS、CSRF 等）
2. 分析代码质量和最佳实践
3. 检查敏感信息泄露（API Key、密码等）
4. 生成结构化审计报告

输出格式（JSON）：
{
  "severity": "high|medium|low",
  "category": "安全|质量|性能",
  "message": "问题描述",
  "suggestion": "修复建议",
  "line_number": 可选的行号
}
"""

    def execute(self, task_id: str, context: Dict) -> Dict:
        """
        执行代码审计任务（异步）

        流程：
        1. 获取待审计的代码
        2. 调用 LLM 进行审计
        3. 解析审计结果
        4. 保存到数据库
        """
        # 1. 获取待审计代码
        code = context.get("code", "")
        file_path = context.get("file_path", "unknown")
        agent_type = context.get("agent_type", "unknown")

        if not code:
            return {"status": "skipped", "reason": "no code to audit"}

        # 2. 调用 LLM 审计
        prompt = f"""请审计以下代码，找出安全漏洞和代码质量问题：

## 代码
```
{code}
```

## 文件路径
{file_path}

请以 JSON 格式输出审计结果，每个问题一个 JSON 对象，包含字段：
- severity: 严重程度 (high/medium/low)
- category: 问题类别 (安全/质量/性能)
- message: 问题描述
- suggestion: 修复建议
- line_number: 问题所在行号（如果可确定）

如果有多个问题，每行输出一个 JSON 对象。
"""
        audit_result = self._call_llm(prompt, temperature=0.2)

        # 3. 解析审计结果
        reports = self._parse_audit_result(audit_result)

        # 4. 保存到数据库
        for report in reports:
            self.db.add_audit_report(
                task_id=task_id,
                agent_type=agent_type,
                severity=report.get("severity", "low"),
                message=report.get("message", ""),
                file_path=file_path,
                line_number=report.get("line_number"),
            )

        # 5. 返回结果
        result = {
            "status": "success",
            "reports_count": len(reports),
            "high_severity": sum(1 for r in reports if r.get("severity") == "high"),
            "reports": reports,
        }
        self._save_result(task_id, str(result))

        return result

    def _parse_audit_result(self, audit_text: str) -> List[Dict]:
        """
        解析 LLM 返回的审计结果
        支持两种格式：
        1. 每行一个 JSON 对象
        2. 代码块中的 JSON 数组
        """
        reports = []

        # 尝试解析代码块中的 JSON
        json_match = re.search(r"```json(.*?)```", audit_text, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group(1).strip())
                if isinstance(data, list):
                    return data
                elif isinstance(data, dict):
                    return [data]
            except json.JSONDecodeError:
                pass

        # 尝试逐行解析 JSON
        for line in audit_text.split("\n"):
            line = line.strip()
            if not line or not line.startswith("{"):
                continue
            try:
                report = json.loads(line)
                if "severity" in report and "message" in report:
                    reports.append(report)
            except json.JSONDecodeError:
                continue

        return reports

    def run_security_scan(self, task_id: str, code: str) -> Dict:
        """
        执行安全扫描（同步，用于关键代码）

        检查常见安全漏洞：
        - SQL 注入
        - XSS
        - 敏感信息泄露
        - 不安全的依赖
        """
        prompt = f"""请对以下代码进行安全扫描，重点检查：

1. SQL 注入漏洞
2. XSS 跨站脚本
3. CSRF 漏洞
4. 敏感信息泄露（硬编码密码、API Key 等）
5. 不安全的加密算法
6. 权限绕过风险

代码：
```
{code}
```

只输出发现的安全问题，格式：
[SEVERITY] 问题描述 - 修复建议
"""
        return {"scan_result": self._call_llm(prompt, temperature=0.1)}
