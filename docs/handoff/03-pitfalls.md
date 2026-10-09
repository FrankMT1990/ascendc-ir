# 踩坑

下面每一条都在 950、CANN 9.1.0、`dav-3510` 上发生过，或者被这次上板的编译器原文否定过。修的时候以 `board-3510` 的 `RESULTS.md` 和当时的 `.so` 为准，不要以较新的 asc-devkit 头文件为准。

## 编译器和头文件

- 内核必须用这套 CANN 里的 `bisheng` 编译，并带 `--npu-arch=dav-3510 -xasc -fPIC`。系统 `c++` 不认识 `--npu-arch`。
- 内核 `.o` 链进共享库时缺 `-fPIC` 会失败。CMake 的 `POSITION_INDEPENDENT_CODE` 不会作用到自定义的 bisheng 命令上，所以命令行里要自己写 `-fPIC`。
- 直调扩展还需要 Python 头文件。用 `Python3_INCLUDE_DIRS`，不要假设 `python` 命令在板上存在。
- `asc_loadalign_unpack`、`ASC_POSITION_EVEN` 在这套 9.1.0 里没有。cast 不要发出它们。

## 向量

- 3510 上没有「UB 指针版」的 `asc_add`。加法走寄存器向量：`asc_load`、`asc_add`、`asc_store`、`asc_update_mask_b32`。2201 那套按 32 字节块计数的 burst，在 3510 上单位是字节，`uint16` 最大 65535。16384 个 f32 是 65536 字节，一次搬不完，要按 8192 字节分块。
- 整数值的浮点字面量必须写成 `0.0f`、`1.0f`、`3.0f`。`0f` 会被当成八进制，`1f`、`3f` 会报非法数字。`arange`、`duplicate`、标量运算和带标量的比较都因此编不过，直到 `512950c`。
- `v.log` 必须发 `asc_ln`。9.1.0 的寄存器接口里没有 `asc_log`。`asc_log` 的指针形态在 2201 的头里。
- `select` 的掩码在 UB，字节数 = f32 个数 × 4 / 8。谓词来自 `asc_loadalign_postupdate`，不要把 `asc_update_mask_b32` 当成选择条件。
- `select_gt` 等比较再选择：比较掩码是 VF 内的寄存器。Agent 不传 mask buffer。
- `axpy` 不要发明降级。cann-samples 里的 axpy 是 Muls 加 Add。头文件里的 `asc_axpy` 会读目的寄存器，套逐元素模板会算错。
- `ceil`、`trunc` 对 `(-1, 0)` 的输入写出 `+0.0`。这是指令行为。检查脚本把正负零都算通过，不要在 IR 里再加一段「修正符号」的指令，除非有新的样例证明应该这样做。

## 矩阵

- 头文件 `cube_datamove.h` 里，`__NPU_ARCH__ == 2201` 和 `3510` 是两套签名。第一轮记录把 2201 的 10 参 `nd2nz` 和 11 参 `l0c2gm` 当成了 9.1.0 的 3510 接口，导致第二轮仍然编不过。
- 3510 上已经编过并算对的写法：
  - `asc_set_gm2l1_nz_para` 之后，`asc_copy_gm2l1_nd2nz(dst, src, 字节行距, 0, rows, cols, 0, false)`。`0` 对应 `NORMAL_FIRST_VICTIM`。本核的字节行距是 `32 × 2 = 64`。
  - `asc_set_l0c2gm_nz2nd(1, 0, 0)` 之后，21 参的 `asc_copy_l0c2gm`，其中 `nz2nd` 为真、`nz2dn` 为假。
  - `asc_mmad(..., 0, true, false, init)`。不要写 `asc_unit_flag_mode::DISABLE`，这个枚举在 9.1.0 上不存在。
- f32 矩阵乘的 K 方向粒度是 8，样例还要转置。不要套 f16 的 C0=16 公式。
- L0C 到 UB 的样例使用 `__mix__(1, 2)`。这一批不生成 mix 核。UB 和 Cube buffer 出现在同一个核里，检查器会拒绝。
- K 分块累加：第一段 init 为真，后面为假，并且在 `init=false` 的 `asc_mmad` 之前发 `asc_sync_pipe(PIPE_M)`。不要在循环里写 `if`。

## 测量

- 不要把不同核数、不同计时入口的时间相减。2.006 μs 是 32 核 aclnnAdd，4.370 μs 是单核流水拷贝下界。用它们算空隙会得到没有意义的负数。
- 向量加生成核已经贴着单核拷贝下界。再测它的时间，看不出 IR 相对直接写 C 的增益。
- 归约的 1.19e-7 是 8 通道再在主机相加，和一次性求和的顺序不同。不要放宽容差来掩盖别的错误。
- wheel 很小而检查仍通过，是导入落到了源码树。确认安装时要离开源码目录再 `import ir_board`。

## 协作

- 上板任务写成要核对的结果，不要写成一串必须原样执行的脚本。编译失败时可以跳过单个核、改构建方式，但要留下编译器原文。
- 结果写 `RESULTS.md` 并推到 `board-3510`。不要只在对话里贴日志。
- 开发机推 GitHub 走本机 `socks5h://127.0.0.1:1080`（Linsoc）。代理只完成 SOCKS 握手、上游不回数据时，Git 会报 TLS eof。这是代理隧道的问题，不是仓库地址的问题。上板环境如果自己能推 GitHub，不要改用开发机的代理。
- 不要改 Git 的用户名、邮箱或全局配置。
