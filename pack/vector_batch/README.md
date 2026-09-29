# 一次上板验证：四个向量算子

单核。设备必须是 Ascend 950。不要改内核。

```bash
bash build.sh --soc=ascend950 --install
python3 scripts/check_batch.py
```

算子：`add_f32_16384`、`leakyrelu_f32`、`cast_half_to_float`、`reduce_sum_f32`。

编译失败带回完整日志。运行失败带回完整报错。成功时原样带回脚本打印的 `add_G1`、`leakyrelu_G1`、`cast_G1`、`reduce_ones`、`reduce_small`，以及设备名和 CANN 版本。
