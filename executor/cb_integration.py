"""
CodeBuddy CLI 集成模块
通过命令行调用 CodeBuddy CLI 执行代码操作
"""

import json
import os
import subprocess
import tempfile
from typing import Dict, List, Optional

from model.config import CODEBUDDY_CONFIG


class CodeBuddyExecutor:
    """CodeBuddy CLI 执行器（静态方法）"""

    @staticmethod
    def _run_cli(command: str, args: List[str], timeout: Optional[int] = None) -> Dict:
        """
        执行 CodeBuddy CLI 命令

        Args:
            command: CLI 命令（如 apply-edit, run-code）
            args: 命令参数列表
            timeout: 超时时间（秒），None 则使用配置文件中的默认值

        Returns:
            执行结果字典
        """
        # 使用配置文件中的 CLI 路径
        cli_path = CODEBUDDY_CONFIG["cli_path"]
        cmd = [cli_path, command] + args

        # 使用配置文件中的超时时间或传入的参数
        actual_timeout = timeout or CODEBUDDY_CONFIG["timeout"]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=actual_timeout,
            )
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": f"命令超时（{actual_timeout}秒）",
            }
        except FileNotFoundError:
            return {
                "success": False,
                "error": f"CodeBuddy CLI 未找到: {cli_path}",
            }

    @staticmethod
    def apply_code_edit(file_path: str, new_code: str) -> Dict:
        """
        应用代码修改（调用 CodeBuddy CLI）

        Args:
            file_path: 目标文件路径
            new_code: 新代码内容

        Returns:
            执行结果
        """
        # 将代码写入临时文件
        with tempfile.NamedTemporaryFile(mode="w", suffix=".tmp", delete=False) as f:
            f.write(new_code)
            temp_path = f.name

        result = CodeBuddyExecutor._run_cli(
            "apply-edit",
            ["--file", file_path, "--content-file", temp_path],
        )

        # 清理临时文件
        os.unlink(temp_path)

        return result

    @staticmethod
    def run_code(code: str, language: str = "python") -> Dict:
        """
        在沙箱中运行代码

        Args:
            code: 代码内容
            language: 编程语言（python/javascript/typescript）

        Returns:
            执行结果（stdout/stderr）
        """
        return CodeBuddyExecutor._run_cli(
            "run-code",
            ["--language", language, "--code", code],
        )

    @staticmethod
    def run_tests(test_path: str) -> Dict:
        """
        运行测试

        Args:
            test_path: 测试文件路径或目录

        Returns:
            测试结果
        """
        return CodeBuddyExecutor._run_cli(
            "run-tests",
            ["--path", test_path],
        )

    @staticmethod
    def review_code(file_path: str) -> Dict:
        """
        代码审查（调用 CodeBuddy 的 AI 审查能力）

        Args:
            file_path: 代码文件路径

        Returns:
            审查结果
        """
        return CodeBuddyExecutor._run_cli(
            "review",
            ["--file", file_path, "--format", "json"],
        )

    @staticmethod
    def get_suggestions(code: str, cursor_position: int) -> List[Dict]:
        """
        获取代码补全建议

        Args:
            code: 当前代码
            cursor_position: 光标位置

        Returns:
            补全建议列表
        """
        result = CodeBuddyExecutor._run_cli(
            "suggest",
            ["--code", code, "--cursor", str(cursor_position)],
        )

        if result["success"]:
            try:
                return json.loads(result["stdout"])
            except json.JSONDecodeError:
                return []
        return []
