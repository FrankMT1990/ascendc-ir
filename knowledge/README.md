# 对照臂 API 知识卡（来源：cannbot-knowledge，业主决策 2026-10-12 引入）

本目录 62 张 Markdown 卡覆盖本任务允许面内的 Ascend C API（950PR/3510 平台视角），内容为函数原型、dtype 支持、参数与限制——纯形态层知识。

## 使用规则

1. 写内核前按符号名查卡（如 `asc_load.md`、`asc_copy_gm2ub_arch_3510.md`），确认调用签名与参数语义。
2. **裁决优先级：上板编译器报错原文 > 本机 CANN 9.1.0 头文件 > 知识卡**。知识卡来自 asc-devkit 文档视角，与本机 9.1.0 实际头文件存在已知漂移（例如 `asc_load` 的返回值形式在卡中有原型，但本机 3510 分支只接受 out-param 形态）。冲突时以编译反馈为准。
3. 调用约定一句话规则：**所有向量计算 intrinsic 的最后一个参数都是 vmask**（`vector_bool`）；装载/存储为 2 参；`__simd_vf__` 辅助函数的参数只能是 `__ubuf__` 指针（向量寄存器引用不能跨函数边界）。
4. 管线记号：`PIPE_MTE2`（GM→UB 搬运）、`PIPE_V`（向量计算）、`PIPE_MTE3`（UB→GM 写回）；同步用 `asc_sync_notify(源管, 目标管, EVENT_IDn)` + `asc_sync_wait` 配对。
5. 已知知识缺口（卡未覆盖，速查页与编译反馈为准）：`asc_update_mask_b32`、`asc_create_mask_b32`（掩码生成）。
