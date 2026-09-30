# vector_add T_baseline / T_HW 封存记录（branch vector-add-baseline）

为后续 Agent 的任务分类（claims.md：h = T_baseline/T_HW − 1）封存两个实测时间。工作量与已测向量加一致：16384 个 float32（2×64KB 读 + 64KB 写），任务规格单核。

## 封存的两个数

| 量 | 值 | 定义 | 原始记录 |
|---|---|---|---|
| **T_baseline** | **2.006 us**（20 步中位；1.535–2.304） | CANN 标准算子 aclnnAdd 在本机 kernel-only 计时下的时延。内核 `aclnnAdd_AddAiCore_Add`，**Block Num=32**（厂商 32 核并行），输出与 CPU golden 位级一致 16384/16384 | `results/probe_aclnn/kernel_details.csv`（目标行 20 个，stdout 同目录） |
| **T_HW** | **4.370 us**（20 步中位；4.248–4.513） | 同 workload 的单核流水线**搬运下界**：M0 流水线 add 内核（4.396/4.398us 那份）仅把 L23 `asc_add` 换成 `asc_or`——搬运、流水结构、每元素 1 条向量指令完全相同，仅去掉加法语义。内核 `_Z10add_customPfS_S_`，Block Num=1，与 or-golden 位级一致 16384/16384 | `results/probe_floor_m0/kernel_details.csv`（冻结环境）；fullops 环境复测 **4.372us**（`results/probe_floor_m0_fullops/`，环境无关性佐证）。内核源 `results/floor_kernel.asc`（sha256 `31d82c3ef777c107b44f0202bba2a2154ee32e654bd576dccb48c363fbdae1b2`，基线文件唯一改动 asc_add→asc_or） |

**h = T_baseline/T_HW − 1 = 2.006/4.370 − 1 ≈ −0.54（负值，不成立）**——基线快于单核下界，因为基线是 32 核并行而任务规格是单核。跨核数的 h 无意义，见设计问题 1。两个数按实测原样封存，未改口径硬凑。

## 设备与环境

- 设备：`Ascend950PR_9589`（与 M0/C1 同一台；torch 2.10.0+cpu / torch_npu 2.10.0.post4）
- CANN：**9.1.0**（两个环境同版本）
  - T_HW：冻结环境 `/usr/local/Ascend/cann-9.1.0`（950-ops refonly，内置 kernel 剥离）
  - T_baseline：`/home/w00964611/cann-9.1.0-fullops`（同版本树副本 + 950-ops **math 子包**；冻结环境里 aclnnAdd 无法运行，见设计问题 2）
- ops 安装包：`Ascend-cann-950-ops_9.1.0_linux-x86_64.run`，sha256 `8f9c42589fa21d76522bc817a276d575f9031fab2080dcf39ea32d308f43b29e`（取自宿主机 /root/d00949691/pkg/）
- 全部环境与哈希：`results/env.txt`；各 csv 哈希：`results/csv_sha256.txt`

## 计时方法（复刻本机 CANNBench/harness 既有纪律，manifest v1.2 冻结参数）

- 判分只读原始 `kernel_details.csv`（torch_npu profiler + tensorboard_trace_handler），统计量=**中位**，不挑行
- 计时窗口前一次：`cann_bench_warmup`（MatMul 10240×10240 f16 ×2）升频 + `cann_bench_cache_clean`（ReduceMax 96×1024×1024 f16）清 L2（与 harness `_boost_freq_and_clear_cache` 同款、同输入）
- 每个测量 step 前：`cann_bench_cache_clean` + sync（与 harness `_clear_cache` 同款）
- profiler schedule `wait=0/warmup=3/active=20`；目标行 = csv 中剔除 `CannBenchCacheClean`/`CannBenchWarmup` 保留名后的行（每步恰 1 行，20 步）
- 探针脚本：`results/probe_timing.py`（`PROBE_OP=aclnn|floor|m0|add`）

## 方法论校验（sanity）

| 测量 | 中位(us) | 说明 |
|---|---|---|
| M0 流水线 add（原版 wheel，冻结环境） | **4.378** | 与 M0 harness 正式结果 4.396/4.398 吻合（<0.5%）→ **探针与 harness 口径等价**；记录 `results/probe_m0add_sanity/`（stdout 未留存，csv 为准） |
| 流水线 floor（冻结环境） | 4.370 | T_HW |
| 流水线 floor（fullops 环境） | 4.372 | 环境无关（差 0.05%） |
| vector_batch 无流水 add（冻结环境） | 7.663 | 次要证据：锁串行结构受限，非搬运受限（`results/probe_add_vb_nonpipe/`） |
| vector_batch 无流水 or-floor | 7.651 | 同上（`results/probe_floor_vb_nonpipe/`）——证明下界必须以流水线结构测，否则测的是结构串行开销 |

**经验结论**：单核 16384 f32 向量加已在其搬运下界上——流水线 add（4.378）≈ 流水线 or-floor（4.370），差 0.2%：该 workload 单核为**搬运顶满**，向量加法本身不占时间。

## 设计问题（测量过程发现，如实上报，未改口径硬凑）

1. **基线核数与任务规格不符（最重要）**：任务冻结规格为单核（`add_custom<<<1,0,stream>>>`），而 CANN 基线 aclnnAdd 对该 shape 下发 **32 block**（csv Block Num 列）。T_baseline（2.006，32 核）< T_HW（4.370，单核），h 为负——**claims.md 的任务分类公式跨核数不成立**。若要分类有效，需业主决策：定义单核基线（厂商不提供单核 aclnn 实现）或改分类为同核数口径。本记录不代做决定。
2. **冻结环境使 CANN 基线不可测**：manifest v1.2 的 950-ops refonly（候选防作弊：剥离内置 kernel）连带使 aclnnAdd 不可运行（冻结环境探针证据：`AclOpKernelInit failed, opType: Add`）。T_baseline 改在 9.1.0 副本树 + math 子包下测得——同 CANN 版本、同 bisheng，仅差防作弊剥离；对计时无影响的佐证：floor 在两环境 4.370/4.372。协议若要求基线同在冻结环境测，需为基线另行开口子。
3. **cann-bench 没有向量加任务**：level1 仅 exp / foreach_addcdiv_scalar / foreach_norm / gelu / masked_scale / mish / sigmoid / swi_glu 八个任务；refs（NPU 参考实现，baseline 采集用）恰好只覆盖这八个（baseline_collection_design.md §6.8）；metadata `950pr.json` 无 add 条目。向量加基线的官方来源不存在——本记录的 T_baseline = 直接重测 aclnnAdd（cann-bench 基线概念所指的 CANN 标准实现）。
4. **cann-bench 的 t_hw_us 是 roofline 计算值而非实测**：metadata 的 t_hw 来自 hap 模型（docs/hap_thw_model：read/vec/write 分量取瓶颈 + 平台常数，亚微秒按 1us 兜底），且无向量加条目。本记录的 T_HW 是**实测**搬运下界（同纪律计时），不是 roofline 推算，也未采用任何 metadata 数字。
5. （过程记录）950-ops 安装器 `--force` 存在路径 bug：hixl 子包卸载阶段路径翻倍（`<install-path>/cann-9.1.0/cann/...`）导致整包 abort；Add 所在的 **math 子包**（302MB）单独 `--full --quiet --install-path=` 安装成功。另：vector_batch 的 setup.py 有 wheel 打包时序缺陷（setuptools build_py 先于 build_ext，wheel 可能打包旧 .so——本次实测命中，源目录 .so 新、wheel 内 .so 旧；M0 的 cmake_build-first 写法无此问题）。

## 复现

- 全部原始 csv 与 stdout 在 `results/probe_*/`；环境与哈希在 `results/env.txt`、`results/csv_sha256.txt`
- 下界内核源 `results/floor_kernel.asc`；探针 `results/probe_timing.py`
- 容器侧留存：`/home/w00964611/vector_add_floor_m0/`（下界 submission）、`/home/w00964611/cann-9.1.0-fullops/`（基线测量环境）；测量后已把容器 cann_bench 恢复为 M0 原版（位级验证过），冻结环境未做任何改动
