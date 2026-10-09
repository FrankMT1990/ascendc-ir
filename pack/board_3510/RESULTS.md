# 3510 上板核对结果（两轮）

设备：Ascend 950（`Ascend950PR_9589`），CANN 9.1.0（`/usr/local/Ascend/cann-9.1.0`，bisheng 同树），架构 `dav-3510`，单核（全部 `<<<1,0,stream>>>`）。
判定：`scripts/check_ir.py`，N=64；div/exp/ln/log/sqrt/leakyrelu 按 `1e-4 + 1e-4*|golden|` 相对容差；ceil/trunc 按正负零判据（512950c 起 `SIGNED_ZERO_OPS`，±0.0 等价）；其余逐位一致。`dn2nz` 无核，两轮均未测、未补实现。

## 第二轮（基线 512950c，fix: 按 9.1.0 上板结果改生成）

分支历史：512950c 合入 board-3510（merge `7e4285f`），删除第一轮 13 个 SKIP（`2829ff1`），重新全量构建。

**结论：49/50 通过，唯一没编过的是 op_mmad。** `check_ir.py` 打印 `failed 1 of 50`（op_mmad 未注册 EXC）。逐行输出见 `logs/round2b_check.txt`，复跑逐行一致（`logs/round2b_check_rerun.txt`），被检 .so 为 `ir_board/_C.abi3.so` md5 `cc0a42fa5d5f934e4b2ab24c4dfd9148`（49 算子，源码树解析机制同第一轮，`logs/round2b_import.txt`）。

### 第一轮没编过的 13 核（本轮验证）

- **逐位一致 64/64（11）**：op_arange、op_duplicate、op_max_scalar、op_min_scalar、op_mul_scalar、op_select_gt_scalar、op_select_lt_scalar、op_select_ne_scalar、op_select_eq_scalar、op_select_ge_scalar、op_select_le_scalar——浮点字面量 `0.0f/1.0f/2.0f/3.0f` 修复后编译通过且数值全对。
- **容差内（1）**：op_log——`asc_ln` 修复后编译通过；`bit 45/64`、`max_abs 1.19e-07`，与 op_ln 完全一致（同一 intrinsic、同一输入），golden 均为自然对数。
- **仍没编过（1）**：op_mmad，见下。

### op_ceil / op_trunc（新判据）

按正负零判据 `ok True`：`bit 55/64`，9 条 `x=-0.875` lane 为 +0.0 vs golden -0.0（第一轮已定位，`logs/probe_ceil_trunc_or.txt`），值差 0，±0 等价通过。其余 55 条逐位一致。`asc_ceil`/`asc_trunc` 不保留负零符号的硬件行为未变，只是判据放宽。

### op_mmad 仍没编过（SKIP，原文在 `csrc/ops/op_mmad/SKIP`，218 行）

512950c 的整型参数化只对了一半：`asc_mmad(..., 0, ...)`、`asc_set_l0c2gm_nz2nd(1, 0, 0)`、`asc_copy_l12l0a/b` 无报错（签名匹配），但搬运/写回两处 5 个错误：

- 4 × `error: no matching function for call to 'asc_copy_gm2l1_nd2nz'`（:20 :21 :35 :37）——10 参调用，3510 分支全部重载为 8 参。
- 1 × `error: no matching function for call to 'asc_copy_l0c2gm'`（:52）——11 参调用，3510 分支全部重载为 21 参。

**对第一轮记录的修正（重要）**：第一轮 RESULTS.md 里写的"9.1.0 原生形态"（10 参 `asc_copy_gm2l1_nd2nz`、11 参 `asc_copy_l0c2gm`）实际取自 `cube_datamove.h` 的 `__NPU_ARCH__ == 2201` 分支（171–995 行），当时没有检查 arch 守卫，把 2201 形态当成了 3510 的，误导了本轮生成。3510 分支（996–2650 行）的真实形态如下（本轮已逐一核对守卫）：

```c
// 3510 分支，8 参 loop 形态（cube_datamove.h 约 1912 行起，half 重载）
asc_copy_gm2l1_nd2nz(__cbuf__ half* dst, __gm__ half* src, uint64_t loop1_src_stride,
    uint8_t l2_cache_ctl, uint16_t n_value, uint32_t d_value,
    uint64_t loop4_src_stride, bool smallc0_en);

// 3510 分支，21 参形态（cube_datamove.h 约 2297 行起，void*/float* 重载）
asc_copy_l0c2gm(__gm__ void *dst_addr, __cc__ float *src_addr,
    uint16_t n_size, uint16_t m_size, uint32_t loop_dst_stride, uint16_t loop_src_stride,
    uint8_t l2_cache_ctl, uint8_t clip_relu_pre, uint8_t unit_flag_ctl, uint64_t quant_pre,
    uint8_t relu_pre, bool split_en, bool nz2nd_en, uint64_t quant_post, uint8_t relu_post,
    bool clip_relu_post, uint8_t eltwise_op, bool eltwise_antq_en, bool c0_pad_en,
    bool broadcast_en, bool nz2dn_en);
```

下一轮生成需要按 3510 分支的 8 参 gm2l1 搬运与 21 参 l0c 写回发射（含 l2_cache_ctl 等控制字节），`asc_mmad`/`asc_set_l0c2gm_nz2nd`/`asc_copy_l12l0a/b` 维持现状即可。K 分两段（a+16/b+16 偏移）、A(n,k)×B(n,k)^T→f32 的语义核对待 mmad 编过后进行。

### 其余 35 核

第一轮已通过的 35 核（32 位一致 + div/ln/sqrt 容差）全部复现通过，数值逐行不变。

### 做法调整记录（本轮）

1. **op_mmad SKIP**：第三轮规范构建（`logs/round2_build.log`）在 op_mmad 处 exit 2，前 18 个内核已编过、字面量与 asc_ln 修复已验证生效。按 README 机制把 5 处错误原文写入 `csrc/ops/op_mmad/SKIP`，第四轮规范重建（`logs/round2b_build.log`，`round2b_build_exit=0`，99 个目标 = 49 插件 + 49 内核 + extension）。
2. wheel 仍为 1695 字节、不含 `_C.abi3.so`（`logs/round2b_wheel.txt`）——setup.py 时序缺陷 512950c 未修；检查仍经源码树 `.so`（机制见第一轮记录），不影响结论。

### 设计问题（更新）

1. （已修复）浮点字面量 `Nf` → `N.0f`：11 核编译并数值通过。
2. （已修复）op_log 发射 `asc_ln`：编译并容差内通过。
3. （未修复）op_mmad 的 gm2l1/l0c 搬运形态仍是 2201 分支的 10 参/11 参签名，3510 分支为 8 参 loop/21 参形态——生成器目录需按 arch 分支区分 cube API 形态。
4. `asc_ceil`/`asc_trunc` 负零行为未变，判据已在 check_ir.py 放宽（`SIGNED_ZERO_OPS`）。
5. （未修）setup.py wheel 时序缺陷。

---

## 第一轮（基线 d3a37d7，历史记录）

基线：master `d3a37d7`（feat: 一次上板核对现有 3510 降级）。第一轮的 SKIP 文件已在本轮删除（`2829ff1`），其内容（13 核编译错误原文）永久保留在本分支历史 `e959a4a` 提交中。

| 分类 | 数量 | 核 |
| --- | --- | --- |
| 逐位一致 | 32 | add/sub/mul/max/min/and/or/prelu/abs/exp/floor/neg/not/relu/rint/round/add_scalar/leakyrelu/select/select_gt/lt/ne/eq/ge/le/xor/shiftleft/shiftright/shiftleft_scalar/shiftright_scalar/cast/repeat_reduce_sum |
| 容差内 | 3 | div（60/64，5.96e-08）、ln（45/64，1.19e-07）、sqrt（55/64，1.19e-07） |
| 数值不对 | 2 | ceil、trunc（-0.0 符号位，9/64 lane，值差 0）——第二轮已按正负零判据通过 |
| 没编过 | 13 | 字面量缺陷 11（arange/duplicate/max_scalar/min_scalar/mul_scalar/select_*_scalar ×6）+ 缺符号 2（op_log 的 asc_log、op_mmad 的 cube 枚举）——第二轮 12 个已修复通过，op_mmad 仍缺 |

op_or 的 `nan 23`：golden 按位或构造产生 23 条 NaN 位型，内核 64/64 位相等，非缺陷（`logs/probe_ceil_trunc_or.txt`）。

第一轮做法调整：`cmake --build -- -k` 枚举全部编译失败（`logs/build_attempt1_keepgoing.log`，仅诊断）；SKIP 机制重建（`logs/build_attempt2.log`）；wheel 缺 .so 与源码树 .so 解析机制的完整记录见第一轮日志（`logs/wheel_content2.txt`、`logs/import_installed.txt`、.so md5 `d340a80ed7979951f783b288a403d485`）。

## 环境与日志索引

- 第一轮：`logs/env.txt`、`logs/build_attempt1.log`、`logs/build_attempt1_keepgoing.log`、`logs/build_attempt2.log`、`logs/check_attempt1.txt`、`logs/check_attempt2.txt`、`logs/check_rerun.txt`、`logs/probe_ceil_trunc_or.txt`
- 第二轮（第三/四次构建）：`logs/round2_env.txt`、`logs/round2_build.log`（512950c 全量，op_mmad 失败）、`logs/round2_check.txt`（该轮导入失败原文）、`logs/round2b_build.log`（mmad SKIP 后成功）、`logs/round2b_check.txt`、`logs/round2b_check_rerun.txt`、`logs/round2b_import.txt`、`logs/round2b_wheel.txt`、`logs/round2b_dist.txt`
