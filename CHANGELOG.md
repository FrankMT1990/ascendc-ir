# CHANGELOG

## 0.1.0（未发布）

- PR1：仓骨架与规范冻结——分层定位、嵌入式 IR 词汇（Vector 通路）、检查器规则 V001–V008、设备表结构、有效性主张 C1–C5 与指标 M0–M9、语料驱动词汇方法。
- 评审修订（2026-09-24 第二轮）：文本 IR 改为 Python 嵌入式（trace 构建，无自写 parser）；`handoff` 更名 `sync`；诊断定位改为调用点（M5 同步调整）；交接抽象级别确认 A 级起步；补充语料驱动词汇流程（CAKE §2.1）。
- PR2：trace/model/devices 实现——`@kernel` trace 构建、callsite 记录、canonical JSON、`ascend950pr.toml` 设备表；语料证据表首填（asc-devkit `648a6018`，表达力 4/5 = 80% 压线）；tests/trace 四组用例。
- PR3：verifier V001–V009 + M4/M5 注入集。新增 V009（跨 PIPE 读取必须先经 sync），覆盖知识仓 runbook「共享 UB 跨流水线须按方向显式同步」；V008 真实注入样本待 2201 设备表。`tests/verify` 11 例、`evals/m4_m5/run_injection.py`（合法 3/3 零误拒、召回 8/8、定位 8/8）。
- ADR 补充：decisions/0001–0008 与 review-guide.md，供评审 agent 定位每次决定的上下文与推翻条件。
- PR4：codegen——检查器门控后生成 `.asc`；reroll 仿射重卷（失败拒绝生成）；event 每逻辑通道一个 ID；WAR 释放边由 stages 推导；计算 op fail-closed（当前仅 `asc_add`）。examples/vector_add 三件套（IR、golden、手写对照）；tests/codegen 6 例；全部 30 测试通过。
