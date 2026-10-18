# 算子评测报告

**评测代号**: cann_correctness_eval_20260928_232520
**评测时间**: 2026-09-28T23:25:20.922851
**设备**: npu:0
**框架版本**: V1.0.0
**评测集版本**: tasks-v1.0.0

## 概览

| 指标 | 数值 |
|------|------|
| 评测算子数 | 1 |
| 总用例数 | 1 |
| 通过用例数 | 0 |
| 失败用例数 | 1 |
| 通过率 | 0.00% |
| 综合得分 | 0.00 |

## 算子详情

### Add（level1/add_m0）

| 指标 | 数值 |
|------|------|
| 用例数 | 1 |
| 通过数 | 0 |
| 失败数 | 0 |
| 通过率 | 0.00% |
| 平均加速比 | 0.00x |
| 编译/运行得分 | 0.00 |
| 精度得分 | 0.00 |
| 性能得分 | 0.00 |
| 得分 | 0.00 |

| 用例ID | 状态 | 耗时(μs) | 加速比 | 精度误差 |
|--------|------|----------|--------|----------|
| level1/add_m0_1 | ❌ | N/A | N/A | AI算子执行失败: cann_bench::add() is missing value for argument 'x'. Declaration: cann_bench::add(Tensor x, Tensor y) -> Tensor
Traceback (most recent call last):
  File "/home/w00964611/cann-bench/src/kernel_eval/eval/op_runner.py", line 395, in _run_simple
    outputs = func(**updated_params)
  File "/usr/local/lib/python3.10/dist-packages/torch/_ops.py", line 1209, in __call__
    return self._op(*args, **kwargs)
  File "/home/w00964611/cann-bench/src/kernel_eval/security/torch_op_guard.py", line 313, in __torch_function__
    return func(*args, **kwargs)
  File "/usr/local/lib/python3.10/dist-packages/torch/_ops.py", line 1209, in __call__
    return self._op(*args, **kwargs)
RuntimeError: cann_bench::add() is missing value for argument 'x'. Declaration: cann_bench::add(Tensor x, Tensor y) -> Tensor |
