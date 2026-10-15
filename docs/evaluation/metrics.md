# 有效性指标 M0–M9（v2.8）

**阈值状态声明**：2026-09-27 业主改定（v2.8）写入 `claims.md`：调度敏感任务的赢线是 `rel ≥ +20%`；带宽顶满任务的 `rel` 只报告；`m3` 不进判词；成功次数少 ≥ 2 次才判不成立，少 1 次为不确定；`rel ≤ −5%` 判输停用，直到开跑前封存噪声底 ε。其余数值阈值（M0 的 5%/10%、检查器各类召回 0.9、M5 的 0.8、K=5、R=5、无效占比 0.5）仍为**提案值**。提案阈值下的验收结论标注「未达冻结线」。每个阈值冻结时必须写明来源（业主决定、试点分布、噪声底或外部基准）。

判词表（任务级四档、负载级与 C1 无「或」按序匹配、兜底行永远最后、rel 与 m3 公式）的唯一版本在 `claims.md`；本文不重复定义，只定义指标本身。

每个指标给两句话：一句大白话（它回答什么），一句精确定义（怎么算）。

## 计时口径与测量清单

性能一律使用 CANNBench kernel-only 口径。每次测量前冻结**测量清单**（manifest），缺一项不得开跑：

- 设备序列号、CANN 版本、锁频命令、清 cache 命令
- warmup 丢弃规则、kernel 名匹配规则（一次 launch 的 `kernel_details.csv` 含多行时按名称+输入 shape 精确过滤，禁止挑较短的行）
- 每候选重复次数、统计量（中位，不是最小值）
- 基线：同一设备、同一 CANN、同一升频流程用同一脚本重测；不重测则基线退出 plateau 的 1.0 阈值、C4 的绝对判定与无效候选占比（记「未测」），只做臂间相对比较
- M0 的测量设备钉死为 C1 同一台 950；2201 只做可移植检查

**离线闭环防污染**：每次离线往返带源码哈希、包哈希与原始 csv 归档；判分脚本只读 csv，不接受手抄时延；上板执行人不得修改源码与包（修改即该候选作废）。

**HAP**（cann-bench 主指标，C4 附注）：

```text
HAP_i = (T_baseline,i − T_HW,i) / ((T_cand,i − T_HW,i) + (T_baseline,i − T_HW,i))
```

`T_HW` 为硬件**时延下界**，`T_baseline` 为重测基线。HAP 仅在 `T_cand`、`T_baseline` 都大于 `T_HW` 时计算，否则该任务 HAP 记「未测」（防止候选快于下界时出负分、或分母为零）。C4 报告以中位 speedup（`T_baseline / T_cand`）为主，HAP 只在全部任务可计算时作附注。

## 上板验证门禁（需要设备，不需要 agent）

生成代码的翻译质量：执行时延与数值精度都必须上板实测，无法在静态阶段验证（本协议无代价模型，见 ADR 0005）。

| 指标 | 大白话 | 定义 | 通过线（提案） |
|---|---|---|---|
| M0 抽象税 | 生成的内核执行时延比手写高多少 | `tax = T_generated / T_handwritten − 1`，**正值表示生成更慢**。通过线的分母只含「去守卫且短 tile」的配对，每个可生成 op 恰好一对；偶数对时中位取较高值（保守方向）。孪生税与带守卫短 tile 单独报告，不进中位 | 中位 ≤ 5%，且每一对 ≤ 10% |
| M0b 数值一致性 | 生成的内核算得对不对 | 配对内核满足与 C1 同一容差 | 必须满足；逐位一致率单独报告 |

**M0 配对集**（随词汇版本扩展）：

1. 孪生对照：与生成结构相同的手写（只回答「降级是否多写了指令」，不进通过线中位）。
2. 去守卫对照：软件流水（剥 prologue/epilogue）的手写——测守卫分支开销，短 tile/短 repeat 形态必测。
3. 官方样例调度对照：官方多核单缓冲写法；IR 表达不了就标为缺口并记录，不计入通过线。
4. 每个已声明可代码生成的 op 恰好一对（去守卫且短 tile）；**该对的 shape（如 2048 个 f32、32 repeat）在测量前写进测量清单，测完不得换**。

每对：固定 shape/dtype，同一 manifest，重复测量次数冻结进清单。

## 上板前验证门禁（连设备都不用）

检查器检查 AscendC-IR 写得对不对：合法的放行，非法的拦住，报错指向该改的那一行。这一步还没上板，所以没有执行时延，也没有数值结果。

| 指标 | 大白话 | 定义 | 通过线（提案） |
|---|---|---|---|
| M4 误拒 / 召回 / 干净 | 好人放行、坏人拦截、不误伤旁枝 | 合法金样本接受率；五类注入（UB、对齐、event 配对、跨 PIPE、未初始化）各自被拦住的比例；实际 ID 集合 == 期望集合的比例 | 误拒 = 0；每一类召回 ≥ 0.9；干净率 = 100%。任一类没有封存注入则 C3 未测 |
| M5 定位命中 | 报错指对地方了吗 | 诊断主调用点与人工金标（file + 源码行片段）一致的比例 | ≥ 0.8（全部规则类，不单列） |

**M4/M5 注入集纪律**：

- 通过线只有一条，由 `evals/m4_m5/run_injection.py` 按它退出非零。
- 五类必须分开计召回，汇总召回不得代替某一类：UB（V002）、对齐（V007）、event 配对（V003）、跨 PIPE（V009）、未初始化（V010）。每一类召回 ≥ 0.9（提案）。任一类没有封存注入，该类未测，C3 未测。
- 分母预注册：每条已测规则至少 3 个单点注入；V008 在 2201 设备表落地前标「未测」，不计通过。
- 金标在修改检查器之前双人冻结；标注不一致的样本**不得**事后移出分母，单独报告。
- 另设一份不从当前规则反写的故障集（历史编译错误 / agent 试点日志）。
- 合法样本覆盖语料里的原调度，包含刚好卡在 UB、对齐和 event 上限的边界例。
- 退出码：1 = 误拒、召回、定位或干净率没过；2 = 这些过了，但五类里有一类不足 3 条、已测规则不足 3 个单点，或独立故障集为空，打印「旧集回归通过，C3 未测」；0 = 边界合法样本、五类分开召回、每条已测规则 ≥ 3、独立故障集都满足。退出码 0 只表示「检查器拦截」这一档的注入集通过。M9 没跑之前不称「诊断有效」。退出码不是 0 时，不得开始 C1 的 agent 实验。

## Agent 对照实验（C1 用）

| 指标 | 大白话 | 定义 | 通过线（提案） |
|---|---|---|---|
| M2 成功率 | 同一个任务，Agent 从零重做 5 次，几次能交出能在 NPU 上跑、算得对、又没违规的内核 | 预算与上板上限内，至少产出一个通过数值门且合规内核的 run 比例 | 进判词表。少 ≥ 2 次判不成立；少 1 次为不确定 |
| M1 执行时间 | 预算花完时，最好的内核比直接写 C 的快多少 | `A = T_baseline / T_best`；`rel = median(A_IR) / median(A_control) − 1`。只在成功 run 上算，偶数取较高中间值。任务类别见 claims.md | 调度敏感且 rel ≥ +0.20 才因执行时间算赢。带宽顶满只报告 rel。噪声底未封存时，不因 rel 判输 |
| M3 首次正确 token | 第一个算对的内核花多少 token | `m3 = median(T_control) / median(T_IR) − 1`，口径见 claims.md；未达到记 > B，且 `> B` 不进入中位 | 只报告，不进判词 |
| M7 逃逸率 | 有没有绕过 IR 直接写 C | IR 臂提交源码中命中逃逸模式的比例（检测脚本随协议冻结） | 逃逸候选作废且不计入 M1/M2/M3 |
| M9 诊断消融 | 诊断到底有没有用 | 三档（都不上板）：完整诊断 / 仅 message（去 callsite 与 suggestion）/ 仅规则 ID。K = 5 轮。**成功 = 5 轮内同时满足：trace 完成、block 诊断为空、被注入的那条计算/搬运调用仍在 trace 结果里（操作数与注入点相同；注释和未执行分支不算）**。删除语句或弄坏 trace 让规则 ID 消失不算成功，单独记一列，不进修复率分子 | 预注册最小差值：完整诊断档相对**每一档**较弱条件的修复率都至少高 0.2，且每档至少 20 个故障。未跑或未超过差值 → C3 只称「检查器拦截」 |

## 后续阶段

| 指标 | 大白话 | 定义 | 通过线（提案） |
|---|---|---|---|
| M8 组合 Gspan | 一个 shape 调好的内核推广到一批 shape | 冻结 shape 集上、含 dispatcher 的逐 shape speedup（分母同 M1 基线）的无权几何平均；失败 shape 记 0 且使 Gspan 为 0 | 单独报告，不与 M1 比较；同时报失败 shape 数 |

## 随 C1 采集的旁路指标

- **无效候选占比**：分母 = 该臂**全部上板次数**；分子 = 数值错误，**或**数值正确且时延 > 4 × 已重测基线。任一臂占比 ≥ 0.5（提案，开跑前冻结）即触发 ADR 0005 回摆。数值错误单独报一列，避免只看见「正确但慢」。基线未重测则本条记「未测」，不得当成占比很低。「慢于本臂当前最佳 2 倍」只作探索曲线报告，不触发 ADR 0005。
- **检索日志**：两臂对 asc-devkit 示例与本仓 examples/ 的不可见性的执行证据。
- **m3 与追上基线的 token**：m3 按 claims.md 报告。另报该 run 首次出现 attainment ≥ 1.0 时的累计 token；到预算结束仍未出现记 `> B`。两者都不进判词。
- **pass@1**：在同一批正式 run 里，看第一次上板是否就已经交出合规且过数值门的内核。报告该比例，不另开预算，不进判词。

## 防误读

- **M1 必须配 M2 看**：M1 只在成功 run 上取中位。5 次只成功 1 次但那次很快，单看 M1 会显得 IR 很好——幸存者偏差。
- **判词唯一**：任务级/负载级判词只按 claims.md 的表；任何文件不得另写一套（含「< 5% 即不确定」这类局部说法）。
- **M4/M5 注入错误**：由合法样本只改一处调用点得到。金标双人冻结，不从诊断文案反推。
- **配对（M0）**：手写 C API 与 IR 生成内核的拷贝、计算、同步边一致，只允许 event 分配在等价类内不同。

## 测量顺序

1. 冻结主设备、容差、测量清单、任务 ID 清单、每个任务的 T_baseline 与 T_HW（用来算空隙并封存类别）、表达力清单、逃逸与越面扫描脚本、W1 用例与基线版本。噪声底若启用，同一时刻封存。
2. 建仓第一批只实现能测 M0、M4、M5 的词汇；**M0 的去守卫短 tile门通过、且 C3 不再是「未测」**，才接 agent。
3. 试点 run 定 B（规则见 claims.md），冻结后跑 C1 与 M9。
4. C5 的 Gspan 等单 shape 种子存在之后再定义 shape 集。

## 已确认决定（2026-09-26 更新）

仓定位（分层，独立建仓）、主设备 950、C1 处理为整套工具链、逃逸与越面都作废、每臂 5 次、计时口径 CANNBench kernel-only、负载与基线取自 cann-bench tasks、C4 不否决 IR、cannbot-dsl 可作第三臂（只定位不判赢）。任务判词以 claims.md v2.8 为准。M0、检查器召回等未写进该判词赢线的阈值仍是提案值。

## M0/M0b 测量清单（2026-09-28 冻结，manifest v1.2）

vector_add 配对（`examples/vector_add/add_golden.asc` 生成版 vs `add_reference.asc` 手写版，ADR 0014 lowering 后）的首次上板测量。缺任一项不得开跑；测完不得回头修改本清单。
版本史（均发生在任何测量数据产生之前）：
- v1.0→v1.1：CANN 9.2.0 → 9.1.0（cann-bench docker/base 验证配对：torch_npu 2.10.0.post4 ↔ torch 2.10.0 ↔ CANN 9.1.0）。
- v1.1→v1.2：不再使用 asc-devkit 头 overlay 与私有副本（shim）。ADR 0014 的 reg 向量 lowering 所需全部接口（reg_load/reg_store/reg_vector/reg_convert、sync、vector_datamove、sys_var）在 **CANN 9.1.0 自带 asc 树的 3510 分支原生齐备**（实测编译通过），内核 TU 与 harness 运行统一用原生 9.1.0。另按 cann-bench docker/eval 的 950 配方补装 **950-ops 包（refonly：保留 libopapi、剥离内置 kernel 二进制）**——950PR 为 aclnn-only 设备，H2D/D2H 拷贝走 aclnnInplaceCopy，无 ops 时 torch_npu 张量搬运直接失败（ERR01007）；refonly 同时封禁内置算子路由（防作弊姿态，harness 的升频/清 cache 为 cann_bench_utils 自定义算子，不依赖内置 kernel）。

### 设备与环境

| 项 | 冻结值 |
|---|---|
| 主设备 | Ascend 950PR（逻辑名 `950pr`），torch_npu 实测名 `Ascend950PR_9589`：64 vector core / 32 cube core / 126208 MB / L2 128 MB。与 C1 同一台 |
| 设备序列号 | PCIe Device Serial Number `00-07-00-09-00-b8-44-00`（PCI 0000:04:00.0，device id `d806` rev 20；宿主机 npu-smi 二进制缺失，以 PCIe DSN 为设备标识） |
| 宿主/容器 | 100.105.88.102 / `w00964611_asc_playground`（/dev/davinci0） |
| 驱动 | 9.1.T13.0.B130（宿主机 /usr/local/Ascend/driver） |
| CANN | 9.1.0 toolkit（官方桶 `Ascend-cann-toolkit_9.1.0_linux-x86_64.run`，`--force` 安装：容器内驱动元数据不全导致兼容检查误报；驱动 9.1.T13 与 toolkit 9.1.0 为正常配对） |
| ops 包 | `Ascend-cann-950-ops_9.1.0_linux-x86_64.run`（同桶同经代理下载）安装到 9.1.0 树，随后 **refonly 剥离**：`rm -rf …/opp/built-in/op_impl/ai_core/tbe/kernel`（保留 libopapi，内置 kernel 二进制删除） |
| libhccl | SONAME-only stub（`int __hccl_stub;` 编成 `libhccl.so` 放入 9.1.0 lib64；torch_npu 的 DT_NEEDED 依赖，direct-launch 不调用 HCCL 功能；对齐 cann-bench docker/base 配方） |
| 编译工具链（内核 TU） | bisheng（CANN 9.1.0 自带，clang 15.0.5，2026-07-30 构建）`--npu-arch=dav-3510 --asc-aicore-lang`；C API 头 = **CANN 9.1.0 自带 asc 树**（`x86_64-linux/asc/include`，3510 分支原生含 reg API；无 overlay） |
| harness 运行环境 | 同一原生 9.1.0 环境（构建与运行同树；`source /usr/local/Ascend/ascend-toolkit/set_env.sh`） |
| torch / torch_npu | 2.10.0+cpu / 2.10.0.post4（cann-bench requirements 钉版；配对 ↔ CANN 9.1.0） |
| cann-bench | gitcode.com/cann/cann-bench master `abb6e47`（2026-09-24），kernel-only 口径（perf_metric_strategy=kernel_details） |
| 提交形态 | direct_launch 样例结构（build.sh → dist/cann_bench-*.whl → TORCH_LIBRARY 直调），两个候选各自独立提交、独立评测 run |

### 冻结 shape（测完不得换）

- TILE=2048 个 f32；TILES=8（GM 每张量 16384 个 f32）；x/y stages=2、z stages=1
- 单核：`add_custom<<<1, 0, stream>>>`；`add_vf` 的 data_len=2048（VF repeat_time=32）
- dtype 一律 float32

### 锁频与清 cache（CANNBench 内置机制，不另设手工命令）

- 测量窗口前一次：`cann_bench_warmup`（MatMul，10240×10240 f16 ×2）+ `torch.npu.synchronize`
- 每个测量 step 前：`cann_bench_cache_clean`（ReduceMax，96×1024×1024 f16）+ `torch.npu.synchronize`
- 判分时按保留名 `CannBenchWarmup` / `CannBenchCacheClean`（回退匹配 MatMulV3/ReduceMax 的 warmup shape）剔除这些行

### warmup 丢弃、采样与统计

- profiler schedule `wait=0, warmup=3, active=20`；warmup step 不进统计
- 每候选重复次数：`--warmup 3 --repeat 20`；统计量 = **中位**（每 step 目标 kernel 时长求和，跨 20 个 step 取中位；本任务每 step 恰一次目标 launch）。不用最小值
- 单卡 `--device-id 0`，`--processes-per-card 1`

### kernel 名匹配规则（判分只读原始 csv）

- 判分脚本只读评测归档的原始 `kernel_details.csv`，不接受手抄时延
- 目标行定义：排除 warmup 保留名后，Name 与被测 kernel 符号一致（含 `add_custom`）、Input Shapes 为本 case 的 16384-f32 输入形态的行
- 同一 step 出现多行同名时按 Input Shapes 过滤，**禁止挑较短的一行**；过滤后仍多于一行则全部计入该 step 的求和，禁止挑选
- 实测的 Name/Type 列值在冒烟后补注到归档记录里（补注事实，不改本规则）

### M0 判据

- `tax = T_generated / T_handwritten − 1`（正值表示生成更慢）；T 取上述中位
- 通过线（提案，未冻结）：中位 ≤ 5% 且该对 ≤ 10%（当前可生成 op 只有 add，中位即该对）
- CANNBench 的 HAP/评分不作判据（本任务无 baseline，得分项按缺失处理）

### M0b 数值容差（开跑前写死；测后改容差无效）

- 比较式（claims.md v2.5.12）：逐元素 `abs(a − b) ≤ atol + rtol × abs(b)`；a=内核输出，b=golden；**atol=1e-6，rtol=1e-6**；比较在 golden 的 dtype（float32）上进行；任一元素不满足、出现 NaN、dtype 或元素个数不一致 → 该内核失败
- golden = `torch.add(x, y)`（CPU，float32）
- 必测输入组（两组都必须过；构造规则如下，开跑时对输入与 golden 分别哈希归档）：
  - G1 均匀：`torch.manual_seed(0)`；`x = torch.rand(16384) * 4 − 2`；`y = torch.rand(16384) * 4 − 2`
  - G2 边界：v = [0.0, -0.0, 1.4e-45, -1.4e-45, 1.1754944e-38, -1.1754944e-38, 2.0, -2.0, 1e30, -1e30]；x = v 循环填充 16384；y = v 错开一位循环填充（所有和均为有限值）
- 逐位一致率单独报告，不与容差构成「或」
- M0b 与 C1 共用同一比较式；C1 的容差文件届时另行冻结

### 防污染与归档

- 开跑前封存哈希：`add_golden.asc`、`add_reference.asc`、`pack/vector_add_m0/` 全部源码、两个 wheel；上板执行中不改上述内容（修改即该候选作废）
- 收包归档：两份原始 `kernel_details.csv`、两份评测报告 JSON、构建日志、输入组与 golden 的哈希、本清单引用的全部工具版本
- 判分、M0b 检查与 tax 计算脚本随归档保存，只读上述原始文件

### 顺序

1. 本清单入仓 → 2. 构建两候选 wheel + 冒烟（跑通一次、结果对）→ 3. 封存哈希 → 4. 正式评测 run（两候选各一次，参数如上）→ 5. 判分与报告。冒烟不产生计分数据。
