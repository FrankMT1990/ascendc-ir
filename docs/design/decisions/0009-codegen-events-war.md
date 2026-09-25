# 0009 代码生成：event 通道、WAR 推导、fail-closed

状态：已确认（2026-09-25，随 PR4）

## 背景

codegen 把 Kernel 模型降到调用 C API 的 `.asc`。三个关键决策点：event 怎么分、WAR 释放边谁写、未核对的 C API 映射怎么办。

## 决定

1. **event 分配**：~~每逻辑通道一个 `EVENT_ID`~~（已由 ADR 0010 修订：event id 按 PIPE 对独立分配，WAR 通道按槽位分配连续 id 块）。通道总数超 `event_ids` 则拒绝生成。同通道跨迭代复用同一 event（生产/消费双方各自按程序顺序配对）。
2. **WAR 释放边由 stages 推导**（ADR 0003 的 A 级）：`stages=N` 的 buffer，复用槽位前生成 `if (i >= N) wait(消费PIPE, 生产PIPE)`，消费完成后生成 `if (i + N < TILES) notify(...)`。agent 不写释放边。
3. **fail-closed 映射**：计算 op 只放行已核对头文件签名的 C API 映射（v0.2 只有 `asc_add`）；其余 op（cast/leakyrelu/reduce 系）trace/verify 可用，codegen 拒绝并列出支持集。
4. **重卷失败拒绝生成**：trace 展开的语句不满足仿射规律时抛 `CodegenError`，不展开生成（展开会丢 stage 下标和 WAR，产生错码）。
5. **单核**：v0.2 不生成 `asc_get_block_idx` 多核切分（语料 gap，未排期）。M0 的手写对照同为单核。

## 后果

- 生成代码与手写对照的差异只允许在 event 编号等价类内（M0 配对前提）。
- 新增计算 op 的 codegen 支持 = 核对头文件签名 + golden 用例，两步缺一不可。

## 推翻条件

- 真实内核出现通道数 > 8 的合法 schedule（需 event 复用策略，而非简单拒绝）。
- WAR 推导被证明在某类流水结构下过度保守或错误（需语料证据）。
