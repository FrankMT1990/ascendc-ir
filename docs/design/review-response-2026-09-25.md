# 评审响应（2026-09 25）

对应 `docs/design/review-findings-2026-09-25.md`。逐条处置如下；修复提交见 CHANGELOG。

## 结论总览

六条必修全部属实，已修复。事实源冲突六条全部属实，已对齐。注入集批评属实，已重构为隔离样本并增加干净率报告。两个核对项：`repeat` 的 `uint8_t` 上限已加 codegen 守卫；copy 的 6 参数形态与官方 `c_api_delicacy_async_add` 逐字一致（`256 = 2048×4B / 32B`），不是 bug，3510 页头文件复核留作后续。

## 必修逐条

| # | 结论 | 处置 |
|---|---|---|
| 1 | WAR 同一 event 连续 notify 是 UB；golden 与手写对照同错 | 接受。WAR 按槽位分配连续 id 块（ADR 0010），同一 id 上 notify/wait 严格交替；`v.add(z, x, x)` 重复读只释放一次；golden 与 reference 重写 |
| 2 | 仿射 GM 地址丢第 0 轮基址 | 接受。`_gm_ptr` 保留基址 + `i * stride`；补基址非 0、stride 为 0 但偏移非 0 两条 codegen 测试 |
| 3 | sync 全不写 stage 时走「成功」直线展开，丢槽位与 WAR | 接受。直写形态只允许「每个槽位至多写一次」，否则拒绝生成；`ir-syntax.md` 写明 `stage` 是迭代号、槽位 = `stage % stages`、循环体内 sync 必须写 `stage=i`；reroll 模块文档同步 |
| 4 | 重卷不比较 op、PIPE、操作数个数 | 接受。`_same_structure` 统一比较类型/PIPE/op/源个数/标量/sync 的 on，`_strides` 与 `_group_matches` 共用 |
| 5 | 既读又写同一槽位时 V003 吃掉消费方 | 接受。先计消费再结束窗口；V003 消费方条件从「恰好一个」改为「至少一个」（多条计算读同一槽位是合法调度，评审未点名、修复时发现）；V005 注入样本与单测改为干净的 V005 |
| 6 | 结果侧 GM 到不了 V006 | 接受。结果侧与源侧同样透传（ADR 0007），V006 统一诊断；规则表与实现对齐 |

## 事实源冲突逐条

| # | 处置 |
|---|---|
| ADR 0002 / 评审指南 / reroll 文档与 0009 不一致 | 以 0009 为准，三处已改 |
| event_ids 语义 | ADR 0010；spec、`rules.py`、设备表注释、测试同步 |
| M5 定义三处不一致 | 统一为 ADR 0006 的「file + 源码行片段」；callsite 的 file 改存相对 cwd 路径，恢复 `to_json()` 跨机器字节稳定；`metrics.md` 与 `run_injection.py` 对齐 |
| 设备数值无来源链接 | 设备表补 cannbot-knowledge 架构卡来源与「待头文件核对」注释；不变量 4 标记为部分满足 |
| README 状态 / positioning PR4 范围 / pack 空目录 | README 状态更新；pack 明确归 PR5 |
| pyproject 缺 package-data | 已加 `devices/*.toml`；wheel 不再丢设备表 |

## 注入集

- 样本重构为「一处改动、一套规则」：v001 整核一致用错 PIPE；v003 改为已生产无消费；v004 保留正确 sync 隔离 V009；v006 保留 y_local 消费隔离 V003。
- 新增 v010（读未写槽位）。
- `gold.json` 改记期望 ID 集合；runner 增报干净率（实际集合 == 期望集合）。
- 引擎按 `(id, file, line, message)` 去重，循环展开不再同一行报 16 次。
- 修复后实测：合法 3/3、召回 9/9、定位 9/9、干净 9/9。

## 规格缺口

- 「读从未写过的槽位」新增 V010，spec/实现/注入/单测同步。

## 评审未点名、修复中顺带处理

- V003「恰好一个消费方」过严 → 「至少一个」。
- 列表推导 `bufs = [ubuf(...) for _ in range(9)]` 产生 9 个同名 buffer → trace 期拒绝并给出改写指引。
- `asc_add` 的 `repeat` 为 `uint8_t` → codegen 守卫 repeat ≤ 255。
