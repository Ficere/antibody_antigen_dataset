"""PDB utility functions"""

from pathlib import Path
from typing import List, Set


def normalize_pdb_id(pdb_id: str) -> str:
    """标准化 PDB ID（转为大写）"""
    return pdb_id.strip().upper()


def parse_chain_ids(chain_str: str) -> List[str]:
    """
    解析链ID字符串，支持多种格式
    
    示例:
        "A" -> ["A"]
        "H,L" -> ["H", "L"]
        "A | B" -> ["A", "B"]
        "NA" -> []
    """
    if not chain_str or chain_str.strip().upper() == "NA":
        return []
    
    # 处理 "|" 分隔符 (SAbDab 格式)
    if "|" in chain_str:
        parts = [p.strip() for p in chain_str.split("|")]
    # 处理 "," 分隔符
    elif "," in chain_str:
        parts = [p.strip() for p in chain_str.split(",")]
    else:
        parts = [chain_str.strip()]
    
    return [p for p in parts if p and p.upper() != "NA"]


def file_exists_case_insensitive(directory: Path, filename: str) -> bool:
    """
    大小写不敏感的文件存在性检查
    
    Args:
        directory: 目录路径
        filename: 文件名
    
    Returns:
        文件是否存在（不区分大小写）
    """
    if not directory.exists():
        return False
    
    filename_lower = filename.lower()
    for file in directory.iterdir():
        if file.name.lower() == filename_lower:
            return True
    return False


def get_existing_pdb_ids(directory: Path) -> Set[str]:
    """
    获取目录中所有已存在的 PDB ID（标准化为大写）
    
    Args:
        directory: 包含 PDB 文件的目录
    
    Returns:
        已存在的 PDB ID 集合（大写）
    """
    existing = set()
    if not directory.exists():
        return existing
    
    for file in directory.iterdir():
        if file.suffix.lower() == ".pdb":
            # 从文件名提取 PDB ID（前4个字符）
            pdb_id = file.stem[:4].upper()
            existing.add(pdb_id)
    
    return existing

