# 一次上板验证：四个向量算子

单核。设备必须是 Ascend 950。不要改内核源码。

```bash
bash build.sh --soc=ascend950 --install
python3 scripts/check_batch.py
```

算子：`add_f32_16384`、`leakyrelu_f32`、`cast_half_to_float`、`reduce_sum_f32`。

验证结束后，把结果提交到分支 `vector-batch-verify` 并推送到 GitHub。不要只在对话里贴日志。
