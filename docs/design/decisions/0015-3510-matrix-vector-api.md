# 0015 第一批按 3510 头文件设计矩阵与向量 IR

## 状态

已接受（2026-09-30）。业主要求在下一次上板前，把 3510 的矩阵计算和向量计算设计进 IR，不再按「语料里数到两次才准入」把 Cube 留到以后。

## 借鉴

CAKE（arXiv:2608.12629）里采用的是：调度写清角色、缓冲、搬运和交接；地址、事件号由编译器推导；布局不做成一套代数，只记录具体存放决定，再由检查器看它和指令是否相符。诊断要指出违反的约束和该改的调用点。

Croqtile（https://github.com/LancerLab/croqtile）里采用的是：编译器返回的不是通过或失败，而是约束、推导和建议修法。tile、流水深度和角色写在表面，不藏进宏。

这两点落到 3510 上，角色是向量 PIPE 和矩阵 PIPE，存放决定是 GM、UB、L1、L0A、L0B、L0C，以及 ND 到 NZ。不引入 CUDA 的 warp 和 layout 代数。

## 决定

1. 词汇以 asc-devkit `579cf014` 的公开声明为准，范围是 `reg_compute`、`cube_compute`、`cube_datamove`。目录在 `src/ascendc_ir/catalog/api_3510.json`，用 `scripts/extract_3510_api.py` 重抽。寄存器 load/store 算编译器内部，Agent 不直接写。
2. 这一批真正生成 C 的只有：已经核对过的向量加、leakyrelu、cast、归约；签名是「目的、同类型源、mask」且不读目的寄存器、mask 只作尾块谓词的 f32 逐元素运算；按 asc-devkit `02_simd_c_api` 样例角色补的 `select`（UB packed bits 谓词）、`select_gt` / `select_lt` / `select_ne` / `select_eq` / `select_ge` / `select_le` 及其标量形式（编译器持有比较掩码）、`duplicate`（仅标量填向量）、`arange`（等差数列，无源）；头文件规范形为 `vector_int32_t` 的 `xor`、`shiftleft`、`shiftright` 及两个标量移位；以及一条 f16 的 `mmad` 通路（GM→L1 ND 转 NZ，L1→L0A/L0B，一次 `asc_mmad`，L0C→GM 转回行优先）。`axpy` 无独立 C 样例调度角色（cann-samples 是 Muls+Add），不发明；f32 矩阵乘的 K 粒度是 8 并且样例要转置，这一批不生成。
3. B 在 GM 和 L1 上按 (n, k) 存放，结果是 A[m, k] @ B.T。K 可以分块：第 0 轮 `init` 为真，其后各轮为假，块与块之间发 `asc_sync_pipe(PIPE_M)`。`nd2nz` 的 `row_stride` 是 GM 上的行宽，用来搬 K 方向的一段。循环后的写回不放进循环体。
4. 目录里有、模板里没有的名字可以写进 trace，检查器 V013 拒绝生成，并给出头文件签名。禁止猜一个重载。
5. 同一个核里不同时放 UB 向量缓冲和 Cube 缓冲。混排留到下一批。

## 后果

向量加的既有降级保持不变。新的矩阵核用 `__global__ __cube__`。上板包只编译这两类已生成的核；缺符号时报告符号，不用另一套头文件覆盖。

## 推翻条件

- CANN 9.1.0 的 3510 头文件里没有本决定发出的某个符号，且不存在同语义的原生替代。
- 官方样例证明 B 的 (n, k) 布局或单次 `mmad` 与硬件结果不符。
- 逐元素模板套到了会读目的寄存器的指令上，数值和手写核不一致。
