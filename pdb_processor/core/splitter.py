"""Structure splitter for antibody-antigen complexes"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from Bio.PDB import PDBIO, PDBParser, Select

from pdb_processor.core.config import Config
from pdb_processor.utils.pdb_utils import normalize_pdb_id, parse_chain_ids

logger = logging.getLogger(__name__)


class ChainSelect(Select):
    """用于选择特定链的 Select 类"""
    
    def __init__(self, chain_ids: List[str]):
        self.chain_ids = set(chain_ids)
    
    def accept_chain(self, chain):
        return chain.id in self.chain_ids


@dataclass
class SplitResult:
    """拆分结果"""
    
    pdb_id: str
    success: bool
    antigen_path: Optional[Path] = None
    antibody_path: Optional[Path] = None
    error: Optional[str] = None
    
    # 验证信息
    antigen_chains: List[str] = None
    antibody_chains: List[str] = None
    antigen_residues: int = 0
    antibody_residues: int = 0


class StructureSplitter:
    """结构拆分器"""
    
    def __init__(self, config: Config):
        self.config = config
        self.parser = PDBParser(QUIET=True)
        self.io = PDBIO()
    
    def get_chain_info(self, pdb_file: Path) -> Dict[str, int]:
        """获取 PDB 文件中的链信息"""
        structure = self.parser.get_structure("struct", str(pdb_file))
        chain_info = {}
        
        for model in structure:
            for chain in model:
                residue_count = sum(1 for r in chain.get_residues())
                chain_info[chain.id] = residue_count
        
        return chain_info
    
    def split_structure(
        self,
        pdb_file: Path,
        antigen_chains: str,
        antibody_chains: str,
        pdb_id: str,
        suffix: str = "",
    ) -> SplitResult:
        """
        拆分 PDB 结构为抗原和抗体
        
        Args:
            pdb_file: PDB 文件路径
            antigen_chains: 抗原链 ID（逗号分隔）
            antibody_chains: 抗体链 ID（逗号分隔）
            pdb_id: PDB ID
            suffix: 文件名后缀（用于区分同一 PDB 的不同条目）
        
        Returns:
            SplitResult 对象
        """
        pdb_id = normalize_pdb_id(pdb_id)
        
        # 解析链 ID
        ag_chains = parse_chain_ids(antigen_chains)
        ab_chains = parse_chain_ids(antibody_chains)
        
        if not ag_chains or not ab_chains:
            return SplitResult(
                pdb_id=pdb_id,
                success=False,
                error="Missing chain IDs",
                antigen_chains=ag_chains,
                antibody_chains=ab_chains,
            )
        
        try:
            structure = self.parser.get_structure(pdb_id, str(pdb_file))
        except Exception as e:
            return SplitResult(
                pdb_id=pdb_id,
                success=False,
                error=f"Parse error: {e}",
            )
        
        # 验证链存在性
        available_chains = set()
        for model in structure:
            for chain in model:
                available_chains.add(chain.id)
        
        missing_ag = set(ag_chains) - available_chains
        missing_ab = set(ab_chains) - available_chains
        
        if missing_ag or missing_ab:
            return SplitResult(
                pdb_id=pdb_id,
                success=False,
                error=f"Missing chains: ag={missing_ag}, ab={missing_ab}",
                antigen_chains=ag_chains,
                antibody_chains=ab_chains,
            )
        
        # 确保输出目录存在
        self.config.antigens_dir.mkdir(parents=True, exist_ok=True)
        self.config.antibodies_dir.mkdir(parents=True, exist_ok=True)
        
        # 保存抗原结构
        antigen_path = self.config.get_antigen_path(pdb_id, suffix)
        self.io.set_structure(structure)
        self.io.save(str(antigen_path), ChainSelect(ag_chains))
        
        # 保存抗体结构
        antibody_path = self.config.get_antibody_path(pdb_id, suffix)
        self.io.save(str(antibody_path), ChainSelect(ab_chains))
        
        # 统计残基数
        ag_residues = sum(
            sum(1 for _ in chain.get_residues())
            for model in structure for chain in model if chain.id in ag_chains
        )
        ab_residues = sum(
            sum(1 for _ in chain.get_residues())
            for model in structure for chain in model if chain.id in ab_chains
        )
        
        logger.info(f"Split {pdb_id}: antigen={ag_chains}, antibody={ab_chains}")
        
        return SplitResult(
            pdb_id=pdb_id,
            success=True,
            antigen_path=antigen_path,
            antibody_path=antibody_path,
            antigen_chains=ag_chains,
            antibody_chains=ab_chains,
            antigen_residues=ag_residues,
            antibody_residues=ab_residues,
        )

