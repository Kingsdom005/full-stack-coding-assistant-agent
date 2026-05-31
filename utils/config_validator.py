"""
配置验证工具 - 检查必需的环境变量和配置
支持 Python 3.13+ 的类型检查
"""

import os
import sys
from typing import Dict, List, Tuple
from utils.logger import get_logger

logger = get_logger(__name__)


class ConfigValidator:
    """配置验证器"""

    # 必需的环境变量
    REQUIRED_ENVS = [
        "TENCENT_API_KEY",
    ]

    # 可选的环境变量及其默认值
    OPTIONAL_ENVS = {
        "TENCENT_API_BASE": "https://api.hunyuan.cloud.tencent.com/hyllm/v1",
        "SQLITE_DB_PATH": "./context.db",
        "CODEBUDDY_CLI_PATH": "codebuddy",
        "CODEBUDDY_TIMEOUT": "60",
        "LOG_LEVEL": "INFO",
        "DEBUG": "false",
    }

    # API Key 格式验证
    API_KEY_PATTERNS = {
        "TENCENT_API_KEY": r"^sk-",  # 腾讯混元 API Key 通常以 sk- 开头
    }

    @classmethod
    def validate_envs(cls, exit_on_error: bool = True) -> Tuple[bool, List[str]]:
        """
        验证环境变量配置

        Args:
            exit_on_error: 验证失败时是否退出程序

        Returns:
            (是否通过验证, 错误信息列表)
        """
        errors = []
        warnings = []

        # 检查必需的环境变量
        for env_name in cls.REQUIRED_ENVS:
            value = os.getenv(env_name)
            if not value or value == f"YOUR_{env_name}_HERE":
                errors.append(f"缺少必需的环境变量: {env_name}")
            else:
                # 验证 API Key 格式
                if env_name in cls.API_KEY_PATTERNS:
                    import re

                    pattern = cls.API_KEY_PATTERNS[env_name]
                    if not re.match(pattern, value):
                        warnings.append(f"{env_name} 格式可能不正确（期望以 sk- 开头）")

        # 检查可选的环境变量
        for env_name, default_value in cls.OPTIONAL_ENVS.items():
            value = os.getenv(env_name)
            if not value:
                warnings.append(
                    f"可选环境变量 {env_name} 未设置，将使用默认值: {default_value}"
                )

        # 输出结果
        if warnings:
            for warning in warnings:
                logger.warning(warning)

        if errors:
            for error in errors:
                logger.error(error)

            if exit_on_error:
                logger.error("配置验证失败，程序退出")
                sys.exit(1)
            return False, errors

        logger.info("✅ 配置验证通过")
        return True, []

    @classmethod
    def print_config_summary(cls):
        """打印配置摘要"""
        print("=" * 60)
        print("配置摘要")
        print("=" * 60)

        # 必需的环境变量
        print("\n【必需配置】")
        for env_name in cls.REQUIRED_ENVS:
            value = os.getenv(env_name)
            if value and value != f"YOUR_{env_name}_HERE":
                # 隐藏 API Key 的大部分内容
                if "API_KEY" in env_name:
                    masked_value = value[:10] + "*" * (len(value) - 10)
                    print(f"  {env_name}: {masked_value}")
                else:
                    print(f"  {env_name}: {value}")
            else:
                print(f"  {env_name}: ❌ 未配置")

        # 可选的环境变量
        print("\n【可选配置】")
        for env_name, default_value in cls.OPTIONAL_ENVS.items():
            value = os.getenv(env_name, default_value)
            print(f"  {env_name}: {value}")

        print("=" * 60)


def validate_config(exit_on_error: bool = True) -> bool:
    """
    便捷函数：验证配置

    Args:
        exit_on_error: 验证失败时是否退出程序

    Returns:
        是否通过验证
    """
    return ConfigValidator.validate_envs(exit_on_error)[0]


def print_config():
    """便捷函数：打印配置摘要"""
    ConfigValidator.print_config_summary()


if __name__ == "__main__":
    # 单独运行此脚本时，打印配置摘要
    print_config()
    print("\n" + "=" * 60)
    validate_config(exit_on_error=False)
