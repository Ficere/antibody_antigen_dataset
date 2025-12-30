# PDB Processor

从 RCSB PDB 下载抗体-抗原复合物结构，并按链 ID 拆分为独立的抗原和抗体文件。支持 SAbDab 数据库批量处理。

## 功能

- 增量下载 PDB 文件（跳过已存在的）
- 解析 SAbDab TSV 文件，批量处理
- 按链 ID 拆分抗原/抗体结构
- 并行处理，生成统计报告

## 使用

使用 `uv run` 运行命令，依赖会自动安装。

### 批量处理 SAbDab

```bash
# 增量处理
uv run pdb-processor sabdab sabdab_summary_all.tsv

# 并行处理
uv run pdb-processor sabdab sabdab_summary_all.tsv --threads 4

# 测试（限制数量）
uv run pdb-processor sabdab sabdab_summary_all.tsv --limit 10
```

参数：
- `--output, -o`: 输出目录（默认: downloads）
- `--threads, -t`: 并行线程数（默认: 1）
- `--limit, -l`: 限制处理数量
- `--no-incremental`: 禁用增量模式

### 处理单个 PDB

```bash
uv run pdb-processor process 6OEJ --antigen A --antibody H,L
```

参数：
- `--antigen, -a`: 抗原链 ID
- `--antibody, -b`: 抗体链 ID
- `--force, -f`: 强制重新下载

### 重试失败条目

```bash
# 重试所有失败条目
uv run pdb-processor retry

# 限制重试数量
uv run pdb-processor retry --limit 100
```

### 查看链信息

```bash
uv run pdb-processor info 6OEJ
```

输出：
```
PDB 6OEJ 链信息:
----------------------------------------
  Chain A: 333 residues
  Chain H: 227 residues
  Chain L: 215 residues
----------------------------------------
```

## 输出结构

```
downloads/
├── raw_pdbs/              # 原始 PDB 文件
├── processed/
│   ├── antigens/          # 抗原结构
│   └── antibodies/        # 抗体结构
├── sabdab/
│   └── failed_entries.json
└── statistics/
    └── processing_summary.json
```

## SAbDab 格式

系统解析 `sabdab_summary_all.tsv` 中的以下字段：

| 字段 | 说明 |
|------|------|
| `pdb` | PDB ID |
| `Hchain` | 重链 ID |
| `Lchain` | 轻链 ID |
| `antigen_chain` | 抗原链 ID（支持 `A \| B` 格式） |

PDB ID 大小写不敏感，统一转为大写处理。

## 处理效果统计

基于 SAbDab 完整数据集的处理结果：

| 指标 | 数量 | 百分比 |
|------|------|--------|
| 总条目数 | 1819 | 100% |
| 成功处理 | 1457 | 80.1% |
| 处理失败 | 362 | 19.9% |

### 失败原因分析

| 错误类型 | 数量 | 占失败比例 |
|----------|------|-----------|
| 下载失败 (PDB/CIF 都不可用) | 301 | 83.1% |
| 解析错误 (残基编号格式) | 37 | 10.2% |
| 链 ID 不存在 | 24 | 6.6% |

**说明**：大部分失败是由于 RCSB PDB 服务器上文件不可用，属于不可修复的外部限制。

## 注意事项

- PDB ID 必须是 4 个字符
- 多个链用逗号分隔：`H,L`
- 需要网络访问 https://files.rcsb.org
- 部分 PDB 使用多字符链 ID，无法转换为标准 PDB 格式

