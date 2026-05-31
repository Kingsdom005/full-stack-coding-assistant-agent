"""
版本管理工具模块

提供版本号读取、校验和升级接口，版本号统一从项目根目录的 VERSION 文件读取。
"""

import re
from pathlib import Path
from typing import Literal, Optional

# 项目根目录（向上查找 VERSION 文件）
PROJECT_ROOT = Path(__file__).resolve().parent.parent
VERSION_FILE = PROJECT_ROOT / "VERSION"

# 语义化版本正则表达式（支持预发布标签和构建元数据）
SEMVER_PATTERN = re.compile(
    r"^(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)"
    r"(?:-(?P<prerelease>(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
    r"(?:\+(?P<buildmetadata>[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
)


def get_version() -> str:
    """
    从 VERSION 文件读取当前版本号

    Returns:
        版本号字符串（如 "0.1.0"）

    Raises:
        FileNotFoundError: VERSION 文件不存在
        ValueError: VERSION 文件格式错误
    """
    if not VERSION_FILE.exists():
        raise FileNotFoundError(f"VERSION 文件不存在: {VERSION_FILE}")

    version = VERSION_FILE.read_text(encoding="utf-8").strip()

    if not version:
        raise ValueError("VERSION 文件为空")

    # 校验版本号格式
    if not validate_version(version):
        raise ValueError(f"VERSION 文件中的版本号格式错误: {version}")

    return version


def validate_version(version: str) -> bool:
    """
    校验版本号是否符合语义化版本规范（SemVer 2.0.0）

    Args:
        version: 版本号字符串

    Returns:
        True 如果格式正确，否则 False
    """
    return SEMVER_PATTERN.match(version) is not None


def bump_version(
    part: Literal["major", "minor", "patch"] = "patch",
    prerelease: Optional[str] = None,
    dry_run: bool = False,
) -> str:
    """
    升级版本号并写回 VERSION 文件

    Args:
        part: 升级部分（major/minor/patch）
        prerelease: 预发布标签（如 "alpha.1"、"beta.1"）
        dry_run: 如果为 True，只计算新版本号但不写入文件

    Returns:
        新版本号字符串

    Examples:
        >>> bump_version("patch")  # 0.1.0 -> 0.1.1
        >>> bump_version("minor")  # 0.1.0 -> 0.2.0
        >>> bump_version("major")  # 0.1.0 -> 1.0.0
        >>> bump_version("patch", prerelease="alpha.1")  # 0.1.0 -> 0.1.1-alpha.1
    """
    current = get_version()
    match = SEMVER_PATTERN.match(current)

    if match is None:
        raise ValueError(f"当前版本号格式错误: {current}")

    major = int(match.group("major"))
    minor = int(match.group("minor"))
    patch = int(match.group("patch"))

    # 升级对应部分
    if part == "major":
        major += 1
        minor = 0
        patch = 0
    elif part == "minor":
        minor += 1
        patch = 0
    elif part == "patch":
        patch += 1
    else:
        raise ValueError(f"无效的升级部分: {part}，支持 major/minor/patch")

    # 构建新版本号
    new_version = f"{major}.{minor}.{patch}"
    if prerelease:
        new_version += f"-{prerelease}"

    if not dry_run:
        write_version(new_version)

    return new_version


def write_version(version: str) -> None:
    """
    将版本号写入 VERSION 文件

    Args:
        version: 版本号字符串

    Raises:
        ValueError: 版本号格式错误
    """
    if not validate_version(version):
        raise ValueError(f"版本号格式错误: {version}")

    VERSION_FILE.write_text(f"{version}\n", encoding="utf-8")


def get_version_info() -> dict:
    """
    获取版本号详细信息

    Returns:
        包含版本号各部分的字典，如：
        {
            "version": "0.1.0",
            "major": 0,
            "minor": 1,
            "patch": 0,
            "prerelease": None,
            "buildmetadata": None,
        }
    """
    version = get_version()
    match = SEMVER_PATTERN.match(version)

    if match is None:
        raise ValueError(f"版本号格式错误: {version}")

    return {
        "version": version,
        "major": int(match.group("major")),
        "minor": int(match.group("minor")),
        "patch": int(match.group("patch")),
        "prerelease": match.group("prerelease"),
        "buildmetadata": match.group("buildmetadata"),
    }


if __name__ == "__main__":
    # 命令行使用示例
    import argparse

    parser = argparse.ArgumentParser(description="版本管理工具")
    parser.add_argument("--get", action="store_true", help="获取当前版本号")
    parser.add_argument("--validate", type=str, help="校验版本号格式")
    parser.add_argument("--bump", type=str, choices=["major", "minor", "patch"], help="升级版本号")
    parser.add_argument("--prerelease", type=str, help="预发布标签")
    parser.add_argument("--dry-run", action="store_true", help="只计算不写入")
    args = parser.parse_args()

    if args.get:
        print(get_version())
    elif args.validate is not None:
        if validate_version(args.validate):
            print(f"✅ 版本号格式正确: {args.validate}")
        else:
            print(f"❌ 版本号格式错误: {args.validate}")
    elif args.bump:
        new_version = bump_version(args.bump, prerelease=args.prerelease, dry_run=args.dry_run)
        print(f"新版本号: {new_version}")
    else:
        print(get_version_info())
