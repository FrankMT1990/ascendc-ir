# C1 任务书 v1.0（冻结版）

冻结于 2026-10-09。试点期间不得修改本文件、`evals/c1/tolerance.json` 与 `evals/c1/scans/`。判词与协议见 `docs/evaluation/claims.md`（v2.8）；任务清单与封存数值见 `evals/c1/freeze.json`。

## 1. 实验设置

- 你（实验 Agent）在一次会话内完成**全部 7 个任务**，每个任务产出一个能在目标设备上编译执行的内核。这次会话构成一个 run。
- 两臂使用同一模型、同一任务书、同一数值门、同一设备。你被指定到其中一臂：
  - **IR 臂**：用 `ascendc_ir` 工具链写嵌入式 IR（Python），产出 `.py` 源文件。
  - **对照臂**：直接写 Ascend C C API 内核，产出 `.asc` 源文件。
- 你的产出以 Git 分支提交（一个 run 一个分支，如 `c1-pilot-1`），分支内含全部源码文件。提交时间以 GitHub commit 时间为准。
- **上板计法**：一个任务的一个候选的完整验证流程（两组必测输入的数值门 + 通过后的计时，打包执行）计 **1 次上板**；构建（含编译失败重试）与 IR 臂本地检查器反馈不计。每 run 上限 20 次；超限终止该 run。一轮全部 7 任务验证 = 7 次上板。

## 2. 共同约束

- 设备：Ascend950PR_9589，CANN 9.1.0（`/usr/local/Ascend/cann-9.1.0`），架构 dav-3510，**单核**（`<<<1,0,stream>>>`）。多核切分与 Cube 接口本批不出现，出现即候选作废。
- 数值门：逐元素 `abs(输出 − golden) ≤ atol + rtol × abs(golden)`，atol=1e-5、rtol=1e-4，在 f32 上比较；任一元素不满足、NaN、形状/元素数不一致即失败。两组必测输入（计时组+边界组）都以封存哈希验证后再生，不得使用自造输入替代。
- `examples/`、参考 `.asc`、asc-devkit 示例与任何专家内核源码对你的会话不可见；不得检索。
- 算子定义与 oracle（`docs/handoff/01-background.md` 所述边界内的算子语义描述，即本文件第 4 节）可见。

## 3. 3510 已验证 API 形态速查（两臂同见）

以下是本设备上已经实测验证的 C API 形态事实，两臂同等享有（它等价于 IR 臂工具链内置的形态知识）：

1. 编译：内核必须用本套 CANN 的 `bisheng`，命令形如 `bisheng --npu-arch=dav-3510 -xasc -std=c++17 -fPIC -c <src> -o <obj>`。系统 `c++` 不认识 `--npu-arch`；`-fPIC` 是链入共享库的必要项。
2. 头文件：`#include "c_api/asc_simd.h"`（`$ASCEND_HOME_PATH` 的 `asc/include` 或 `x86_64-linux/asc/include` 下）。该头按 `__NPU_ARCH__` 分支：3510 分支只引入寄存器向量 API（`c_api/reg_compute/reg_vector.h` 等）；其他文档里出现的 10 参搬运/11 参写回等形态属于 2201 分支，**在 3510 上不存在**。
3. 向量计算是**寄存器形态**：`vector_float` 寄存器 + `asc_load`/`asc_store` + 计算 intrinsic + `vector_bool vmask`。3510 没有按 UB 指针逐元素计算的二元接口。
4. GM↔UB 搬运 `asc_copy_gm2ub`/`asc_copy_ub2gm` 的长度参数单位是**字节**，`uint16` 上限 65535（一次最多 65535 字节，更大的量要分块循环）；寄存器向量循环的尾块用 `asc_update_mask_b32(data_len)` 掩码。
5. 自然对数 intrinsic 是 `asc_ln`（3510 寄存器 API 没有 `asc_log`）。
6. 整数值的浮点字面量必须带小数点：写 `0.0f`/`1.0f`/`3.0f`；`0f` 是八进制错误、`1f` 是非法数字。
7. `asc_ceil`/`asc_trunc` 对 (−1,0) 区间输入返回 `+0.0`（IEEE 参考为 −0.0）；数值门按正负零等价判过。
8. `asc_select` 的谓词掩码是 UB 上的**位打包**字节流（字节数 = f32 个数 × 4 / 8），由 `asc_loadalign_postupdate` 装载；比较后选择（`asc_gt` 等 + `asc_select`）的比较掩码留在 VF 寄存器内，不占 UB buffer。
9. 类型转换只有 half→float 方向的样例形态（`vlds` 带 `UNPK_B16` 解包 + `asc_half2float`）。
10. 软件流水稳态循环里不能出现 `if` 分支；K 分块累加时首段 init 置真、后续段置假。

## 4. 任务列表与内核签名（冻结自 `evals/c1/freeze.json`）

每个任务的内核签名**固定**如下（GM 参数顺序、类型、输出必须一致，上板环境按此对接喂输入；IR 臂 `gmptr` 注解、对照臂 `__gm__` 指针）：

| 任务 | 计时输入 shape/attrs | 数值语义 | 内核签名 |
|---|---|---|---|
| exp_f32 | [2048,2048] f32，base=-1.0（自然指数），scale=1.5，shift=0.0 | y = exp(1.5·x) | `(x: f32, z: f32)` |
| sigmoid_f32 | [2048,2048] f32 | y = 1/(1+exp(−x)) | `(x: f32, z: f32)` |
| gelu_f32 | [8192,8192] f32，approximate=tanh | y = 0.5·x·(1+tanh(0.7978845608·(x+0.044715·x³))) | `(x: f32, z: f32)` |
| mish_f32 | [2048,2048] f32 | y = x·tanh(ln(1+exp(x))) | `(x: f32, z: f32)` |
| masked_scale_f32 | x [2048,2048] f32；掩码按 select 位打包形态提供（字节=f32 个数×4/8，u8 流），scale=1.0 | y = x·m·scale（m∈{0,1}，等价 select(m, x, 0)） | `(x: f32, mask: u8, z: f32)` |
| swi_glu_f32 | [2048,4096] f32，dim=-1（末维分半 x0=x[:,:2048], x1=x[:,2048:]） | y = x0·sigmoid(x0)·x1 | `(x: f32, z: f32)`（z 为 [2048,2048]；分半在内核内处理，x1 起点即 x + 2048·2048 个元素处） |
| foreach_addcdiv_f32 | x1/x2/x3 各 [2,1024,1024] f32（连续父张量视角），scalar=1.0 | y_i = x1_i + (x2_i/x3_i)·1.0，两个 tensor 各自独立 | `(x1: f32, x2: f32, x3: f32, z: f32)`（z 为 [2,1024,1024]） |

超越函数（sigmoid/tanh）不在 3510 的单指令集内，由基础指令组合实现；组合方式属于**调度层**，不在速查页范围内。

## 5. IR 臂接口

- 工具链 `ascendc_ir`：`@kernel(device="ascend950pr")`、`gmptr(f32)`、`ubuf(f32, N, stages=k)`、`sync(pipe, pipe, on=...)`、`mte2/mte3.copy`、`v.<op>` / `v.compute(name, ...)`、`v.select/m.duplicate` 等。可用指令集 = 冻结支持集（`evals/c1/freeze.json` support_set_ref）。
- 检查器（V001–V010）在本地拦截非法 IR 并给出诊断；代码生成产出 `.asc`。这些本地反馈不占上板次数。
- 提交物：7 个 `.py` 文件（每任务一个内核函数）。

## 6. 对照臂接口

- 直接写 `.asc`（每任务一个文件）：内核函数 + `extern "C" launch_<task>(...)` 包装（`<<<1,0,stream>>>`），由上板环境用 bisheng 编译并按 torch 直调插件挂载执行。
- 允许面 = `evals/c1/scans/allowed_surface.json`（其中的 asc_* 记号 + 搬运/同步原语）；越面候选作废。
- 提交物：7 个 `.asc` 文件。

## 7. 执行与判分（上板环境执行，Agent 可见流程）

- 你的提交按到达顺序被构建与执行：数值门（两组必测输入）通过 = 该任务成功；任一组失败 = 该内核失败，可修复后重新提交（重新执行计上板次数）。
- 合规正确且数值门通过后，上板环境用计时组输入测 kernel-only 中位时延（cann-bench PerfEvaluator 同入口）；全部任务分类为带宽顶满（h<0.20），判词只看成功次数，不因速度判输赢。
- 扫描：IR 臂源码过逃逸扫描，对照臂源码过越面扫描；命中即该候选作废。
- token 计量：T = 该 run 截至首次「全部 7 任务数值门通过」时的**会话累计 completion_tokens**（provider usage 为准）；工具回传是否另计、按哪个 usage 键计，在第一份试点发出前写死进 freeze.json 并封存 runner 侧 usage 原文哈希。
