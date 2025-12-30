"""CLI command implementations"""

from typing import Optional

from pdb_processor.core.config import Config
from pdb_processor.core.downloader import PDBDownloader
from pdb_processor.core.splitter import StructureSplitter
from pdb_processor.sabdab.processor import SAbDabProcessor


def cmd_sabdab(
    tsv_file: str,
    output_dir: str,
    incremental: bool,
    threads: int,
    limit: Optional[int],
):
    """处理 SAbDab 数据库"""
    config = Config(base_dir=output_dir)
    processor = SAbDabProcessor(config)
    
    print(f"处理 SAbDab 文件: {tsv_file}")
    print(f"输出目录: {output_dir}")
    print(f"增量模式: {incremental}")
    print(f"线程数: {threads}")
    if limit:
        print(f"限制数量: {limit}")
    print("-" * 50)
    
    stats = processor.process_sabdab(
        tsv_path=tsv_file,
        incremental=incremental,
        max_threads=threads,
        limit=limit,
    )
    
    print("\n" + "=" * 50)
    print("处理完成！统计信息：")
    print(f"  总条目数: {stats.total_entries}")
    print(f"  有效条目: {stats.valid_entries}")
    print(f"  跳过(已存在): {stats.skipped_existing}")
    print(f"  新下载: {stats.downloaded}")
    print(f"  下载失败: {stats.download_failed}")
    print(f"  拆分成功: {stats.split_success}")
    print(f"  拆分失败: {stats.split_failed}")
    print("=" * 50)


def cmd_process(
    pdb_id: str,
    antigen_chains: str,
    antibody_chains: str,
    output_dir: str,
    force: bool,
):
    """处理单个 PDB"""
    config = Config(base_dir=output_dir)
    config.ensure_directories()
    
    downloader = PDBDownloader(config)
    splitter = StructureSplitter(config)
    
    print(f"处理 PDB: {pdb_id}")
    print(f"抗原链: {antigen_chains}")
    print(f"抗体链: {antibody_chains}")
    print("-" * 50)
    
    # 下载
    download_result = downloader.download(pdb_id, force=force)
    if not download_result.success:
        print(f"下载失败: {download_result.error}")
        return
    
    if download_result.skipped:
        print(f"跳过下载（已存在）: {download_result.path}")
    else:
        print(f"下载完成: {download_result.path}")
    
    # 拆分
    split_result = splitter.split_structure(
        pdb_file=download_result.path,
        antigen_chains=antigen_chains,
        antibody_chains=antibody_chains,
        pdb_id=pdb_id,
    )
    
    if split_result.success:
        print(f"抗原结构: {split_result.antigen_path}")
        print(f"  链: {split_result.antigen_chains}")
        print(f"  残基数: {split_result.antigen_residues}")
        print(f"抗体结构: {split_result.antibody_path}")
        print(f"  链: {split_result.antibody_chains}")
        print(f"  残基数: {split_result.antibody_residues}")
    else:
        print(f"拆分失败: {split_result.error}")


def cmd_info(pdb_id: str, output_dir: str):
    """查看 PDB 链信息"""
    config = Config(base_dir=output_dir)
    config.ensure_directories()

    downloader = PDBDownloader(config)
    splitter = StructureSplitter(config)

    # 确保 PDB 已下载
    download_result = downloader.download(pdb_id)
    if not download_result.success:
        print(f"下载失败: {download_result.error}")
        return

    # 获取链信息
    chain_info = splitter.get_chain_info(download_result.path)

    print(f"\nPDB {pdb_id.upper()} 链信息:")
    print("-" * 40)
    for chain_id, residue_count in sorted(chain_info.items()):
        print(f"  Chain {chain_id}: {residue_count} residues")
    print("-" * 40)

