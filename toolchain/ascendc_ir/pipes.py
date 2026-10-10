# Copyright (c) 2026 Huawei Technologies Co., Ltd.
# This program is free software, you can redistribute it and/or modify it under the terms and conditions of
# CANN Open Software License Agreement Version 2.0 (the "License").
# Please refer to the License for details. You may not use this file except in compliance with the License.
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY, OR FITNESS FOR A PARTICULAR PURPOSE.
# See LICENSE in the root of the software repository for the full text of the License.

"""PIPE 门面：mte2 / mte3 搬运，v 向量计算。计算 op 集合来自语料证据。"""

from __future__ import annotations

from .model.core import BufRef, Buffer, GmRef, Pipe, as_bufref
from .model.stmts import ComputeStmt, CopyStmt
from .trace.builder import current_builder, user_callsite


class PipeFacade:
    def __init__(self, pipe: Pipe):
        self.pipe = pipe


def _coerce(obj):
    """Buffer 归一为 BufRef；GmRef 透传（由检查器 V001/V006 判定）；其余类型拒绝。"""
    if isinstance(obj, (BufRef, GmRef)):
        return obj
    return as_bufref(obj)


class _CopyPipe(PipeFacade):
    def copy(self, src, dst) -> None:
        current_builder().add_stmt(CopyStmt(self.pipe, _coerce(src), _coerce(dst), user_callsite()))

    def nd2nz(self, src, dst, rows: int, cols: int, row_stride: int | None = None) -> None:
        """GM 上的 ND 矩阵搬到 L1，并转成 NZ。rows、cols 是这一块的逻辑行列。

        row_stride 是 GM 上每一行的元素个数。K 方向只搬一段时，它大于 cols。
        """
        stride = cols if row_stride is None else row_stride
        if stride < cols:
            raise ValueError(f"row_stride={stride} 小于这一块的列数 {cols}")
        scalars = (int(rows), int(cols)) if stride == cols else (int(rows), int(cols), int(stride))
        self._copy_form("nd2nz", src, dst, scalars)

    def dn2nz(self, src, dst, rows: int, cols: int, row_stride: int | None = None) -> None:
        """GM 上的 DN 矩阵搬到 L1 并转成 NZ。对照 data_copy_gm2l1.asc 的 asc_copy_gm2l1_dn2nz。"""
        stride = cols if row_stride is None else row_stride
        if stride < cols:
            raise ValueError(f"row_stride={stride} 小于这一块的列数 {cols}")
        scalars = (int(rows), int(cols)) if stride == cols else (int(rows), int(cols), int(stride))
        self._copy_form("dn2nz", src, dst, scalars)

    def l12l0a(self, src, dst, rows: int, cols: int) -> None:
        self._copy_form("l12l0a", src, dst, (int(rows), int(cols)))

    def l12l0b(self, src, dst, rows: int, cols: int) -> None:
        self._copy_form("l12l0b", src, dst, (int(rows), int(cols)))

    def l0c2gm(self, src, dst, rows: int, cols: int) -> None:
        """L0C 的分形结果写回 GM，布局转成行优先。rows 是 M，cols 是 N。"""
        self._copy_form("l0c2gm", src, dst, (int(rows), int(cols)))

    def _copy_form(self, form: str, src, dst, scalars: tuple) -> None:
        current_builder().add_stmt(
            CopyStmt(self.pipe, _coerce(src), _coerce(dst), user_callsite(), form, scalars)
        )


class _VectorPipe(PipeFacade):
    def add(self, dst, src0, src1) -> None:
        self._record("add", dst, (src0, src1), ())

    def cast(self, dst, src) -> None:
        self._record("cast", dst, (src,), ())

    def leakyrelu(self, dst, src, alpha: float) -> None:
        self._record("leakyrelu", dst, (src,), (float(alpha),))

    def repeat_reduce_sum(self, dst, src) -> None:
        self._record("repeat_reduce_sum", dst, (src,), ())

    def datablock_reduce_sum(self, dst, src) -> None:
        self._record("datablock_reduce_sum", dst, (src,), ())

    def select(self, dst, src0, src1, mask) -> None:
        """按 UB 打包位掩码在 src0/src1 间选择。对照 select.asc：谓词来自 mask 缓冲，不是尾块 update_mask。"""
        self._record("select", dst, (src0, src1, mask), ())

    def select_ne_scalar(self, dst, src0, src1, scalar: float) -> None:
        """src0 != scalar 时取 src0，否则取 src1。对照 floor_mod.asc 里的 asc_ne_scalar。"""
        self._record("select_ne_scalar", dst, (src0, src1), (float(scalar),))

    def select_gt(self, dst, src0, src1) -> None:
        """src0 > src1 时取 src0，否则取 src1。对照 compare.asc 场景1：比较掩码由编译器持有。"""
        self._record("select_gt", dst, (src0, src1), ())

    def select_gt_scalar(self, dst, src0, src1, scalar: float) -> None:
        """src0 > scalar 时取 src0，否则取 src1。对照 compare.asc 场景2。"""
        self._record("select_gt_scalar", dst, (src0, src1), (float(scalar),))

    def select_lt(self, dst, src0, src1) -> None:
        """src0 < src1 时取 src0，否则取 src1。对照 compare.asc 里的 asc_lt。"""
        self._record("select_lt", dst, (src0, src1), ())

    def select_lt_scalar(self, dst, src0, src1, scalar: float) -> None:
        """src0 < scalar 时取 src0，否则取 src1。对照 elu.asc 里的 asc_lt_scalar。"""
        self._record("select_lt_scalar", dst, (src0, src1), (float(scalar),))

    def select_ne(self, dst, src0, src1) -> None:
        """src0 != src1 时取 src0，否则取 src1。对照 floor_mod.asc 里的 asc_ne。"""
        self._record("select_ne", dst, (src0, src1), ())

    def select_eq(self, dst, src0, src1) -> None:
        """src0 == src1 时取 src0，否则取 src1。对照 asc_eq 的比较再选择。"""
        self._record("select_eq", dst, (src0, src1), ())

    def select_eq_scalar(self, dst, src0, src1, scalar: float) -> None:
        """src0 == scalar 时取 src0，否则取 src1。"""
        self._record("select_eq_scalar", dst, (src0, src1), (float(scalar),))

    def select_ge(self, dst, src0, src1) -> None:
        """src0 >= src1 时取 src0，否则取 src1。对照 asc_ge。"""
        self._record("select_ge", dst, (src0, src1), ())

    def select_ge_scalar(self, dst, src0, src1, scalar: float) -> None:
        """src0 >= scalar 时取 src0，否则取 src1。"""
        self._record("select_ge_scalar", dst, (src0, src1), (float(scalar),))

    def select_le(self, dst, src0, src1) -> None:
        """src0 <= src1 时取 src0，否则取 src1。对照 asc_le。"""
        self._record("select_le", dst, (src0, src1), ())

    def select_le_scalar(self, dst, src0, src1, scalar: float) -> None:
        """src0 <= scalar 时取 src0，否则取 src1。"""
        self._record("select_le_scalar", dst, (src0, src1), (float(scalar),))

    def duplicate(self, dst, scalar: float) -> None:
        """把标量填满目的向量。对照 duplicate.asc：只有 dst 与 scalar，无源向量。"""
        self._record("duplicate", dst, (), (float(scalar),))

    def arange(self, dst, start: float = 0.0) -> None:
        """按起始值写等差数列。对照 arange.asc：asc_arange，无源向量；每 VL 块 start 递增。"""
        self._record("arange", dst, (), (float(start),))

    def compute(self, name: str, dst, srcs=(), scalars=()) -> None:
        """记录目录里的向量计算名。没有降级模板的名字会在检查器里被拒绝，并带上头文件签名。"""
        self._record(str(name), dst, tuple(srcs), tuple(scalars))

    def __getattr__(self, name: str):
        from .catalog import BINARY_F32, BINARY_I32, SCALAR_F32, SCALAR_I32, UNARY_F32

        if name in BINARY_F32 | BINARY_I32 and name != "add":

            def binary(dst, src0, src1, _name=name):
                self._record(_name, dst, (src0, src1), ())

            return binary
        if name in UNARY_F32:

            def unary(dst, src, _name=name):
                self._record(_name, dst, (src,), ())

            return unary
        if name in SCALAR_F32:

            def scalar(dst, src, value: float, _name=name):
                self._record(_name, dst, (src,), (float(value),))

            return scalar
        if name in SCALAR_I32:

            def scalar_i32(dst, src, value: int, _name=name):
                self._record(_name, dst, (src,), (int(value),))

            return scalar_i32
        raise AttributeError(f"向量 PIPE 没有 {name!r}。目录里的其他计算用 v.compute(名字, ...) 记录")

    def _record(self, op: str, dst, srcs: tuple, scalars: tuple) -> None:
        stmt = ComputeStmt(Pipe.V, op, _coerce(dst), tuple(_coerce(s) for s in srcs), tuple(scalars), user_callsite())
        current_builder().add_stmt(stmt)


class _CubePipe(PipeFacade):
    def mmad(self, dst, a, b, m: int, k: int, n: int, init: bool = True) -> None:
        """一次矩阵乘。B 在 GM 和 L1 上按 (n, k) 存放，结果是 A[m, k] @ B.T。init 为真时清掉 L0C 里的旧值。"""
        flag = 1 if init else 0
        stmt = ComputeStmt(
            Pipe.M,
            "mmad",
            _coerce(dst),
            (_coerce(a), _coerce(b)),
            (int(m), int(k), int(n), flag),
            user_callsite(),
        )
        current_builder().add_stmt(stmt)

    def compute(self, name: str, dst, srcs=(), scalars=()) -> None:
        stmt = ComputeStmt(
            Pipe.M, str(name), _coerce(dst), tuple(_coerce(s) for s in srcs), tuple(scalars), user_callsite()
        )
        current_builder().add_stmt(stmt)


mte1 = _CopyPipe(Pipe.MTE1)
mte2 = _CopyPipe(Pipe.MTE2)
mte3 = _CopyPipe(Pipe.MTE3)
fix = _CopyPipe(Pipe.FIX)
v = _VectorPipe(Pipe.V)
m = _CubePipe(Pipe.M)
