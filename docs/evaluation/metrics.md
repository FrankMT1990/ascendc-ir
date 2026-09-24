# 有效性指标 M0–M9（冻结版）

所有阈值为提案值，经评审后冻结；修改必须更新本文与 CHANGELOG。

## 计时口径

性能一律使用 CANNBench kernel-only 口径：NPU profiler 的 `kernel_details.csv`，每次测量前升频清 cache，过滤 warmup kernel，取中位。时延不含编译与 Python 派发。负载、cases、golden、`baseline_perf_us` 与硬件锚 `T_HW` 取自 cann-bench tasks 的冻结版本。

## 指标表

| 指标 | 主张 | 定义 | 通过线（提案） | 需要 agent |
|---|---|---|---|---|
| M0 抽象税 | C2 | 同一 schedule：手写 C API 与 IR 生成内核的 kernel-only 时延比 − 1 | 中位 ≤ 5%，单对 ≤ 10% | 否 |
| M0b 数值一致性 | C2 | 配对内核在相同输入上逐位一致或误差为 0 | 必须一致；不一致先修代码生成 | 否 |
| M4 误拒 / 召回 | C3 | 合法金样本接受率；注入非法样本被拒比例 | 误拒 = 0；召回 ≥ 0.9 | 否 |
| M5 定位命中 | C3 | 诊断主调用点与人工金标（file:line）一致的比例 | 同步与地址空间类 ≥ 0.8 | 否 |
| M1 匹配 attainment | C1 | 预算 B 处最佳正确内核时延除进冻结基线时延；报中位与 [min, max] | IR 中位 > C API 中位 | 是 |
| M2 可计分率 | C1 | 预算内至少产出一个通过数值门内核的 run 比例 | 与 M1 一起报，单独不判赢 | 是 |
| M3 首次正确 token | C1 | 到第一个通过数值门的候选为止的 token；未达到记 > B | IR 中位 < C API 中位，或与 M1 之二成立 | 是 |
| M7 逃逸率 | C1 | 候选里嵌入原始 C API 片段的比例 | C1 实验中逃逸候选作废 | 是 |
| M9 诊断消融 | C3 | 同一 IR、同一注入错误：开诊断 vs 只给编译器原文，K 轮内修好且改到金标位置 | 开诊断修复率更高；K = 5 开跑前冻结 | 是 |
| M8 组合 Gspan | C5 | 冻结 shape 集上、含 dispatcher 的逐 shape speedup 的无权几何平均 | 单独报告，不与 M1 比较 | 是 |

## 补充协议

- **数值门**：开跑前按 dtype 冻结相对/绝对容差；输入至少包含均匀分布与算子定义允许的边界值。错误内核没有 speedup。
- **Plateau**：检查点取预算的 20/40/60/80/100%；某检查点最佳 eligible attainment ≥ 1.0 且之后下降不超过 3%，记为 plateau。
- **M1 基线**：cann-bench tasks metadata 的 BuiltIn `baseline_perf_us`（黑盒）；C4 对应 HAP > 0.5。
- **M4/M5 注入错误**：由合法样本只改一处调用点得到——漏 sync、地址空间用错、buffer 超 UB、event 复用冲突。两人标注不一致的样本退出分母，单独报告不一致数。
- **配对（M0）**：手写 C API 与 IR 生成内核的拷贝、计算、同步边一致，只允许 event 分配在等价类内不同。

## 测量顺序

1. 冻结主设备、容差、计时口径、W1/W2 用例与基线版本。
2. 建仓第一批只实现能测 M0、M4、M5 的词汇；三个门过了再接 agent。
3. 跑 C1 与 M9。
4. C5 的 Gspan 等单 shape 种子存在之后再定义 shape 集。

## 已确认决定（2026-09-24）

仓定位（分层，独立建仓）、主设备 950、C1 处理为整套环境、逃逸作废、抽象税 5%/10%、每臂 5 次、负载 W1+W2 都过才算成立、计时口径 CANNBench kernel-only、负载与基线取自 cann-bench tasks、C4 不否决 IR。cannbot-dsl 可作为第三臂参加 C1，只定位不判赢。
