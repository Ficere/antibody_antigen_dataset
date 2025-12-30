"""SAbDab TSV file parser"""

import csv
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterator, List, Optional

from pdb_processor.utils.pdb_utils import normalize_pdb_id, parse_chain_ids

logger = logging.getLogger(__name__)


@dataclass
class SAbDabEntry:
    """SAbDab 数据库条目"""
    
    pdb_id: str  # 标准化的 PDB ID（大写）
    original_pdb_id: str  # 原始 PDB ID
    heavy_chain: str  # 重链 ID
    light_chain: str  # 轻链 ID（可能为空）
    antigen_chains: List[str]  # 抗原链 ID 列表
    antigen_type: str  # 抗原类型
    resolution: Optional[float]  # 分辨率
    method: str  # 实验方法
    
    @property
    def antibody_chains(self) -> List[str]:
        """获取抗体链列表（重链 + 轻链，去重）"""
        chains = []
        if self.heavy_chain and self.heavy_chain not in chains:
            chains.append(self.heavy_chain)
        if self.light_chain and self.light_chain not in chains:
            chains.append(self.light_chain)
        return chains
    
    @property
    def is_valid(self) -> bool:
        """检查条目是否有效（必须有抗体链和抗原链）"""
        return bool(self.antibody_chains and self.antigen_chains)
    
    @property
    def entry_key(self) -> str:
        """生成唯一的条目键（用于区分同一 PDB 的不同抗体-抗原对）"""
        ab_chains = ",".join(sorted(self.antibody_chains))
        ag_chains = ",".join(sorted(self.antigen_chains))
        return f"{self.pdb_id}_{ab_chains}_{ag_chains}"


class SAbDabParser:
    """SAbDab TSV 文件解析器"""
    
    REQUIRED_COLUMNS = ["pdb", "Hchain", "antigen_chain"]
    
    def __init__(self, tsv_path: str):
        self.tsv_path = Path(tsv_path)
        if not self.tsv_path.exists():
            raise FileNotFoundError(f"SAbDab file not found: {tsv_path}")
    
    def parse(self) -> Iterator[SAbDabEntry]:
        """解析 TSV 文件，逐行生成 SAbDabEntry"""
        with open(self.tsv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter="\t")
            
            # 验证必需列
            if reader.fieldnames:
                missing = set(self.REQUIRED_COLUMNS) - set(reader.fieldnames)
                if missing:
                    raise ValueError(f"Missing columns: {missing}")
            
            for row_num, row in enumerate(reader, start=2):
                try:
                    entry = self._parse_row(row)
                    if entry:
                        yield entry
                except Exception as e:
                    logger.warning(f"Row {row_num}: Parse error - {e}")
    
    def _parse_row(self, row: Dict[str, str]) -> Optional[SAbDabEntry]:
        """解析单行数据"""
        pdb_id = row.get("pdb", "").strip()
        if not pdb_id or len(pdb_id) != 4:
            return None

        # 解析链信息，转换为大写（PDB 文件中链 ID 为大写）
        heavy_chain = self._normalize_chain_id(row.get("Hchain", ""))
        light_chain = self._normalize_chain_id(row.get("Lchain", ""))
        antigen_chain_str = row.get("antigen_chain", "")
        antigen_chains = [c.upper() for c in parse_chain_ids(antigen_chain_str)]

        # 解析分辨率
        resolution = None
        res_str = row.get("resolution", "").strip()
        if res_str and res_str.upper() != "NA":
            try:
                resolution = float(res_str)
            except ValueError:
                pass

        return SAbDabEntry(
            pdb_id=normalize_pdb_id(pdb_id),
            original_pdb_id=pdb_id,
            heavy_chain=heavy_chain,
            light_chain=light_chain,
            antigen_chains=antigen_chains,
            antigen_type=row.get("antigen_type", ""),
            resolution=resolution,
            method=row.get("method", ""),
        )

    def _normalize_chain_id(self, chain_id: str) -> str:
        """标准化链 ID：去除空白、转大写、处理 NA"""
        chain_id = chain_id.strip().upper()
        return "" if chain_id == "NA" else chain_id
    
    def get_valid_entries(self) -> List[SAbDabEntry]:
        """获取所有有效的条目"""
        return [e for e in self.parse() if e.is_valid]
    
    def get_unique_pdb_ids(self) -> set:
        """获取所有唯一的 PDB ID（标准化为大写）"""
        return {e.pdb_id for e in self.parse()}

