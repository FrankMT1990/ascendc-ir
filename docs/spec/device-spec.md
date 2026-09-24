# 设备规格表 v0.1

设备规格是数据文件，不是代码分支。每代设备一个 TOML，放在 `src/ascendc_ir/devices/<device_id>.toml`。IR 文本不区分代际语法；检查器与代码生成按设备表判定合法性。

## 表结构

```toml
[device]
id = "ascend950pr"
npu_arch = 3510

[memory]
ub_usable_bytes = 253952    # 248KB；物理 256KB，编译器预留 8KB
l1_bytes = 524288           # 512KB
align_bytes = 32

[pipes]
available = ["s", "v", "m", "mte1", "mte2", "mte3", "fix"]
event_ids = 8

[pathways]
"gm->ubuf" = "mte2"
"ubuf->gm" = "mte3"
"ubuf->ubuf" = "v"
```

## 字段语义

| 字段 | 含义 | 消费规则 |
|---|---|---|
| `npu_arch` | 架构代号，对应 asc-devkit `impl/c_api/instr_impl/npu_arch_*` 目录 | 代码生成选指令实现 |
| `ub_usable_bytes` | 扣除编译器预留后的 UB 可用字节 | V002 |
| `align_bytes` | 搬运对齐 | V007 |
| `pipes.available` | 该设备存在的 PIPE | V008 |
| `event_ids` | 硬件 event 数 | V005 |
| `pathways` | 地址空间组合 → 执行 PIPE | V001、V004、V008 |

## 当前设备

| device_id | npu_arch | 状态 |
|---|---|---|
| `ascend950pr` | 3510 | v0.1 主设备，C1 评估设备 |
| （2201 设备表） | 2201 | 后续加入，只做 M0 可移植检查 |

## 扩展规则

- v0.1 的 `pathways` 只列 Vector 通路；`cbuf`/L0/Cube 通路（`gm->cbuf`、`cbuf->l0*`、`l0c->*` 等）随 Cube 词汇版本一起进入，并同步更新 V001/V008 的接受/拒绝用例。
- 数值以 asc-devkit 头文件与官方文档为准；修改设备表必须在 PR 说明里给出来源链接。
