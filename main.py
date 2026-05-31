"""
全栈代码助手智能体 - 主入口
支持 Python 3.13+
"""

import argparse
import signal
import sys
from pathlib import Path
from typing import Dict, List, Optional

from coordinator.coordinator import Coordinator
from utils.agent_selector import AgentSelector
from utils.config_validator import validate_config
from utils.logger import debug, error, info, warning
from utils.output_manager import OutputManager
from utils.pdf_reader import read_document

# 退出命令集合
EXIT_COMMANDS = {"exit", "quit", "bye", "q"}

# Ctrl+C 退出标志
_interrupt_received = False


def _signal_handler(sig, frame):
    """处理 Ctrl+C 信号"""
    global _interrupt_received
    _interrupt_received = True
    info("\n\n收到退出信号，正在退出...")


def _is_exit_command(user_input: str) -> bool:
    """判断用户输入是否为退出命令"""
    return user_input.strip().lower() in EXIT_COMMANDS


def _print_welcome():
    """打印欢迎信息"""
    info("=" * 60)
    info("全栈代码助手智能体 (Full-Stack Coding Assistant Agent)")
    info("=" * 60)
    info("")
    info("交互模式已启动。输入需求开始开发，输入 exit/quit/bye 退出。")
    info("")


def _print_help():
    """打印帮助信息"""
    info("")
    info("可用命令:")
    info("  help, h, ?      - 显示此帮助")
    info("  status, s        - 显示当前项目状态")
    info("  agents, a        - 显示可用 Agent 列表")
    info("  load <文件>      - 加载 PDF/TXT/MD 文档作为需求上下文")
    info("  exit, quit, bye  - 退出程序")
    info("")
    info("输入任意文本即可作为新需求进行迭代开发。")
    info("")


def _print_agent_list(selector: AgentSelector):
    """打印可用 Agent 列表"""
    info("")
    info("可用 Agent:")
    for name, desc in selector.AGENT_DESCRIPTIONS.items():
        info(f"  - {name}: {desc}")
    info("")


def _print_project_status(output_dir: Optional[Path]):
    """打印当前项目状态"""
    info("")
    if output_dir is None or not output_dir.exists():
        info("当前状态: 未创建项目（请先输入项目描述）")
        info("")
        return

    info(f"输出目录: {output_dir}")
    info("")

    # 读取元数据
    meta_file = output_dir / ".meta.json"
    if meta_file.exists():
        import json

        meta = json.loads(meta_file.read_text(encoding="utf-8"))
        info(f"项目描述: {meta.get('task_description', 'N/A')}")
        info(f"创建时间: {meta.get('created_at', 'N/A')}")
        info(f"迭代次数: {meta.get('iteration_count', 0)}")
        info(f"最后任务: {meta.get('last_task_id', 'N/A')}")
        info(f"状态: {meta.get('status', 'N/A')}")
    else:
        info("未找到项目元数据")

    info("")

    # 统计文件数量
    for sub_dir in ["backend", "frontend", "tests", "audits"]:
        target = output_dir / sub_dir
        if target.exists():
            files = list(target.iterdir())
            info(f"  {sub_dir}: {len(files)} 个文件")
        else:
            info(f"  {sub_dir}: 未创建")

    # 统计 trace 文件
    traces_dir = output_dir / "traces"
    if traces_dir.exists():
        trace_count = sum(1 for _ in traces_dir.rglob("*.md"))
        if trace_count > 0:
            info(
                f"  traces: {trace_count} 个审计 trace 文件（Agent 每一步的输入输出记录）"
            )

    info("")


def _get_user_input(prompt: str = ">>> ") -> Optional[str]:
    """
    获取用户输入，处理 Ctrl+C

    Returns:
        用户输入字符串，如果收到中断则返回 None
    """
    global _interrupt_received

    if _interrupt_received:
        return None

    try:
        user_input = input(prompt).strip()
        if _interrupt_received:
            return None
        return user_input
    except (EOFError, KeyboardInterrupt):
        return None


def _get_project_description() -> Optional[str]:
    """
    首次启动时，引导用户输入项目描述

    支持：
    - 纯文本描述
    - file:path/to/file.pdf  从 PDF 读取描述
    - file:path/to/file.txt  从 TXT 读取描述

    Returns:
        项目描述字符串，如果取消则返回 None
    """
    info("")
    info("欢迎使用全栈代码助手！")
    info("请描述你要开发的项目，或者指定文档文件：")
    info("  直接输入   - 文本描述项目")
    info("  file:xxx   - 从 PDF/TXT 文件读取描述")
    info("  exit       - 退出")
    info("")

    while True:
        user_input = _get_user_input("项目描述> ")
        if user_input is None:
            return None
        if _is_exit_command(user_input):
            return None
        if not user_input:
            warning("项目描述不能为空，请重新输入。")
            continue

        # 检查是否为 file: 指令
        if user_input.startswith("file:"):
            file_path = user_input[5:].strip()
            description = _load_document_description(file_path)
            if description is None:
                continue  # 加载失败，让用户重新输入
            return description

        return user_input


def _load_document_description(file_path: str) -> Optional[str]:
    """
    从文档文件加载原始文本内容

    支持 .pdf / .txt / .md 格式。
    成功时返回文档的原始全文，失败时打印错误并返回 None。

    Args:
        file_path: 文档文件路径

    Returns:
        文档的原始全文，或 None
    """
    try:
        summary, full_text = read_document(file_path)
        info(f"  已从文件加载: {file_path}")
        info(f"  文档摘要: {summary}")
        info(f"  文档长度: {len(full_text)} 字符")
        return full_text
    except FileNotFoundError:
        error(f"文件不存在: {file_path}")
        return None
    except ValueError as e:
        error(str(e))
        return None
    except ImportError as e:
        error(str(e))
        error("请运行: pip install PyPDF2")
        return None
    except Exception as e:
        error(f"读取文档失败: {str(e)}")
        return None


def _merge_description(pdf_path: str, text_desc: str = "") -> str:
    """
    将从 PDF 加载的内容和文本描述合并为一个完整描述

    Args:
        pdf_path: PDF 文件路径
        text_desc: 用户输入的文本描述（可选）

    Returns:
        合并后的描述文本
    """
    summary, full_text = read_document(pdf_path)
    if text_desc:
        # 文本描述作为摘要，PDF 内容作为详细需求
        description = (
            f"{text_desc}\n\n"
            f"---\n"
            f"以下为详细需求文档（来自 {pdf_path}）:\n\n"
            f"{full_text}"
        )
    else:
        # 纯 PDF，用摘要作为描述
        description = f"{summary}\n\n---\n以下来自文档 {pdf_path}:\n\n{full_text}"
    return description


def _select_all_agents() -> List[str]:
    """返回全部 Agent 列表"""
    return ["backend", "frontend", "test", "audit"]


def _run_task(
    coordinator: Coordinator,
    output_mgr: OutputManager,
    output_dir: Path,
    description: str,
    requirements: str,
    agent_types: List[str],
    is_first_run: bool,
) -> Dict:
    """
    执行一次任务（可能只运行选中的 Agent）

    Args:
        coordinator: 协调器实例
        output_mgr: 输出管理器实例
        output_dir: 输出目录
        description: 任务描述
        requirements: 详细需求
        agent_types: 选中的 Agent 类型列表
        is_first_run: 是否为首次运行

    Returns:
        执行结果字典
    """
    # 重置 DAG
    coordinator.reset_dag()

    # 提交任务
    if is_first_run:
        # 首次运行：使用 submit_task（完整 DAG）
        main_task_id = coordinator.submit_task(
            description=description,
            requirements=requirements,
            is_iteration=False,
        )
    else:
        # 迭代运行：使用 submit_iteration_task（只创建选中的 Agent）
        main_task_id = coordinator.submit_iteration_task(
            description=description,
            requirements=requirements,
            agent_types=agent_types,
        )

    info(f"  主任务 ID: {main_task_id}")
    info(f"  选中 Agent: {', '.join(agent_types)}")
    debug("任务已提交到 DAG 调度器")

    # 执行任务
    info("-" * 60)
    results = coordinator.run(main_task_id)
    info("-" * 60)
    debug(f"任务执行完成，结果: {len(results)} 个任务")

    # 保存迭代记录
    if output_dir is not None:
        try:
            output_mgr.save_iteration(
                output_path=output_dir,
                prompt=description + (" " + requirements if requirements else ""),
                result={
                    "task_id": main_task_id,
                    "results": {
                        k: v.get("status")
                        for k, v in results.items()
                        if not k.startswith("_")
                    },
                },
            )
            # 更新元数据
            output_mgr.update_meta(
                output_path=output_dir,
                last_task_id=main_task_id,
                status="completed",
            )
        except Exception as e:
            error(f"保存迭代记录失败: {str(e)}")

    return results


def _print_results(
    results: Dict,
    output_dir: Optional[Path],
    coordinator: Coordinator,
    main_task_id: str,
):
    """打印任务执行结果"""
    info("")
    info("执行结果:")
    info("=" * 60)
    for task_suffix, result in results.items():
        if task_suffix.startswith("_"):
            continue
        status = result.get("status", "unknown")
        info(f"\n[{task_suffix}]:")
        info(f"  状态: {status}")
        if result.get("error"):
            error(f"  错误: {result['error']}")
            if result.get("traceback"):
                debug(f"  堆栈: {result['traceback']}")
        files = result.get("files", [])
        if files:
            info(f"  生成文件: {len(files)} 个")

    # 获取完整状态
    status = coordinator.get_task_status(main_task_id)
    info("")
    info("任务状态汇总:")
    info("=" * 60)
    for agent, agent_info in status["tasks"].items():
        info(f"  {agent}: {agent_info['status']}")

    info("")
    if output_dir:
        info(f"输出目录: {output_dir}")
        # 提示 trace 文件位置
        traces_dir = output_dir / "traces"
        if traces_dir.exists():
            trace_count = sum(1 for _ in traces_dir.rglob("*.md"))
            if trace_count > 0:
                info(f"Agent 执行追溯: {traces_dir} ({trace_count} 个 trace 文件)")
    info("完成！")
    info("=" * 60)


def interactive_mode(
    coordinator: Coordinator,
    output_mgr: OutputManager,
    output_dir: Optional[Path],
    selector: AgentSelector,
    first_description: Optional[str] = None,
):
    """
    交互模式主循环

    Args:
        coordinator: 协调器实例（持久化，跨迭代复用）
        output_mgr: 输出管理器实例
        output_dir: 输出目录（首次可能为 None）
        selector: Agent 选择器实例
        first_description: 首次运行的项目描述（命令行参数传入）
    """
    global _interrupt_received

    _print_welcome()

    # 情况 1: 命令行已传入描述，先执行一次
    if first_description:
        info(f"[首次运行] 项目描述: {first_description}")
        info("")

        # 创建输出目录
        output_dir = output_mgr.create_output_dir(first_description)
        coordinator.output_dir = output_dir
        for agent in coordinator.agents.values():
            agent._set_output_dir(output_dir)

        info("[1/3] 智能选择 Agent...")
        # 首次运行，无已有代码，使用全部 Agent
        agent_types = _select_all_agents()
        info(f"  选中: {', '.join(agent_types)}")
        info("")

        info("[2/3] 提交并执行任务...")
        results = _run_task(
            coordinator=coordinator,
            output_mgr=output_mgr,
            output_dir=output_dir,
            description=first_description,
            requirements="",
            agent_types=agent_types,
            is_first_run=True,
        )

        info("[3/3] 输出结果...")
        # 获取 main_task_id（从 coordinator）
        main_task_id = coordinator._main_task_id
        _print_results(results, output_dir, coordinator, main_task_id)

        # 自动生成 README.md
        output_mgr.generate_readme(output_dir)
        info(f"  已生成执行说明: {output_dir / 'README.md'}")

    # 情况 2: 无参数启动，引导用户输入项目描述
    if output_dir is None:
        project_desc = _get_project_description()
        if project_desc is None or _interrupt_received:
            info("退出程序。")
            return

        # 创建输出目录
        output_dir = output_mgr.create_output_dir(project_desc)
        coordinator.output_dir = output_dir
        for agent in coordinator.agents.values():
            agent._set_output_dir(output_dir)

        info("[1/3] 首次运行，使用全部 Agent...")
        agent_types = _select_all_agents()

        info("[2/3] 提交并执行任务...")
        results = _run_task(
            coordinator=coordinator,
            output_mgr=output_mgr,
            output_dir=output_dir,
            description=project_desc,
            requirements="",
            agent_types=agent_types,
            is_first_run=True,
        )

        main_task_id = coordinator._main_task_id
        info("[3/3] 输出结果...")
        _print_results(results, output_dir, coordinator, main_task_id)

        # 自动生成 README.md
        output_mgr.generate_readme(output_dir)
        info(f"  已生成执行说明: {output_dir / 'README.md'}")

    # 进入主循环
    info("")
    info("进入交互模式。输入 help 查看可用命令。")
    info("")

    while not _interrupt_received:
        user_input = _get_user_input("\n>>> ")
        if user_input is None:
            break
        if not user_input:
            continue

        # 处理命令
        cmd = user_input.strip().lower()

        if _is_exit_command(cmd):
            info("再见！")
            break

        if cmd in ("help", "h", "?"):
            _print_help()
            continue

        if cmd in ("status", "s"):
            _print_project_status(output_dir)
            continue

        if cmd in ("agents", "a"):
            _print_agent_list(selector)
            continue

        if cmd.startswith("load "):
            file_path = user_input.strip()[5:].strip()
            doc_text = _load_document_description(file_path)
            if doc_text is None:
                continue
            info("  文档已加载，接下来输入的需求将附带此文档内容。")
            info("  请输入具体的开发需求（基于以上文档）：")
            user_input = _get_user_input("\n>>> ")
            if user_input is None or _is_exit_command(user_input.strip().lower()):
                break
            if not user_input:
                continue
            # 将文档内容拼接到用户需求后面，不改变 user_input 用于 Agent 选择（取第一行）
            user_input = f"{user_input}\n\n---\n以下来自文档 {file_path}:\n\n{doc_text}"
            # 继续执行下面的任务流程（不 continue）
            cmd = user_input.strip().lower()

        # 用户需求：智能选择 Agent 并执行
        info("[1/3] 智能选择 Agent...")

        # 收集已有代码摘要
        code_summary = ""
        if output_dir is not None:
            code_summary = AgentSelector.format_existing_code_summary(str(output_dir))

        try:
            selection = selector.select_agents(user_input, code_summary)
            agent_types = selection["agents"]
            reason = selection["reason"]
            info(f"  选中: {', '.join(agent_types)}")
            debug(f"  原因: {reason}")
        except Exception as e:
            warning(f"Agent 选择失败，使用全部 Agent: {e}")
            agent_types = _select_all_agents()

        info("")
        info("[2/3] 提交并执行任务...")

        results = _run_task(
            coordinator=coordinator,
            output_mgr=output_mgr,
            output_dir=output_dir,
            description=user_input,
            requirements="",
            agent_types=agent_types,
            is_first_run=False,
        )

        main_task_id = coordinator._main_task_id
        info("[3/3] 输出结果...")
        _print_results(results, output_dir, coordinator, main_task_id)

        # 自动生成/更新 README.md
        output_mgr.generate_readme(output_dir)
        info(f"  已更新执行说明: {output_dir / 'README.md'}")


def main():
    """主函数"""
    info("=" * 60)
    info("全栈代码助手智能体 (Full-Stack Coding Assistant Agent)")
    info("=" * 60)
    info("")

    # 0. 验证配置
    info("[0/5] 验证配置...")
    if not validate_config(exit_on_error=False):
        error("配置验证失败，请检查 .env 文件")
        error("运行: python utils/config_validator.py 查看详细配置")
        sys.exit(1)

    # 解析命令行参数
    parser = argparse.ArgumentParser(
        description="全栈代码助手智能体（交互模式）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 无参数启动：进入交互模式，引导创建项目
  python main.py

  # 带描述启动：先执行一次，然后进入交互模式
  python main.py "开发一个用户登录功能"

  # 从 PDF 文件加载项目描述
  python main.py --pdf spec.pdf "开发一个后台管理系统"

  # 纯 PDF 文件作为描述（自动提取摘要）
  python main.py --pdf spec.pdf

  # 继续已有项目
  python main.py --continue output/20260530_230000_xxx

交互模式命令:
  help, h, ?      - 显示帮助
  status, s        - 显示项目状态
  agents, a        - 显示可用 Agent
  load <文件>      - 加载 PDF/TXT/MD 文档作为需求
  exit, quit, bye  - 退出
""",
    )
    parser.add_argument(
        "description", nargs="?", help="项目描述（可选，可与 --pdf 组合使用）"
    )
    parser.add_argument("-r", "--requirements", default="", help="详细需求")
    parser.add_argument("-p", "--pdf", dest="pdf_path", help="PDF 需求文档路径")
    parser.add_argument(
        "-c",
        "--continue",
        dest="continue_dir",
        help="已有项目的输出目录路径（继续开发）",
    )
    args = parser.parse_args()

    # 注册 Ctrl+C 信号处理
    signal.signal(signal.SIGINT, _signal_handler)

    # 初始化协调器和输出管理器
    info("[1/5] 初始化协调器...")
    try:
        coordinator = Coordinator()
        debug("协调器初始化成功")
    except Exception as e:
        error(f"协调器初始化失败: {str(e)}")
        sys.exit(1)

    output_mgr = OutputManager()
    selector = AgentSelector(coordinator.model_router)

    output_dir = None
    first_description = None

    # 合并 PDF + 文本描述
    _pdf_content = ""  # PDF 原始文本（用于 --continue 模式注入到需求）
    if args.pdf_path:
        info(f"[2/5] 加载 PDF 文档: {args.pdf_path}")
        try:
            summary, _pdf_content = read_document(args.pdf_path)
            if args.description:
                first_description = _merge_description(args.pdf_path, args.description)
            else:
                first_description = _merge_description(args.pdf_path)
            info(f"  文档已加载，摘要: {summary[:60]}...")
        except Exception as e:
            error(f"加载 PDF 失败: {str(e)}")
            sys.exit(1)

    # 处理 --continue 模式
    if args.continue_dir is not None:
        info(f"[2/5] 加载已有项目: {args.continue_dir}")
        try:
            existing_context = output_mgr.load_output_dir(args.continue_dir)
            output_dir = Path(args.continue_dir).resolve()
            coordinator.output_dir = output_dir
            for agent in coordinator.agents.values():
                agent._set_output_dir(output_dir)

            info(f"  项目描述: {existing_context['meta'].get('task_description', '')}")
            info(f"  迭代次数: {existing_context['meta'].get('iteration_count', 0)}")
        except FileNotFoundError as e:
            error(str(e))
            sys.exit(1)

        # --continue + --pdf: PDF 内容作为本次迭代的额外需求
        if _pdf_content:
            first_description = f"{args.description or '请基于已有代码继续开发'}\n\n---\n以下来自文档 {args.pdf_path}:\n\n{_pdf_content}"
        else:
            first_description = args.description or ""

    elif args.description or _pdf_content:
        # 有描述或 PDF：先执行一次，然后进入交互模式
        if not first_description:
            first_description = args.description
        info(f"[2/5] 准备首次运行: {first_description[:100]}...")
    else:
        # 无参数：进入交互模式，由交互模式引导创建项目
        info("[2/5] 无参数启动，将进入交互模式")

    info("[3] 启动交互模式...")
    info("=" * 60)

    # 进入交互模式
    interactive_mode(
        coordinator=coordinator,
        output_mgr=output_mgr,
        output_dir=output_dir,
        selector=selector,
        first_description=first_description,
    )


if __name__ == "__main__":
    main()
