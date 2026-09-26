# 设计决策记录（ADR）

每份 ADR 记录一个已确认的决定：背景、选项、决定、后果、推翻条件。评审 agent 的重点是「推翻条件」——当列出的证据出现时，该决定应该被重新评审而不是被绕过。

| 编号 | 决定 | 日期 |
|---|---|---|
| [0001](0001-layered-positioning.md) | 分层定位：独立仓，前期 Agent 直写，后期作 CANNBot-DSL 降级目标 | 2026-09-24 |
| [0002](0002-embedded-ir.md) | Python 嵌入式 IR，无自写 parser | 2026-09-24 |
| [0003](0003-sync-abstraction.md) | 同步原语命名 `sync`，A 级抽象起步 | 2026-09-24 |
| [0004](0004-corpus-driven-vocabulary.md) | 词汇语料驱动（CAKE §2.1） | 2026-09-24 |
| [0005](0005-evaluation-over-cost-model.md) | 不做代价模型，有效性靠 CANNBench 实测 | 2026-09-24 |
| [0006](0006-callsite-diagnostics.md) | 诊断按调用点定位，结构化 JSON | 2026-09-24 |
| [0007](0007-trace-lenient-verify-strict.md) | trace 期宽松、verify 期严格的职责划分 | 2026-09-25 |
| [0008](0008-v009-cross-pipe-read.md) | 新增 V009：跨 PIPE 读取必须先经 sync | 2026-09-25 |
| [0009](0009-codegen-events-war.md) | 代码生成：event 通道分配、WAR 推导、fail-closed 映射 | 2026-09-25 |
| [0010](0010-event-semantics.md) | event 语义修正：按 PIPE 对独立 + WAR 按槽位分配（修订 0009） | 2026-09-25 |
| [0011](0011-per-slot-unroll.md) | 循环按槽位展开：event id 全字面量；WAR 释放点在最后一次消费之后（修订 0010） | 2026-09-26 |

规则：
- ADR 一旦合入不原地改写；决定被推翻时把状态改为「已废弃/已被 XXXX 替代」并新增一份 ADR。
- 代码与 ADR 冲突时，以 ADR 为起点定位唯一事实源（spec / device 表 / 评估文档），在同一变更中修正两边。
