# 0014 向量计算在 3510 上降级为 reg 向量风格

## 状态

已接受（2026-09-28）。修订代码生成的 add 映射；调度、IR、检查器与 ADR 0013 的软件流水不变。
依 M0 上板授权流程执行：先证明生成错误，再改 `emit.py`，重生成 golden，对齐 reference，整对重测。

## 背景

M0 上板准备时发现：`add_golden.asc` / `add_reference.asc` 使用的 UB 指针（memory-vector）版
`asc_add(dst, src0, src1, repeat, strides...)` 在 950PR（npu_arch 3510）上**没有实现**。证据：

1. CANN 9.2.0 内置树（`x86_64-linux/asc`）：`asc_simd.h` 的 3510 分支不含 `vector_compute.h`，
   其 `npu_arch_3510/.../asc_add_impl.h` 只有 reg 版（`vector_float&` 签名）；
2. asc-devkit `92ab0ff5f`（2026-08-27）：同上，3510 的向量计算 impl 只有 reg 版；
3. asc-devkit 上游 `c665de826`（2026-09-28）：impl 树重构为 `memory_base_impl` / `reg_base_impl`，
   UB 指针版向量计算 impl 仍然只挂在 `__NPU_ARCH__ == 2201` 分支。

同一份 wrapper 在 `--npu-arch=dav-2201` 下编译通过、在 `dav-3510` 下报 `asc_add` 未定义。
本机测量设备实测为 `Ascend950PR_9589`（950PR，3510），且协议钉死 M0 用该设备（2201 只做可移植检查）。
`@kernel(device="ascend950pr")` 声明目标 3510，而生成结果发出 3510 不存在的指令形式——构成生成错误。
搬运（`asc_copy_gm2ub` / `asc_copy_ub2gm`）与同步（`asc_sync_notify` / `asc_sync_wait`）在 3510 均有实现，
官方 dav-3510 文档样例即用同一同步风格。

## 决定

1. `emit.py` 对 `v.add` 在 3510 上降级为 reg 向量风格：`__simd_vf__` 内联函数
   （`asc_load` ×2 + `asc_add(reg, mask)` + `asc_store` 循环），写法逐行对齐官方样例
   `examples/02_simd_c_api/00_introduction/04_reg_base_add_compute/c_api_simd_add`。
   `asc_update_mask_b32` 的 `value` 是引用参数，每次调用自动减 64（VL=256B 的 b32 元素数），尾块由掩码收敛。
2. helper 每个内核只发一份，计算语句处发 `add_vf(src0, src1, dst, 单 stage 元素数)`；
   搬运、同步边、WAR 语义、event 分配、prologue/稳态/epilogue 切分全部不变。
3. 只核对 f32 的头文件签名；f16 fail-closed（明确报错），待签名核对后再开放。
4. 移除 `asc_add` 专属的 uint8 repeat 上限守卫（`repeat_time` 为 `uint16_t`）；新增
   「单 stage 字节数必须是 256B（VL）整数倍」的对齐检查。
5. `add_golden.asc` 由 `generate()` 重写；`add_reference.asc` 的 `#include` 之后指令流逐行与其一致。
6. **搬运 burst 单位修正（诊断发现，2026-09-28）**：3510 上 `asc_copy_gm2ub` / `asc_copy_ub2gm`
   的 6 参重载中 `burst_len` 单位为**字节**（官方 `asc_copy_gm2ub_arch_3510.md`；2201 文档为 32B 块数，
   同名参数两架构单位不同）。旧发射 `1, 256, 0, 0` 在 3510 上只搬 256 字节=64 个 f32——上板诊断内核
   实测：z 与 UB 源缓冲均从第 64 个元素起损坏，与该解释逐元素吻合（含 2 个偶然相等的零元素）。
   `_burst` 改为直接发单 stage 字节数，并加 `burst_len ≤ 65535`（uint16_t）守卫。

## 后果

计算段从单条 `asc_add` 变为一次 helper 调用（内部 VF 循环），M0 配对两边同形，tax 判据不变。
稳态循环里仍没有 `if`（helper 内的 VF `for` 是确定性循环，不是守卫分支）。
golden 字节与 2026-09-27 审定版不同，重审以本 ADR 与 `generate()` 可复现性为准。

## 推翻条件

- 任一 SDK 来源为 3510 提供 UB 指针版向量计算实现，且官方样例改回该风格。届时恢复单条
  `asc_add` 发射，本 ADR 的 f32/f16 与对齐检查随之复核。
- CANNBench 测出本对中位差超过 5% 或单对超过 10%。先查包装、编译选项与 csv 过滤，再决定是否
  调整 helper 写法（如展开 VF 循环），不把 `if` 写回稳态循环。
