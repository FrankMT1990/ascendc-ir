# 评审指南

给评审本仓代码的 agent：先读这份，再读 ADR，再读代码。

## 事实源地图

| 主题 | 唯一事实源 | 必须同步的消费者 |
|---|---|---|
| IR 词汇与语义 | `docs/spec/ir-syntax.md` | `src/ascendc_ir/trace/`、`src/ascendc_ir/pipes.py`、`examples/` |
| 检查器规则语义 | `docs/spec/verifier-rules.md` | `src/ascendc_ir/verify/rules.py`、`tests/verify/`、`evals/m4_m5/` |
| 设备数值 | `src/ascendc_ir/devices/*.toml`（结构见 `docs/spec/device-spec.md`） | 检查器、代码生成；改动须带来源链接 |
| 有效性主张与指标 | `docs/evaluation/claims.md`、`metrics.md` | `evals/` |
| 设计决定与推翻条件 | `docs/design/decisions/`（ADR） | 相关代码与 spec |

冲突处理：不要在某一个消费者里加局部例外。先定位事实源，在同一变更中修正事实源、消费者和测试。

## 不变量（评审时必查）

1. `rules.py` 的每条规则与 `verifier-rules.md` 的条件逐字一致；每条规则至少一接受一拒绝用例。
2. 诊断的 callsite 指向用户代码（包外栈帧），不指向 `ascendc_ir` 内部。
3. `Kernel.to_json()` 字节稳定：同一 trace 两次序列化结果相同。
4. 设备表数值必须有来源（asc-devkit 头文件或官方文档），PR 说明里给链接。
5. 评估阈值（M0–M9）改动必须同时改 `metrics.md` 与 CHANGELOG。
6. 所有非空 Python/Shell 文件带 CANN 2.0 许可头。

## 已知限制（不是 bug，是有意的边界）

- trace 期 `for range` 展开，模型不保留循环结构（ADR 0002）；codegen 重卷失败时拒绝生成（ADR 0009）。
- v0.2 无 block 级多核切分（无 `asc_get_block_idx` 词汇）——语料 gap，未排期。
- v0.2 无 Cube/Reg/原子/缓存控制词汇（见 vocabulary-evidence.md gap 表）。
- codegen 只支持已核对头文件签名的 C API 映射；未核对的 op 拒绝生成。

## 评审中的未决问题

- **守卫分支开销**（2026-09-25 评审提出）：生成的循环体内带 `if (i >= N)` / `if (i + N < TILES)` 守卫。标量分支与异步 PIPE 并行，理论上开销小；但 tile 小、指令短（如 2048 f32 = 32 repeat）时，每轮标量开销占比可能顶到 M0 的 5% 线。处理：M0 增加「守卫开销」配对类实测；超线则 codegen 改软件流水（剥 prologue/epilogue，稳态无分支）。实测前不改生成方式。

## 如何验证

```bash
python -m pytest tests/ -q            # 单元测试
python evals/m4_m5/run_injection.py   # M4/M5 注入集
```

## 评审记录

2026-09-25 对 `10a8142`…`c37f331` 的结论在 `docs/design/review-findings-2026-09-25.md`，逐条处置在 `docs/design/review-response-2026-09-25.md`。
2026-09-26 对 `e17705b` 的复审结论在 `docs/design/review-findings-2026-09-26.md`，逐条处置在 `docs/design/review-response-2026-09-26.md`。

2026-09-26 对修复提交 `e17705b` 的复审在 `docs/design/review-findings-2026-09-26.md`。原六条里五条已成立；还要改的是多消费者 WAR，以及就地写被槽位复用判定误伤。

## PR 历史

| commit | 内容 | 关键上下文 |
|---|---|---|
| `10a8142` | PR1 骨架与规范 | ADR 0001–0006 |
| `ca05afd` | PR2 trace/model/devices | ADR 0002/0004；语料证据表首填 |
| `99e0d52` | PR3 verifier + 注入集 | ADR 0007/0008；V009 补漏 |
| `7e10e91` | ADR 补充 | ADR 0001–0008 |
| `0f2e861` | PR4 codegen | ADR 0009；golden diff + fail-closed |
| 评审修复 | 评审六条 + 事实源对齐 + V010 | ADR 0010；review-response-2026-09-25 |
| 复审修复 | 最后读之后释放 + 按槽位展开 + RMW 明确拒绝 | ADR 0011；review-response-2026-09-26 |
