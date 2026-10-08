# 3510 一次上板：批量核对现有 IR

单核。设备是 Ascend 950，CANN 9.1.0，架构 `dav-3510`。不要改核里的计算。不要用开发套件的头文件覆盖这套 CANN。

本包覆盖当前已经能生成 C 的降级：f32 逐元素、比较后选择、`select`、`duplicate`、`arange`、f16 转 f32、64 个数求和、int32 的异或和移位，以及 K 分两段的 f16 矩阵乘。`dn2nz` 没有单独的核，这次不测。加、leakyrelu、cast、求和以前用别的核测过，这里用 IR 重新生成的小核再对一次数。

```bash
bash build.sh --soc=ascend950 --install
python3 scripts/check_ir.py
```

某个核编译失败时：把编译器原文写进该核目录的 `SKIP` 文件（例如 `csrc/ops/op_exp/SKIP`），再执行上面的两条命令。`build.sh` 会丢掉上一次的构建目录。缺符号就记下符号名，继续剩下的核。

数值脚本会打印每一条的 `bit` 或 `max_abs`。退出码 0 表示打印出来的核都对上了。被 SKIP 的核不在这次数值结果里。

核：`op_add`、`op_sub`、`op_mul`、`op_div`、`op_max`、`op_min`、`op_and`、`op_or`、`op_prelu`、`op_abs`、`op_ceil`、`op_exp`、`op_floor`、`op_ln`、`op_log`、`op_neg`、`op_not`、`op_relu`、`op_rint`、`op_round`、`op_sqrt`、`op_trunc`、`op_add_scalar`、`op_max_scalar`、`op_min_scalar`、`op_mul_scalar`、`op_leakyrelu`、`op_select`、`op_select_gt`、`op_select_lt`、`op_select_ne`、`op_select_eq`、`op_select_ge`、`op_select_le`、`op_select_gt_scalar`、`op_select_lt_scalar`、`op_select_ne_scalar`、`op_select_eq_scalar`、`op_select_ge_scalar`、`op_select_le_scalar`、`op_duplicate`、`op_arange`、`op_xor`、`op_shiftleft`、`op_shiftright`、`op_shiftleft_scalar`、`op_shiftright_scalar`、`op_cast`、`op_repeat_reduce_sum`、`op_mmad`。

结果写进本目录的 `RESULTS.md`，推到分支 `board-3510`。
