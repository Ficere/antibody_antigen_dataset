"""SAbDab batch processor with parallel processing support"""

import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set

from tqdm import tqdm

from pdb_processor.core.config import Config
from pdb_processor.core.downloader import DownloadResult, PDBDownloader
from pdb_processor.core.splitter import SplitResult, StructureSplitter
from pdb_processor.sabdab.parser import SAbDabEntry, SAbDabParser
from pdb_processor.utils.pdb_utils import normalize_pdb_id

logger = logging.getLogger(__name__)


@dataclass
class ProcessingStats:
    """处理统计信息"""
    
    total_entries: int = 0
    valid_entries: int = 0
    skipped_existing: int = 0
    downloaded: int = 0
    download_failed: int = 0
    split_success: int = 0
    split_failed: int = 0
    start_time: str = ""
    end_time: str = ""
    duration_seconds: float = 0.0


@dataclass
class EntryResult:
    """单个条目的处理结果"""
    
    entry_key: str
    pdb_id: str
    download_success: bool
    split_success: bool
    skipped: bool = False
    error: Optional[str] = None


class SAbDabProcessor:
    """SAbDab 批量处理器"""
    
    def __init__(self, config: Config):
        self.config = config
        self.downloader = PDBDownloader(config)
        self.splitter = StructureSplitter(config)
        self.stats = ProcessingStats()
        self.failed_entries: List[Dict] = []
    
    def get_existing_entries(self) -> Set[str]:
        """获取已处理的条目键集合"""
        existing = set()
        
        # 检查已存在的抗原和抗体文件
        if self.config.antigens_dir.exists():
            for f in self.config.antigens_dir.glob("*_antigen.pdb"):
                # 从文件名提取 PDB ID
                pdb_id = f.stem.replace("_antigen", "")
                existing.add(normalize_pdb_id(pdb_id[:4]))
        
        return existing
    
    def process_entry(self, entry: SAbDabEntry) -> EntryResult:
        """处理单个 SAbDab 条目"""
        # 下载 PDB
        download_result = self.downloader.download(entry.pdb_id)
        
        if not download_result.success:
            return EntryResult(
                entry_key=entry.entry_key,
                pdb_id=entry.pdb_id,
                download_success=False,
                split_success=False,
                error=download_result.error,
            )
        
        # 拆分结构
        antigen_chains = ",".join(entry.antigen_chains)
        antibody_chains = ",".join(entry.antibody_chains)
        
        # 生成后缀用于区分同一 PDB 的不同条目
        suffix = f"_{entry.heavy_chain}"
        if entry.light_chain:
            suffix += entry.light_chain
        
        split_result = self.splitter.split_structure(
            pdb_file=download_result.path,
            antigen_chains=antigen_chains,
            antibody_chains=antibody_chains,
            pdb_id=entry.pdb_id,
            suffix=suffix,
        )
        
        return EntryResult(
            entry_key=entry.entry_key,
            pdb_id=entry.pdb_id,
            download_success=True,
            split_success=split_result.success,
            skipped=download_result.skipped,
            error=split_result.error if not split_result.success else None,
        )
    
    def process_sabdab(
        self,
        tsv_path: str,
        incremental: bool = True,
        max_threads: int = 1,
        limit: Optional[int] = None,
    ) -> ProcessingStats:
        """
        批量处理 SAbDab 数据库
        
        Args:
            tsv_path: SAbDab TSV 文件路径
            incremental: 是否增量处理（跳过已存在的）
            max_threads: 最大线程数
            limit: 限制处理数量（用于测试）
        
        Returns:
            ProcessingStats 统计信息
        """
        self.stats = ProcessingStats()
        self.stats.start_time = datetime.now().isoformat()
        self.failed_entries = []
        
        # 确保目录存在
        self.config.ensure_directories()
        
        # 解析 SAbDab 文件
        parser = SAbDabParser(tsv_path)
        entries = parser.get_valid_entries()
        
        self.stats.total_entries = len(list(parser.parse()))
        self.stats.valid_entries = len(entries)
        
        logger.info(f"Parsed {self.stats.valid_entries} valid entries")
        
        # 增量处理：获取已存在的 PDB
        existing_pdbs = set()
        if incremental:
            existing_pdbs = self.get_existing_entries()
            logger.info(f"Found {len(existing_pdbs)} existing PDB IDs")
        
        # 过滤已处理的条目
        entries_to_process = []
        for entry in entries:
            if incremental and entry.pdb_id in existing_pdbs:
                self.stats.skipped_existing += 1
            else:
                entries_to_process.append(entry)
        
        if limit:
            entries_to_process = entries_to_process[:limit]
        
        logger.info(f"Processing {len(entries_to_process)} entries")
        
        # 处理条目
        results = self._process_entries(entries_to_process, max_threads)
        
        # 统计结果
        self._compile_stats(results)
        
        self.stats.end_time = datetime.now().isoformat()
        
        # 保存报告
        self._save_reports()

        return self.stats

    def _process_entries(
        self, entries: List[SAbDabEntry], max_threads: int
    ) -> List[EntryResult]:
        """处理条目列表（支持并行）"""
        results = []

        if max_threads <= 1:
            # 顺序处理
            for entry in tqdm(entries, desc="Processing"):
                result = self.process_entry(entry)
                results.append(result)
        else:
            # 并行处理
            with ThreadPoolExecutor(max_workers=max_threads) as executor:
                futures = {
                    executor.submit(self.process_entry, e): e
                    for e in entries
                }
                for future in tqdm(
                    as_completed(futures),
                    total=len(futures),
                    desc="Processing",
                ):
                    results.append(future.result())

        return results

    def _compile_stats(self, results: List[EntryResult]):
        """编译统计信息"""
        for result in results:
            if result.download_success:
                if result.skipped:
                    pass  # 已在 skipped_existing 中计数
                else:
                    self.stats.downloaded += 1
            else:
                self.stats.download_failed += 1

            if result.split_success:
                self.stats.split_success += 1
            elif result.download_success:
                self.stats.split_failed += 1

            if result.error:
                self.failed_entries.append({
                    "entry_key": result.entry_key,
                    "pdb_id": result.pdb_id,
                    "error": result.error,
                })

    def _save_reports(self):
        """保存处理报告"""
        # 保存统计信息
        stats_path = self.config.statistics_dir / "processing_summary.json"
        stats_path.parent.mkdir(parents=True, exist_ok=True)
        with open(stats_path, "w") as f:
            json.dump(asdict(self.stats), f, indent=2)

        # 保存失败条目
        if self.failed_entries:
            failed_path = self.config.sabdab_dir / "failed_entries.json"
            with open(failed_path, "w") as f:
                json.dump(self.failed_entries, f, indent=2)

        logger.info(f"Reports saved to {self.config.statistics_dir}")

