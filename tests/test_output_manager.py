"""
输出管理器单元测试
"""
import json
import tempfile
import pytest
from pathlib import Path
from utils.output_manager import OutputManager


class TestOutputManager:
    """测试输出管理器"""

    @pytest.fixture
    def temp_base_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def output_mgr(self, temp_base_dir):
        return OutputManager(base_output_dir=str(temp_base_dir))

    def test_create_output_dir(self, output_mgr):
        """测试创建输出目录"""
        output_dir = output_mgr.create_output_dir("测试项目描述")
        assert output_dir.exists()
        assert (output_dir / "backend").exists()
        assert (output_dir / "frontend").exists()
        assert (output_dir / "tests").exists()
        assert (output_dir / "audits").exists()
        assert (output_dir / "iterations").exists()
        assert (output_dir / "traces").exists()

    def test_create_output_dir_metadata(self, output_mgr):
        """测试输出目录元数据文件"""
        output_dir = output_mgr.create_output_dir("测试项目")
        meta_file = output_dir / ".meta.json"
        assert meta_file.exists()
        with open(meta_file, "r", encoding="utf-8") as f:
            meta = json.load(f)
        assert "task_description" in meta
        assert "created_at" in meta
        assert meta["task_description"] == "测试项目"

    def test_save_iteration(self, output_mgr):
        """测试保存迭代记录——end to end: 创建目录 -> 保存迭代 -> 文件存在"""
        output_dir = output_mgr.create_output_dir("测试项目")
        output_mgr.save_iteration(
            output_path=output_dir,
            prompt="添加新功能",
            result={"task_id": "test_001", "status": "success"},
        )
        iter_dir = output_dir / "iterations"
        files = list(iter_dir.glob("*.md"))
        assert len(files) > 0
        content = files[0].read_text(encoding="utf-8")
        # 文件内容至少包含迭代记录标识
        assert "迭代记录" in content or "test_001" in content or "success" in content

    def test_update_meta(self, output_mgr):
        """测试更新元数据"""
        output_dir = output_mgr.create_output_dir("测试项目")
        output_mgr.update_meta(output_path=output_dir, status="completed", last_task_id="task_abc")
        meta_file = output_dir / ".meta.json"
        with open(meta_file, "r", encoding="utf-8") as f:
            meta = json.load(f)
        assert meta["status"] == "completed"
        assert meta["last_task_id"] == "task_abc"

    def test_load_output_dir(self, output_mgr):
        """测试加载已有输出目录"""
        output_dir = output_mgr.create_output_dir("测试项目")
        # Create some files to test loading
        (output_dir / "backend" / "app.py").write_text("# backend code", encoding="utf-8")
        (output_dir / "frontend" / "App.tsx").write_text("// frontend code", encoding="utf-8")
        result = output_mgr.load_output_dir(str(output_dir))
        assert "meta" in result
        assert "backend_code" in result
        assert "frontend_code" in result
        assert "test_code" in result

    def test_get_project_context(self, output_mgr):
        """测试获取项目上下文"""
        output_dir = output_mgr.create_output_dir("电商项目")
        (output_dir / "backend" / "main.py").write_text("print('hello')", encoding="utf-8")
        context = output_mgr.get_project_context(output_dir)
        assert len(context) > 0

    def test_generate_readme(self, output_mgr):
        """测试生成 README"""
        output_dir = output_mgr.create_output_dir("测试项目")
        output_mgr.generate_readme(output_dir)
        readme = output_dir / "README.md"
        assert readme.exists()
        content = readme.read_text(encoding="utf-8")
        assert len(content) > 0

    def test_multiple_iterations(self, output_mgr):
        """测试多次迭代记录"""
        output_dir = output_mgr.create_output_dir("迭代项目")
        for i in range(3):
            output_mgr.save_iteration(
                output_path=output_dir,
                prompt=f"第{i+1}次迭代",
                result={"task_id": f"task_{i:03d}", "status": "success"},
            )
        iter_files = list((output_dir / "iterations").glob("*.md"))
        assert len(iter_files) >= 3

    def test_get_project_context_empty_dir(self, output_mgr):
        """测试空项目的上下文"""
        output_dir = output_mgr.create_output_dir("空项目")
        context = output_mgr.get_project_context(output_dir)
        assert isinstance(context, str)

    def test_save_trace(self, output_mgr):
        """测试保存 agent 执行 trace"""
        output_dir = output_mgr.create_output_dir("trace测试")
        output_mgr.save_trace(
            output_path=output_dir,
            agent_type="backend",
            task_id="task_test001_backend",
            system_prompt="你是一个后端开发助手",
            user_prompt="创建用户API",
            llm_response="好的，我来创建用户API",
            parsed_result={"status": "success", "files": ["users.py"]},
        )
        trace_dir = output_dir / "traces" / "backend"
        assert trace_dir.exists()
        trace_files = list(trace_dir.glob("*.md"))
        assert len(trace_files) > 0

    def test_get_recent_iterations(self, output_mgr):
        """测试获取最近迭代记录"""
        output_dir = output_mgr.create_output_dir("迭代项目")
        for i in range(5):
            output_mgr.save_iteration(
                output_path=output_dir,
                prompt=f"迭代{i}",
                result={"task_id": f"task_{i}", "status": "success"},
            )
        recent = output_mgr.get_recent_iterations(output_dir, count=2)
        assert isinstance(recent, str)
