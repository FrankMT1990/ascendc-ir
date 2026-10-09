# AscendC-IR 项目计划书

目标：做出 Agent 写得顺、能降到 Ascend C C 接口、并在 950 上算对的 IR。

当前在第 17 步。`board-3510` 的 `b9d57ce` 复核了 `512950c`：49/50 通过。字面量、`asc_ln`、ceil/trunc 的正负零判据都对了。矩阵乘仍编不过，因为发出的是 2201 的 10 参搬运和 11 参写回；3510 分支是 8 参搬运和 21 参写回。

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
| 9 | 让 IR 代码生成发出 leakyrelu、f16 转 f32、f32 归约 | 已接入。`datablock_reduce_sum` 和 f16 leakyrelu 仍拒绝生成 | done |
| 10 | 用第 8 步的结果对齐 IR 生成的 C | cast 改为 `vlds(..., UNPK_B16)` 和 `asc_half2float(dst, src, mask)`；直调构建补了 Python 头和 `-fPIC` | done |
| 11 | 封存向量加的基线时间和硬件时延下界 | `9be68d6` 有实测。32 核基线对不上单核下界，不再重测，不据此分类 | done |
| 12 | 按 3510 头文件设计矩阵和向量 IR | 目录覆盖三个头文件范围；f16 mmad 可按 K 分块累加；f32 逐元素能生成；其余拒绝并带签名 | done |
| 13 | 对抗检查这一批设计和生成 | 已采纳：`axpy`/`select` 不套模板，f32 mmad 不生成，搬运形状必须和 mmad 一致，混用 UB 与 Cube、未初始化累加都在检查器拒绝 | done |
| 14 | 准备一次上板包 | `pack/board_3510`：50 个 IR 生成核，沿用已跑通的 bisheng 直调构建；缺符号可 SKIP 后继续 | done |
| 15 | 950 上一次编译并跑这个包 | `e959a4a`：32 逐位一致，div/ln/sqrt 在容差内；ceil/trunc 负零符号位不对；13 个核 SKIP，未换头文件 | done |
| 16 | 按上板结果补降级模板 | `b9d57ce`：11 个字面量核逐位一致，`log` 在容差内，ceil/trunc 按正负零通过。mmad 的搬运写回仍是 2201 形态 | done |
| 17 | 把矩阵搬运改成 3510 的参数个数 | `nd2nz` 发 8 参，`l0c2gm` 发 21 参；`asc_mmad` 与 `asc_set_l0c2gm_nz2nd` 保持现状。再上板只核对 `op_mmad` | todo |
