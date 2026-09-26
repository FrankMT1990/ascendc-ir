# CHANGELOG

## 0.1.0（未发布）

- PR1：仓骨架与规范冻结——分层定位、嵌入式 IR 词汇（Vector 通路）、检查器规则 V001–V008、设备表结构、有效性主张 C1–C5 与指标 M0–M9、语料驱动词汇方法。
- 评审修订（2026-09-24 第二轮）：文本 IR 改为 Python 嵌入式（trace 构建，无自写 parser）；`handoff` 更名 `sync`；诊断定位改为调用点（M5 同步调整）；交接抽象级别确认 A 级起步；补充语料驱动词汇流程（CAKE §2.1）。
- PR2：trace/model/devices 实现——`@kernel` trace 构建、callsite 记录、canonical JSON、`ascend950pr.toml` 设备表；语料证据表首填（asc-devkit `648a6018`，表达力 4/5 = 80% 压线）；tests/trace 四组用例。
- PR3：verifier V001–V009 + M4/M5 注入集。新增 V009（跨 PIPE 读取必须先经 sync），覆盖知识仓 runbook「共享 UB 跨流水线须按方向显式同步」；V008 真实注入样本待 2201 设备表。`tests/verify` 11 例、`evals/m4_m5/run_injection.py`（合法 3/3 零误拒、召回 8/8、定位 8/8）。
- ADR 补充：decisions/0001–0008 与 review-guide.md，供评审 agent 定位每次决定的上下文与推翻条件。
- PR4：codegen——检查器门控后生成 `.asc`；reroll 仿射重卷（失败拒绝生成）；event 每逻辑通道一个 ID；WAR 释放边由 stages 推导；计算 op fail-closed（当前仅 `asc_add`）。examples/vector_add 三件套（IR、golden、手写对照）；tests/codegen 6 例；全部 30 测试通过。
- 评审修复（2026-09-25，对应 review-findings-2026-09-25）：六条必修全修——WAR 按槽位分配 event（同一 id 严格交替，ADR 0010）、GM 仿射保留基址、无迭代号标记的槽位复用拒绝生成、reroll 比较 op/PIPE/操作数、V003 先计消费再结束窗口且消费方改为「至少一个」、结果侧 GM 进 V006。事实源对齐——event id 按 PIPE 对独立（V005 同步改）、M5 统一为「file + 行片段」且 callsite 存相对路径恢复字节稳定、设备表补来源注释、pyproject 补 package-data、README/positioning 状态更正。新增 V010（读未写槽位）。注入集重构为隔离样本并增报干净率；buffer 重名 trace 期拒绝；`asc_add` repeat ≤ 255 守卫。43 测试通过；注入集 3/3、9/9、9/9、干净 9/9。
- 复审修复（2026-09-26，对应 review-findings-2026-09-26）：WAR 释放点改到槽位在循环体内的最后一次消费之后（两条计算读同一槽位不再提前释放/连续 notify）；循环按槽位展开（`i += N`），event id 全为编译期字面量，消除运行时三元（复审核对项）；新约束 TILES % lcm(stages) == 0；就地 RMW 由发射端以「生产 PIPE 唯一」明确拒绝并写入 spec。46 测试通过；注入集维持 3/3、9/9、9/9、干净 9/9。
- 验收协议 v2（2026-09-26，grok-4.7-xhigh 对抗性评审 16 条）：claims/metrics 重写——两臂表达力对齐（任务 ID/指令面/支持集三清单预注册）、判词四档互斥并预注册聚合规则、token/预算 B/上板上限/逃逸检测操作定义、测量清单与离线闭环哈希归档、M0 公式方向修正（tax = 生成/手写 − 1）与配对集扩为四类、M9 改三档消融、plateau 独立成条款（100% 检查点不构成 plateau）、阈值全部标注提案值、表达力回测分母含 gap 且用未见过内核、无效候选占比随 C1 采集（ADR 0005 推翻条件可测）、C1 主张改名「工具链」。注入集通过线唯一化（误拒=0、召回≥0.9、定位≥0.8、干净率=100%）。ADR 0012。
