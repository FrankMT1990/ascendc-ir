# Copyright (c) 2026 Huawei Technologies Co., Ltd.
# This program is free software, you can redistribute it and/or modify it under the terms and conditions of
# CANN Open Software License Agreement Version 2.0 (the "License").
# Please refer to the License for details. You may not use this file except in compliance with the License.
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY, OR FITNESS FOR A PARTICULAR PURPOSE.
# See LICENSE in the root of the software repository for the full text of the License.

"""语句模型：copy / compute / sync。"""

from __future__ import annotations

from dataclasses import dataclass

from .core import BufRef, Buffer, Callsite, GmRef, Pipe


@dataclass
class CopyStmt:
    pipe: Pipe
    src: GmRef | BufRef
    dst: GmRef | BufRef
    callsite: Callsite

    def to_dict(self) -> dict:
        return {
            "kind": "copy",
            "pipe": self.pipe.value,
            "src": self.src.to_dict(),
            "dst": self.dst.to_dict(),
            "callsite": self.callsite.to_dict(),
        }


@dataclass
class ComputeStmt:
    pipe: Pipe
    op: str
    dst: BufRef
    srcs: tuple
    scalars: tuple
    callsite: Callsite

    def to_dict(self) -> dict:
        return {
            "kind": "compute",
            "pipe": self.pipe.value,
            "op": self.op,
            "dst": self.dst.to_dict(),
            "srcs": [s.to_dict() for s in self.srcs],
            "scalars": list(self.scalars),
            "callsite": self.callsite.to_dict(),
        }


@dataclass
class SyncStmt:
    producer: Pipe
    consumer: Pipe
    on: tuple
    stage: int | None
    callsite: Callsite

    def to_dict(self) -> dict:
        return {
            "kind": "sync",
            "producer": self.producer.value,
            "consumer": self.consumer.value,
            "on": [b.name for b in self.on],
            "stage": self.stage,
            "callsite": self.callsite.to_dict(),
        }
