# C1 任务书（草案 v1，信息对齐细节待业主确认后冻结）

实验对象 Agent 在受控条件下完成下列任务之一，产出一个能在 Ascend950PR_9589 上编译执行的内核。判词与协议见 `docs/evaluation/claims.md`（v2.8）；任务清单与封存数值见 `evals/c1/freeze.json`。

## 共同约束（两臂相同）

- 设备：Ascend950PR_9589，CANN 9.1.0（`/usr/local/Ascend/cann-9.1.0`），架构 dav-3510，**单核**（`<<<1,0,stream>>>`；无多核切分词汇；Cube 接口本批任务不出现）。
- 数值门：逐元素 `abs(输出 − golden) ≤ atol + rtol × abs(golden)`，atol=1e-5、rtol=1e-4，golden dtype=f32；NaN/形状不一致即失败（`evals/c1/tolerance.json`，哈希已封存）。
- 必测输入两组（计时组+边界组），以封存哈希验证一致后才可计分；计时只认计时组。
- 每次运行上板上限 20 次；超限即终止。
- `examples/`、参考 `.asc`、asc-devkit 示例与专家内核对两臂都不可见。
- 提交物：源码文件（IR 臂：`.py` IR 源；对照臂：`.asc`/`.cpp`）；上板环境负责构建、执行、计时（CANNBench kernel-only 同入口）与扫描（逃逸/越面）。

## 任务列表（冻结自 `evals/c1/freeze.json`）

| 任务 | 计时输入 shape/attrs | 数值语义 |
|---|---|---|
| exp_f32 | [2048,2048] f32，base=-1.0（自然指数），scale=1.5，shift=0.0 | y = exp(1.5·x) |
| sigmoid_f32 | [2048,2048] f32 | y = 1/(1+exp(−x)) |
| gelu_f32 | [8192,8192] f32，approximate=tanh | y = 0.5·x·(1+tanh(√(2/π)·(x+0.044715·x³))) |
| mish_f32 | [2048,2048] f32 | y = x·tanh(ln(1+exp(x))) |
| masked_scale_f32 | x [2048,2048] f32，掩码按 select 位打包形态给出（字节=f32 个数×4/8），scale=1.0 | y = x·m·scale（m∈{0,1}；等价 select(m, x, 0)） |
| swi_glu_f32 | [2048,4096] f32，dim=-1（末维分半 x0/x1） | y = x0·sigmoid(x0)·x1 |
| foreach_addcdiv_f32 | x1/x2/x3 各 [2,1024,1024] f32（连续父张量视角），scalar=1.0 | y_i = x1_i + (x2_i/x3_i)·1.0，两个 tensor 各自独立计算 |

## IR 臂（工具链臂）

- 用 `ascendc_ir`（`@kernel`、`gmptr`、`ubuf`、`sync`、`mte2/mte3/v`）写调度；检查器拦截非法 IR（V001–V010）；代码生成产出 `.asc`。
- 可用指令即冻结支持集（`evals/c1/freeze.json` support_set_ref）；超越函数需用基础指令组合。
- 提交物只含 `.py` 源码；扫描检测逃逸（字面 asc_*、动态指令名、exec/eval、另写 .asc、内嵌 C 字符串）。

## 对照臂（直接写 C API）

- 直接写 `.asc`（Ascend C C API，`#include "c_api/asc_simd.h"`），由上板环境用 bisheng（`--npu-arch=dav-3510 -xasc -fPIC`）编译。
- 允许面 = `evals/c1/scans/allowed_surface.json`（冻结支持集内的 asc_* 记号+搬运同步原语）；Cube 接口与多核切分词汇命中即越面作废。
- 【待业主确认】给对照臂的 API 形态提示边界：头文件位置（`$ASCEND_HOME_PATH` 下的 `asc/include/c_api/`）与 3510 已验证形态（寄存器向量接口、搬运按字节、正负零语义）给出到什么程度，需要与 IR 臂工具链的信息量对齐。

## 计时与判词（由上板环境执行）

- T_best：该 run 最佳合规内核的 kernel-only 中位时延（cann-bench PerfEvaluator 同入口）；输入必须是计时组（哈希一致）。
- 全部任务分类为带宽顶满（h<0.20，见 freeze.json）；判词只看成功次数与扫描合规，不因 rel 判输赢。
- token 计量：T = completion_tokens + 工具回传 token（键名于正式开跑前写死并封存 usage 原文哈希）；任务书固定前置两臂等额，不占预算 B。
