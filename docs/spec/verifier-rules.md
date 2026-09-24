# 检查器规则 v0.2

检查器在 trace 之后、代码生成之前运行。所有规则产出结构化诊断；`block` 级诊断拒绝生成 `.asc`。v0.2 不使用 `warn`。

v0.2 相对 v0.1 的变化：`handoff` 更名 `sync`；诊断位置从文本行号改为调用点（callsite）。

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
| V001 | 通路合法 | copy 的源/目标地址空间组合与方向必须存在于设备表 `pathways`，且调用前缀 PIPE 与表中一致 | C API 流水类型文档 |
| V002 | UB 容量 | 全部 `ubuf` buffer 的 `elems × dtype 字节 × stages` 之和 ≤ 设备表 `ub_usable_bytes` | cannbot-knowledge 架构卡 |
| V003 | sync 配对 | `sync` 的 `on` 中每个 buffer（按 stage）必须恰好有一个上游生产调用和一个下游消费调用 | C API 同步语义 |
| V004 | sync 方向 | `sync(p, q, ...)` 中 p 必须是生产调用所在 PIPE，q 必须是消费调用所在 PIPE | `asc_sync_notify` 参数语义 |
| V005 | event 压力 | 同一循环迭代内活跃 sync 数 ≤ 设备表 `event_ids`（8） | cannbot-knowledge pipeline 卡 |
| V006 | 计算操作数空间 | `v.*` 的操作数与结果必须都是 `ubuf` buffer，不得直接引用 `gmptr` 参数 | C API 计算接口约束 |
| V007 | 对齐 | copy 的 `elems × dtype 字节` 必须是设备表 `align_bytes`（32）的整数倍 | C API 搬运接口约束 |
| V008 | 设备守卫 | 使用了设备表不存在的 PIPE 或通路时拒绝，`suggestion` 给出该设备的合法替代 | 分层定位决定 |

## 接受 / 拒绝示例约定

- 每条规则在 `tests/verify/` 至少有一个接受用例和一个拒绝用例。
- 拒绝用例由合法样本**只改一处调用点**得到，注入集与金标放在 `evals/m4_m5/`。
- 合法样本从语料改写（见 `docs/design/vocabulary-evidence.md`），不手写。
- 金标（该改的调用点）由人按 C API 规则填写，不从诊断文案反推。

## 拒绝示例（非完整，示意）

| 规则 | 非法写法 | 期望诊断要点 |
|---|---|---|
| V001 | `mte3.copy(x[i * TILE], x_local[i % 2])` | GM→UB 不在 mte3 通路；建议 mte2 |
| V002 | 三个 `ubuf(f32, 65536, stages=2)` | 总字节超 `ub_usable_bytes`，指出各 buffer 占用 |
| V003 | `sync(mte2, v, on=x_local)` 后无 `v.*` 消费 x_local | 指出 x_local 缺消费者 |
| V004 | `sync(v, mte2, on=x_local)`，但 x_local 由 mte2 生产 | 方向颠倒，指出生产 PIPE 是 mte2 |
| V005 | 单迭代内 9 条 sync | 超 event_ids=8，指出需合并交接 |
| V006 | `v.add(z_local, x_local, y)`，y 是 gmptr 参数 | gm 参数不能直算 |
| V007 | `ubuf(f32, 100)`（100×4=400B，非 32 倍数）参与 copy | 对齐违例，给出最近合法值 |
| V008 | device 为 2201 时使用 3510 才有的通路 | 指出该设备无此通路及替代 |
