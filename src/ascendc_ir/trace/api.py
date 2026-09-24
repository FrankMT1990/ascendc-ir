# Copyright (c) 2026 Huawei Technologies Co., Ltd.
# This program is free software, you can redistribute it and/or modify it under the terms and conditions of
# CANN Open Software License Agreement Version 2.0 (the "License").
# Please refer to the License for details. You may not use this file except in compliance with the License.
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY, OR FITNESS FOR A PARTICULAR PURPOSE.
# See LICENSE in the root of the software repository for the full text of the License.

"""用户侧原语：gmptr / ubuf / sync。"""

from __future__ import annotations

from ..model.core import BufRef, Buffer, DType, Pipe
from ..model.stmts import SyncStmt
from .builder import current_builder, lhs_name, user_callsite


class GmParamSpec:
    """`gmptr(dtype)` 的返回值，用作 @kernel 函数的参数注解。"""

    def __init__(self, dtype: DType):
        if not isinstance(dtype, DType):
            raise TypeError(f"gmptr 的参数必须是 DType，得到 {dtype!r}")
        self.dtype = dtype


def gmptr(dtype: DType) -> GmParamSpec:
    return GmParamSpec(dtype)


def ubuf(dtype: DType, elems: int, stages: int = 1) -> Buffer:
    """创建 UB buffer；默认名取赋值左侧变量名。"""
    callsite = user_callsite()
    name = lhs_name(callsite.statement)
    return current_builder().add_buffer(dtype, elems, stages, callsite, name)


def sync(producer, consumer, on, stage: int | None = None) -> None:
    """声明一条生产→消费交接边，对应 asc_sync_notify + asc_sync_wait 配对。

    on 接受 Buffer、BufRef 或它们的 tuple/list； BufRef 的 stage 可作为默认 stage。
    """
    p = _as_pipe(producer)
    q = _as_pipe(consumer)
    items = tuple(on) if isinstance(on, (tuple, list)) else (on,)
    if not items:
        raise ValueError("sync 的 on 不能为空")
    resolved = []
    derived_stage = stage
    for item in items:
        if isinstance(item, BufRef):
            resolved.append(item.buffer)
            if derived_stage is None:
                derived_stage = item.stage
        elif isinstance(item, Buffer):
            resolved.append(item)
        else:
            raise TypeError(f"sync 的 on 只接受 Buffer/BufRef，得到 {item!r}")
    current_builder().add_stmt(SyncStmt(p, q, tuple(resolved), derived_stage, user_callsite()))


def _as_pipe(obj) -> Pipe:
    if isinstance(obj, Pipe):
        return obj
    pipe = getattr(obj, "pipe", None)
    if isinstance(pipe, Pipe):
        return pipe
    raise TypeError(f"sync 的 pipe 参数必须是 Pipe 或 pipe 门面，得到 {obj!r}")
