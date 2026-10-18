# M0/M0b 测量会话结果（2026-09-28/29，manifest v1.2）

## 结论一览

| 项 | 状态 | 结果 |
|---|---|---|
| M0b 数值一致性（生成版） | **完成，通过** | 容差（atol=rtol=1e-6）全过；G1 均匀组 + G2 边界组逐位一致率均为 **16384/16384** |
| M0b 数值一致性（手写版） | **完成，通过** | 同上（与生成版输出完全一致） |
| harness 精度阶段 | 完成 | 两候选各 1/1 case 通过（CANNBench 生态精度标准） |
| **M0 抽象税（计时）** | **未测（环境阻塞）** | 本机 2026-09-17 重启后 IOMMU 未启用 → 内核 prof 通道初始化失败（`prof_open` ENOENT），**全机**设备侧采集不可用 → `kernel_details.csv` 无法产出（CANNBench kernel-only 唯一数据源）。证据链见 `m0_blocked_evidence.txt` |

## M0 阻塞摘要（详见 m0_blocked_evidence.txt；根因已于 09-29 修正）

- 内核日志：`prof_open Failed to open the prof device file (error=2)` → `Failed init profiling(-1)`
- **根因修正**：初版归因「IOMMU 未启用」不成立——grub 从未配置 intel_iommu，且本机历史上不开 IOMMU 时采集正常。更可能的时间线：**09-16 10:17 有人重装驱动（当时在跑 2025 年内核 5.4.0-216，模块部署进 -216 目录）→ 09-17 01:57 重启后机器起来在 2022 年旧内核 5.4.0-125 上** → 新用户态驱动与旧内核模块错配 → prof 通道/devmm 节点等边缘功能损坏（计算主路径不受影响，M0b 全过）
- 全机（/home、/root）自 2026-09-17 后零 `PROF_*` 产出（此前多个用户有成功记录）
- 修复建议（按优先级）：① grub 默认内核切回 5.4.0-216 重启（最轻，无需 IOMMU/BIOS）② 或为 -125 重装配套驱动 ③ IOMMU 仅作最后备选。均需宿主机管理员执行（共享机器）

## 本会话产物

- `frozen_hashes.txt`：run 时点源码/包哈希（golden eb1398… 系列、wheel、pack 全树）
- `m0b_results.txt`：M0b 判定 + 输入/golden 哈希
- `m0_blocked_evidence.txt`：M0 阻塞证据链
- `add_generated/`、`add_reference/`：两候选的评测报告（correctness/performance/final）+ profiler 原始归档（`prof_data/`，其中 `PROF_*/device_0/data` 为空即阻塞现场；`attempt1_task_naming_failed/` 是任务输入名修正前的失败尝试，无测量数据）

## 恢复计时的路径（供决策）

1. 宿主机开启 IOMMU（BIOS + `intel_iommu=on`）并重启 —— 需机器管理员协调；修复后重跑 `run_evaluation.sh`（两候选，参数见 manifest）+ `score_m0.py` 即得 tax
2. 或换一台设备采集正常的 950（manifest 钉死本机为 C1 同机，换机属协议变更）
3. 或改用非 profiling 的计时口径（协议变更，需业主另行冻结；本次未采用）

---

## 【2026-09-29 更新】M0 计时已完成（环境修复后）

管理员于 09-29 00:03 为运行内核 5.4.0-125 重装驱动（即上述根因的修复路径②）并于 04:25 重启；prof 通道恢复。同日按 manifest v1.2 冻结参数完成 M0 正式测量，**tax ≈ −0.05%**（生成版 4.396us vs 手写版 4.398us，各 20 步中位；提案通过线通过）。完整材料（判分原始输出、两份 kernel_details.csv、harness 报告、构建可复现性核验、环境证据）见 **`timing_20260929/`**。

