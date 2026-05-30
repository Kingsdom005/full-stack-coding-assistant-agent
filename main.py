"""
全栈代码助手智能体 - 主入口
"""

import sys
from coordinator.coordinator import Coordinator


def main():
    """主函数"""
    print("=" * 60)
    print("全栈代码助手智能体 (Full-Stack Coding Assistant Agent)")
    print("=" * 60)
    print()

    if len(sys.argv) < 2:
        print("用法:")
        print("  python main.py '任务描述' ['详细需求']")
        print()
        print("示例:")
        print("  python main.py '开发一个用户登录功能' '包含前后端实现'")
        sys.exit(1)

    # 解析命令行参数
    description = sys.argv[1]
    requirements = sys.argv[2] if len(sys.argv) > 2 else ""

    # 初始化协调器
    print("[1/3] 初始化协调器...")
    coordinator = Coordinator()

    # 提交任务
    print(f"[2/3] 提交任务: {description}")
    main_task_id = coordinator.submit_task(description, requirements)
    print(f"  主任务 ID: {main_task_id}")

    # 执行任务
    print("[3/3] 开始执行任务...")
    print("-" * 60)
    results = coordinator.run(main_task_id)
    print("-" * 60)

    # 输出结果
    print("\n执行结果:")
    print("=" * 60)
    for task_suffix, result in results.items():
        print(f"\n[{task_suffix}]:")
        print(f"  状态: {result.get('status', 'unknown')}")
        if result.get("error"):
            print(f"  错误: {result['error']}")

    # 获取完整状态
    status = coordinator.get_task_status(main_task_id)
    print("\n任务状态汇总:")
    print("=" * 60)
    for agent, info in status["tasks"].items():
        print(f"  {agent}: {info['status']}")

    print("\n完成！")


if __name__ == "__main__":
    main()
