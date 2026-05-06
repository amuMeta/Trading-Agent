"""
文档加载器模块 - 支持多种格式的文档解析
"""

import os
from pathlib import Path
from typing import List, Optional


SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt", ".md"}


def load_document(file_path: str) -> str:
    """
    根据文件扩展名加载文档

    Args:
        file_path: 文件路径

    Returns:
        str: 提取的文本内容
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")

    ext = path.suffix.lower()

    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"不支持的文件格式: {ext}，支持的格式: {SUPPORTED_EXTENSIONS}")

    if ext == ".pdf":
        return load_pdf(file_path)
    elif ext in [".docx", ".doc"]:
        return load_docx(file_path)
    elif ext == ".txt":
        return load_txt(file_path)
    elif ext == ".md":
        return load_markdown(file_path)
    else:
        raise ValueError(f"不支持的文件格式: {ext}")


def load_pdf(path: str) -> str:
    """
    使用pdfplumber解析PDF文档

    Args:
        path: PDF文件路径

    Returns:
        str: 提取的文本内容
    """
    try:
        import pdfplumber

        text_parts = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        return "\n\n".join(text_parts)
    except ImportError:
        raise ImportError("pdfplumber未安装，请运行: pip install pdfplumber")


def load_docx(path: str) -> str:
    """
    使用python-docx解析Word文档

    Args:
        path: Word文件路径

    Returns:
        str: 提取的文本内容
    """
    try:
        from docx import Document

        doc = Document(path)
        paragraphs = []
        for para in doc.paragraphs:
            if para.text.strip():
                paragraphs.append(para.text)
        return "\n\n".join(paragraphs)
    except ImportError:
        raise ImportError("python-docx未安装，请运行: pip install python-docx")


def load_txt(path: str) -> str:
    """
    读取纯文本文件

    Args:
        path: 文本文件路径

    Returns:
        str: 文件内容
    """
    encodings = ["utf-8", "gbk", "gb2312", "gb18030"]

    for encoding in encodings:
        try:
            with open(path, "r", encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue

    raise ValueError(f"无法使用支持的编码读取文件: {path}")


def load_markdown(path: str) -> str:
    """
    读取Markdown文件

    Args:
        path: Markdown文件路径

    Returns:
        str: 文件内容
    """
    return load_txt(path)


def load_documents_from_directory(
    directory: str,
    extensions: Optional[List[str]] = None,
    recursive: bool = False
) -> List[tuple]:
    """
    从目录加载多个文档

    Args:
        directory: 目录路径
        extensions: 要加载的文件扩展名列表，如 [".pdf", ".txt"]
        recursive: 是否递归搜索子目录

    Returns:
        List[tuple]: [(file_path, content), ...] 元组列表
    """
    dir_path = Path(directory)

    if not dir_path.exists() or not dir_path.is_dir():
        raise ValueError(f"目录不存在或不是有效目录: {directory}")

    if extensions:
        extensions = [ext.lower() if ext.startswith(".") else f".{ext.lower()}" for ext in extensions]
    else:
        extensions = list(SUPPORTED_EXTENSIONS)

    files = []
    if recursive:
        for ext in extensions:
            files.extend(dir_path.rglob(f"*{ext}"))
    else:
        for ext in extensions:
            files.extend(dir_path.glob(f"*{ext}"))

    results = []
    for file_path in sorted(files):
        try:
            content = load_document(str(file_path))
            results.append((str(file_path), content))
        except Exception as e:
            print(f"[WARN] 加载文件失败 {file_path}: {e}")
            continue

    return results


def get_file_info(path: str) -> dict:
    """
    获取文件的基本信息

    Args:
        path: 文件路径

    Returns:
        dict: 包含文件名、扩展名、大小等信息
    """
    file_path = Path(path)

    if not file_path.exists():
        raise FileNotFoundError(f"文件不存在: {path}")

    return {
        "name": file_path.name,
        "filename": file_path.stem,
        "extension": file_path.suffix.lower(),
        "size": file_path.stat().st_size,
        "size_mb": round(file_path.stat().st_size / (1024 * 1024), 2),
        "path": str(file_path.absolute()),
    }


__all__ = [
    "load_document",
    "load_pdf",
    "load_docx",
    "load_txt",
    "load_markdown",
    "load_documents_from_directory",
    "get_file_info",
    "SUPPORTED_EXTENSIONS",
]