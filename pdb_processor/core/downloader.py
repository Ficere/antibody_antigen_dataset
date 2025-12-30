"""PDB file downloader with incremental download support"""

import logging
import time
from pathlib import Path
from typing import List, Optional, Set, Tuple

import requests
from Bio.PDB import MMCIFParser, PDBIO

from pdb_processor.core.config import Config
from pdb_processor.utils.pdb_utils import get_existing_pdb_ids, normalize_pdb_id

logger = logging.getLogger(__name__)

CIF_BASE_URL = "https://files.rcsb.org/download/"


class DownloadResult:
    """下载结果"""
    
    def __init__(self, pdb_id: str, success: bool, path: Optional[Path] = None,
                 error: Optional[str] = None, skipped: bool = False):
        self.pdb_id = pdb_id
        self.success = success
        self.path = path
        self.error = error
        self.skipped = skipped


class PDBDownloader:
    """PDB 文件下载器，支持增量下载"""
    
    def __init__(self, config: Config):
        self.config = config
        self._existing_ids: Optional[Set[str]] = None
    
    @property
    def existing_pdb_ids(self) -> Set[str]:
        """获取已存在的 PDB ID 集合（懒加载）"""
        if self._existing_ids is None:
            self._existing_ids = get_existing_pdb_ids(self.config.raw_pdbs_dir)
        return self._existing_ids
    
    def refresh_existing_ids(self):
        """刷新已存在的 PDB ID 缓存"""
        self._existing_ids = None
    
    def is_downloaded(self, pdb_id: str) -> bool:
        """检查 PDB 是否已下载（大小写不敏感）"""
        return normalize_pdb_id(pdb_id) in self.existing_pdb_ids
    
    def download(self, pdb_id: str, force: bool = False) -> DownloadResult:
        """
        下载单个 PDB 文件
        
        Args:
            pdb_id: PDB ID
            force: 是否强制重新下载
        
        Returns:
            DownloadResult 对象
        """
        pdb_id = normalize_pdb_id(pdb_id)
        output_path = self.config.get_pdb_path(pdb_id)
        
        # 检查是否已存在
        if not force and self.is_downloaded(pdb_id):
            logger.debug(f"Skipping {pdb_id}: already exists")
            return DownloadResult(pdb_id, True, output_path, skipped=True)
        
        # 确保目录存在
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 尝试下载 PDB 格式
        result = self._try_download_pdb(pdb_id, output_path)
        if result:
            return result

        # PDB 格式失败，尝试 CIF 格式并转换
        result = self._try_download_cif(pdb_id, output_path)
        if result:
            return result

        error_msg = f"Failed after {self.config.MAX_RETRIES} attempts (PDB and CIF)"
        logger.error(f"Download failed: {pdb_id} - {error_msg}")
        return DownloadResult(pdb_id, False, error=error_msg)

    def _try_download_pdb(self, pdb_id: str, output_path: Path) -> Optional[DownloadResult]:
        """尝试下载 PDB 格式"""
        url = f"{self.config.PDB_BASE_URL}{pdb_id}.pdb"

        for attempt in range(self.config.MAX_RETRIES):
            try:
                response = requests.get(url, timeout=self.config.DOWNLOAD_TIMEOUT)
                if response.status_code == 404:
                    logger.debug(f"PDB format not available for {pdb_id}")
                    return None  # 尝试 CIF 格式
                response.raise_for_status()

                output_path.write_bytes(response.content)
                self.existing_pdb_ids.add(pdb_id)
                logger.info(f"Downloaded: {pdb_id}")
                return DownloadResult(pdb_id, True, output_path)
            except requests.RequestException as e:
                logger.warning(f"PDB download failed for {pdb_id} (attempt {attempt + 1}): {e}")
                if attempt < self.config.MAX_RETRIES - 1:
                    time.sleep(self.config.RETRY_DELAY)
        return None

    def _try_download_cif(self, pdb_id: str, output_path: Path) -> Optional[DownloadResult]:
        """尝试下载 CIF 格式并转换为 PDB"""
        url = f"{CIF_BASE_URL}{pdb_id}.cif"

        for attempt in range(self.config.MAX_RETRIES):
            try:
                response = requests.get(url, timeout=self.config.DOWNLOAD_TIMEOUT)
                if response.status_code == 404:
                    return None
                response.raise_for_status()

                # 保存临时 CIF 文件
                cif_path = output_path.with_suffix(".cif")
                cif_path.write_bytes(response.content)

                # 转换 CIF 到 PDB
                if self._convert_cif_to_pdb(cif_path, output_path, pdb_id):
                    cif_path.unlink()  # 删除临时 CIF 文件
                    self.existing_pdb_ids.add(pdb_id)
                    logger.info(f"Downloaded (CIF->PDB): {pdb_id}")
                    return DownloadResult(pdb_id, True, output_path)
                else:
                    cif_path.unlink(missing_ok=True)
                    return None
            except requests.RequestException as e:
                logger.warning(f"CIF download failed for {pdb_id} (attempt {attempt + 1}): {e}")
                if attempt < self.config.MAX_RETRIES - 1:
                    time.sleep(self.config.RETRY_DELAY)
        return None

    def _convert_cif_to_pdb(self, cif_path: Path, pdb_path: Path, pdb_id: str) -> bool:
        """将 CIF 文件转换为 PDB 格式"""
        try:
            parser = MMCIFParser(QUIET=True)
            structure = parser.get_structure(pdb_id, str(cif_path))

            io = PDBIO()
            io.set_structure(structure)
            io.save(str(pdb_path))
            return True
        except Exception as e:
            logger.warning(f"CIF to PDB conversion failed for {pdb_id}: {e}")
            return False
    
    def download_batch(
        self,
        pdb_ids: List[str],
        force: bool = False,
    ) -> List[DownloadResult]:
        """批量下载 PDB 文件（顺序下载）"""
        results = []
        for pdb_id in pdb_ids:
            result = self.download(pdb_id, force)
            results.append(result)
        return results
    
    def get_download_stats(
        self, results: List[DownloadResult]
    ) -> Tuple[int, int, int]:
        """获取下载统计: (成功数, 跳过数, 失败数)"""
        success = sum(1 for r in results if r.success and not r.skipped)
        skipped = sum(1 for r in results if r.skipped)
        failed = sum(1 for r in results if not r.success)
        return success, skipped, failed

