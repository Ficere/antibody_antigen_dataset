"""CLI entry point for PDB Processor"""

import argparse
import sys

from pdb_processor.cli.commands import cmd_info, cmd_process, cmd_sabdab
from pdb_processor.cli.retry import cmd_retry


def create_parser() -> argparse.ArgumentParser:
    """创建命令行解析器"""
    parser = argparse.ArgumentParser(
        prog="pdb-processor",
        description="增量PDB数据下载和预处理系统",
    )
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # sabdab 命令
    sabdab_parser = subparsers.add_parser(
        "sabdab",
        help="处理 SAbDab 数据库",
    )
    sabdab_parser.add_argument(
        "tsv_file",
        help="SAbDab TSV 文件路径",
    )
    sabdab_parser.add_argument(
        "--output", "-o",
        default="downloads",
        help="输出目录 (默认: downloads)",
    )
    sabdab_parser.add_argument(
        "--incremental",
        action="store_true",
        default=True,
        help="增量处理，跳过已存在的 (默认: True)",
    )
    sabdab_parser.add_argument(
        "--no-incremental",
        action="store_true",
        help="禁用增量处理，重新处理所有",
    )
    sabdab_parser.add_argument(
        "--threads", "-t",
        type=int,
        default=1,
        help="并行线程数 (默认: 1)",
    )
    sabdab_parser.add_argument(
        "--limit", "-l",
        type=int,
        help="限制处理数量（用于测试）",
    )
    
    # process 命令
    process_parser = subparsers.add_parser(
        "process",
        help="处理单个 PDB",
    )
    process_parser.add_argument(
        "pdb_id",
        help="PDB ID (4字符)",
    )
    process_parser.add_argument(
        "--antigen", "-a",
        required=True,
        help="抗原链ID (如: A 或 A,B)",
    )
    process_parser.add_argument(
        "--antibody", "-b",
        required=True,
        help="抗体链ID (如: H,L)",
    )
    process_parser.add_argument(
        "--output", "-o",
        default="downloads",
        help="输出目录",
    )
    process_parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="强制重新下载",
    )
    
    # info 命令
    info_parser = subparsers.add_parser(
        "info",
        help="查看 PDB 链信息",
    )
    info_parser.add_argument(
        "pdb_id",
        help="PDB ID (4字符)",
    )
    info_parser.add_argument(
        "--output", "-o",
        default="downloads",
        help="输出目录",
    )

    # retry 命令
    retry_parser = subparsers.add_parser(
        "retry",
        help="重新处理失败的条目",
    )
    retry_parser.add_argument(
        "--output", "-o",
        default="downloads",
        help="输出目录 (默认: downloads)",
    )
    retry_parser.add_argument(
        "--limit", "-l",
        type=int,
        help="限制重试数量",
    )

    return parser


def main():
    """主入口函数"""
    parser = create_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    try:
        if args.command == "sabdab":
            incremental = not args.no_incremental
            cmd_sabdab(
                args.tsv_file,
                args.output,
                incremental,
                args.threads,
                args.limit,
            )
        elif args.command == "process":
            cmd_process(
                args.pdb_id,
                args.antigen,
                args.antibody,
                args.output,
                args.force,
            )
        elif args.command == "info":
            cmd_info(args.pdb_id, args.output)
        elif args.command == "retry":
            cmd_retry(args.output, args.limit)
    except KeyboardInterrupt:
        print("\n操作已取消")
        sys.exit(1)
    except Exception as e:
        print(f"错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

