# 0004 词汇语料驱动（CAKE §2.1）

状态：已确认（2026-09-24）

## 背景

CAKE 的 IR 词汇不是预先设计的，而是从生产内核语料中提取反复出现的调度模式而来（§2.1 Bottom-up IR evolution）。v0.1 的词汇是自顶向下从 C API 文档拍的，评审指出这一课没学到家。

## 决定

每个词汇构造必须有语料证据：计数 + 固定 commit 链接，记入 `docs/design/vocabulary-evidence.md`。语料有而词汇无的模式记为 gap。词汇冻结后回测：无需扩展可表达的语料族比例 ≥ 80%。

## 后果

- v0.2 首填：asc-devkit `648a6018`，Memory 矢量 5 族可表达 4 族（80% 压线），gap 三项（Reg 通路、Cube 通路、compare mask）。
- 计算 op 集合 = 语料实际出现的五个（add/cast/leakyrelu/repeat_reduce_sum/datablock_reduce_sum）。
- M4 合法金样本从语料改写，不手写。

## 推翻条件

- 语料扩充后表达力跌破 80% 且 gap 无法收敛——说明提取方法或抽象层级有问题，回到 ADR 0001/0003 复审。
