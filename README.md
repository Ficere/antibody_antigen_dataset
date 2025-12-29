# 抗体-抗原对接基准数据集

## 📋 数据集概述

本仓库包含 **112 个抗体-抗原对接测试案例**，提供结合态（bound）和非结合态（unbound）结构，存储在 `ABAG-Docking_benchmark_dataset` 文件夹中。用户可以下载该数据集来测试和评估其预测算法的性能。

## 📁 数据集结构

### 主要文件夹

```
ABAG-Docking_benchmark_dataset/
├── 87cases/                      # 87 个标准测试案例
├── 25cases_Truncated_file/       # 25 个特殊案例（截断版本）
└── 25cases_Not_truncated_file/   # 25 个特殊案例（完整版本）
```

### 文件命名规则

每个测试案例文件夹包含 **4 个 PDB 文件**，命名规则如下：

| 文件名 | 说明 |
|--------|------|
| `PDBID_r_b.pdb` | **结合态抗体结构** (Bound Antibody) |
| `PDBID_l_b.pdb` | **结合态抗原结构** (Bound Antigen) |
| `PDBID_r_u.pdb` | **非结合态抗体结构** (Unbound Antibody) |
| `PDBID_l_u.pdb` | **非结合态抗原结构** (Unbound Antigen) |

> **命名说明**：
> - `r` = receptor（受体，此处指抗体）
> - `l` = ligand（配体，此处指抗原）
> - `b` = bound（结合态）
> - `u` = unbound（非结合态）

## 🔬 核心概念：Bound vs Unbound

### 什么是结合态（Bound）？

**结合态结构**是指抗体和抗原**已经形成复合物**时的蛋白质结构。

- **来源**：从同一个抗体-抗原复合物的 PDB 结构中提取
- **特点**：
  - 抗体和抗原处于相互结合的构象
  - 结合界面区域可能发生了构象变化（诱导契合）
  - 代表了"最终结合状态"的真实结构
- **用途**：作为对接预测的**参考答案**（ground truth）

### 什么是非结合态（Unbound）？

**非结合态结构**是指抗体或抗原**单独存在、未与对方结合**时的蛋白质结构。

- **来源**：从其他可以与目标复合物结构比对的独立 PDB 结构中提取
- **特点**：
  - 蛋白质处于自由状态的构象
  - 可能与结合态存在构象差异
  - 更接近实际对接预测的**起始状态**
- **用途**：作为对接算法的**输入结构**

### 为什么需要区分 Bound 和 Unbound？

在真实的药物设计和蛋白质对接场景中：

1. **实际情况**：我们通常只能获得抗体或抗原的单独结构（unbound），而不知道它们结合后的样子
2. **算法挑战**：对接算法需要从非结合态结构预测出结合态的复合物结构
3. **评估标准**：使用 unbound 结构作为输入，用 bound 结构作为评估标准，可以更真实地测试算法性能

### 示例说明

以 `6OEJ` 案例为例：

```
6OEJ_r_b.pdb  ←─┐
                ├─ 来自同一个复合物 PDB: 6OEJ
6OEJ_l_b.pdb  ←─┘

6OEJ_r_u.pdb  ← 来自独立的抗体结构 PDB: 4FZ8
6OEJ_l_u.pdb  ← 来自独立的抗原结构 PDB: 3TGT
```

**重要**：所有结构已经过**预对齐处理**，方便可视化和比较构象变化。

## 📊 特殊案例说明

在 112 个测试案例中，有 **25 个特殊案例**需要注意：

### 问题描述

这 25 个案例中，**抗原的非结合态结构**（`*_l_u.pdb`）的氨基酸序列**比结合态更长**。

### 解决方案

为这 25 个案例提供了**两个版本**：

| 版本 | 文件夹 | 说明 |
|------|--------|------|
| **截断版本** | `25cases_Truncated_file/` | 将非结合态抗原截断至与结合态相同长度 |
| **完整版本** | `25cases_Not_truncated_file/` | 保留非结合态抗原的完整序列 |

### 使用建议

- **推荐使用截断版本**：适合大多数对接算法，避免额外序列干扰
- **完整版本**：适合研究序列长度差异对对接的影响

### 涉及的 25 个案例

```
6P50, 6PZ8, 6XC2, 6YIO, 6YLA, 6ZDG_1, 6ZDG_2, 6ZER, 6ZFO, 6ZLR,
7A5S_1, 7A5S_2, 7C01, 7JVA, 7KFW, 7NP1, 7S0E, 7SOC, 7SWN, 7VNG,
7VYR, 7WRV, 7X7O, 7ZF9, 8GZ5
```

## 📝 数据集清单

完整的 PDB ID 列表请参见：`ABAG-Docking_benchmark_dataset_PDBID.txt`

**总计**：112 个测试案例
- 87 个标准案例（位于 `87cases/` 文件夹）
- 25 个特殊案例（同时提供截断和完整版本）

## 🚀 使用方法

### 1. 下载数据集

```bash
git clone https://github.com/Ficere/Antibody-antigen-complex-structure-benchmark-dataset
cd Antibody-antigen-complex-structure-benchmark-dataset
```

### 2. 选择测试案例

- **标准案例**：直接使用 `87cases/` 中的数据
- **特殊案例**：根据需求选择 `25cases_Truncated_file/` 或 `25cases_Not_truncated_file/`

### 3. 运行对接算法

```python
# 伪代码示例
antibody_unbound = load_pdb("PDBID_r_u.pdb")  # 输入：非结合态抗体
antigen_unbound = load_pdb("PDBID_l_u.pdb")   # 输入：非结合态抗原

predicted_complex = docking_algorithm(antibody_unbound, antigen_unbound)

# 评估预测结果
antibody_bound = load_pdb("PDBID_r_b.pdb")    # 参考：结合态抗体
antigen_bound = load_pdb("PDBID_l_b.pdb")     # 参考：结合态抗原
rmsd = calculate_rmsd(predicted_complex, (antibody_bound, antigen_bound))
```

## 📖 引用

如果您在研究中使用了本数据集，请引用相关论文。

## 📧 联系方式

如有问题或建议，请通过 GitHub Issues 联系我们。

---

**最后更新**：2025-12-29

