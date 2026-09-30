# AscendC-IR 项目计划书

目标：做出 Agent 写得顺、能降到 Ascend C C 接口、并在 950 上算对的 IR。

当前在第 9 步和第 10 步。第 8 步已完成：`vector-batch-verify` 的 `a884886`，四个算子编译通过且数值通过。cast 在 CANN 9.1.0 上不能用 devkit 专有的 `asc_loadalign_unpack`。第 9 步的本地代码生成还用着这套符号，第 10 步要改成 950 上已跑通的原生写法。

进度有变化时，只改这张表的状态，并和对应代码一起提交到本仓库。

| 序号 | 步骤 | 完成标志 | 状态 |
|---|---|---|---|
| 1 | 定下 IR 的位置 | Agent 写 buffer、流水线和交接；编译器生成 `asc_*`，并在上板前指出该改的那一行 | done |
| 2 | 嵌入式写法、trace、检查器、950 设备表 | `@kernel` 能记成 IR；V001–V010 能拦非法写法 | done |
| 3 | 向量加的代码生成 | 稳态循环没有 `if`；3510 用寄存器向量；搬运长度按字节 | done |
| 4 | 检查器按五类分开测量 | UB、对齐、event 配对、跨 PIPE、未初始化各自能测，注入脚本退出码 0 | done |
| 5 | 评估口径 v2.8 | 判词、时间差和数值规则写进 `docs/evaluation/` | done |
| 6 | 向量加上板：同一份调度的生成内核和手写内核 | 时间差约 −0.05%，两组输入逐位一致 | done |
| 7 | 准备四个直调内核并推到 GitHub | `pack/vector_batch` 在提交 `11cdb81`：向量加、leakyrelu、half 转 float、256 个数求和 | done |
| 8 | 950 上一次编译并跑这四个内核 | `a884886`：build_exit=0，check_exit=0。加、leakyrelu、cast 逐位一致；归约全 1 精确，随机输入绝对误差 1.19e-7 | done |
| 9 | 让 IR 代码生成发出 leakyrelu、f16 转 f32、f32 归约 | 本地测试通过；`datablock_reduce_sum` 和 f16 leakyrelu 仍拒绝生成；尚未推送 | doing |
| 10 | 用第 8 步的结果对齐 IR 生成的 C | cast 改为 CANN 9.1.0 原生的 half 装载和 `asc_half2float`；构建侧补上 Python 头文件和 bisheng 的 `-fPIC` | doing |
| 11 | 封存向量加的基线时间和硬件时延下界 | 同一台 950、CANNBench kernel-only；没有这两项则任务保持未分类 | todo |
| 12 | 试点，定 token 预算 | 前两次成功的首次正确 token 的最大值乘 3，写回仓库后才能发正式任务 | todo |
| 13 | Agent 对照：同一向量加，一边写 IR，一边直接写 C，各 5 次 | 只测向量通路。Cube 没有词汇，本轮最多到「部分成立」 | todo |
| 14 | 按 Agent 实际失败改 IR | 改的是写不出、检查器没拦住、或生成的 C 编不过的地方 | todo |
| 15 | 下一个单核向量算子走同一条通路 | 先能生成，再并进一次上板，不来回单算子验证 | todo |
| 16 | 多核和 Cube | 任务和语料都需要时再进入 IR | todo |
