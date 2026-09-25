# 检查器规则 v0.2

检查器在 trace 之后、代码生成之前运行。所有规则产出结构化诊断；`block` 级诊断拒绝生成 `.asc`。v0.2 不使用 `warn`。

本文是规则语义的唯一事实源；`src/ascendc_ir/verify/rules.py` 的实现必须与本文一致，两者同步修改。

## 诊断格式

```json
{
  "id": "V003",
  "severity": "block",
  "callsite": {
    "file": "add.py",
    "line": 14,
    "function": "add_custom",
    "statement": "sync(mte2, v, on=(x_local, y_local), stage=i)"
  },
  "message": "sync 的 on 中 y_local 没有消费语句",
  "suggestion": "在 v.* 计算中消费 y_local，或从 on 中移除",
  "knowledge": null
}
```

- `callsite` 指向**需要修改的调用点**，由 trace 时记录（`inspect` 取 `file:line`），不是编译器内部位置。
- `knowledge` 为 cannbot-knowledge 卡片相对路径；无对应卡片时为 `null`。
- 同一调用点可产生多条诊断；输出按 `(file, line)` 排序，稳定可复现。

## 规则表

| ID | 规则 | 条件 | 来源 |
|---|---|---|---|
| V001 | 通路合法 | copy 的源/目标地址空间组合必须存在于设备表 `pathways`，且调用前缀 PIPE 与表中一致 | C API 流水类型文档 |
| V002 | UB 容量 | 全部 `ubuf` buffer 的 `elems × dtype 字节 × stages` 之和 ≤ 设备表 `ub_usable_bytes`；诊断指向占用最大的 buffer 声明 | cannbot-knowledge 架构卡 |
| V003 | sync 配对 | 对 sync 的 `on` 中每个 buffer（按 stage 槽位）：生产方 = 该 sync 之前最近一次写入该槽位的调用，必须存在；消费方 = 该 sync 之后、下一次写入同一槽位之前读取该槽位的调用，**至少一个**。同一条语句既读又写同一槽位时，读发生在写之前：先计入消费，再结束窗口 | C API 同步语义 |
| V004 | sync 方向 | `sync(p, q, ...)` 中 p 必须是生产调用所在 PIPE，q 必须是消费调用所在 PIPE | `asc_sync_notify` 参数语义 |
| V005 | event 压力 | 任一程序点上，同一 `(生产PIPE, 消费PIPE)` 对内的未决 sync 数 ≤ 设备表 `event_ids`（8）。event id 按 PIPE 对独立，不同对可复用同一 id | cannbot-knowledge pipeline 卡 + 官方样例四通道共用 EVENT_ID0 |
| V006 | 计算操作数空间 | `v.*` 的操作数与结果必须都是 `ubuf` buffer，不得直接引用 `gmptr` 参数（结果侧同样由本规则诊断，不在 trace 期抛类型错误） | C API 计算接口约束 |
| V007 | 对齐 | 参与 copy 的 buffer，其 `elems × dtype 字节`（单 stage）必须是设备表 `align_bytes`（32）的整数倍；诊断指向 buffer 声明 | C API 搬运接口约束 |
| V008 | 设备守卫 | 使用了设备表不存在的 PIPE 或通路时拒绝，`suggestion` 给出该设备的合法替代 | 分层定位决定 |
| V009 | 跨 PIPE 读取必须先经 sync | 每次读取 buffer 槽位时，若最近一次写入在另一条 PIPE，则写入之后、本次读取之前必须存在覆盖该槽位的 sync(生产PIPE, 消费PIPE)；诊断指向读取调用点 | cannbot-knowledge runbook `shared_ub_cross_pipeline_per_direction_sync` |
| V010 | 读取必须有生产 | 读取从未写入过的槽位时拒绝（V009 要求存在最近一次写入；不存在时由本条接管） | 评审 2026-09-25 规格缺口 |

## 诊断去重

trace 展开后，循环体每一轮都会产生诊断；同一 `(id, file, line, message)` 只报一次。

## 接受 / 拒绝示例约定

- 每条规则在 `tests/verify/` 至少有一个接受用例和一个拒绝用例。
- 拒绝用例由合法样本**只改一处调用点**得到，注入集与金标放在 `evals/m4_m5/`。
- 合法样本从语料改写（见 `docs/design/vocabulary-evidence.md`），不手写。
- 金标（该改的调用点）由人按 C API 规则填写，不从诊断文案反推。
- V008 说明：`ascend950pr` 设备表包含全部 PIPE，真实注入样本需要 2201 设备表落地后构造；当前由 `tests/verify` 的夹具设备表（从 950 表移除 mte2）覆盖接受/拒绝行为。

## 拒绝示例（非完整，示意）

| 规则 | 非法写法 | 期望诊断要点 |
|---|---|---|
| V001 | `mte3.copy(x[i * TILE], x_local[i % 2])` | GM→UB 不在 mte3 通路；建议 mte2 |
| V002 | `ubuf(f32, 40000, stages=2)` 等三个 buffer 超容 | 总字节超 `ub_usable_bytes`，指出各 buffer 占用 |
| V003 | `sync(mte2, v, on=(x_local, z_local))`，z_local 尚未生产 | 指出 z_local 缺生产调用 |
| V004 | `sync(v, mte2, on=x_local)`，但 x_local 由 mte2 生产 | 方向颠倒，指出生产 PIPE 是 mte2 |
| V005 | 单迭代内 9 条未决 sync | 超 event_ids=8，指出需合并交接 |
| V006 | `v.add(z_local, x_local, y[0])`，y 是 gmptr 参数 | gm 参数不能直算 |
| V007 | `ubuf(f32, 100)`（100×4=400B，非 32 倍数）参与 copy | 对齐违例，给出最近合法 elems |
| V008 | device 表中无某 PIPE 时使用之 | 指出该设备无此 PIPE 及可用集合 |
| V009 | 删除 `sync(mte2, v, ...)` 后直接 `v.add(z_local, x_local, ...)` | 读取前缺少 mte2→v 的 sync，指向读取行 |

## 运行注入集

```bash
python evals/m4_m5/run_injection.py
```

输出合法样本误拒数、注入召回数、定位命中数与诊断干净率；召回与定位全过时退出码为 0。当前状态（2026-09-25，评审修复后）：合法 3/3 零误拒，召回 9/9，定位 9/9，干净 9/9。
