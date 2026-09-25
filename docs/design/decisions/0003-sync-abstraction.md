# 0003 同步原语命名 `sync`，A 级抽象起步

状态：已确认（2026-09-24）

## 背景

跨 PIPE 的生产→消费交接在 C API 里是必须成对出现的 `asc_sync_notify` + `asc_sync_wait`。IR 把它做成一条声明。初版命名 `handoff`（借 CAKE 的 producer–consumer handoff），评审后更名 `sync`，更贴近 C API 术语。

## 选项（抽象级别）

- A：`sync(p, q, on=..., stage=i)`，event 分配与 WAR 释放边由编译器推导。
- B（CAKE 风格）：暴露显式 barrier 计数、多生产者合并。

## 决定

A 级起步。v0.2 只有 Vector 通路，单生产单消费覆盖 W1；出现语料证据再升级 B。

## 后果

- 编译器推导：event 通道分配（每逻辑通道一个 EVENT_ID）、WAR 释放边（`stages=N` 的 buffer 在复用槽位前等待消费完成）。
- 表达力赌注：如果 C1 实验显示 agent 需要控制交接粒度（如双层流水交叉释放），向 B 回摆。

## 推翻条件

- 语料或 C1 实验出现 A 级表达不了的同步模式（先在 vocabulary-evidence.md 记 gap）。
