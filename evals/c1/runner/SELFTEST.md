# C1 上板脚手架自测记录（2026-10-10）

脚手架 = `harness.py`（收包→扫描→构建→数值门→计时→归档）+ `kernel_wrap.py`（.asc 解析/launch 包装/直调 pack 组装）+ `inputs_gate.py`（必测输入确定性再生、封存哈希核对、容差比较）。自测样例源码不入仓（对实验 Agent 不可见原则），仅存运行记录。

## 自测 A（失败路径）：7 个下界形态 IR 内核

- 扫描：7/7 干净（ir_escape 零命中）。
- IR 链路：trace→verify→codegen 全过（diags=0）；签名与任务规范比对通过（含 `__gm__` 前缀规范化）。
- 构建：bisheng 直调 pack 构建成功、wheel 安装、离开源码树可导入。
- 数值门：board_used=7（每任务 1 次上板）；7/7 正确 FAIL（or(x,x)=x 与 golden 的逐元素差全部超容差，violation 计数与首违例元素记录在案）；哈希核对全部通过（含 masked_scale 边界组"哈希对象=原始 uint8 掩码、执行参数=位打包"的分离处理）。
- 记录：`selftest_a_record.json`。

## 自测 B（成功路径）：exp_f32 正确实现（mul_scalar(1.5)+exp 流水）

- 数值门：计时组+边界组双 pass（asc_exp 与 golden 位级差在容差内，与 board_3510 的 64/64 位一致经验吻合）。
- 计时：t_best_us=777.52（kernel_details_csv 源），快于 floor 下界核的 899.94μs——floor 核是实测基准而非理论下确界，Agent 调度可优于它，如实记录。
- 记录：`selftest_b_record.json`。

## 结论

脚手架按任务书 v1.0 冻结，可接收试点包。待办：工具回传 token 的 usage 键名（等业主侧 runner 的 provider usage 结构核实后在第一份试点发出前写死）。
