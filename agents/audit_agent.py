"""
代码审计智能体
异步执行安全扫描、代码质量检查
"""

import json
import re
from datetime import datetime
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
每个问题一行 JSON 对象，包含字段：
{
  "severity": "high|medium|low",
  "category": "安全|质量|性能",
  "message": "问题描述",
  "suggestion": "修复建议",
  "line_number": 可选的行号
}
"""

    def _get_sub_dir(self) -> str:
        return "audits"

    def execute(self, task_id: str, context: Dict) -> Dict:
        """
        执行代码审计任务（异步）

        流程：
        1. 获取待审计的代码
        2. 调用 LLM 进行审计
        3. 解析审计结果
        4. 保存到数据库
        5. 将审计报告写入文件系统
        """
        # 1. 获取待审计代码
        code = context.get("code", "")
        file_path = context.get("file_path", "unknown")
        agent_type = context.get("agent_type", "unknown")

        if not code:
            return {"status": "skipped", "reason": "no code to audit"}

        # 2. 调用 LLM 审计
        system_prompt = self.get_system_prompt()
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

        # 5. 将审计报告写入文件系统
        audit_md = self._format_audit_report(reports, file_path, audit_result)
        audit_filename = f"audits/audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        self._write_file(audit_filename, audit_md)

        # 6. 返回结果
        result = {
            "status": "success",
            "reports_count": len(reports),
            "high_severity": sum(1 for r in reports if r.get("severity") == "high"),
            "reports": reports,
            "audit_file": audit_filename,
        }
        self._save_result(task_id, str(result))

        # 7. 保存 Agent 执行 trace（完整 I/O 审计）
        self._save_trace(
            task_id=task_id,
            system_prompt=system_prompt,
            user_prompt=prompt,
            llm_response=audit_result,
            parsed_result=result,
        )

        return result

    def _format_audit_report(
        self, reports: List[Dict], file_path: str, raw_result: str
    ) -> str:
        """将审计结果格式化为 Markdown 报告"""
        lines = [
            f"# 代码审计报告",
            "",
            f"- 审计时间: {datetime.now().isoformat()}",
            f"- 审计文件: {file_path}",
            f"- 发现问题数: {len(reports)}",
            "",
            "## 问题列表",
            "",
        ]
        for i, r in enumerate(reports, 1):
            lines.append(
                f"### {i}. [{r.get('severity', 'low').upper()}] {r.get('category', '未知')}"
            )
            lines.append(f"- **描述**: {r.get('message', '')}")
            lines.append(f"- **建议**: {r.get('suggestion', '')}")
            if r.get("line_number"):
                lines.append(f"- **行号**: {r.get('line_number')}")
            lines.append("")

        lines += ["## 原始审计输出", "", "```", raw_result, "```", ""]
        return "\n".join(lines)

    def _parse_audit_result(self, audit_text: str) -> List[Dict]:
        """
        解析 LLM 返回的审计结果
        支持多种格式：
        1. ```json 代码块中的 JSON 数组或对象
        2. 裸 JSON 数组 [{{}}, {{}}]
        3. 每行一个 JSON 对象
        """
        reports = []

        # 尝试 1: json 代码块（支持 ```json 和 ``` 两种格式）
        json_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", audit_text, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group(1).strip())
                if isinstance(data, list):
                    return [r for r in data if isinstance(r, dict)]
                elif isinstance(data, dict):
                    return [data]
            except json.JSONDecodeError:
                pass

        # 尝试 2: 裸 JSON 数组或对象（整个文本就是 JSON）
        stripped = audit_text.strip()
        if stripped.startswith("[") or stripped.startswith("{"):
            try:
                data = json.loads(stripped)
                if isinstance(data, list):
                    return [r for r in data if isinstance(r, dict)]
                elif isinstance(data, dict):
                    return [data]
            except json.JSONDecodeError:
                pass

        # 尝试 3: 逐行解析 JSON 对象
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
