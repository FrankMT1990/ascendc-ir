# Copyright (c) 2026 Huawei Technologies Co., Ltd.
# This program is free software, you can redistribute it and/or modify it under the terms and conditions of
# CANN Open Software License Agreement Version 2.0 (the "License").
# Please refer to the License for details. You may not use this file except in compliance with the License.
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY, OR FITNESS FOR A PARTICULAR PURPOSE.
# See LICENSE in the root of the software repository for the full text of the License.

"""AscendC-IR 核心数据模型：dtype、PIPE、buffer、引用与调用点。"""

from __future__ import annotations

import enum
from dataclasses import dataclass


class DType(enum.Enum):
    f16 = "f16"
    f32 = "f32"

    @property
    def nbytes(self) -> int:
        return _DTYPE_NBYTES[self]


_DTYPE_NBYTES = {DType.f16: 2, DType.f32: 4}

f16 = DType.f16
f32 = DType.f32


class Pipe(enum.Enum):
    S = "s"
    V = "v"
    M = "m"
    MTE1 = "mte1"
    MTE2 = "mte2"
    MTE3 = "mte3"
    FIX = "fix"


@dataclass(frozen=True)
class Callsite:
    """用户代码调用点：诊断定位的最小单位。"""

    file: str
    line: int
    function: str
    statement: str

    def to_dict(self) -> dict:
        return {
            "file": self.file,
            "line": self.line,
            "function": self.function,
            "statement": self.statement,
        }


@dataclass(frozen=True)
class GmParam:
    name: str
    dtype: DType

    def __getitem__(self, offset: int) -> "GmRef":
        if not isinstance(offset, int) or offset < 0:
            raise TypeError(f"GM 偏移必须是非负整数，得到 {offset!r}")
        return GmRef(self, offset)


@dataclass(frozen=True)
class GmRef:
    param: GmParam
    offset: int

    def to_dict(self) -> dict:
        return {"param": self.param.name, "offset": self.offset}


@dataclass(eq=False)
class Buffer:
    name: str
    dtype: DType
    elems: int
    stages: int
    callsite: Callsite

    def __post_init__(self) -> None:
        if self.elems <= 0:
            raise ValueError(f"buffer {self.name} 的 elems 必须为正，得到 {self.elems}")
        if self.stages <= 0:
            raise ValueError(f"buffer {self.name} 的 stages 必须为正，得到 {self.stages}")

    @property
    def stage_bytes(self) -> int:
        return self.elems * self.dtype.nbytes

    @property
    def total_bytes(self) -> int:
        return self.stage_bytes * self.stages

    def __getitem__(self, stage: int) -> "BufRef":
        if not isinstance(stage, int) or not 0 <= stage < self.stages:
            raise IndexError(f"buffer {self.name} 的 stage 必须在 [0, {self.stages})，得到 {stage!r}")
        return BufRef(self, stage)


@dataclass(frozen=True)
class BufRef:
    buffer: Buffer
    stage: int

    def to_dict(self) -> dict:
        return {"buffer": self.buffer.name, "stage": self.stage}


def as_bufref(obj) -> BufRef:
    """把裸 Buffer 归一为 BufRef；多 stage buffer 必须显式下标。"""
    if isinstance(obj, BufRef):
        return obj
    if isinstance(obj, Buffer):
        if obj.stages != 1:
            raise TypeError(
                f"buffer {obj.name} 有 {obj.stages} 个 stage，必须显式下标，如 {obj.name}[i % {obj.stages}]"
            )
        return BufRef(obj, 0)
    raise TypeError(f"期望 Buffer/BufRef，得到 {obj!r}")
