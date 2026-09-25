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

    def _record(self, op: str, dst, srcs: tuple, scalars: tuple) -> None:
        stmt = ComputeStmt(Pipe.V, op, _coerce(dst), tuple(_coerce(s) for s in srcs), tuple(scalars), user_callsite())
        current_builder().add_stmt(stmt)


mte2 = _CopyPipe(Pipe.MTE2)
mte3 = _CopyPipe(Pipe.MTE3)
v = _VectorPipe(Pipe.V)
