# C1 任务清单：冻结支持集 ∩ cann-bench level1

按 `docs/handoff/04-next-work.md` 第 1 节产出。清单 = 当前 `master`（`6e6e459`）代码生成真能发出的指令集 ∩ cann-bench level1（`abb6e47` 的 `tasks/level1`，8 任务 × 20 case）。粒度与前一份草稿一致：任务 × dtype。判词依据 `docs/evaluation/claims.md`（v2.8）。

## 冻结支持集（依据）

向量 f32（`src/ascendc_ir/catalog/__init__.py` 集合 + `pipes.py` 专用降级，上板证据 `board-3510@ac1ba1a` 50/50）：

- 二元：`add sub mul div max min and or prelu`
- 一元：`abs ceil exp floor ln log neg not relu rint round sqrt trunc`（`log`/`ln` 都降级为 `asc_ln`）
- 标量：`add_scalar max_scalar min_scalar mul_scalar`（无 `div_scalar`/`sub_scalar`）
- 专用：`leakyrelu`、`cast`（仅 half→float）、`select`（UB 位打包掩码）、`select_{gt,lt,ne,eq,ge,le}` 及其 `_scalar`、`duplicate`、`arange`、`repeat_reduce_sum`、`datablock_reduce_sum`
- int32：`xor shiftleft shiftright shiftleft_scalar shiftright_scalar`
- Cube（f16，`m.mmad`）：A[m,k] @ B(n,k)^T，K 分块累加；`nd2nz/dn2nz/l12l0a/l12l0b/l0c2gm`

调度面：`ubuf` 多级流水、`mte2/mte3.copy` 带元素偏移、Python `for` 循环分块、跨管 `sync`。单核 `<<<1,0,stream>>>`，无 block 词汇。

不在支持集（判出局用）：`erf`/`tanh`/`sigmoid`/`reciprocal` 等超越函数直发（可由基础算子组合）；f32→f16、bf16 任何方向的 `cast`；把向量收成标量的全归约；`axpy`；`gather`；多核切分。

## 交集结果

| 任务 ID | 入/出 | 计时 case（cann-bench case_id） | IR 指令分解（计时 case 所需） |
|---|---|---|---|
| `exp_f32` | 入 | level1/exp case 2：`[2048,2048]` f32，`{base:-1.0, scale:1.5, shift:0.0}`，输入范围 [-2,2] | 分块搬运 + `mul_scalar(1.5)` + `exp` |
| `sigmoid_f32` | 入 | level1/sigmoid case 2：`[2048,2048]` f32，`{}`，[-2,2] | `neg` + `exp` + `add_scalar(1.0)` + `duplicate(1.0)` + `div` |
| `gelu_f32` | 入（限 tanh 近似 case） | level1/gelu case 5：`[8192,8192]` f32，`{approximate:"tanh"}`，[-100,100] | `mul`,`mul`(x³) + `mul_scalar(0.044715)` + `add` + `mul_scalar(0.7978845608)` + tanh 链（`mul_scalar(2)`+sigmoid 链+`mul_scalar(2)`+`add_scalar(-1)`） + `add_scalar(1.0)` + `mul_scalar(0.5)` + `mul` |
| `mish_f32` | 入 | level1/mish case 2：`[2048,2048]` f32，`{}`，[-2,2] | `exp` + `add_scalar(1.0)` + `ln` + tanh 链 + `mul` |
| `masked_scale_f32` | 入（select 形态） | level1/masked_scale case 2：`x=[2048,2048]` f32，`mask=[2048,2048]` uint8，`{scale:1.0}`，x∈[-2,2]、mask∈{0,1} | `mul_scalar(1.0)` + `duplicate(0.0)` + `select`（uint8 掩码在输入侧按 select 的 UB 位打包形态预处理；`x*m*scale` 在 m∈{0,1} 时与 select 等价） |
| `swi_glu_f32` | 入 | level1/swi_glu case 2：`[2048,4096]` f32，`{dim:-1}`（末维分半 2048+2048），[-2,2] | 双路偏移搬运 + `neg`+`exp`+`add_scalar(1.0)`+`duplicate(1.0)`+`div`（silu） + `mul` ×2 |
| `foreach_addcdiv_f32` | 入 | level1/foreach_addcdiv_scalar case 1：x1/x2/x3 各为 2×`[1024,1024]` 的 TensorList，`{scalar:1.0}`，x1,x2∈[-1,1]、x3∈[0.5,1] | 每 tensor：`div` + `mul_scalar(1.0)` + `add`；2 个 tensor 顺序/流水调度 |
| `foreach_norm_f32` | **出** | — | torch._foreach_norm 把每个 Tensor 收成一个标量（全归约）。支持集只有 `repeat_reduce_sum`/`datablock_reduce_sum` 这类保留通道的形态，检查器拒绝「把一条向量收成更少结果的归约（repeat_reduce_sum 除外）」 |

## 出局记录（全部理由）

1. **foreach_norm（任务级出局）**：全归约 tensor→标量，不支持（见上表）。
2. **全部 8 任务的 f16 / bf16 变体**：`cast` 只有 half→float 方向。f16 计时 case 需要计算后回落 f16 输出、bf16 连装载都不支持。f32 变体全部保留。
3. **gelu 的 `approximate:"none"` case**（f32 的 6/8 个）：需 `erf`，不在支持集。gelu_f32 只能用 tanh 近似 case；f32 tanh case 为 case 5（[8192,8192]，全对齐）与 case 8（[1537,769]，行宽 3076B 非 32B 对齐，尾块搬运未在板上验证过）。选 case 5，并把 case 8 的对齐风险记在此处。
4. **exp 的 `base>0` case**：可发（`ln(base)` 在输入侧算好作为 `mul_scalar` 常数），但计时 case 选 attrs 最简的 case 2（自然指数）。
5. **masked_scale 的 `scale=nan` case（case 13）**：select 形态下 `m=0` 的位置输出 0，而 `x*nan*0=nan`，语义不等价，不可用 select 表达；计时 case 选 scale=1.0 的 case 2。case 5（scale=2.0, int8 mask）同样可入，未选作计时 case。
6. **向量加**：不是 level1 任务，按交接不塞入。它已贴单核拷贝下界（4.370 μs 口径见 `pack/vector_add_baseline`），不用于时间增益判词。

## W2（Cube 负载）

level1 的 8 个任务全部是逐元素/掩码/foreach/激活类，没有矩阵乘任务。f16 mmad 虽已上板 50/50（`ac1ba1a`），但 level1 里没有可生成的 Cube 任务。**W2 = 未测**，理由：level1 里没有可生成的 Cube 任务。C1 依判词表最多「部分成立（W1）」。

## 哈希与封存状态

- 本清单与其机器可读版 `evals/c1/freeze.json` 一并提交；提交即封存，之后只允许追加，不允许改写已封存字段。
- `t_baseline_us` / `t_hw_us` / `timing_input_sha256` 目前全部为 `null`，`kind = unclassified`，待第 2/3 步按 `04-next-work.md` 封存后回填。收包后不得补 `T_HW` 改分类。
