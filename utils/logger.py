"""
日志工具 - 提供统一的日志记录功能
支持 Python 3.13+ 的最新日志特性
"""

import os
import logging
from datetime import datetime
from typing import Optional


def setup_logger(
    name: str = "coding_agent",
    log_level: Optional[str] = None,
    log_file: Optional[str] = None,
) -> logging.Logger:
    """
    设置日志记录器

    Args:
        name: 日志记录器名称
        log_level: 日志级别 (DEBUG/INFO/WARNING/ERROR)
        log_file: 日志文件路径

    Returns:
        配置好的 Logger 实例
    """
    # 从环境变量读取配置
    if log_level is None:
        log_level = os.getenv("LOG_LEVEL", "INFO")

    if log_file is None:
        log_file = os.getenv("LOG_FILE", "logs/app.log")

    # 创建日志记录器
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper()))

    # 避免重复添加 handler
    if logger.handlers:
        return logger

    # 创建日志目录
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)

    # 日志格式（Python 3.13+ 优化）
    formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 文件 Handler（带轮转）
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(getattr(logging, log_level.upper()))
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # 控制台 Handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, log_level.upper()))
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger


# 全局日志记录器
logger = setup_logger()


def get_logger(name: str) -> logging.Logger:
    """获取指定名称的日志记录器"""
    return setup_logger(name)


# 便捷函数
def debug(msg: str, *args, **kwargs):
    """记录 DEBUG 日志"""
    logger.debug(msg, *args, **kwargs)


def info(msg: str, *args, **kwargs):
    """记录 INFO 日志"""
    logger.info(msg, *args, **kwargs)


def warning(msg: str, *args, **kwargs):
    """记录 WARNING 日志"""
    logger.warning(msg, *args, **kwargs)


def error(msg: str, *args, **kwargs):
    """记录 ERROR 日志"""
    logger.error(msg, *args, **kwargs)
