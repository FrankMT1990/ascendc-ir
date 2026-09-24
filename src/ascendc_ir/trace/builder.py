# Copyright (c) 2026 Huawei Technologies Co., Ltd.
# This program is free software, you can redistribute it and/or modify it under the terms and conditions of
# CANN Open Software License Agreement Version 2.0 (the "License").
# Please refer to the License for details. You may not use this file except in compliance with the License.
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY, OR FITNESS FOR A PARTICULAR PURPOSE.
# See LICENSE in the root of the software repository for the full text of the License.

"""trace 构建器：维护当前 kernel 上下文，记录调用点。"""

from __future__ import annotations

import contextvars
import inspect
import linecache
from pathlib import Path

from ..model.core import Buffer, Callsite, DType
from ..model.kernel import Kernel

_PACKAGE_ROOT = Path(__file__).resolve().parents[1]

_active: contextvars.ContextVar = contextvars.ContextVar("ascendc_ir_builder", default=None)


class TraceBuilder:
    def __init__(self, name: str, device: str):
        self.kernel = Kernel(name=name, device=device)
        self._buffer_seq = 0

    def add_buffer(self, dtype: DType, elems: int, stages: int, callsite: Callsite, name: str | None = None) -> Buffer:
        if name is None:
            name = f"buf_{self._buffer_seq}"
            self._buffer_seq += 1
        buf = Buffer(name=name, dtype=dtype, elems=elems, stages=stages, callsite=callsite)
        self.kernel.buffers.append(buf)
        return buf

    def add_stmt(self, stmt) -> None:
        self.kernel.statements.append(stmt)


def current_builder() -> TraceBuilder:
    builder = _active.get()
    if builder is None:
        raise RuntimeError("ascendc_ir 原语只能在 @kernel 函数 trace 期间调用")
    return builder


def user_callsite() -> Callsite:
    """向上找到第一个不在 ascendc_ir 包内的栈帧，作为用户调用点。"""
    frame = inspect.currentframe()
    if frame is not None:
        frame = frame.f_back
    while frame is not None:
        path = Path(frame.f_code.co_filename).resolve()
        if not path.is_relative_to(_PACKAGE_ROOT):
            statement = linecache.getline(str(path), frame.f_lineno).strip()
            return Callsite(file=str(path), line=frame.f_lineno, function=frame.f_code.co_name, statement=statement)
        frame = frame.f_back
    return Callsite(file="<unknown>", line=0, function="<unknown>", statement="")


def lhs_name(statement: str) -> str | None:
    """从调用点源码行提取赋值左侧变量名，作为 buffer 的默认名。"""
    if "=" not in statement or "==" in statement:
        return None
    lhs = statement.split("=", 1)[0].strip()
    return lhs if lhs.isidentifier() else None
