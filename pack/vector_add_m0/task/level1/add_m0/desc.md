# Add（M0 配对测量任务）

ascendc-ir M0/M0b 的测量任务定义：冻结 shape 一维 16384 个 float32
（TILE=2048 × TILES=8，单核，`add_vf` data_len=2048 / VF repeat_time=32）。

- 候选 1（生成版）：`../submissions/add_generated`，kernel = `add_golden.asc`（`codegen.generate()` 输出）
- 候选 2（手写版）：`../submissions/add_reference`，kernel = `add_reference.asc`

测量清单、判分规则与容差见 `docs/evaluation/metrics.md`（2026-09-28 冻结，manifest v1.0）。
本任务不配 baseline（M0 判据为两候选间 tax，HAP/评分不作判据）。
