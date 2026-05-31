"""
输出目录管理器 - 负责输出目录的完整生命周期管理
包括：目录创建、加载已有项目、迭代记录、项目上下文收集
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


class OutputManager:
    """管理 Agent 输出目录的创建、加载和迭代记录"""

    def __init__(self, base_output_dir: str = "output"):
        """
        初始化输出管理器

        Args:
            base_output_dir: 输出根目录，相对于工作目录
        """
        self.base_output_dir = Path(base_output_dir)
        self.base_output_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ #
    #  目录创建
    # ------------------------------------------------------------------ #

    def create_output_dir(self, task_description: str) -> Path:
        """
        创建新的输出目录

        目录命名格式: output/{YYYYMMDD}_{HHMMSS}_{任务摘要}/

        Args:
            task_description: 任务描述，用于生成目录名摘要

        Returns:
            创建的目录 Path 对象
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        summary = self._slugify(task_description)[:20]  # 最多取前 20 个字符
        dir_name = f"{timestamp}_{summary}"
        output_path = self.base_output_dir / dir_name
        output_path.mkdir(parents=True, exist_ok=True)

        # 创建子目录
        (output_path / "backend").mkdir(exist_ok=True)
        (output_path / "frontend").mkdir(exist_ok=True)
        (output_path / "tests").mkdir(exist_ok=True)
        (output_path / "audits").mkdir(exist_ok=True)
        (output_path / "iterations").mkdir(exist_ok=True)
        (output_path / "traces").mkdir(exist_ok=True)
        (output_path / "traces" / "backend").mkdir(exist_ok=True)
        (output_path / "traces" / "frontend").mkdir(exist_ok=True)
        (output_path / "traces" / "test").mkdir(exist_ok=True)
        (output_path / "traces" / "audit").mkdir(exist_ok=True)

        # 创建元数据文件
        meta = {
            "task_description": task_description,
            "requirements": "",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "iteration_count": 0,
            "last_task_id": "",
            "status": "running",
        }
        self._write_meta(output_path, meta)

        # 创建初始迭代记录
        self.save_iteration(
            output_path=output_path,
            prompt=task_description,
            result={"type": "initial", "message": "项目初始化"},
            is_initial=True,
        )

        return output_path

    # ------------------------------------------------------------------ #
    #  目录加载
    # ------------------------------------------------------------------ #

    def load_output_dir(self, output_path: str) -> Dict:
        """
        加载已有输出目录，收集项目上下文

        Args:
            output_path: 输出目录路径（相对于工作目录或绝对路径）

        Returns:
            包含项目上下文的字典:
            {
                "output_path": Path,
                "meta": dict,
                "backend_code": str,    # backend/ 下所有代码合并
                "frontend_code": str,   # frontend/ 下所有代码合并
                "test_code": str,        # tests/ 下所有代码合并
                "audit_reports": list,   # audits/ 下所有报告内容列表
            }
        """
        path = Path(output_path)
        if not path.is_absolute():
            path = Path.cwd() / path
        path = path.resolve()

        if not path.exists():
            raise FileNotFoundError(f"输出目录不存在: {path}")

        meta = self._read_meta(path)

        return {
            "output_path": path,
            "meta": meta,
            "backend_code": self._collect_code(path / "backend"),
            "frontend_code": self._collect_code(path / "frontend"),
            "test_code": self._collect_code(path / "tests"),
            "audit_reports": self._collect_audits(path / "audits"),
        }

    # ------------------------------------------------------------------ #
    #  迭代记录
    # ------------------------------------------------------------------ #

    def save_iteration(
        self,
        output_path: Path,
        prompt: str,
        result: Dict,
        is_initial: bool = False,
    ):
        """
        保存迭代记录到 iterations/ 目录

        Args:
            output_path: 输出目录 Path
            prompt: 本次迭代的用户提示词
            result: 执行结果字典
            is_initial: 是否为初始创建记录
        """
        meta = self._read_meta(output_path)
        count = meta.get("iteration_count", 0)
        if not is_initial:
            count += 1
        meta["iteration_count"] = count
        meta["updated_at"] = datetime.now().isoformat()

        if is_initial:
            filename = "001_initial.md"
        else:
            # 用 prompt 前 30 个字符作为文件名摘要
            prompt_summary = self._slugify(prompt)[:30]
            filename = f"{count:03d}_{prompt_summary}.md"

        iterations_dir = output_path / "iterations"
        iterations_dir.mkdir(exist_ok=True)
        file_path = iterations_dir / filename

        content = self._format_iteration_content(prompt, result, meta)
        file_path.write_text(content, encoding="utf-8")

        self._write_meta(output_path, meta)

    # ------------------------------------------------------------------ #
    #  项目上下文收集（供 Agent prompt 注入）
    # ------------------------------------------------------------------ #

    def get_project_context(self, output_path: Path) -> str:
        """
        收集项目上下文，格式化为可供 LLM prompt 注入的文本

        Args:
            output_path: 输出目录 Path

        Returns:
            格式化的项目上下文字符串
        """
        context = self.load_output_dir(str(output_path))
        meta = context["meta"]

        lines = [
            "## 已有项目上下文",
            f"- 项目描述: {meta.get('task_description', '')}",
            f"- 创建时间: {meta.get('created_at', '')}",
            f"- 迭代次数: {meta.get('iteration_count', 0)}",
            "",
        ]

        if context["backend_code"].strip():
            lines += [
                "### 已有后端代码",
                "```python",
                context["backend_code"],
                "```",
                "",
            ]

        if context["frontend_code"].strip():
            lines += [
                "### 已有前端代码",
                "```tsx",
                context["frontend_code"],
                "```",
                "",
            ]

        if context["test_code"].strip():
            lines += [
                "### 已有测试代码",
                "```python",
                context["test_code"],
                "```",
                "",
            ]

        if context["audit_reports"]:
            lines += [
                "### 已有审计报告摘要",
                "",
            ]
            for report in context["audit_reports"][-3:]:  # 只取最近 3 份
                lines.append(f"- {report[:200]}...")

        return "\n".join(lines)

    def get_recent_iterations(self, output_path: Path, count: int = 3) -> str:
        """
        获取最近的迭代记录摘要，用于注入到 Agent prompt

        Args:
            output_path: 输出目录 Path
            count: 获取的迭代记录数量

        Returns:
            格式化的迭代历史字符串
        """
        iterations_dir = output_path / "iterations"
        if not iterations_dir.exists():
            return "（无迭代记录）"

        files = sorted(iterations_dir.glob("*.md"), reverse=True)
        if not files:
            return "（无迭代记录）"

        lines = ["## 迭代历史", ""]
        for f in files[:count]:
            content = f.read_text(encoding="utf-8", errors="replace")
            # 只取前 500 字符作为摘要
            summary = content[:500].replace("\n", " ").strip()
            lines.append(f"- {f.name}: {summary}")

        return "\n".join(lines)

    # ------------------------------------------------------------------ #
    #  Agent Trace 保存（可审计的完整 LLM 输入输出记录）
    # ------------------------------------------------------------------ #

    def save_trace(
        self,
        output_path: Path,
        agent_type: str,
        task_id: str,
        system_prompt: str,
        user_prompt: str,
        llm_response: str,
        parsed_result: Dict,
    ):
        """
        保存 Agent 的完整执行 trace，包括 LLM 的输入输出

        文件保存在: traces/{agent_type}/{timestamp}_{task_id}.md

        Args:
            output_path: 项目输出目录 Path
            agent_type: Agent 类型 (backend/frontend/test/audit)
            task_id: 任务 ID
            system_prompt: 系统提示词
            user_prompt: 发送给 LLM 的用户提示词（完整）
            llm_response: LLM 的原始返回
            parsed_result: 解析后的操作结果（文件列表、契约等）
        """
        traces_dir = output_path / "traces" / agent_type
        traces_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{task_id}.md"
        file_path = traces_dir / filename

        # 解析结果格式化
        parsed_lines = []
        if parsed_result.get("files"):
            parsed_lines.append("### 生成/修改的文件")
            for f in parsed_result["files"]:
                parsed_lines.append(f"- `{f}`")
            parsed_lines.append("")
        if parsed_result.get("contracts"):
            parsed_lines.append("### 提取的 API 契约")
            for c in parsed_result["contracts"]:
                parsed_lines.append(
                    f"- **{c.get('method', '?')} {c.get('endpoint', '?')}**"
                )
            parsed_lines.append("")
        if parsed_result.get("reports_count") is not None:
            parsed_lines.append(
                f"- 发现问题数: {parsed_result.get('reports_count', 0)}"
            )
            parsed_lines.append(f"- 高危问题: {parsed_result.get('high_severity', 0)}")
            parsed_lines.append("")
        if parsed_result.get("status"):
            parsed_lines.append(f"- 状态: {parsed_result['status']}")
            parsed_lines.append("")

        content = f"""# Agent Trace: {agent_type}

- **时间**: {datetime.now().isoformat()}
- **任务ID**: {task_id}
- **Agent 类型**: {agent_type}

---

## 系统提示词 (System Prompt)

{system_prompt}

---

## 用户提示词 (User Prompt, sent to LLM)

{user_prompt}

---

## LLM 原始输出 (Raw Response)

{llm_response}

---

## 解析结果 (Parsed Result)

{chr(10).join(parsed_lines) if parsed_lines else '（无解析结果）'}

---

## 文件写入记录

"""
        file_path.write_text(content, encoding="utf-8")

        return file_path

    # ------------------------------------------------------------------ #
    #  元数据读写
    # ------------------------------------------------------------------ #

    def update_meta(self, output_path: Path, **kwargs):
        """更新元数据字段"""
        meta = self._read_meta(output_path)
        meta.update(kwargs)
        meta["updated_at"] = datetime.now().isoformat()
        self._write_meta(output_path, meta)

    def _read_meta(self, output_path: Path) -> Dict:
        """读取 .meta.json"""
        meta_path = output_path / ".meta.json"
        if not meta_path.exists():
            return {}
        return json.loads(meta_path.read_text(encoding="utf-8"))

    def _write_meta(self, output_path: Path, meta: Dict):
        """写入 .meta.json"""
        meta_path = output_path / ".meta.json"
        meta_path.write_text(
            json.dumps(meta, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # ------------------------------------------------------------------ #
    #  自动生成 README.md
    # ------------------------------------------------------------------ #

    def generate_readme(self, output_path: Path, task_results: Optional[Dict] = None):
        """
        在输出目录下自动生成 README.md，包含各组件的运行指令。

        根据实际生成的文件类型和内容，动态组装各章节：
        - 后端运行指令（自动检测 Python/Node.js 等）
        - 前端运行指令（自动检测 React/Vue 等框架）
        - 测试运行指令
        - 审计报告摘要
        - Agent trace 说明

        生成前会自动补充缺失的工程配置框架文件（package.json、tsconfig.json 等），
        确保 README 中的指令可实际执行。

        Args:
            output_path: 项目输出目录 Path
            task_results: 任务执行结果（可选），用于填充状态信息
        """
        # 1. 先检测技术栈，发现缺失的配置文件
        stack = self._detect_tech_stack(output_path)

        # 2. 自动补充缺失的工程配置文件
        generated_configs = self._auto_generate_missing_configs(output_path, stack)
        if generated_configs:
            # 重新检测（配置文件已补充）
            stack = self._detect_tech_stack(output_path)

        # 3. 构建 README
        meta = self._read_meta(output_path)
        lines = self._build_readme(output_path, meta, task_results or {})
        readme_path = output_path / "README.md"
        readme_path.write_text("\n".join(lines), encoding="utf-8")

    def _build_readme(
        self,
        output_path: Path,
        meta: Dict,
        task_results: Dict,
    ) -> List[str]:
        """构建 README.md 内容，返回行列表"""
        description = meta.get("task_description", "未命名项目")
        created_at = meta.get("created_at", "")
        task_id = meta.get("last_task_id", "")

        lines = [
            f"# {description}",
            "",
            f"> **生成时间**: {created_at[:19] if created_at else 'N/A'}  ",
            f"> **任务ID**: {task_id}  ",
            f"> **状态**: ✅ {meta.get('status', 'completed')}  ",
            "",
            "---",
            "",
            "## 项目概览",
            "",
        ]

        # 技术栈检测
        tech_stack = self._detect_tech_stack(output_path)
        lines += self._format_tech_table(tech_stack)

        # 目录结构
        lines += [
            "",
            "## 目录结构",
            "",
            "```",
        ]
        lines += self._build_tree(output_path, prefix="")
        lines += [
            "```",
            "",
        ]

        # 后端运行指令
        backend_section = self._build_backend_section(output_path, tech_stack)
        if backend_section:
            lines += backend_section

        # 前端运行指令
        frontend_section = self._build_frontend_section(output_path, tech_stack)
        if frontend_section:
            lines += frontend_section

        # 测试运行指令
        test_section = self._build_test_section(output_path, tech_stack)
        if test_section:
            lines += test_section

        # 审计报告
        audit_section = self._build_audit_section(output_path)
        if audit_section:
            lines += audit_section

        # Agent traces
        trace_section = self._build_trace_section(output_path)
        if trace_section:
            lines += trace_section

        # 快速验证清单
        lines += self._build_quick_check(output_path, tech_stack)

        return lines

    # ---------------------------------------------------------------- #
    #  技术栈检测
    # ---------------------------------------------------------------- #

    def _detect_tech_stack(self, output_path: Path) -> Dict:
        """
        检测项目的技术栈

        扫描 backend/ 和 frontend/ 目录，识别使用的语言和框架。
        """
        stack = {
            "backend_lang": None,
            "backend_framework": None,
            "backend_entry": None,
            "frontend_framework": None,
            "frontend_pkg_mgr": "npm",
            "frontend_missing_config": False,  # 有源码但缺 package.json
            "test_backend_framework": None,
            "test_frontend_framework": None,
            "has_backend": False,
            "has_frontend": False,
            "has_tests": False,
            "has_audits": False,
            "has_traces": False,
        }

        # 检测后端
        backend_dir = output_path / "backend"
        if backend_dir.exists():
            py_files = list(backend_dir.rglob("*.py"))
            if py_files:
                stack["has_backend"] = True
                stack["backend_lang"] = "python"
                stack["backend_framework"] = self._detect_py_framework(backend_dir)
                stack["backend_entry"] = self._detect_entry_file(backend_dir, [".py"])
            else:
                js_files = list(backend_dir.rglob("*.js")) + list(
                    backend_dir.rglob("*.ts")
                )
                if js_files:
                    stack["has_backend"] = True
                    stack["backend_lang"] = "node"
                    stack["backend_entry"] = self._detect_entry_file(
                        backend_dir, [".js", ".ts"]
                    )

        # 检测前端——有 package.json 或有源码文件都算有前端
        frontend_dir = output_path / "frontend"
        if frontend_dir.exists():
            pkg_json = frontend_dir / "package.json"
            has_config = pkg_json.exists()
            has_source = bool(
                list(frontend_dir.rglob("*.tsx"))
                + list(frontend_dir.rglob("*.ts"))
                + list(frontend_dir.rglob("*.jsx"))
                + list(frontend_dir.rglob("*.js"))
                + list(frontend_dir.rglob("*.html"))
            )

            if has_config or has_source:
                stack["has_frontend"] = True

            if has_config:
                stack["frontend_framework"] = self._detect_frontend_framework(pkg_json)
                # 检测包管理器
                if (frontend_dir / "yarn.lock").exists():
                    stack["frontend_pkg_mgr"] = "yarn"
                elif (frontend_dir / "pnpm-lock.yaml").exists():
                    stack["frontend_pkg_mgr"] = "pnpm"
            elif has_source:
                # 有源码但缺配置文件
                stack["frontend_missing_config"] = True
                # 尝试从源码中推断框架
                for f in frontend_dir.rglob("*.tsx"):
                    try:
                        c = f.read_text(encoding="utf-8", errors="replace")
                    except Exception:
                        continue
                    if "react" in c.lower() or "jsx" in c:
                        stack["frontend_framework"] = "React"
                        break
                if not stack["frontend_framework"]:
                    for f in frontend_dir.rglob("*.vue"):
                        stack["frontend_framework"] = "Vue"
                        break
                if not stack["frontend_framework"]:
                    stack["frontend_framework"] = "Unknown"

        # 检测测试
        tests_dir = output_path / "tests"
        if tests_dir.exists() and list(tests_dir.iterdir()):
            stack["has_tests"] = True
            for f in tests_dir.rglob("*.py"):
                stack["test_backend_framework"] = "pytest"
                break
            # 只有当前端有 package.json 或测试目录下有 jest 配置时才认为有前端测试框架
            if has_config or (tests_dir / "jest.config.js").exists():
                for f in tests_dir.rglob("*.tsx"):
                    stack["test_frontend_framework"] = "jest"
                    break

        # 检测审计
        audits_dir = output_path / "audits"
        if audits_dir.exists() and list(audits_dir.glob("*.md")):
            stack["has_audits"] = True

        # 检测 traces
        traces_dir = output_path / "traces"
        if traces_dir.exists() and list(traces_dir.rglob("*.md")):
            stack["has_traces"] = True

        return stack

    @staticmethod
    def _detect_py_framework(backend_dir: Path) -> str:
        """检测 Python Web 框架"""
        for f in backend_dir.rglob("*.py"):
            try:
                content = f.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            if (
                "from flask" in content
                or "import flask" in content
                or "Flask(" in content
            ):
                return "Flask"
            if (
                "from fastapi" in content
                or "import fastapi" in content
                or "FastAPI(" in content
            ):
                return "FastAPI"
            if "from django" in content or "import django" in content:
                return "Django"
        return "Python"

    @staticmethod
    def _detect_frontend_framework(pkg_json: Path) -> str:
        """从 package.json 检测前端框架"""
        try:
            import json

            data = json.loads(pkg_json.read_text(encoding="utf-8"))
            deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
            if "react" in deps:
                if "next" in deps:
                    return "Next.js"
                return "React"
            if "vue" in deps:
                return "Vue"
            if "@angular/core" in deps:
                return "Angular"
            return "Node.js"
        except Exception:
            return "Unknown"

    @staticmethod
    def _detect_entry_file(directory: Path, extensions: List[str]) -> Optional[str]:
        """检测入口文件（main.py / app.py / index.js 等）"""
        candidates = ["main", "app", "index", "server", "run"]
        for name in candidates:
            for ext in extensions:
                f = directory / f"{name}{ext}"
                if f.exists():
                    return f.name
        # fallback: 取第一个匹配文件
        for ext in extensions:
            files = list(directory.glob(f"*{ext}"))
            if files:
                return files[0].name
        return None

    # ---------------------------------------------------------------- #
    #  自动补充缺失的工程配置文件
    # ---------------------------------------------------------------- #

    def _auto_generate_missing_configs(
        self, output_path: Path, stack: Dict
    ) -> List[str]:
        """
        检查并自动生成缺失的工程配置文件。

        当 Agent 生成的前端代码缺少 package.json、tsconfig.json 等配置文件时，
        自动创建模板文件使项目可运行。

        Returns:
            生成的文件路径列表
        """
        generated = []

        # 前端配置文件补充
        if stack.get("frontend_missing_config"):
            frontend_dir = output_path / "frontend"
            pkg_path = frontend_dir / "package.json"
            if not pkg_path.exists():
                self._generate_template_package_json(frontend_dir, stack)
                generated.append("frontend/package.json")

            tsconfig_path = frontend_dir / "tsconfig.json"
            if not tsconfig_path.exists():
                self._generate_template_tsconfig_json(frontend_dir)
                generated.append("frontend/tsconfig.json")

            # 检查是否有 src/index.tsx 作为入口
            has_entry = (frontend_dir / "src" / "index.tsx").exists() or (
                frontend_dir / "index.tsx"
            ).exists()
            public_html = frontend_dir / "public" / "index.html"
            if has_entry and not public_html.exists():
                self._generate_template_html(frontend_dir)
                generated.append("frontend/public/index.html")

        # Jest 配置补充（测试目录有 .tsx 但前端根目录缺 jest.config.js）
        tests_dir = output_path / "tests"
        frontend_dir = output_path / "frontend"
        if tests_dir.exists() and list(tests_dir.rglob("*.tsx")):
            jest_config = frontend_dir / "jest.config.js"
            if not jest_config.exists() and (frontend_dir / "package.json").exists():
                self._generate_template_jest_config(frontend_dir)
                generated.append("frontend/jest.config.js")
            setup_tests = frontend_dir / "src" / "setupTests.ts"
            if not setup_tests.exists() and (frontend_dir / "src").exists():
                self._generate_template_setup_tests(frontend_dir)
                generated.append("frontend/src/setupTests.ts")

        return generated

    @staticmethod
    def _generate_template_package_json(frontend_dir: Path, stack: Dict):
        """生成 React + TypeScript 项目的 package.json 模板"""
        framework = stack.get("frontend_framework", "React")
        import json

        pkg = {
            "name": "frontend",
            "version": "1.0.0",
            "private": True,
            "scripts": {
                "start": "react-scripts start",
                "build": "react-scripts build",
                "test": "react-scripts test",
                "eject": "react-scripts eject",
            },
            "dependencies": {
                "react": "^18.2.0",
                "react-dom": "^18.2.0",
                "react-scripts": "5.0.1",
            },
            "devDependencies": {
                "@testing-library/jest-dom": "^5.16.5",
                "@testing-library/react": "^14.0.0",
                "@testing-library/user-event": "^14.4.3",
                "@types/jest": "^29.5.0",
                "@types/node": "^20.1.0",
                "@types/react": "^18.2.0",
                "@types/react-dom": "^18.2.0",
                "typescript": "^4.9.5",
                "web-vitals": "^3.3.0",
            },
            "browserslist": {
                "production": [">0.2%", "not dead", "not op_mini all"],
                "development": [
                    "last 1 chrome version",
                    "last 1 firefox version",
                    "last 1 safari version",
                ],
            },
            "homepage": ".",
        }

        if framework == "Vue":
            pkg["dependencies"] = {"vue": "^3.3.0"}
            pkg["devDependencies"] = {
                "@vitejs/plugin-vue": "^4.2.0",
                "vite": "^4.3.0",
                "typescript": "^5.0.0",
            }
            pkg["scripts"] = {
                "dev": "vite",
                "build": "vite build",
                "preview": "vite preview",
            }

        pkg_path = frontend_dir / "package.json"
        pkg_path.write_text(
            json.dumps(pkg, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    @staticmethod
    def _generate_template_tsconfig_json(frontend_dir: Path):
        """生成 TypeScript 配置模板"""
        import json

        tsconfig = {
            "compilerOptions": {
                "target": "ES2020",
                "lib": ["DOM", "DOM.Iterable", "ES2020"],
                "allowJs": True,
                "skipLibCheck": True,
                "esModuleInterop": True,
                "allowSyntheticDefaultImports": True,
                "strict": True,
                "forceConsistentCasingInFileNames": True,
                "noFallthroughCasesInSwitch": True,
                "module": "ESNext",
                "moduleResolution": "node",
                "resolveJsonModule": True,
                "isolatedModules": True,
                "noEmit": True,
                "jsx": "react-jsx",
            },
            "include": ["src", "*.tsx", "*.ts"],
        }
        (frontend_dir / "tsconfig.json").write_text(
            json.dumps(tsconfig, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    @staticmethod
    def _generate_template_html(frontend_dir: Path):
        """生成 React 入口 HTML 模板"""
        html = """<!DOCTYPE html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="theme-color" content="#000000" />
    <meta name="description" content="AI-generated web application" />
    <title>App</title>
  </head>
  <body>
    <noscript>您需要启用 JavaScript 才能运行此应用。</noscript>
    <div id="root"></div>
  </body>
</html>
"""
        public_dir = frontend_dir / "public"
        public_dir.mkdir(parents=True, exist_ok=True)
        (public_dir / "index.html").write_text(html, encoding="utf-8")

    @staticmethod
    def _generate_template_jest_config(frontend_dir: Path):
        """生成 Jest 配置模板"""
        config = """module.exports = {
  testEnvironment: 'jsdom',
  setupFilesAfterSetup: ['<rootDir>/src/setupTests.ts'],
  moduleNameMapper: {
    '\\\\.(css|less|scss|sass)$': 'identity-obj-proxy',
  },
};
"""
        (frontend_dir / "jest.config.js").write_text(config, encoding="utf-8")

    @staticmethod
    def _generate_template_setup_tests(frontend_dir: Path):
        """生成 Jest setup 文件"""
        content = "import '@testing-library/jest-dom';\n"
        src_dir = frontend_dir / "src"
        src_dir.mkdir(parents=True, exist_ok=True)
        (src_dir / "setupTests.ts").write_text(content, encoding="utf-8")

    # ---------------------------------------------------------------- #
    #  各章节生成
    # ---------------------------------------------------------------- #

    def _format_tech_table(self, stack: Dict) -> List[str]:
        """格式化成技术栈表格"""
        lines = ["| 组件 | 技术栈 | 目录 |", "|------|--------|------|"]
        if stack["has_backend"]:
            framework = stack["backend_framework"] or stack["backend_lang"] or "—"
            lines.append(f"| 后端 API | {framework} | `backend/` |")
        if stack["has_frontend"]:
            framework = stack["frontend_framework"] or "—"
            note = " ⚠️缺配置" if stack.get("frontend_missing_config") else ""
            lines.append(f"| 前端界面 | {framework}{note} | `frontend/` |")
        if stack["has_tests"]:
            test_info = []
            if stack["test_backend_framework"]:
                test_info.append(stack["test_backend_framework"])
            if stack["test_frontend_framework"]:
                test_info.append(stack["test_frontend_framework"])
            lines.append(f"| 测试 | {', '.join(test_info) or '—'} | `tests/` |")
        if stack["has_audits"]:
            lines.append("| 代码审计 | AI 自动审计 | `audits/` |")
        if stack["has_traces"]:
            lines.append("| 执行追溯 | Agent I/O | `traces/` |")
        return lines

    def _build_tree(
        self, path: Path, prefix: str = "", max_depth: int = 3, _depth: int = 0
    ) -> List[str]:
        """生成目录树"""
        if _depth >= max_depth:
            return []
        lines = []
        entries = sorted(
            [e for e in path.iterdir() if not e.name.startswith(".")],
            key=lambda e: (e.is_file(), e.name),
        )
        for i, entry in enumerate(entries):
            is_last = i == len(entries) - 1
            connector = "└── " if is_last else "├── "
            if entry.is_dir():
                lines.append(f"{prefix}{connector}{entry.name}/")
                sub_prefix = prefix + ("    " if is_last else "│   ")
                lines += self._build_tree(entry, sub_prefix, max_depth, _depth + 1)
            else:
                lines.append(f"{prefix}{connector}{entry.name}")
        return lines

    def _build_backend_section(self, output_path: Path, stack: Dict) -> List[str]:
        """生成后端运行章节"""
        if not stack["has_backend"]:
            return []

        backend_dir = output_path / "backend"
        lines = [
            "",
            "## 一、运行后端 (Backend)",
            "",
        ]

        entry = stack["backend_entry"]

        if stack["backend_lang"] == "python":
            # 收集依赖
            deps = self._collect_py_deps(backend_dir)
            lines += [
                "### 1.1 安装依赖",
                "",
                "```bash",
                "cd backend/",
            ]
            if deps:
                lines.append(f"pip install {' '.join(deps)}")
            else:
                lines.append("# 如有 requirements.txt: pip install -r requirements.txt")
            lines += [
                "```",
                "",
                "### 1.2 启动服务",
                "",
                "```bash",
            ]
            if entry:
                lines.append(f"python {entry}")
            else:
                lines.append("python main.py")
            lines += [
                "```",
                "",
            ]

            # 提取 API 契约
            contracts = self._extract_api_contracts(backend_dir)
            if contracts:
                lines += [
                    "### 1.3 API 契约",
                    "",
                    "| 方法 | 端点 | 请求体 | 响应体 |",
                    "|------|------|--------|--------|",
                ]
                for c in contracts:
                    method = c.get("method", "?")
                    endpoint = c.get("endpoint", "?")
                    req = c.get("request_schema", "—")
                    resp = c.get("response_schema", "—")
                    lines.append(f"| {method} | `{endpoint}` | `{req}` | `{resp}` |")

                # 生成 curl 示例
                lines += [
                    "",
                    "### 1.4 验证 API",
                    "",
                ]
                for c in contracts[:1]:  # 只生成第一个端点的示例
                    method = c.get("method", "GET")
                    endpoint = c.get("endpoint", "/")
                    req_schema = c.get("request_schema", "")
                    # 简单解析 JSON schema 生成 curl
                    curl = self._gen_curl_example(method, endpoint, req_schema)
                    lines += curl
                    lines.append("")

        elif stack["backend_lang"] == "node":
            lines += [
                "### 1.1 安装依赖",
                "",
                "```bash",
                "cd backend/",
                f"{stack['frontend_pkg_mgr']} install",
                "```",
                "",
                "### 1.2 启动服务",
                "",
                "```bash",
                f"{stack['frontend_pkg_mgr']} start",
                "```",
                "",
            ]

        return lines

    def _build_frontend_section(self, output_path: Path, stack: Dict) -> List[str]:
        """生成前端运行章节"""
        if not stack["has_frontend"]:
            return []

        frontend_dir = output_path / "frontend"
        lines = [
            "",
            "## 二、运行前端 (Frontend)",
            "",
        ]

        pkg_json_path = frontend_dir / "package.json"
        if not pkg_json_path.exists():
            # 有源码但缺配置文件——理论上 auto_generate 应该已经处理了，
            # 这里作为兜底，给出手动初始化 React 的指令
            lines += [
                "> ⚠️ **缺少工程配置文件**：前端源码存在但无 `package.json`，需要手动初始化。",
                "",
                "### 2.1 初始化前端项目",
                "",
                "```bash",
                "# 使用 Create React App 初始化 TypeScript 模板",
                "cd frontend/",
                "npx create-react-app . --template typescript --use-npm 2>/dev/null || \\",
                "  npm init -y && npm install react react-dom react-scripts typescript \\",
                "    @types/react @types/react-dom @testing-library/react @testing-library/jest-dom",
                "```",
                "",
                "### 2.2 将源码移入 src/ 目录",
                "",
                "```bash",
                "# 将组件和入口文件移入 src/（如果尚未在 src/ 中）",
                "find . -maxdepth 1 -name '*.tsx' -o -name '*.ts' \\",
                "  -o -name '*.css' | grep -v 'node_modules' | xargs -I{} mv {} src/ 2>/dev/null",
                "```",
                "",
                "### 2.3 启动开发服务器",
                "",
                "```bash",
                "npm start",
                "```",
                "",
            ]
            return lines

        framework = stack["frontend_framework"]
        if framework:
            pkg_mgr = stack["frontend_pkg_mgr"]
            lines += [
                "### 2.1 安装依赖",
                "",
                "```bash",
                "cd frontend/",
                f"{pkg_mgr} install",
                "```",
                "",
                "### 2.2 启动开发服务器",
                "",
                "```bash",
            ]
            if framework == "Next.js":
                lines.append(f"{pkg_mgr} run dev")
            else:
                lines.append(f"{pkg_mgr} start")
            lines += [
                "```",
                "",
            ]

            # 检测是否需要补充依赖
            missing = self._detect_missing_deps(frontend_dir)
            if missing:
                lines += [
                    "> ⚠️ **可能缺少的依赖**: `package.json` 未声明但代码中引用了：",
                ]
                for dep in missing:
                    lines.append(f"> - `{dep}`")
                lines += [
                    f"> 如需安装: `{pkg_mgr} install {' '.join(missing)}`",
                    "",
                ]
        else:
            # 纯 HTML 前端
            html_files = list(frontend_dir.rglob("*.html"))
            if html_files:
                entry_html = html_files[0]
                lines += [
                    "可以直接用浏览器打开 HTML 文件，或使用简单 HTTP 服务器：",
                    "",
                    "```bash",
                    "cd frontend/",
                    "python -m http.server 8000",
                    "```",
                    f"浏览器访问: `http://localhost:8000/{entry_html.name}`",
                    "",
                ]

        return lines

    def _build_test_section(self, output_path: Path, stack: Dict) -> List[str]:
        """生成测试运行章节"""
        if not stack["has_tests"]:
            return []

        tests_dir = output_path / "tests"
        frontend_pkg = (output_path / "frontend" / "package.json").exists()

        lines = [
            "",
            "## 三、运行测试 (Tests)",
            "",
        ]

        # 后端测试
        py_tests = list(tests_dir.rglob("*.py"))
        if py_tests:
            test_files = " ".join(f"tests/{f.name}" for f in py_tests)
            lines += [
                "### 3.1 后端测试",
                "",
                "```bash",
                "# 在项目根目录（本目录）下执行",
                f"python -m pytest {test_files} -v",
                "```",
                "",
                "**测试文件**:",
            ]
            for f in py_tests:
                cases = self._extract_test_cases(f)
                lines.append(f"- `{f.name}`: {cases}")
            lines.append("")

        # 前端测试——搜索 tests/ 和 frontend/src/ 两个目录
        frontend_test_candidates = (
            list(tests_dir.rglob("*.tsx"))
            + list(tests_dir.rglob("*.ts"))
            + list(tests_dir.rglob("*.jsx"))
            + list(tests_dir.rglob("*.js"))
        )
        frontend_dir = output_path / "frontend"
        if frontend_dir.exists():
            frontend_test_candidates += (
                list(frontend_dir.rglob("*.test.tsx"))
                + list(frontend_dir.rglob("*.test.ts"))
                + list(frontend_dir.rglob("*.test.jsx"))
                + list(frontend_dir.rglob("*.test.js"))
                + list(frontend_dir.rglob("*.spec.tsx"))
                + list(frontend_dir.rglob("*.spec.ts"))
            )
        js_tests = [f for f in frontend_test_candidates if f.suffix != ".py"]
        if js_tests:
            if frontend_pkg:
                pkg_mgr = stack["frontend_pkg_mgr"]
                lines += [
                    "### 3.2 前端测试",
                    "",
                    "```bash",
                    "cd frontend/",
                    f"{pkg_mgr} test",
                    "```",
                    "",
                    "**测试文件**:",
                ]
                for f in js_tests:
                    lines.append(f"- `{f.relative_to(tests_dir.parent)}`")
                lines.append("")
            else:
                lines += [
                    "### 3.2 前端测试",
                    "",
                    "> ⚠️ **缺少 `frontend/package.json`**，前端测试无法直接运行。",
                    "> 请先初始化前端项目（参见 README 中'运行前端'章节），然后：",
                    "",
                    "**测试文件**（位于 `tests/` 目录，需移到 `frontend/src/` 下运行）:",
                ]
                for f in js_tests:
                    lines.append(f"- `{f.relative_to(tests_dir.parent)}`")
                lines.append("")

        return lines

    def _build_audit_section(self, output_path: Path) -> List[str]:
        """生成审计章节"""
        audits_dir = output_path / "audits"
        if not audits_dir.exists():
            return []

        audit_files = sorted(audits_dir.glob("*.md"))
        if not audit_files:
            return []

        lines = [
            "",
            "## 四、代码审计报告",
            "",
        ]

        for af in audit_files:
            content = af.read_text(encoding="utf-8", errors="replace")
            # 提取发现的问题数
            import re as _re

            count_match = _re.search(r"发现问题数[：:]\s*(\d+)", content)
            issue_count = count_match.group(1) if count_match else "?"
            lines.append(f"- [{af.name}](audits/{af.name}) — 发现 {issue_count} 个问题")

        lines += [
            "",
            "查看完整报告：",
            "",
            "```bash",
            f"cat audits/{audit_files[0].name}",
            "```",
            "",
        ]

        return lines

    def _build_trace_section(self, output_path: Path) -> List[str]:
        """生成 trace 章节"""
        traces_dir = output_path / "traces"
        if not traces_dir.exists():
            return []

        trace_files = list(traces_dir.rglob("*.md"))
        if not trace_files:
            return []

        lines = [
            "",
            "## 五、Agent 执行追溯",
            "",
            "每个 Agent 的完整输入输出记录在 `traces/` 下，用于审计和调试：",
            "",
            "```bash",
        ]
        for sub in sorted(traces_dir.iterdir()):
            if sub.is_dir():
                count = len(list(sub.glob("*.md")))
                if count > 0:
                    lines.append(
                        f"cat traces/{sub.name}/*.md   # {count} 个 trace 文件"
                    )
        lines += [
            "```",
            "",
        ]
        return lines

    def _build_quick_check(self, output_path: Path, stack: Dict) -> List[str]:
        """生成快速验证清单"""
        frontend_pkg = (output_path / "frontend" / "package.json").exists()

        lines = [
            "",
            "## 六、快速验证清单",
            "",
            "| 步骤 | 操作 | 预期 |",
            "|------|------|------|",
        ]

        if stack["has_backend"]:
            entry = stack["backend_entry"] or "main.py"
            lines.append(f"| 后端启动 | `cd backend && python {entry}` | 服务运行中 |")
            # 尝试找 API 端点
            api_info = self._find_first_api(output_path)
            if api_info:
                lines.append(f"| API 验证 | `curl {api_info}` | 返回 200 |")

        if stack["has_frontend"] and frontend_pkg:
            lines.append(
                f"| 前端启动 | `cd frontend && {stack['frontend_pkg_mgr']} start` | 页面可访问 |"
            )
        elif stack["has_frontend"]:
            lines.append("| 前端初始化 | 参见「运行前端」章节补充配置文件 | — |")

        if stack["has_tests"] and stack["test_backend_framework"]:
            lines.append("| 后端测试 | `python -m pytest tests/ -v` | 全部通过 |")

        if stack["has_tests"] and stack["test_frontend_framework"] and frontend_pkg:
            lines.append(
                f"| 前端测试 | `cd frontend && {stack['frontend_pkg_mgr']} test` | 全部通过 |"
            )

        if stack["has_audits"]:
            lines.append("| 查看审计 | `cat audits/*.md` | 含问题清单 |")

        if stack["has_traces"]:
            lines.append("| 查看追溯 | `ls traces/*/` | trace 文件 |")

        lines.append("")

        # 端到端启动（仅当配置文件齐全时提供脚本）
        can_start_frontend = (
            stack["has_frontend"] and frontend_pkg and stack.get("frontend_framework")
        )
        if stack["has_backend"] or can_start_frontend:
            lines += [
                "---",
                "",
                "## 端到端启动",
                "",
                "```bash",
                f"cd {output_path.name}",
                "",
            ]
            if stack["has_backend"] and stack["backend_lang"] == "python":
                entry = stack["backend_entry"] or "main.py"
                lines += [
                    "# 启动后端",
                    "cd backend/",
                    "pip install flask marshmallow 2>/dev/null",
                    f"python {entry} &",
                    "BACKEND_PID=$!",
                    "cd ..",
                    "",
                ]
            if can_start_frontend:
                pkg_mgr = stack["frontend_pkg_mgr"]
                lines += [
                    "# 启动前端",
                    "cd frontend/",
                    f"{pkg_mgr} install 2>/dev/null",
                    f"{pkg_mgr} start &",
                    "FRONTEND_PID=$!",
                    "cd ..",
                    "",
                ]
            lines += [
                'echo "后端: http://127.0.0.1:5000"',
                'echo "前端: http://localhost:3000"',
                "",
                "# 停止服务",
                "# kill $BACKEND_PID $FRONTEND_PID",
                "```",
                "",
            ]

        return lines

    # ---------------------------------------------------------------- #
    #  README 构建辅助方法
    # ---------------------------------------------------------------- #

    @staticmethod
    def _collect_py_deps(backend_dir: Path) -> List[str]:
        """从 Python 文件中收集常见的第三方 import"""
        common_deps = {
            "flask": "flask",
            "marshmallow": "marshmallow",
            "fastapi": "fastapi",
            "pydantic": "pydantic",
            "sqlalchemy": "sqlalchemy",
            "django": "django",
            "requests": "requests",
            "celery": "celery",
            "redis": "redis",
            "pymongo": "pymongo",
            "psycopg2": "psycopg2-binary",
            "pytest": "pytest",
        }
        found = set()
        for f in backend_dir.rglob("*.py"):
            try:
                content = f.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            for mod, pkg in common_deps.items():
                if f"import {mod}" in content or f"from {mod}" in content:
                    found.add(pkg)
        # 读取 requirements.txt（如果存在）
        reqs_file = backend_dir / "requirements.txt"
        if reqs_file.exists():
            return []  # 有 requirements.txt 就让用户自己装
        return sorted(found) if found else []

    @staticmethod
    def _extract_api_contracts(backend_dir: Path) -> List[Dict]:
        """从后端代码中提取 API_CONTRACT 注释块"""
        contracts = []
        for f in backend_dir.rglob("*.py"):
            try:
                content = f.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            # 匹配 API_CONTRACT_START ... API_CONTRACT_END 块
            import re as _re

            pattern = r"###\s*API_CONTRACT_START\s*\n(.*?)###\s*API_CONTRACT_END"
            for match in _re.finditer(pattern, content, _re.DOTALL):
                block = match.group(1)
                contract = {}
                for line in block.strip().split("\n"):
                    line = line.strip()
                    if line.startswith("endpoint:"):
                        contract["endpoint"] = line.split(":", 1)[1].strip()
                    elif line.startswith("method:"):
                        contract["method"] = line.split(":", 1)[1].strip()
                    elif line.startswith("request_schema:"):
                        contract["request_schema"] = line.split(":", 1)[1].strip()
                    elif line.startswith("response_schema:"):
                        contract["response_schema"] = line.split(":", 1)[1].strip()
                if contract.get("endpoint"):
                    contracts.append(contract)
        return contracts

    @staticmethod
    def _gen_curl_example(method: str, endpoint: str, req_schema: str) -> List[str]:
        """根据 API 契约生成 curl 示例"""
        lines = ["```bash"]
        # 生成请求体示例
        body = "{}"
        if req_schema:
            import re as _re

            # 简单解析 {"key": "type"} 格式
            props = _re.findall(r'"(\w+)":\s*"(\w+)"', req_schema)
            if props:
                body_parts = [f'"{k}": "{v}"' for k, v in props]
                body = "{" + ", ".join(body_parts) + "}"
        if method.upper() in ("POST", "PUT", "PATCH"):
            lines.append(f"curl -X {method.upper()} http://127.0.0.1:5000{endpoint} \\")
            lines.append(f'  -H "Content-Type: application/json" \\')
            lines.append(f"  -d '{body}'")
        else:
            lines.append(f"curl http://127.0.0.1:5000{endpoint}")
        lines.append("```")
        return lines

    @staticmethod
    def _extract_test_cases(test_file: Path) -> str:
        """从测试文件中提取测试函数名"""
        try:
            content = test_file.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return "—"
        import re as _re

        names = _re.findall(r"def (test_\w+)", content)
        if names:
            return f"{len(names)} 个用例: {', '.join(names[:5])}" + (
                "..." if len(names) > 5 else ""
            )
        return "—"

    @staticmethod
    def _detect_missing_deps(frontend_dir: Path) -> List[str]:
        """检测代码中使用但 package.json 未声明的依赖"""
        pkg_json = frontend_dir / "package.json"
        if not pkg_json.exists():
            return []

        try:
            import json

            data = json.loads(pkg_json.read_text(encoding="utf-8"))
            declared = set(data.get("dependencies", {}).keys()) | set(
                data.get("devDependencies", {}).keys()
            )
        except Exception:
            return []

        # 常用前端库名映射
        import_to_pkg = {
            "react-router-dom": "react-router-dom",
            "react-router": "react-router-dom",
            "react-toastify": "react-toastify",
            "axios": "axios",
            "lodash": "lodash",
            "@testing-library/react": "@testing-library/react",
            "@testing-library/jest-dom": "@testing-library/jest-dom",
            "@testing-library/user-event": "@testing-library/user-event",
            "redux": "redux",
            "react-redux": "react-redux",
            "mobx": "mobx",
            "antd": "antd",
            "@ant-design/icons": "@ant-design/icons",
            "element-plus": "element-plus",
            "vue-router": "vue-router",
            "pinia": "pinia",
        }

        missing = set()
        for f in frontend_dir.rglob("*.tsx"):
            try:
                content = f.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            for ic, pkg in import_to_pkg.items():
                if pkg in declared:
                    continue
                if (
                    f"from '{ic}'" in content
                    or f'from "{ic}"' in content
                    or f"require('{ic}')" in content
                    or f'require("{ic}")' in content
                ):
                    missing.add(pkg)
        return sorted(missing)

    @staticmethod
    def _find_first_api(output_path: Path) -> Optional[str]:
        """在 backend 目录中找到第一个 API 端点，生成 curl 示例"""
        contracts = OutputManager._extract_api_contracts(output_path / "backend")
        if contracts:
            c = contracts[0]
            method = c.get("method", "GET")
            endpoint = c.get("endpoint", "/")
            if method.upper() in ("POST", "PUT"):
                return (
                    f"-X {method.upper()} http://127.0.0.1:5000{endpoint} "
                    f"-H 'Content-Type: application/json' "
                    f'-d \'{{"key":"value"}}\''
                )
            else:
                return f"http://127.0.0.1:5000{endpoint}"
        return None

    # ------------------------------------------------------------------ #
    #  内部工具方法
    # ------------------------------------------------------------------ #

    @staticmethod
    def _slugify(text: str) -> str:
        """
        将文本转换为安全的目录名：
        - 保留中文、字母、数字
        - 其他字符替换为下划线
        - 合并多个下划线为一个
        """
        # 保留中文、字母、数字，其余替换为下划线
        safe = re.sub(r"[^\w\u4e00-\u9fff]", "_", text)
        # 合并多个下划线
        safe = re.sub(r"_+", "_", safe)
        return safe.strip("_")

    @staticmethod
    def _collect_code(directory: Path) -> str:
        """
        收集目录下所有代码文件内容，合并为单个字符串
        每个文件用 ### FILE: 标记分隔
        """
        if not directory.exists():
            return ""
        parts = []
        for file_path in sorted(directory.rglob("*")):
            if file_path.is_file():
                rel = file_path.relative_to(directory.parent)  # 相对于 output_dir
                content = file_path.read_text(encoding="utf-8", errors="replace")
                parts.append(f"### FILE: {rel}\n{content}\n")
        return "\n".join(parts)

    @staticmethod
    def _collect_audits(directory: Path) -> List[str]:
        """收集 audits/ 目录下所有报告内容"""
        if not directory.exists():
            return []
        reports = []
        for file_path in sorted(directory.glob("*.md")):
            reports.append(file_path.read_text(encoding="utf-8", errors="replace"))
        return reports

    @staticmethod
    def _format_iteration_content(prompt: str, result: Dict, meta: Dict) -> str:
        """格式化迭代记录为 Markdown"""
        lines = [
            f"# 迭代记录 #{meta.get('iteration_count', 0)}",
            "",
            f"- 时间: {datetime.now().isoformat()}",
            f"- 提示词: {prompt}",
            "",
            "## 执行结果",
            "",
            "```json",
            json.dumps(result, ensure_ascii=False, indent=2),
            "```",
            "",
        ]
        return "\n".join(lines)
