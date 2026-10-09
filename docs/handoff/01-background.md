# 背景

## 这个仓库做什么

`ascendc-ir`（https://github.com/FrankMT1990/ascendc-ir）是给 Agent 用的 Ascend C 中间表示。Agent 写 buffer、搬运、流水和同步。编译器填 event id、地址和 NZ 参数，并降到 Ascend C 的 C API（`asc_*`）。

不使用 AscendNPU-IR。Cube 和向量不要放进同一个核。这一批是单核，没有 `asc_get_block_idx`。

目录里没有降级模板的名字，检查器用 V013 拒绝，并带上头文件签名。不要猜重载。

## 设备和工具链

| 项 | 值 |
|---|---|
| 设备 | Ascend950PR_9589 |
| 序列号 | `00-07-00-09-00-b8-44-00` |
| CANN | 9.1.0，本机路径 `/usr/local/Ascend/cann-9.1.0` |
| 架构 | `dav-3510` |
| 编译器 | 这套 CANN 自带的 `bisheng`，内核用 `-xasc --npu-arch=dav-3510` |
| 启动 | 单核 `<<<1, 0, stream>>>` |

只使用这套 CANN 的头文件。asc-devkit 的头更新，含有 9.1.0 上不存在的枚举和符号。用开发套件头文件覆盖本机 CANN 会测到另一套接口。

## 谁写什么

Agent 写的是调度：buffer 放在哪个空间、tile 多大、哪条 PIPE 搬、何时把 buffer 交给下一条 PIPE。

编译器写的是：event 编号、软件流水里不能出现的分支、搬运描述符、寄存器向量循环里的尾块掩码。比较类指令的比较掩码留在 VF 里，不交给 Agent 当 buffer，除非样例明确把掩码放在 UB（`select` 是这样，`select_gt` 不是）。

## 有效性以后怎么判

主张写在 `docs/evaluation/claims.md`（v2.8）。和这次交接有关的三条：

- **C2**：同一份调度，IR 生成的核相对手写 C 不多付性能。向量加上已经测过，见进展文档。这不是 Agent 对比。
- **C1**：同一个 Agent，一臂写 IR 再降级，一臂直接写 `.asc`。这才是「性能增益」要回答的问题。现在还没开跑。
- **C3**：检查器必须在上板前拦住非法 IR。C3 未测就不能进 Agent 环。

时间增益只在开跑前封成「调度敏感」的任务上才算赢：空隙 `h = T_baseline / T_HW − 1 ≥ 0.20`，并且 IR 臂相对直接写 C 的中位比值差 `rel ≥ +0.20`。带宽已经顶满的任务不靠变快来判赢。

## 相关仓库（只作参考，不要把事实写回去）

- asc-devkit：头文件和 `examples/02_simd_c_api`。本机开发机上的副本较新，不能代替 9.1.0。
- cann-samples：https://gitcode.com/cann/cann-samples 。`elemwise_axpy` 是 Muls+Add，不是 `asc_axpy`。
- cann-bench：C1 的任务来自它的 level1，和当前代码生成支持集取交集。

开发机是 Windows，Python 用 `py -3`。上板环境是 Linux，用 `python3`。两边通过 GitHub 交接，不要靠拷贝工作区文件。
