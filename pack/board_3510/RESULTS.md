# 3510 一次上板核对结果

基线：master `d3a37d7`（feat: 一次上板核对现有 3510 降级）的 `pack/board_3510`，50 个 IR 生成核。
设备：Ascend 950（`Ascend950PR_9589`），CANN 9.1.0（`/usr/local/Ascend/cann-9.1.0`，bisheng 同树 `bin/bisheng`），架构 `dav-3510`，单核（全部 `<<<1,0,stream>>>`）。环境记录见 `logs/env.txt`。
判定：`scripts/check_ir.py`，N=64；div/exp/ln/log/sqrt/leakyrelu 按 `1e-4 + 1e-4*|golden|` 相对容差，其余逐位一致。`dn2nz` 本包无核，未测，也未补实现。

## 结论一览

| 分类 | 数量 | 核 |
| --- | --- | --- |
| 逐位一致 | 32 | 见下 |
| 容差内通过 | 3 | op_div、op_ln、op_sqrt |
| 数值不对 | 2 | op_ceil、op_trunc（负零符号位） |
| 没编过（SKIP） | 13 | 见下 |

`check_ir.py` 打印 `failed 15 of 50`（= 13 个未注册 EXC + 2 个数值不对）。逐行输出见 `logs/check_attempt2.txt`，复跑逐行一致（`logs/check_rerun.txt`）。

## 逐位一致（32）

op_add、op_sub、op_mul、op_max、op_min、op_and、op_or、op_prelu、op_abs、op_exp、op_floor、op_neg、op_not、op_relu、op_rint、op_round、op_add_scalar、op_leakyrelu、op_select、op_select_gt、op_select_lt、op_select_ne、op_select_eq、op_select_ge、op_select_le、op_xor、op_shiftleft、op_shiftright、op_shiftleft_scalar、op_shiftright_scalar、op_cast、op_repeat_reduce_sum。

均为 `bit 64/64`、`max_abs 0.0`（op_cast 为 f16→f32，64/64；op_repeat_reduce_sum 为 64 个 1.0 求和，`lane_sum 64.0` 精确）。
op_or 的 `nan 23` 说明：golden 是把两个 f32 的位型按位或（`(x.view(int32) | y.view(int32)).view(float32)`），构造本身产生 23 条 NaN 位型（如 `0x7fb00000`），内核输出与 golden 64/64 位相等，非缺陷（见 `logs/probe_ceil_trunc_or.txt` 末段）。

## 容差内通过（3）

| 核 | bit | max_abs | 容差 |
| --- | --- | --- | --- |
| op_div | 60/64 | 5.96e-08 | ≤1e-4(1+|golden|) ✓ |
| op_ln | 45/64 | 1.19e-07 | ✓ |
| op_sqrt | 55/64 | 1.19e-07 | ✓ |

## 数值不对（2）：op_ceil、op_trunc

- 现象：`bit 55/64`、`max_abs 0.0`——值差为 0，但符号位不一致。
- 定位（`logs/probe_ceil_trunc_or.txt`，实际输出全文）：输入 `x=(i%7)-3+0.125` 中 `x=-0.875` 的 9 条 lane（i%7==2：lane 2,9,16,23,30,37,44,51,58），内核输出 `0x00000000`(+0.0)，golden 为 `0x80000000`(-0.0)。其余 55 条逐位一致。
- 结论：`asc_ceil`/`asc_trunc` 对 (-1,0) 区间输入返回 +0.0，与 IEEE 754 的 ceil/trunc（保留符号，ceil(-0.875)=trunc(-0.875)=-0.0）不一致。值级误差为 0，纯符号位差异；ceil/trunc 不在容差类，按逐位判据计为不对。
- 当时编译进设备的源码：`csrc/ops/op_ceil/op_kernel/op_ceil_kernel.cpp`、`csrc/ops/op_trunc/op_kernel/op_trunc_kernel.cpp`，与 d3a37d7 完全一致（本分支未改任何内核源码，`git diff d3a37d7 -- csrc` 为空）。

## 没编过（13，SKIP 原文在各核目录 `SKIP` 文件）

第一轮规范构建在首个错误处中止（`logs/build_attempt1.log`），随后用 `cmake --build -- -k` 一次性枚举全部编译错误（`logs/build_attempt1_keepgoing.log`，仅诊断，未改包内构建）。13 个核分两类：

**类 A：浮点字面量发射缺陷，11 个核。** 生成器把浮点标量发射成 `0f/1f/2f/3f`（应为 `0.0f/1.0f/2.0f/3.0f`），bisheng 原文：

- op_arange（`0f`，octal 报错）：`op_arange_kernel.cpp:30:27: error: invalid digit 'f' in octal constant`
- op_duplicate（`3f`）、op_max_scalar/op_min_scalar（`1f`，:36:38）、op_mul_scalar（`2f`）、op_select_{eq,ge,gt,le,lt,ne}_scalar（`1f`，:42:51）：`error: invalid digit 'f' in decimal constant`

**类 B：CANN 9.1.0 缺符号，2 个核。**

- op_log：`op_log_kernel.cpp:21:9: error: use of undeclared identifier 'asc_log'`（寄存器形态 `asc_log(reg_dst, reg_src, vmask)`）。9.1.0 的 dav-3510 分支 `asc_simd.h` 只引入 `reg_compute/reg_vector.h`（寄存器 API），其中自然对数叫 `asc_ln`，不存在 `asc_log`；指针形态 `asc_log(__ubuf__ float* dst, __ubuf__ float* src, uint32_t count)` 声明在 `vector_compute.h`，但该头只在 2201 分支被 `asc_simd.h` 引入。op_log 与 op_ln 的 golden 同为 `torch.log`（自然对数），生成器对 log 发 `asc_log` 即断层。
- op_mmad：10 处 `use of undeclared identifier`（原文见 `csrc/ops/op_mmad/SKIP`）：`asc_load_l2_cache_mode`（:21,:23,:38,:41）、`asc_unit_flag_mode`（:32,:51,:56）、`asc_set_l0c_copy_nz_para`（:55）、`asc_store_l2_cache_mode`（:56）、`asc_relu_pre_mode`（:56）。这些枚举/函数属于更新版 CANN 的 cube c_api。9.1.0 原生形态（`x86_64-linux/asc/include/c_api/cube_datamove/cube_datamove.h`、`cube_compute/cube_compute.h`）为：
  - `asc_copy_gm2l1_nd2nz(dst, src, nd_num, n_value, d_value, src_nd_matrix_stride, src_d_value, dst_nz_c0_stride, dst_nz_n_stride, dst_nz_matrix_stride)`——10 参，无 L2 模式枚举、无 bool；
  - `asc_copy_l0c2gm(dst, src, n_size, m_size, dst_stride_dst_d, src_stride, uint8_t unit_flag_mode, uint64_t quant_pre, uint8_t relu_pre, bool channel_split, bool nz2nd_en)`——原始整型/布尔参数；
  - 配套 `asc_set_l0c2gm_config(uint64_t relu_pre, uint64_t quant_pre, bool enable_unit_flag)`，而非 `asc_set_l0c_copy_nz_para`。

处理后按包内机制写入 `csrc/ops/<op>/SKIP`（内容=编译器原文），重新走规范 `bash build.sh --soc=ascend950 --install`，`build2_exit=0`，37 个核全部编出并链接（`logs/build_attempt2.log`）。

## 做法调整记录（允许范围内）

1. **make -k 诊断**：第一轮 make 在 op_arange 处中止，后续核未尝试。用 `cmake --build build/temp.linux-x86_64-3.10 -- -k` 枚举全部 13 个失败核（`logs/build_attempt1_keepgoing.log`）。未修改包内构建脚本。
2. **SKIP 机制**：13 个失败核按 README 写入 SKIP 后重建，规范构建成功。SKIP 文件随本分支提交。
3. **wheel 缺 `_C.abi3.so`（未调整，记录事实）**：`dist/ir_board-1.0.0-cp38-abi3-linux_x86_64.whl` 仅 1695 字节，内容只有 `ir_board/__init__.py` + dist-info（`logs/wheel_content2.txt`）。原因：setuptools `bdist_wheel` 的 `build_py` 先于 `build_ext` 运行，而 `build.sh` 先删了源目录 `ir_board/_C.abi3.so`，故 wheel 打不进 .so；cmake 随后只把新 .so 写进源码树。pip 安装态因此不完整（site-packages 副本无 .so，`logs/pip_show2.txt`）。
4. **检查实际加载的 .so**：规范命令 `python3 scripts/check_ir.py` 仍跑在新编的 .so 上——CANN `set_env.sh` 导出的 `PYTHONPATH` 以冒号结尾（空项=当前目录），该项位于 site-packages 之前，`import ir_board` 解析到包目录源码树（attempt1 的 traceback 路径与 `logs/import_installed.txt` 均印证）。被检 .so：`ir_board/_C.abi3.so`，md5 `d340a80ed7979951f783b288a403d485`，1720440 字节，恰含 37 个注册算子（13 个 SKIP 算子调用报 `AttributeError ... no attribute 'op_...'`，与 SKIP 集合一致）。复跑 `check_ir.py` 逐行一致（`logs/check_rerun.txt`）。

## 设计问题（供生成器/检查脚本作者）

1. 浮点标量字面量发射为 `Nf`（11 核编不过）；应发射 `N.0f`。
2. `op_log` 应发射 `asc_ln`（3510 reg API 的自然对数名），与 `op_ln` 一致。
3. `op_mmad` 的 cube 调用对准了更新版 CANN 的 API 形态；若要兼容 9.1.0 需按上文原生签名/参数形态发射（枚举 → 原始整型，`asc_set_l0c_copy_nz_para` → `asc_set_l0c2gm_config`）。目录 `src/ascendc_ir/catalog/api_3510.json` 的提取源版本高于本机 9.1.0。
4. `asc_ceil`/`asc_trunc` 对 (-1,0) 输入不保留零符号（与 IEEE 不一致）：要么 IR 层补符号处理，要么把 ceil/trunc 的判据改为「值相等且非 NaN 时 ±0 视为一致」。
5. `setup.py` 的 wheel 时序缺陷（见调整记录 3）：建议 cmake-build-first 或在 `build_ext` 后补拷贝 .so 到 build/lib，否则干净环境下 `--install` 装出的是不含 .so 的包。
6. `check_ir.py` 对 op_or 打印 `nan 23` 易误读（golden 按位或构造所致），可加一行说明。

## 环境

- 设备/编译器/时间线：`logs/env.txt`（attempt1: build_exit=1；attempt2: skip_count=13, build2_exit=0）
- 检查输出：`logs/check_attempt2.txt`、复跑 `logs/check_rerun.txt`、attempt1 导入失败原文 `logs/check_attempt1.txt`
- 数值不对的实际输出：`logs/probe_ceil_trunc_or.txt`
- 构建日志：`logs/build_attempt1.log`、`logs/build_attempt1_keepgoing.log`、`logs/build_attempt2.log`
- wheel/安装态：`logs/wheel_content2.txt`、`logs/pip_show2.txt`、`logs/import_installed.txt`、`logs/dist_listing2.txt`
