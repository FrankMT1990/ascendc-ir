# 分层定位与已确认决定

本文记录 AscendC-IR 在 CANNBot 仓群中的定位，以及评审中已确认的决定。决定变更必须改本文并在 CHANGELOG 记录。

## 定位

AscendC-IR 是显式物理 schedule 层，独立于现有各编程层：

```text
PyPTO（tile 级）
CANNBot-DSL（托管 buffer / Channel 抽象，同步隐式）
AscendC-IR（显式角色 / PIPE / 交接边，编译前验证）   ← 本仓
Ascend C C++ API（TPipe / TQue / Tensor API）
Ascend C C API（指针级，asc_* 指令接口）           ← 代码生成目标
```

- **前期**：Agent 直接编写嵌入式 IR（Python，`@kernel`），工具链 trace、验证并生成 `.asc`。
- **后期**：CANNBot-DSL 以本仓为降级目标，两层共用同一检查器。
- 本仓不依赖、不复用 AscendNPU-IR；硬件事实以 asc-devkit C API 头文件与 cannbot-knowledge 治理知识为准。

## 为什么这一层是空的

CANNBot-DSL 的 `Channel(depth=N)` 把交接和同步藏起来，服务「快速生成正确算子」；C API 把 event、stride、同步全部留给调用方。两者之间缺一层：Agent 能显式表达 warp 级以外的硬件调度（AIC/AIV 角色、PIPE、交接边），同时编译器能在上板前拒绝非法 schedule 并指出改哪一行。AscendC-IR 占这一层。

## 已确认决定（2026-09-24）

| 决定 | 结论 |
|---|---|
| 仓定位 | 独立建仓；前期 Agent 直写，后期作为 CANNBot-DSL 降级目标 |
| IR 形态 | Python 嵌入式（`@kernel` + trace），无自写 parser；trace 产物序列化为 canonical JSON 供审计 |
| 同步原语 | 命名 `sync`，对应 C API 的 `asc_sync_notify` + `asc_sync_wait` 配对 |
| 交接抽象级别 | A 级：event 分配与 WAR 释放边由编译器推导；出现语料证据再升级 |
| 词汇方法 | 语料驱动（CAKE §2.1）：构造须有生产内核语料证据，回测门禁 ≥ 80%，见 docs/design/vocabulary-evidence.md |
| 工具链语言 | Python，包名 `ascendc_ir` |
| 代码生成目标 | 只产调用 C API 的 `.asc`；不生成带内部自动同步的计算接口 |
| 设备规格 | 数据文件（TOML），3510 先行；IR 文本不分代际语法 |
| 主评估设备 | Ascend 950（npu_arch_3510）做 C1；2201 只做 M0 可移植检查 |
| 评估口径 | CANNBench kernel-only；负载与基线取自 cann-bench tasks |
| 有效性主张 | C1–C5 分开判定，见 docs/evaluation/claims.md |

## 路线图

1. PR1：仓骨架 + 规范冻结（本文、语法、检查器规则、设备表、评估）。
2. PR2：trace/model + 语料证据表（docs/design/vocabulary-evidence.md）+ 测试。
3. PR3：verifier 首批规则 + M4/M5 注入集（不需要设备）。
4. PR4：codegen + examples/vector_add（golden + 手写对照）。
5. PR5：cann_bench 打包（`pack/`）+ M0 配对执行包，在 CANNBench 环境跑通后接 C1 agent 实验。
