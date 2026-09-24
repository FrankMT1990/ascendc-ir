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

## 证据表（PR2 填写）

| 构造 | 语料出现次数 | 代表来源（固定 commit） | 备注 |
|---|---|---|---|
| `ubuf(..., stages=2)` 双缓冲 | 待填 | 待填 | |
| `mte2.copy` gm→ubuf | 待填 | 待填 | |
| `mte3.copy` ubuf→gm | 待填 | 待填 | |
| `v.add` | 待填 | 待填 | |
| `sync(mte2, v, ...)` | 待填 | 待填 | |
| `sync(v, mte3, ...)` | 待填 | 待填 | |
| `for i in range(TILES)` 流水循环 | 待填 | 待填 | |

## Gap 记录（PR2 填写）

| 语料中反复出现的模式 | 出现次数 | 当前无法表达的原因 | 候选版本 |
|---|---|---|---|
