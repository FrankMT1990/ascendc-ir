# 评审结论（2026-09-25）

评审范围：`10a8142`、`ca05afd`、`99e0d52`、`7e10e91`、`0f2e861`、`c37f331`（`master` @ `c37f331`）。

入口按 `docs/design/review-guide.md`：事实源、六条不变量、已知限制。本文件只记录结论，不改实现。修复时先改对应事实源，再改消费者和测试，不要在单个消费者里加例外。

## 验证

在 `c37f331` 上复现：

- `python3 -m pytest tests/ -q`：30 passed
- `python3 evals/m4_m5/run_injection.py`：合法 3/3、召回 8/8、定位 8/8，退出码 0

这套测试锁住的是 `examples/vector_add/add.py` 这一条路径。下面第 1–4 条都会在检查器放行之后生成错误的 `.asc`；现有 golden 把其中第 1 条冻住了。

## 必须先改

### 1. 双缓冲 WAR 在同一个 event 上连续 notify

C API：相同源流水、相同目标流水、相同 id，连续 `asc_sync_notify` 是未定义行为；配对的 `notify` / `wait` 的 `pipe`、`tpipe`、`id` 必须一致。

<https://asc.gitcode.com/api/SIMD-API/c_api/sync/asc_sync_notify.html>

`examples/vector_add/add_golden.asc` 里 `x_local` 的 WAR 只用 `EVENT_ID0`。`i=0` 和 `i=1` 都会执行 notify，第一次 wait 在 `i=2`：

```18:27:examples/vector_add/add_golden.asc
        if (i >= 2) { asc_sync_wait(PIPE_V, PIPE_MTE2, EVENT_ID0); }
        asc_copy_gm2ub(x_local + (i % 2) * 2048, x + i * 2048, 1, 256, 0, 0);
        if (i >= 2) { asc_sync_wait(PIPE_V, PIPE_MTE2, EVENT_ID1); }
        asc_copy_gm2ub(y_local + (i % 2) * 2048, y + i * 2048, 1, 256, 0, 0);
        asc_sync_notify(PIPE_MTE2, PIPE_V, EVENT_ID2);
        asc_sync_wait(PIPE_MTE2, PIPE_V, EVENT_ID2);
        if (i >= 1) { asc_sync_wait(PIPE_MTE3, PIPE_V, EVENT_ID3); }
        asc_add(z_local, x_local + (i % 2) * 2048, y_local + (i % 2) * 2048, 32, 1, 1, 1, 8, 8, 8);
        if (i + 2 < 8) { asc_sync_notify(PIPE_V, PIPE_MTE2, EVENT_ID0); }
        if (i + 2 < 8) { asc_sync_notify(PIPE_V, PIPE_MTE2, EVENT_ID1); }
```

`z_local`（`stages=1`）是下一轮先 wait 再 notify，配对成立。错的是 `stages>1` 时整个 buffer 共用一个 id。`add_reference.asc` 是同一套写法，golden diff 对不出来。

修复方向：WAR 的 event 键落到槽位（`i % stages`）。同一槽位上，下一次 notify 之前必须已经 wait。距离条件 `if (i >= N)` / `if (i + N < TILES)` 可以保留。golden 和手写对照一起改，否则 M0 会把两份同样非法的同步边当成配对。

同一条计算的两个源如果是同一个 buffer，发射端会在一个基本块里把同一 id notify 两次。`v.add(z, x, x)` 能通过检查器。根子在：

```216:217:src/ascendc_ir/codegen/emit.py
        for s in stmt.srcs:
            lines.extend(self._war_notify(s.buffer))
```

同一个 buffer 只发一次。

### 2. 仿射 GM 地址丢掉第 0 轮基址

`x[8 + i * 64]` 检查器通过，生成 `x + i * 64`。每一轮偏移相同的 `x[8]` 生成 `x`。`add.py` 的第 0 轮偏移是 0，所以现有样例看不出来。

```123:129:src/ascendc_ir/codegen/emit.py
    def _gm_ptr(self, ref: GmRef, stmt_index: int, ref_index: int) -> str:
        if not self.looped:
            return ref.param.name if ref.offset == 0 else f"{ref.param.name} + {ref.offset}"
        stride = self._gm_stride(stmt_index, ref_index)
        if stride == 0:
            return ref.param.name
        return f"{ref.param.name} + i * {stride}"
```

有循环时要带上第 0 轮偏移：常量项和 `i * stride` 都要留下。补一条基址非 0、一条 stride 为 0 但偏移非 0 的 codegen 测试。

### 3. sync 全部不写 stage 时，重卷走「成功」的直线展开，槽位和 WAR 一起丢

`reroll` 用 `max(sync.stage)+1` 推断 TILES。全部 `stage=None` 时返回 `(1, 全部语句, True)`。`stages=2`、`x_local[i % 2]`、循环 4 次、sync 不带 stage：检查器通过，四次搬运都写成同一个基址，没有 `i % 2`，也没有 WAR。

这就是 ADR 0009 拒绝的那种错码，只是它走了 `tiles==1` 的成功分支。模块文档还写着失败时「返回 `(1, 全部语句)`，由发射端展开」，和函数文档、`generate()` 相反：

```9:14:src/ascendc_ir/codegen/reroll.py
"""循环重卷：trace 期展开的语句序列，按仿射规律还原为单迭代循环体。
...
验证失败则返回 (1, 全部语句)，由发射端展开生成。
"""
```

`stage` 现在有两层含义，`ir-syntax.md` 只写了槽位这一层：

- 检查器：`stage % stages` 当槽位（`rules.py` 的 `_slot_of`）
- 重卷：`stage == i` 且 `max(stage)+1 == TILES` 当迭代号

`sync(..., stage=i % 2)` 对检查器是槽位，对重卷对不上。修复时在 `ir-syntax.md` 写明 `stage` 是迭代号还是槽位，并让「每个槽位至多写一次」以外的直线展开拒绝生成，而不是当成单 tile。

### 4. 重卷不比较 op、PIPE、操作数个数

`for i in range(2)` 第 0 轮 `v.add`、第 1 轮 `v.cast`，两边读同一个 buffer。检查器诊断为空，生成的循环两轮都是 `asc_add`。`_group_matches` 只对引用和标量；源个数不同时 `zip` 会截断。模板和每一轮至少要比 op、pipe、源个数、标量，对不上就 `ok=False`。

### 5. 同一条语句既读又写同一槽位时，V003 把消费方吃掉

```70:74:src/ascendc_ir/verify/rules.py
            for j in range(idx + 1, len(stmts)):
                if any(_matches(w, buf, slot) for w in _writes(stmts[j])):
                    break
                if any(_matches(r, buf, slot) for r in _reads(stmts[j])):
                    consumers.append(stmts[j])
```

`v.add(b, b, b)` 得到 V003「下游消费调用数为 0」。这条语句上的读发生在写之前，应先计入消费，再因写入结束窗口。

`evals/m4_m5/injected/v005_event_pressure.py` 和 `tests/verify/test_verifier.py` 的 V005 用例都是就地 add，断言只要求含有 V005。实测该注入样本是 V003×9 加 V005×1。修 V003 时这两处要改成干净的 V005，或者把「就地计算非法」写进 `verifier-rules.md` 并单独给样例。按当前规则表，就地计算应当能配上消费方。

### 6. 结果操作数上的 GM 到不了 V006

`docs/spec/verifier-rules.md`：`v.*` 的操作数和结果都必须是 ubuf。源操作数按 ADR 0007 透传。`v.add(z[0], x_local, x_local)` 在 `as_bufref` 里直接 `TypeError`。要么让结果侧 GM 同样进入 V006，要么改规则表，写明结果侧类型错误在 trace 期抛出。现在两边都算事实源，条件没有逐字一致。

## 事实源冲突（和代码一起改）

- `docs/design/review-guide.md` 已知限制、ADR 0002 的后果，仍写「重卷失败则展开生成」。ADR 0009 和 `generate()` 已是失败即 `CodegenError`。以 0009 为准时，改 0002、评审指南和 `reroll.py` 模块文档。
- V005 和 `ascend950pr.toml` 把 `event_ids=8` 当成全局未决 sync 上限。C API 写的是每一对 pipe 各自 8 个独立 id，不同 pipe 对可以复用同一个 `EVENT_ID`。因此「不同 pipe 对上合计超过 8、每一对都不超过 8」会被误拒；codegen 又把所有通道编进一条全局 `EVENT_ID` 序列。改 spec、`rules.py`、设备表注释和测试，不要只改一边。
- `docs/evaluation/metrics.md` 的 M5 仍是 file:line。ADR 0006 改成了「file + 源码行片段」。`evals/m4_m5/run_injection.py` 只查 `gold_line_contains in statement`，不查 file，也不查 line。callsite 的 file 是 `Path.resolve()` 绝对路径，换目录后 `to_json()` 字节不同。指标定义、ADR、测量入口要合成一个说法。
- 不变量 4：`src/ascendc_ir/devices/ascend950pr.toml` 的 248KB、预留 8KB、L1 512KB、`event_ids=8` 没有头文件或文档链接。`248*1024=253952` 只说明注释自洽。
- `README.md` 状态仍是「当前为 PR1，不含实现」。`docs/positioning.md` 的 PR4 仍包含 cann_bench 打包，`src/ascendc_ir/pack/` 仍是空目录。
- `pyproject.toml` 没有把 `devices/*.toml` 列为 package data，也没有 `MANIFEST.in`。从源码树跑能读到表；wheel 会丢设备表。

## 注入集

8 个注入样本里，诊断集合干净的只有 V002、V007、V009。召回只要求期望 ID 出现，所以 8/8 不表示「一处改动、一条规则」。

| 样本 | 期望 | 实测 |
|---|---|---|
| v001 | V001 | V001×8，V004×8，V009×8 |
| v002 | V002 | V002×1 |
| v003 | V003 | V003×9，V004×7，V009×8 |
| v004 | V004 | V004×32，V009×16 |
| v005 | V005 | V003×9，V005×1 |
| v006 | V006 | V003×8，V006×8，V005×1 |
| v007 | V007 | V007×1 |
| v009 | V009 | V009×16 |

V001 / V003 / V004 / V006 的额外 ID 多数是这一处改动带出来的。V005 的 V003 是第 5 条的误拒，不是连带。V009 删一条 sync，展开后同一行报 16 次。

另外：没有规则抓「读一个从未写过的槽位」。V009 的前提是存在最近一次写入。这是规格缺口，不是某一条规则写错。

## 按提交

| commit | 结论 |
|---|---|
| `10a8142` PR1 | 分层、C1–C5、M0–M9、V001–V008 的表和后面的实现对得上。规范把循环写成一个调用点，模型里没有循环节点，TILES 只能从 `sync.stage` 反推。 |
| `ca05afd` PR2 | trace、callsite 跳出包内栈帧、同一进程里 `to_json()` 两次字节相同，这三件成立。`lhs_name` 取整行赋值左侧，`bufs = [ubuf(...) for _ in range(9)]` 会得到 9 个同名 buffer，检查器不拒绝。语料表达力 4/5 只覆盖 asc-devkit 的 5 个 memory 矢量族；`v.cast` 在证据表里标了「源码待逐行核」。 |
| `99e0d52` PR3 | V001、V002、V004、V007、V008、V009 和规则表一致。V009 补的是真洞。第 5、6 条在这里。 |
| `7e10e91` | ADR 0007、0008 足够解释切分。0002 和评审指南没有随后来的 0009 改掉。 |
| `0f2e861` PR4 | 有 block 诊断就拒绝生成、未核对的 op 拒绝生成，这两条做到了。第 1–4 条在这里，golden 测试把错误的 event 配对冻住了。 |
| `c37f331` | `.gitattributes` 把 `*.asc` / `*.py` / `*.toml` / `*.md` 固定为 LF，和 golden 字节比较的目的一致。没有行为问题。 |

许可头：38 个非空 Python 文件都有 CANN 2.0 头，仓库里没有 Shell。

## 核对项（未坐实为错码）

对照 asc-devkit `648a6018` 的声明，不要用仓库内 `add_reference.asc` 互证。

- 公开的 `asc_add` 签名里 `repeat` 是 `uint8_t`。单 stage 超过 255×256 字节、仍小于 248KB UB 时，现在会打出 `repeat=256`。样例的 32 在范围内。
- 同步示例里的搬运是 3 参数字节长度 `asc_copy_gm2ub(dst, src, nbytes)`。生成代码是 6 参数 `(dst, src, 1, 256, 0, 0)`。`256` 只有在 `burst_len` 以 32 字节为单位时才等于 2048 个 float。3510 页本次没有打开，所以这是核对项。

## 不变量对照

| # | 结果 |
|---|---|
| 1 规则与 spec 逐字一致，一接受一拒绝 | V001/V002/V004/V007/V008/V009 对齐。V003 就地读写、V006 结果侧没有对齐。 |
| 2 callsite 指向用户代码 | 栈帧会走出包。file 是绝对路径。 |
| 3 `to_json()` 字节稳定 | 同一进程两次相同。绝对路径使换机器的 diff 不稳定。 |
| 4 设备数值有来源链接 | 未满足。 |
| 5 阈值改动同步 metrics 与 CHANGELOG | 数值阈值没改。M5 的判定定义在 ADR 0006 和 `metrics.md` 之间不一致。 |
| 6 非空 Python/Shell 许可头 | 满足。 |
