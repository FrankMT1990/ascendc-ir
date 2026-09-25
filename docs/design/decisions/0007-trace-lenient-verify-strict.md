# 0007 trace 期宽松、verify 期严格的职责划分

状态：已确认（2026-09-25）

## 背景

`v.add(z_local, x_local, y[0])`（GM 参数直算）这类错误，可以在 trace 期抛 TypeError，也可以记录下来由 verify 期产出结构化诊断。

## 决定

分层：Python 类型错误（裸多 stage buffer 不下标、参数类型不对）在 trace 期抛异常，因为那是 API 误用；**调度语义错误**（GM 直算、缺 sync、通路错误）必须能 trace 成功，由 verify 产出 V 系列诊断。为此 `pipes.py` 的 compute srcs 允许 `GmRef` 透传。

## 后果

- M4/M5 能测到 V006 这类规则的诊断质量，而不是被 trace 崩溃截断。
- trace 期异常信息也必须可读（agent 会看到），但不走 Diagnostic 格式。

## 推翻条件

- agent 反馈 trace 期异常与 verify 期诊断的边界难以理解；或某类 trace 崩溃在 C1 实验中高频出现且本可结构化。
