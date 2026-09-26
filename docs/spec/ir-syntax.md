# AscendC-IR 语法规范 v0.2

状态：PR1 评审稿。范围：仅覆盖 Vector 通路（GM↔UB 搬运 + 向量计算），足以表达与官方 `c_api_delicacy_async_add` 等价的内核。Cube、Reg/SIMT、原子、缓存控制不在本版。

v0.2 相对 v0.1 的变化：形态改为 Python 嵌入式（trace 构建，无独立文本语法与 parser）；`handoff` 更名 `sync`；诊断指向调用点。

## 1. 形态

- Python 嵌入式 DSL：`@kernel` 装饰普通 Python 函数，执行时 trace 构建 IR。**没有独立文本语法，没有自写 parser**。
- trace 产物可序列化为 canonical JSON，用于审计、diff、缓存与演化记录；agent 不直接编写它。
- 每个影响性能的调度决定恰好对应一个**调用点**（callsite）：buffer 创建、stage 数、sync 边、循环结构。
- 机械后果由编译器推导：event 编号、repeat/stride、WAR 释放边、地址推进。
- 布局不做代数：v0.2 只有 ND 连续搬运；布局转换随 Cube 通路后续版本进入。
- 诊断按调用点的 `文件:行号` 定位，不指向编译器内部位置。

## 2. 词汇（Vector 通路）

| 构造 | 含义 |
|---|---|
| `@kernel(device="<device_id>")` | 声明内核与目标设备；device_id 引用 `src/ascendc_ir/devices/<device_id>.toml` |
| 参数注解 `gmptr(<dtype>)` | GM 张量参数，每个参数一个 |
| `ubuf(<dtype>, <elems>, stages=<n>)` | 创建 UB buffer；`stages` 声明流水深度 |
| `mte2.copy(<gm_ref>, <buf_ref>)` | GM → UB 搬运（PIPE_MTE2） |
| `mte3.copy(<buf_ref>, <gm_ref>)` | UB → GM 搬运（PIPE_MTE3） |
| `v.add(dst, s0, s1)` | 向量加（PIPE_V） |
| `v.cast(dst, src)` | 类型转换，dtype 由 buffer 声明决定 |
| `v.leakyrelu(dst, src, alpha)` | Leaky ReLU，`alpha` 为标量 |
| `v.repeat_reduce_sum(dst, src)` / `v.datablock_reduce_sum(dst, src)` | 归约求和两种形态 |
| `sync(<pipe>, <pipe>, on=<buf 或 tuple>, stage=<i>)` | 生产→消费交接边 |
| `for i in range(<const>):` | 循环，块内可使用循环变量 |

计算 op 集合来自语料证据（`docs/design/vocabulary-evidence.md`）；新增 op 必须先补证据表条目。

引用形式：

- buffer 引用：`x_local[i % 2]`，取第 i 个 stage 槽位。
- GM 引用：`x[i * TILE]`，按元素偏移。
- dtype：`f16` `f32`。
- buffer 默认名取赋值左侧变量名（`x_local = ubuf(...)` 得名 `x_local`），提取失败时回退为 `buf_N`。

`sync` 对应 C API 中必须成对出现的 `asc_sync_notify` + `asc_sync_wait`：生产 PIPE 通知、消费 PIPE 等待，event 由编译器分配。写成一条调用而不是两行，是因为配对、方向和 event 一致性可以在 trace 后静态检查。

## 3. 语义

- 同一 PIPE 内操作按程序顺序执行；不同 PIPE 并行。
- `sync(p, q, on=b)`：p 上对 b 的生产完成后，q 上的消费方才可开始。编译器分配 `EVENT_ID*`，生成 `asc_sync_notify` / `asc_sync_wait`。
- **`stage` 是迭代号**：循环体内的 sync 必须写 `stage=i`（i 为循环变量），槽位由编译器按 `stage % stages` 推导；循环外的 sync 不写 `stage`。只写槽位（如 `stage=i % 2`）会让重卷无法还原循环，代码生成拒绝。
- `stages = N` 的 buffer 是 N 深流水。编译器从 stage 数自动推导 WAR 释放边（消费完成 → 生产方可复用该槽位），agent 不写释放边。
- buffer 名必须唯一（默认取赋值左侧变量名；列表推导会重名，用循环 `append` 代替）。
- `for` 循环按程序顺序语义展开；地址推进由编译器生成。
- 循环上界与 tile 大小必须编译期可知；v0.2 不支持符号 shape。

## 4. 完整例子（vector add）

```python
# examples/vector_add/add.py
from ascendc_ir import kernel, gmptr, ubuf, f32, sync
from ascendc_ir.pipes import mte2, v, mte3

@kernel(device="ascend950pr")
def add_custom(x: gmptr(f32), y: gmptr(f32), z: gmptr(f32)):
    TILE, TILES = 2048, 8
    x_local = ubuf(f32, TILE, stages=2)
    y_local = ubuf(f32, TILE, stages=2)
    z_local = ubuf(f32, TILE, stages=1)
    for i in range(TILES):
        mte2.copy(x[i * TILE], x_local[i % 2])
        mte2.copy(y[i * TILE], y_local[i % 2])
        sync(mte2, v, on=(x_local, y_local), stage=i)
        v.add(z_local, x_local[i % 2], y_local[i % 2])
        sync(v, mte3, on=z_local)
        mte3.copy(z_local, z[i * TILE])
```

对应生成目标：官方 `c_api_delicacy_async_add` 等价结构——`asc_copy_gm2ub` / `asc_add` / `asc_copy_ub2gm`，同步为 `asc_sync_notify` / `asc_sync_wait`，event 编号与 repeat/stride 由编译器填写。手写对照见 `examples/vector_add/add_reference.asc`。

## 5. 词汇来源

词汇不自顶向下设计。每个构造必须有生产内核语料中的反复出现作为证据，证据表与准入规则见 `docs/design/vocabulary-evidence.md`；语料中反复出现但当前词汇表达不了的模式记为 gap，进入下一版本候选。

## 6. 显式非目标（v0.2）

- 无函数抽象、递归、动态分配、运行时分支（`if` 仅允许编译期可求值条件）。
- 无 `cbuf`/L0/Cube、Reg/SIMT、原子、缓存控制。
- 无符号 shape、无多 kernel、无 dispatcher。
- 无布局转换声明（随 Cube 通路进入后续版本）。
- 无显式 barrier 计数 / 多生产者合并（A 级抽象；出现语料证据再升级）。
- 不支持跨 PIPE 就地改写：一个 buffer 的生产 PIPE 必须唯一；如需改写，读旧 buffer、写新 buffer（复审 2026-09-26 第 2 条）。
