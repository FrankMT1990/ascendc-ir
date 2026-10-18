# M0 计时会话（2026-09-29，timing_20260929/）

环境修复后对 M0 抽象税的正式测量（M0b 数值一致性已于 09-28/29 会话完成并通过，见 `../m0b_results.txt`）。

## 环境修复事实（供复核）

- 2026-09-29 00:03 管理员为运行内核 5.4.0-125 重装驱动（版本串不变 9.1.T13.0.B130，`version.info` timestamp=20260929_000325090）；04:25:28 宿主机重启。即 09-28 会话阻塞根因（新用户态驱动配旧内核模块）按「为 -125 补装驱动」路径修复。
- 修复验证：prof 探针（`/tmp/prof_probe.py`，torch_npu profiler + tensorboard_trace_handler）产出 kernel_details.csv，无 prof_open 报错；探针同时验证内核位级一致 16384/16384。
- manifest v1.2 其余环境项（设备 Ascend950PR_9589、CANN 9.1.0、torch 2.10.0+cpu / torch_npu 2.10.0.post4、bisheng dav-3510）未变。

## 完整性（测前测后核验）

- pack 源码 39/39 条目与 `../frozen_hashes.txt` 一致；两提交构建系统与 examples 的 .asc 未动。
- harness 按其流程原地重建两候选：重建 `_C.abi3.so` 与冻结哈希**位级一致**（add_generated `186cdef9…`、add_reference `5d3fe8b8…`）——所测内核二进制即冻结版。
- wheel zip 因内嵌时间戳哈希变化（新：`ad12300a…` / `de30982c…`）；冻结版 wheel 与 .so 备份于 `prebuild_artifacts_backup/`（哈希与 frozen_hashes.txt 一致）。

## 测量（manifest 冻结参数）

`--warmup 3 --repeat 20 --device-id 0 --processes-per-card 1`；profiler schedule wait=0/warmup=3/active=20；两候选各一次正式 run。

## 结果

| 候选 | 中位时延（us，20 步） | harness elapsed（us） |
|---|---|---|
| add_generated（生成版） | **4.396** | 4.4 |
| add_reference（手写版） | **4.398** | 4.4 |

- **tax = 4.396 / 4.398 − 1 ≈ −0.05%**（生成版快 0.05%，在步间波动噪声内；两候选分布区间几乎完全重叠）
- 提案通过线（中位 ≤5% 且该对 ≤10%）：**通过**
- 判分原始输出与 csv 事实补注：`m0_timing_results.txt`；原始 kernel_details.csv 在 `add_{generated,reference}/prof_data/level1/add_m0/1/*/ASCEND_PROFILER_OUTPUT/`（两份，各 40 数据行 = 20 步 × (cache-clean + add_custom)）

## 目录内容

- `m0_timing_results.txt`：score_m0.py 原始输出 + tax + 补注
- `add_generated/`、`add_reference/`：harness 报告（correctness/performance/final × json/md/html）+ profiler 原始归档（含 kernel_details.csv、op_summary 等）
- `prebuild_artifacts_backup/`：冻结 wheel 与 .so 备份
- `env_evidence.txt`：修复后环境证据（驱动 version.info、uname、uptime、设备节点）
