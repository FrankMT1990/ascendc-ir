# 0006 诊断按调用点定位，结构化 JSON

状态：已确认（2026-09-24）

## 背景

Croqtile 的 Compiler-Harness Co-Design：诊断要指出违反的约束并给出修复建议。CAKE：finding 指向 resource/role/stage。嵌入式形态确定后，定位单位从文本行号改为调用点。

## 决定

诊断格式：`{id, severity, callsite: {file, line, function, statement}, message, suggestion, knowledge}`。callsite 由 trace 时 `inspect` 记录用户栈帧得到。`knowledge` 链接 cannbot-knowledge 卡片，无则 null。输出按 `(file, line)` 排序，稳定可复现。

## 后果

- M5 定位命中的金标 = 人工标注的 callsite（file + 源码行片段），不从诊断文案反推。
- 同一调用点可产生多条诊断。

## 推翻条件

- 调用点信息在真实 agent 工作流中不足以定位（如宏/闭包包装后行号漂移），届时需要引入 IR 语句 ID 作为第二定位轴。
