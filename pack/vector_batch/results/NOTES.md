# 四个向量算子上板验证记录（vector-batch-verify 分支）

## 最终结果

- 设备：`Ascend950PR_9589`（device.txt）
- CANN：`/usr/local/Ascend/cann-9.1.0`（bisheng clang 15.0.5，`--npu-arch=dav-3510 -xasc`）
- 被测提交：`e8bcd7c`（= master 4ce7894 + 本分支三个修复提交）
- **最终编译：成功（build_exit=0）**；**数值检查：通过（check_exit=0）**

数值输出（check.txt 原文）：

```
add_G1 dtype torch.float32 numel 16384 nan 0 max_abs 0.0 tol_ok True bit 16384 / 16384
leakyrelu_G1 dtype torch.float32 numel 16384 nan 0 max_abs 0.0 tol_ok True bit 16384 / 16384
cast_G1 dtype torch.float32 numel 1024 nan 0 max_abs 0.0 tol_ok True bit 1024 / 1024
reduce_ones lane_sum 256.0 golden 256.0 abs_err 0.0 nan 0
reduce_small lane_sum 1.3183293342590332 golden 1.3183294534683228 abs_err 1.1920928955078125e-07 nan 0
```

判定：add / leakyrelu / cast 与 CPU golden **逐位一致**（容差 atol=rtol=1e-6 亦全过，未放宽）；reduce_sum 全 1 输入精确，随机小数输入 abs_err=1.19e-07 —— 内核按 8 lane 做部分和、host 端再求和，与 torch 的求和舍入顺序不同，属**浮点求和顺序差异，非实现错误**。

## 修复历程（四轮，每轮原始日志在 results/）

| 轮 | 被测提交 | 结果 | 失败原因 → 修复 |
|---|---|---|---|
| 1 | 4ce7894（master 原样） | build_exit=1 | cast 内核用了 devkit-only API（`asc_loadalign_unpack` / `ASC_POSITION_EVEN`），CANN 9.1.0 原生 c_api 树无此符号（`build_attempt_4ce7894.log`） |
| 2 | a123a61 | build_exit=1 | `_C` 目标 extension.cpp 找不到 `Python.h`（`build_attempt_a123a61_pythonh.log`） |
| 3 | 2cd5c1a | build_exit=1 | 内核 .o 缺 `-fPIC`，链入共享库失败（`build_attempt_2cd5c1a_fpic.log`） |
| 4 | e8bcd7c | **build_exit=0, check_exit=0** | 四算子全部通过 |

## 本分支改过的文件

- `a123a61` — `csrc/ops/cast_half_to_float/op_kernel/cast_half_to_float_kernel.cpp`
- `2cd5c1a` — `CMakeLists.txt`（`_C` 目标补 `${Python3_INCLUDE_DIRS}`）
- `e8bcd7c` — `CMakeLists.txt`（bisheng 直调命令补 `-fPIC`）

（4ce7894 的「用 add_custom_command 直调 bisheng 编内核」修复是 master 侧提交，不在本分支改动内。）

## 设计问题（供 AscendC-IR 侧参考）

1. **cast 拆包 API 断层（AscendC-IR 侧问题）**：内核按 asc-devkit 扩展 API 书写（`asc_loadalign_unpack` + `asc_half2float(..., ASC_POSITION_EVEN)`，出自 `asc-devkit/examples/02_simd_c_api/03_c_api/02_reg_vector_compute/cast/cast.asc`），但测量清单 manifest v1.2 已决定构建统一用 CANN 9.1.0 原生 asc 树（弃用 devkit overlay/shim），原生树没有这些符号。**不是算法错误**——语义等价的原生序列存在，且就是 CANN 自带 Cast Level-2 的实现方式：
   - `vlds(src, x + i*64, 0, UNPK_B16)`：解包装载 64 个 half 进偶位槽（devkit 的 `asc_loadalign_unpack` 实现同为 `vlds(..., UNPK_B16)`，见 devkit `impl/.../asc_loadalign_impl.h:556`）
   - `asc_half2float(dst, src, vmask)`：即 `vcvt(..., PART_EVEN)`，按序取出偶位 64 个（原生 `c_api/reg_compute/reg_convert.h:996`；CANN 自带 `asc/impl/basic_api/dav_m310/kernel_operator_vec_vconv_impl.h` 的 `LV2_LOAD_UPPER` 用 `vlds(..., UNPK_B16)`、`VCVT_F16_TO_F32` 用 `vcvt PART_EVEN`，循环步进 64 与本内核一致）
   - 修复后输出与 golden **逐位一致（1024/1024）**，证明语义等价成立
   - 建议：AscendC-IR 的 3510 代码生成/示例要么统一钉死 devkit 头，要么提供原生 API 的 cast lowering，二者取一，不要混用两套符号面
2. **CMake 公共 include 列表缩水**：M0 包（`pack/vector_add_m0/submissions/*/CMakeLists.txt`）的公共 `INCLUDE_DIRECTORIES` 含 `${Python3_INCLUDE_DIRS}`，vector_batch 的 CMakeLists 漏了它——`extension.cpp` 经 `torch/extension.h` 间接包含 `<Python.h>`。前两轮内核编不过时该目标从未被编到，缺陷被掩盖。
3. **custom command 绕过 CMake 的 PIC 机制**：4ce7894 为绕开「project() 后改 `CMAKE_CXX_COMPILER` 无效」改用 add_custom_command 直调 bisheng，但 custom command 不经过 `POSITION_INDEPENDENT_CODE` 属性，内核 .o 需显式 `-fPIC` 才能链入 `_C.abi3.so`（ld 报 `R_X86_64_PC32 ... can not be used when making a shared object`）。
4. **（观察，未改）reduce_sum 求和顺序**：reduce_small 的 abs_err=1.19e-07 是 8-lane 部分和 + host 求和与 torch 求和的舍入顺序差异，不是实现错误；容差保持 check_batch.py 冻结值（atol=rtol=1e-6）未动。

## 复现

`device.txt` / `build.log` / `check.txt` 为最终轮（e8bcd7c）原始输出；`build_attempt_*.log` / `device_attempt_*.txt` 为前三轮失败原始输出。构建命令：`bash build.sh --soc=ascend950 --install`；检查命令：`python3 scripts/check_batch.py`。
