"""Configuration management for PDB Processor"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class Config:
    """PDB Processor 配置类"""
    
    # 基础目录配置
    base_dir: str = "downloads"
    
    # 下载配置
    DOWNLOAD_TIMEOUT: int = 60
    MAX_RETRIES: int = 3
    RETRY_DELAY: float = 2.0
    PDB_BASE_URL: str = "https://files.rcsb.org/download/"
    
    # 预处理配置
    REMOVE_HETERO: bool = True
    REMOVE_WATER: bool = True
    KEEP_HYDROGEN: bool = False
    
    # 并行处理配置
    MAX_THREADS: int = 4
    
    # 日志配置
    LOG_LEVEL: int = logging.INFO
    
    # 内部路径（自动生成）
    _paths_initialized: bool = field(default=False, repr=False)
    
    def __post_init__(self):
        self._init_paths()
        self._init_logging()
    
    def _init_paths(self):
        """初始化目录结构"""
        base = Path(self.base_dir)
        
        # 主要目录
        self.raw_pdbs_dir = base / "raw_pdbs"
        self.processed_dir = base / "processed"
        self.antigens_dir = self.processed_dir / "antigens"
        self.antibodies_dir = self.processed_dir / "antibodies"
        self.quality_reports_dir = self.processed_dir / "quality_reports"
        self.logs_dir = base / "logs"
        self.sabdab_dir = base / "sabdab"
        self.statistics_dir = base / "statistics"
        
        self._paths_initialized = True
    
    def _init_logging(self):
        """初始化日志配置"""
        logging.basicConfig(
            level=self.LOG_LEVEL,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
    
    def ensure_directories(self):
        """创建所有必要的目录"""
        directories = [
            self.raw_pdbs_dir,
            self.antigens_dir,
            self.antibodies_dir,
            self.quality_reports_dir,
            self.logs_dir,
            self.sabdab_dir,
            self.statistics_dir,
        ]
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    def get_pdb_path(self, pdb_id: str) -> Path:
        """获取原始 PDB 文件路径"""
        return self.raw_pdbs_dir / f"{pdb_id.upper()}.pdb"
    
    def get_antigen_path(self, pdb_id: str, suffix: str = "") -> Path:
        """获取抗原文件路径"""
        name = f"{pdb_id.upper()}{suffix}_antigen.pdb"
        return self.antigens_dir / name
    
    def get_antibody_path(self, pdb_id: str, suffix: str = "") -> Path:
        """获取抗体文件路径"""
        name = f"{pdb_id.upper()}{suffix}_antibody.pdb"
        return self.antibodies_dir / name

