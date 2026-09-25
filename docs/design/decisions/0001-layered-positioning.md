# 0001 分层定位：独立仓，前期直写，后期作 CANNBot-DSL 降级目标

状态：已确认（2026-09-24）

## 背景

CANNBot 仓群已有 CANNBot-DSL（`cannbotdsl`，Python 嵌入式，托管 `Channel` 抽象，同步隐式），目标 3510。AscendC-IR 立项时需要回答：新仓还是并入，与 CANNBot-DSL 什么关系。

## 选项

1. 分层：独立建仓，定位显式 schedule 层，后期 CANNBot-DSL 以它为降级目标。
2. 并行：两个独立 DSL 都降到 C API，对照竞争。
3. 并入：作为 cannbot-dsl 仓内的 IR/验证层。

## 决定

选项 1。理由：CANNBot-DSL 的 Channel 把同步藏起来，不适合「agent 显式控制交接」的实验；独立建仓让检查器和诊断 ID 成为一等公民，不被 Python DSL 的发布节奏绑住；cannbot-dsl 当时只开源了 samples，并入依赖未完全开放的代码库。

## 后果

- 本仓代码生成只产调用 C API 的 `.asc`，不依赖 AscendNPU-IR（竞品）。
- 与 CANNBot-DSL 共用检查器是后期目标，当前不保证两边词汇一致。

## 推翻条件

- CANNBot-DSL 完全开源且暴露出显式同步/验证能力，本层变冗余。
- C1 实验证明 agent 在显式 schedule 上不比托管抽象做得更好。
