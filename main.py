"""
全栈代码助手智能体 - 主入口
支持 Python 3.13+
"""

import sys
from coordinator.coordinator import Coordinator
from utils.config_validator import validate_config, print_config
from utils.logger import info, error, debug, get_logger

# 获取日志记录器
logger = get_logger(__name__)


def main():
    """主函数"""
    info("=" * 60)
    info("全栈代码助手智能体 (Full-Stack Coding Assistant Agent)")
    info("=" * 60)
    info("")

    # 0. 验证配置
    info("[0/4] 验证配置...")
    if not validate_config(exit_on_error=False):
        error("配置验证失败，请检查 .env 文件")
        error("运行: python utils/config_validator.py 查看详细配置")
        sys.exit(1)

    if len(sys.argv) < 2:
        info("用法:")
        info("  python main.py '任务描述' ['详细需求']")
        info("")
        info("示例:")
        info("  python main.py '开发一个用户登录功能' '包含前后端实现'")
        sys.exit(1)

    # 解析命令行参数
    description = sys.argv[1]
    requirements = sys.argv[2] if len(sys.argv) > 2 else ""

    # 1. 初始化协调器
    info("[1/4] 初始化协调器...")
    try:
        coordinator = Coordinator()
        debug("协调器初始化成功")
    except Exception as e:
        error(f"协调器初始化失败: {str(e)}")
        sys.exit(1)

    # 2. 提交任务
    info(f"[2/4] 提交任务: {description}")
    try:
        main_task_id = coordinator.submit_task(description, requirements)
        info(f"  主任务 ID: {main_task_id}")
        debug(f"任务已提交到 DAG 调度器")
    except Exception as e:
        error(f"任务提交失败: {str(e)}")
        sys.exit(1)

    # 3. 执行任务
    info("[3/4] 开始执行任务...")
    info("-" * 60)
    try:
        results = coordinator.run(main_task_id)
        info("-" * 60)
        debug(f"任务执行完成，结果: {len(results)} 个任务")
    except RuntimeError as e:
        error(f"任务调度失败: {str(e)}")
        sys.exit(1)
    except Exception as e:
        error(f"任务执行失败: {str(e)}")
        sys.exit(1)

    # 4. 输出结果
    info("")
    info("执行结果:")
    info("=" * 60)
    for task_suffix, result in results.items():
        status = result.get("status", "unknown")
        info(f"\n[{task_suffix}]:")
        info(f"  状态: {status}")
        if result.get("error"):
            error(f"  错误: {result['error']}")
        if result.get("message"):
            info(f"  消息: {result['message']}")

    # 获取完整状态
    status = coordinator.get_task_status(main_task_id)
    info("")
    info("任务状态汇总:")
    info("=" * 60)
    for agent, info in status["tasks"].items():
        info(f"  {agent}: {info['status']}")

    info("")
    info("完成！")
    info("=" * 60)


if __name__ == "__main__":
    main()
