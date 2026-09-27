# AscendC-IR

AscendC-IR 是 CANNBot 友好的显式物理 schedule 表示：Agent 用 Python 嵌入式 DSL 声明 buffer、流水线角色与 sync 边，编译器生成调用 Ascend C C API 的 `.asc` 内核，并在上板之前给出指向具体调用点的诊断。

## 分层定位

```text
CANNBot-DSL（托管 Channel 抽象，快速生成正确算子）
        │  后期：以本仓为降级目标，两层共用检查器
        ▼
AscendC-IR（显式 schedule：角色 / PIPE / 交接边，编译前验证）   ← 本仓
        │  代码生成
        ▼
Ascend C C API（c_api/asc_simd.h，asc_* 指令级接口）
```

- 前期：Agent 直接编写嵌入式 IR（Python，`@kernel`）。
- 后期：CANNBot-DSL 把本仓作为降级目标。
- 本仓不依赖、不复用 AscendNPU-IR。

## 仓群位置

| 仓 | 关系 |
|---|---|
| [asc-devkit](https://gitcode.com/cann/asc-devkit) | C API 头文件是 IR 词汇的事实源 |
| [cann-bench](https://gitcode.com/cann/cann-bench) | 有效性评估的负载、基线与计时口径来源 |
| [cannbot-dsl](https://gitcode.com/cann/cannbot-dsl) | 上层托管抽象 DSL |
| [cannbot-knowledge](https://gitcode.com/cann/cannbot-knowledge) | 检查器规则的知识来源 |
| [cannbot-skills](https://gitcode.com/cann/cannbot-skills) | Agent 接入与同步审计规则复用 |

## 状态

PR1–PR4 已合入：规范、trace/model、verifier（V001–V010）、codegen（Vector 通路，循环按槽位展开、event id 全字面量）。

**评审状态**：代码经两轮评审（2026-09-25/26，结论与逐条处置见 `docs/design/review-findings-2026-09-25.md`、`review-findings-2026-09-26.md` 及对应 response 文档）。验收协议经 grok-4.7-xhigh 对抗性评审 **25 轮、74 条挑战全部处置，已于 v2.5.18 收敛（评审明确「无更多挑战」）**；逐条处置见 `docs/design/review-response-acceptance-2026-09-26.md`。协议判词、公式与封存规则的后续修改必须重开对抗性评审，不得直接编辑。

测试：`pytest tests/` 46 项全过；`evals/m4_m5/run_injection.py` 旧集回归通过（退出码 2：C3 新纪律落地前不宣称 PASS）。

路线图见 `docs/positioning.md`。下一步：PR5（cann_bench 打包 + M0 执行包）、C3 注入集新纪律（边界合法样本、每规则 ≥3 单点注入、独立故障集）。

## 目录

- `docs/positioning.md` — 分层定位与已确认决定
- `docs/spec/ir-syntax.md` — 嵌入式 IR 词汇与语义（v0.2：Vector 通路）
- `docs/spec/verifier-rules.md` — 检查器规则与诊断 ID
- `docs/spec/device-spec.md` — 设备规格表结构
- `docs/design/vocabulary-evidence.md` — 语料驱动词汇方法与证据表
- `docs/design/decisions/` — 设计决策记录（ADR），含推翻条件
- `docs/design/review-guide.md` — 评审指南：事实源地图、不变量、已知限制
- `docs/evaluation/claims.md` — 有效性主张 C1–C5 与判词表（v2.5.18，25 轮评审收敛）
- `docs/evaluation/metrics.md` — 指标 M0–M9、计时口径与测量清单（v2.5 配套）
- `src/ascendc_ir/` — 工具链（trace / model / verify / codegen 已落地，pack 归 PR5）
- `examples/` — 最小例子（IR / 已审定生成输出 / 手写对照三件套）
- `evals/` — M0 配对、M4/M5 注入集、C1 协议
