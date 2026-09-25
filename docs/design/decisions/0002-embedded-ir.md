# 0002 Python 嵌入式 IR，无自写 parser

状态：已确认（2026-09-24）。推翻 v0.1 的「文本 IR 为唯一规范形态」。

## 背景

v0.1 设计为独立文本语法（`.ascir`），理由是诊断行号、git diff、M5 金标需要稳定文本。评审意见：不能因评估方法的需要反过来决定 IR 形态（因噎废食）；嵌入式省去自写 parser，agent 对 Python 更熟。

## 选项

1. 独立文本语法 + 自写 parser。
2. Python 嵌入式（`@kernel` + trace），无 parser。

## 决定

选项 2。评估方法适配 IR 形态，而不是相反：M5 的金标从「文本行号」改为「调用点 file:line」，trace 时用 `inspect` 记录每个原语调用的用户栈帧。

## 后果

- trace 产物序列化为 canonical JSON（排序键、字节稳定），供审计/diff/缓存；agent 不直接编写。
- `for i in range(N)` 在 trace 期展开，模型不保留循环结构；代码生成端需要时做仿射重卷（reroll），失败则展开生成并标注。
- 后期 CANNBot-DSL 降级对接变顺：同为 Python，降级 = 生成 `ascendc_ir` 调用。

## 推翻条件

- 需要把 IR 存进非 Python 工具链（如独立 diff/缓存服务）且 canonical JSON 不够用。
- trace 期展开在大 TILES 内核上产生不可接受的模型体积，且 reroll 失败率高。
