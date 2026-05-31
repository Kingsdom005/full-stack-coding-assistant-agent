"""
PDF 文档读取器 - 从 PDF 文件中提取文本内容作为项目描述

支持 PyPDF2 纯 Python 解析，零系统依赖。
设计为可扩展，后续可增加 docx/txt 等格式。
"""

import re
from pathlib import Path
from typing import Optional, Tuple


class PDFReader:
    """PDF 文件文本提取器"""

    @staticmethod
    def extract_text(file_path: str) -> str:
        """
        从 PDF 文件中提取全部文本

        Args:
            file_path: PDF 文件路径

        Returns:
            提取的文本内容

        Raises:
            FileNotFoundError: 文件不存在
            ValueError: 文件不是 PDF 或无法读取
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        if path.suffix.lower() != ".pdf":
            raise ValueError(f"文件不是 PDF 格式: {file_path}")

        try:
            from PyPDF2 import PdfReader
        except ImportError:
            raise ImportError("需要安装 PyPDF2: pip install PyPDF2")

        reader = PdfReader(str(path))
        pages = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages.append(text)

        if not pages:
            raise ValueError(f"PDF 文件中没有可提取的文本: {file_path}")

        full_text = "\n\n".join(pages)
        return PDFReader._clean_text(full_text)

    @staticmethod
    def extract_summary(
        file_path: str,
        max_chars: int = 100,
    ) -> Tuple[str, str]:
        """
        从 PDF 提取文本，同时返回摘要和完整内容

        Args:
            file_path: PDF 文件路径
            max_chars: 摘要最大字符数

        Returns:
            (summary, full_text) 元组
        """
        full_text = PDFReader.extract_text(file_path)
        # 取第一段非空内容作为摘要
        first_line = full_text.strip().split("\n")[0].strip() if full_text else ""
        if len(first_line) > max_chars:
            summary = first_line[:max_chars] + "..."
        else:
            summary = first_line[:max_chars]
        return summary, full_text

    @staticmethod
    def _clean_text(text: str) -> str:
        """
        清洗 PDF 提取的文本：
        - 合并多余空白行
        - 修复断行（PDF 常见的换行符问题）
        - 移除页码等噪音
        """
        # 移除多余空白行（3个以上连续空行合并为2个）
        text = re.sub(r"\n{3,}", "\n\n", text)
        # 移除行尾多余空格
        text = re.sub(r"[ \t]+$", "", text, flags=re.MULTILINE)
        # 移除页码模式（如 "Page 1 of 10" 或 "- 1 -"）
        text = re.sub(
            r"\n\s*(?:Page\s+\d+\s+of\s+\d+|[-\s]*\d+[-\s]*)\s*\n", "\n", text
        )
        return text.strip()


def read_document(file_path: str) -> Tuple[str, str]:
    """
    通用文档读取入口，根据扩展名自动选择解析器

    当前支持: .pdf
    后续扩展: .docx, .txt, .md

    Args:
        file_path: 文档路径

    Returns:
        (summary, full_text) 元组
    """
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix == ".pdf":
        return PDFReader.extract_summary(file_path)
    elif suffix in (".txt", ".md"):
        content = path.read_text(encoding="utf-8")
        summary = content[:100].replace("\n", " ").strip()
        return summary, content
    else:
        raise ValueError(f"不支持的文件格式: {suffix}，当前支持 .pdf / .txt / .md")
