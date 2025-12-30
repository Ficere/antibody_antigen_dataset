"""Retry failed entries command"""

import json
from typing import Optional

from tqdm import tqdm

from pdb_processor.core.config import Config
from pdb_processor.core.downloader import PDBDownloader
from pdb_processor.core.splitter import StructureSplitter


def cmd_retry(output_dir: str, limit: Optional[int]):
    """重新处理失败的条目"""
    config = Config(base_dir=output_dir)
    config.ensure_directories()

    failed_file = config.sabdab_dir / "failed_entries.json"
    if not failed_file.exists():
        print(f"未找到失败记录文件: {failed_file}")
        return

    with open(failed_file, "r") as f:
        failed_entries = json.load(f)

    if not failed_entries:
        print("没有失败的条目需要重试")
        return

    print(f"找到 {len(failed_entries)} 个失败条目")

    downloader = PDBDownloader(config)
    splitter = StructureSplitter(config)

    stats = _retry_entries(downloader, splitter, failed_entries, limit)

    # 更新失败记录
    remaining = failed_entries[limit:] if limit else []
    all_still_failed = stats["still_failed"] + remaining

    with open(failed_file, "w") as f:
        json.dump(all_still_failed, f, indent=2)

    print("\n" + "=" * 50)
    print("重试完成！")
    print(f"  成功: {stats['success']}")
    print(f"  仍失败: {stats['failed']}")
    print(f"  剩余未处理: {len(remaining)}")
    print("=" * 50)


def _retry_entries(downloader, splitter, failed_entries, limit):
    """执行重试逻辑"""
    retry_success = 0
    retry_failed = 0
    still_failed = []

    entries_to_retry = failed_entries[:limit] if limit else failed_entries

    for entry in tqdm(entries_to_retry, desc="Retrying"):
        result = _process_entry(downloader, splitter, entry)
        if result["success"]:
            retry_success += 1
        else:
            still_failed.append(result["error_entry"])
            retry_failed += 1

    return {"success": retry_success, "failed": retry_failed, "still_failed": still_failed}


def _process_entry(downloader, splitter, entry):
    """处理单个失败条目"""
    pdb_id = entry["pdb_id"]
    entry_key = entry["entry_key"]

    # 解析 entry_key: PDB_antibody_antigen
    parts = entry_key.split("_")
    if len(parts) < 3:
        return {"success": False, "error_entry": entry}

    antibody_chains = parts[1]
    antigen_chains = parts[2]

    # 转换为大写并去重
    ab_unique = list(dict.fromkeys(c.upper() for c in antibody_chains.split(",")))
    ag_unique = list(dict.fromkeys(c.upper() for c in antigen_chains.split(",")))
    antibody_chains = ",".join(ab_unique)
    antigen_chains = ",".join(ag_unique)

    # 下载
    download_result = downloader.download(pdb_id)
    if not download_result.success:
        return {
            "success": False,
            "error_entry": {"entry_key": entry_key, "pdb_id": pdb_id, "error": download_result.error},
        }

    # 拆分
    split_result = splitter.split_structure(
        pdb_file=download_result.path,
        antigen_chains=antigen_chains,
        antibody_chains=antibody_chains,
        pdb_id=pdb_id,
        suffix=antibody_chains.replace(",", ""),
    )

    if split_result.success:
        return {"success": True, "error_entry": None}
    else:
        return {
            "success": False,
            "error_entry": {"entry_key": entry_key, "pdb_id": pdb_id, "error": split_result.error},
        }

