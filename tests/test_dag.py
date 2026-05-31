"""
DAG 调度器单元测试
"""
import pytest
from coordinator.dag import DAGScheduler


class TestDAGScheduler:
    """测试 DAG 调度器核心逻辑"""

    def test_add_single_task(self):
        dag = DAGScheduler()
        dag.add_task("task_1", agent_type="backend", dependencies=[], context={"desc": "test"})
        assert "task_1" in dag.tasks
        assert dag.tasks["task_1"]["agent_type"] == "backend"

    def test_add_task_with_deps(self):
        dag = DAGScheduler()
        dag.add_task("task_a", agent_type="backend", dependencies=[])
        dag.add_task("task_b", agent_type="frontend", dependencies=["task_a"])
        assert dag.in_degree["task_b"] == 1
        assert "task_b" in dag.graph["task_a"]

    def test_get_runnable_tasks_no_deps(self):
        dag = DAGScheduler()
        dag.add_task("task_1", agent_type="backend", dependencies=[])
        runnable = dag.get_runnable_tasks()
        assert runnable == ["task_1"]

    def test_get_runnable_tasks_with_blocked(self):
        dag = DAGScheduler()
        dag.add_task("task_a", agent_type="backend", dependencies=[])
        dag.add_task("task_b", agent_type="frontend", dependencies=["task_a"])
        runnable = dag.get_runnable_tasks()
        assert runnable == ["task_a"]  # task_b blocked

    def test_mark_done_unblocks_downstream(self):
        dag = DAGScheduler()
        dag.add_task("task_a", agent_type="backend", dependencies=[])
        dag.add_task("task_b", agent_type="frontend", dependencies=["task_a"])
        dag.mark_done("task_a")
        assert dag.status["task_a"] == "completed"
        assert dag.in_degree["task_b"] == 0
        runnable = dag.get_runnable_tasks()
        assert runnable == ["task_b"]

    def test_mark_failed_cascade(self):
        dag = DAGScheduler()
        dag.add_task("task_a", agent_type="backend", dependencies=[])
        dag.add_task("task_b", agent_type="frontend", dependencies=["task_a"])
        dag.add_task("task_c", agent_type="test", dependencies=["task_b"])
        dag.mark_failed("task_a")
        assert dag.status["task_a"] == "failed"
        assert dag.status["task_b"] == "failed"
        assert dag.status["task_c"] == "failed"

    def test_is_completed_all_done(self):
        dag = DAGScheduler()
        dag.add_task("task_1", agent_type="backend", dependencies=[])
        dag.mark_done("task_1")
        assert dag.is_completed() is True

    def test_is_completed_with_failure(self):
        dag = DAGScheduler()
        dag.add_task("task_1", agent_type="backend", dependencies=[])
        dag.mark_failed("task_1")
        assert dag.is_completed() is True

    def test_is_completed_pending(self):
        dag = DAGScheduler()
        dag.add_task("task_1", agent_type="backend", dependencies=[])
        assert dag.is_completed() is False

    def test_reset(self):
        dag = DAGScheduler()
        dag.add_task("task_1", agent_type="backend", dependencies=[])
        dag.mark_done("task_1")
        dag.reset()
        assert len(dag.tasks) == 0
        assert len(dag.graph) == 0

    def test_topological_sort(self):
        dag = DAGScheduler()
        dag.add_task("a", agent_type="backend", dependencies=[])
        dag.add_task("b", agent_type="frontend", dependencies=["a"])
        dag.add_task("c", agent_type="test", dependencies=["a", "b"])
        dag.add_task("d", agent_type="audit", dependencies=["c"])
        order = dag.topological_sort()
        # a must come before b, b before c, c before d
        assert order.index("a") < order.index("b")
        assert order.index("b") < order.index("c")
        assert order.index("c") < order.index("d")

    def test_get_task_context(self):
        dag = DAGScheduler()
        dag.add_task("task_a", agent_type="backend", dependencies=[],
                     context={"desc": "backend task"})
        dag.add_task("task_b", agent_type="frontend", dependencies=["task_a"],
                     context={"desc": "frontend task"})
        dag.tasks["task_a"]["result"] = {"status": "success", "files": ["api.py"]}
        dag.mark_done("task_a")
        context = dag.get_task_context("task_b")
        assert "desc" in context
        assert context["desc"] == "frontend task"
        # Dependency result key is "backend_result" (agent_type)
        assert "backend_result" in context
        assert context["backend_result"] == {"status": "success", "files": ["api.py"]}

    def test_multiple_independent_tasks(self):
        dag = DAGScheduler()
        dag.add_task("a", agent_type="backend", dependencies=[])
        dag.add_task("b", agent_type="backend", dependencies=[])
        dag.add_task("c", agent_type="backend", dependencies=[])
        runnable = dag.get_runnable_tasks()
        assert sorted(runnable) == ["a", "b", "c"]

    def test_diamond_dependency(self):
        """菱形依赖: a → b, a → c, b+c → d"""
        dag = DAGScheduler()
        dag.add_task("a", agent_type="backend", dependencies=[])
        dag.add_task("b", agent_type="frontend", dependencies=["a"])
        dag.add_task("c", agent_type="test", dependencies=["a"])
        dag.add_task("d", agent_type="audit", dependencies=["b", "c"])
        # Only a is runnable initially
        assert dag.get_runnable_tasks() == ["a"]
        dag.mark_done("a")
        # b and c become runnable
        assert sorted(dag.get_runnable_tasks()) == ["b", "c"]
        dag.mark_done("b")
        # d still blocked by c
        assert dag.get_runnable_tasks() == ["c"]
        dag.mark_done("c")
        # now d is runnable
        assert dag.get_runnable_tasks() == ["d"]
