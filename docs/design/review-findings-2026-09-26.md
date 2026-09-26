# 复审结论（2026-09-26）

评审对象：`e17705b`（`fix: 评审 2026-09-25 六条必修与事实源对齐`），对照 `docs/design/review-findings-2026-09-25.md` 与 `docs/design/review-response-2026-09-25.md`。

本文件只记录结论，不改实现。

## 验证

在 `e17705b` 上复现：

- `python3 -m pytest tests/ -q`：43 passed
- `python3 evals/m4_m5/run_injection.py`：合法 3/3、召回 9/9、定位 9/9、干净 9/9，退出码 0

这套测试锁住的是单消费者的 `add.py`。下面「还要改」的第一条不在其中。

## 已经成立

| 原结论 | 现在 |
|---|---|
| 仿射 GM 丢掉第 0 轮基址 | `x[8 + i * 64]` 生成 `x + 8 + i * 64`；常数偏移 `x[8]` 生成 `x + 8` |
| 不写 `stage` 的槽位复用被当成直线展开 | 拒绝生成 |
| 重卷不比较 op / PIPE / 源个数 | `v.add` 与 `v.cast` 混在一轮里拒绝生成 |
| 就地 `v.add(b, b, b)` 被 V003 误拒 | 检查器通过。同一条语句里 `v.add(z, x, x)` 只 `notify` 一次 |
| 结果侧 GM 到不了 V006 | `v.add(z[0], ...)` 得到 V006 |
| `add.py` 双缓冲同一 id 连续 `notify` | golden 按槽位拆成 `EVENT_ID0/1` 与 `EVENT_ID2/3`。同一 id 上是先 `notify`，隔一轮再 `wait` |

事实源：ADR 0002、评审指南、`reroll` 文档都已改成重卷失败即拒绝生成。V005 按 PIPE 对计数。M5 与 `metrics.md` 都是「file + 源码行片段」。`pyproject.toml` 已包含 `devices/*.toml`。设备表来源仍标着「待头文件核对」，与响应文档一致，不另计为新缺陷。

## 还要改

### 1. 同一槽位被两条计算读时，WAR 在第一次读之后就释放，并在同一 id 上连续 notify

V003 改为「至少一个消费方」之后，下面这种核检查器诊断为空，`generate()` 成功。循环体里实际是：

```text
asc_add(z, x, y);
if (i + 2 < TILES) { asc_sync_notify(PIPE_V, PIPE_MTE2, ((i % 2) == 0 ? EVENT_ID0 : EVENT_ID1)); }
asc_add(w, x, y);
if (i + 2 < TILES) { asc_sync_notify(PIPE_V, PIPE_MTE2, ((i % 2) == 0 ? EVENT_ID0 : EVENT_ID1)); }
```

两条都来自 `src/ascendc_ir/codegen/emit.py`：每次读都调用 `_war_notify`。同一语句里的重复读已经用 `released` 去掉，跨语句没有。

同一条 PIPE_V 上，第一次 `notify` 排在第二条 `asc_add` 之前。标志只表示第一条加完了，`i + stages` 的 `wait` 可以通过，MTE2 会在第二条加还在读这个槽位时把它覆写。紧接着的第二次 `notify` 又是同一 `(PIPE_V, PIPE_MTE2, id)` 上的连续 `notify`，仍是未定义行为。

修复方向：`notify` 留到该槽位在本轮的最后一次消费之后，并且每轮每个 buffer 只发一次。`examples/vector_add/add_golden.asc` 只有一个消费者，现有 golden 看不出这个问题。补一条「两读同一槽位」的 codegen 测试。

### 2. 就地写被「每槽位至多写一次」误伤

单 tile 的 `mte2.copy` 再 `v.add(b, b, b)` 再写出：检查器为空，`generate()` 报重卷失败。`reroll._has_slot_reuse` 把 copy 和就地 add 算成两次写。这不是缺 `stage` 的循环。

若就地计算要能生成，把「同一条语句对刚写过的槽位再写」排除出复用判定。若 v0.2 就不生成就地写，写进 `docs/spec/ir-syntax.md`。现在检查器放行、codegen 拒绝，两边说法不一致。

## 核对项

`examples/vector_add/add_golden.asc` 里 WAR 的 event 是运行时三元表达式，不是字面量 `EVENT_IDn`。槽位配对是对的。若 `asc_sync_notify` / `asc_sync_wait` 的 id 必须是编译期立即数，这行编不过。编不过就改成按槽位分叉，每支里写死一个 `EVENT_IDn`。本次没有再打开 3510 头文件。
