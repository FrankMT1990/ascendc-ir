# 进展

主分支 `master` 的尖端是 `3acb588`（2026-10-09 已推到 GitHub）。上板结果在分支 `board-3510` 的 `ac1ba1a`。

计划表在 `docs/project-plan.md`。第 1–19 步都是 done。第 19 步的安装包修复还没有在 950 上再装一次确认。

## 已经在 950 上成立的事

`board-3510` 的 `ac1ba1a`：`pack/board_3510` 里 50 个由 IR 生成的核，`scripts/check_ir.py` 退出码 0。

- 44 个逐位一致，其中包括矩阵乘 **1024/1024**。
- 4 个在容差内：div（最大绝对误差 5.96e-08）、ln、log（都是 1.19e-07）、sqrt（1.19e-07）。容差是 `1e-4 + 1e-4×|golden|`。
- ceil、trunc 按正负零判据通过。输入 `-0.875` 的 9 条 lane 上，核写出 `+0.0`，参考是 `-0.0`，值差为 0。

矩阵乘的布局：A、B 都是 `(32, 32)` f16，B 按 `(n, k)` 存放，K 分成 16+16。第一段 `asc_mmad` 的 init 为真，第二段为假，累加前有 `asc_sync_pipe(PIPE_M)`。结果是 A 乘 B 的转置，对 float32。输入是 0、1、2，点积在 f32 里是整数。

更早的向量加 M0（同一份调度，生成核对手写核）：中位约 4.396 μs 对 4.398 μs，税约 −0.05%，16384/16384 逐位一致。这只说明代码生成没有多付钱。不要把 4.398 μs 写成 C1 的 `T_baseline`。

四个直调核（加、leakyrelu、half 转 float、求和）在 `a884886` 上通过。cast 是 `vlds(..., UNPK_B16)` 再 `asc_half2float`。归约随机输入的绝对误差 1.19e-7 来自求和顺序，不是错结果。

## 代码现在会发出什么

向量：f32 逐元素（二进制、一元、标量）、`select` 与六种比较及其标量形式、`duplicate`、`arange`、`cast`（half 到 float）、`repeat_reduce_sum`、int32 的 `xor` 和移位。`v.log` 发出的指令是 `asc_ln`。

矩阵：f16 的 `nd2nz`（8 参，行距是字节，L2 模式 0）、`l12l0a` / `l12l0b`、`asc_mmad`（unit flag 整数 0）、`l0c2gm`（21 参，`nz2nd` 为真）。前面分别有 `asc_set_gm2l1_nz_para` 和 `asc_set_l0c2gm_nz2nd(1, 0, 0)`。

没有模板、因此会在 V013 拒绝的例子：`axpy`、`madd`、`addc`、会读目的寄存器的融合、把一条向量收成更少结果的归约（`repeat_reduce_sum` 除外）、`gather`、`mmad_mx`、f32 的转置矩阵乘。`dn2nz` 有生成，但这 50 个核里没有单独测过。

## 关键提交

| 提交 | 内容 |
|---|---|
| `285361f` | 记下向量加基线与硬件下界，分类仍未定 |
| `d3a37d7` | 第一版 50 核上板包 |
| `512950c` | 浮点字面量改成 `N.0f`，`log` 改成 `asc_ln`。搬运当时误用了 2201 的参数个数 |
| `f29f782` | `nd2nz` 8 参，`l0c2gm` 21 参。与后来板上改的 5 处调用一致 |
| `0e09320` | 记下 50/50 通过 |
| `3acb588` | 编译结束后把 `_C.abi3.so` 复制进 wheel 的 build lib |
| `ac1ba1a`（`board-3510`） | 上板全文记录，在 `pack/board_3510/RESULTS.md` |

## 安装包

`pack/board_3510` 用 `bash build.sh --soc=ascend950 --install` 构建。历史上 wheel 只有约 1695 字节，因为 `build_py` 先于 `build_ext`，`.so` 只出现在源码树。检查当时能跑，是因为 CANN 的 `PYTHONPATH` 末尾有空项，导入先落到源码目录。`3acb588` 在编译结束后把 `.so` 复制进 setuptools 的 build lib。这一修复还没有在 950 上重装确认。下次本来要构建时，看 wheel 是否明显大于 1695 字节，并且离开源码目录仍能 `import ir_board`。

## 还不能当成封存的文件

`evals/c1/freeze.json`、`task_book.md`、`tolerance.txt` 在开发机上是未跟踪草稿。支持集只有 `add_f32`，`t_baseline` 和 `t_hw` 都是 null，W2 的理由仍写着「没有 Cube 词汇」。不要把这三份文件提交成正式封存，除非按 `04-next-work.md` 重写并在第一份试点之前完成哈希。
