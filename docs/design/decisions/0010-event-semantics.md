# 0010 event 语义修正：按 PIPE 对独立 + WAR 按槽位分配

状态：已确认（2026-09-25，评审 2026-09-25 第 1 条与事实源冲突第 2 条）。修订 ADR 0009 的 event 分配一节。

## 背景

评审发现两个 event 语义错误：

1. **WAR 同一 event 连续 notify 是未定义行为**。`stages=2` 的 buffer 共用一个 event 时，`i=0` 和 `i=1` 的释放 notify 都先于 `i=2` 的第一次 wait——同一 (生产PIPE, 消费PIPE, id) 上连续两次 notify 违反 C API 约定。golden 测试把这套错误配对冻住了，手写对照也犯了同一个错。
2. **event id 不是全局池**。C API 里每对 (生产PIPE, 消费PIPE) 各有 8 个独立 id；官方 `c_api_delicacy_async_add` 在四条通道上共用 `EVENT_ID0` 即为证据。V005 的全局未决上限和 codegen 的全局 EVENT_ID 序列都建错了。

## 决定

1. event id 按 (生产PIPE, 消费PIPE) 对独立分配；不同对可复用同一 id。
2. WAR 通道按槽位分配连续 id 块：`stages=N` 的 buffer 用 N 个 id，发射 `((i % N) == s ? EVENT_ID… : …)`，保证同一 id 上 notify/wait 严格交替。
3. V005 改为按 PIPE 对计未决 sync 数。
4. 同一语句重复读同一 buffer（`v.add(z, x, x)`）只释放一次。

## 后果

- `add_golden.asc` 与 `add_reference.asc` 同步重写；M0 配对纪律不变。
- 设备表 `event_ids` 注释写明按对独立及证据。

## 推翻条件

- 头文件核对证明 event id 语义与本文不同（如按方向无序对而非有序对），按头文件重写本节与分配器。
