# 语料驱动词汇

方法借自 CAKE §2.1（Bottom-up IR evolution）：IR 词汇不自顶向下设计，从生产内核语料中提取反复出现的调度模式而来。每个词汇版本发布前执行一次本文流程，产出证据表。

## 流程

1. **种子语料**（Vector 通路，全部固定到 commit）：
   - asc-devkit `examples/02_simd_c_api`（官方 C API 例子）
   - cann-samples 中的 Ascend C vector 算子
   - ops-* 仓中的 vector kernel
   - cannbot-knowledge runbook 中的代码片段
   - cannbot-dsl samples（如 rms_norm；DSL 所写，只作调度模式参考）
2. **提取**：对每个 kernel 记录其调度模式——搬运方向序列、buffer 数量与 stages 深度、sync 配对结构、循环结构、计算 op 家族。
3. **准入**：每个词汇构造必须映射到语料中的反复出现，证据表给出计数与代表文件（固定 commit 链接）。没有语料证据的构造不进入词汇。
4. **回测门禁**：词汇冻结后用语料回测——无需扩展即可表达的 vector kernel 比例 ≥ 80%（提案阈值，随 PR2 评审）。表达不了的逐条记录为 gap，进入下一版本候选。
5. **副产物**：M4 的合法金样本从语料改写，不手写；gap 列表是检查器新规则与 IR 新构造的共同候选池。

## 证据表（v0.2，2026-09-24 填写）

语料来源：asc-devkit `examples/02_simd_c_api`，固定 commit [`648a6018`](https://gitcode.com/cann/asc-devkit/tree/648a6018207d75af44c6865f96511bafadd90630)（2026-09-24 master）。cann-samples / ops-* / runbook 片段 / cannbot-dsl samples 待补，补齐后重算表达力比例。

| 构造 | 语料出现 | 代表来源（固定 commit） | 备注 |
|---|---|---|---|
| `ubuf(..., stages=2)` 双缓冲 | 1 族 | [c_api_add.asc](https://gitcode.com/cann/asc-devkit/blob/648a6018207d75af44c6865f96511bafadd90630/examples/02_simd_c_api/00_introduction/01_add/c_api_delicacy_async_add/c_api_add.asc) | 流水循环内双缓冲 |
| `mte2.copy`（gm→ubuf） | 5 族 | 同上 add；[reduce](https://gitcode.com/cann/asc-devkit/blob/648a6018207d75af44c6865f96511bafadd90630/examples/02_simd_c_api/03_c_api/01_memory_vector_compute/reduce/reduce.asc)、[fused_compute](https://gitcode.com/cann/asc-devkit/blob/648a6018207d75af44c6865f96511bafadd90630/examples/02_simd_c_api/03_c_api/01_memory_vector_compute/fused_compute/fused_compute.asc)、cast、compare | 对应 `asc_copy_gm2ub` / `asc_copy_gm2ub_align` |
| `mte3.copy`（ubuf→gm） | 5 族 | 同上 | 对应 `asc_copy_ub2gm` / `asc_copy_ub2gm_align` |
| `v.add` | 1 族 | add | `asc_add` |
| `v.cast` | 1 族 | [cast](https://gitcode.com/cann/asc-devkit/tree/648a6018207d75af44c6865f96511bafadd90630/examples/02_simd_c_api/03_c_api/01_memory_vector_compute/cast) | `asc_half2int4` / `asc_half2int32`；README 级证据，源码待逐行核 |
| `v.leakyrelu` | 1 族 | fused_compute | `asc_leakyrelu`，含标量 alpha |
| `v.repeat_reduce_sum` / `v.datablock_reduce_sum` | 1 族 | reduce | `asc_repeat_reduce_sum` / `asc_datablock_reduce_sum` |
| `sync(mte2, v, ...)` / `sync(v, mte3, ...)` | 1 族 | add | `asc_sync_notify` + `asc_sync_wait` 配对 |
| `for i in range(TILES)` 流水循环 | 1 族 | add | 单 tile 族（reduce 等）无循环，可表达为退化形态 |

## Gap 记录（v0.2，2026-09-24 填写）

| 语料中反复出现的模式 | 出现次数 | 当前无法表达的原因 | 候选版本 |
|---|---|---|---|
| Reg 矢量通路（reg_load_gather / reg_load_store_align / reg_load_store_mask） | 3 族 | 无 Reg 角色与寄存器 load/store 词汇 | v0.3 候选 |
| Cube 通路（data_copy_gm2l1、data_copy_l0c2gm/l1/ub、data_copy_ub2l1、03_matrix_compute） | ≥ 6 族 | 无 `cbuf`/L0 地址空间与 `m`/`fix` PIPE | W2 需要，下一版 |
| compare 的 mask 语义（`asc_get_cmp_mask`） | 1 族 | mask 值模型未定义 | 待更多语料证据 |

## 表达力回测（v0.2）

- Memory 矢量语料族：add、reduce、fused_compute、cast、compare，共 5 族。
- 无需扩展可表达：4 族（compare 记 gap）。
- 比例：4/5 = 80%，压线达标。语料目前只覆盖 asc-devkit，扩充后必须重算；若低于 80%，按 gap 优先级补词汇而不是放宽门禁。
