# Copyright (c) 2026 Huawei Technologies Co., Ltd.
# This program is free software, you can redistribute it and/or modify it under the terms and conditions of
# CANN Open Software License Agreement Version 2.0 (the "License").
# Please refer to the License for details. You may not use this file except in compliance with the License.
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY, OR FITNESS FOR A PARTICULAR PURPOSE.
# See LICENSE in the root of the software repository for the full text of the License.

"""Kernel 模型与 canonical JSON 序列化。"""

from __future__ import annotations

import json
from dataclasses import dataclass, field


@dataclass
class Kernel:
    name: str
    device: str
    params: list = field(default_factory=list)
    buffers: list = field(default_factory=list)
    statements: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "device": self.device,
            "params": [{"name": p.name, "dtype": p.dtype.value} for p in self.params],
            "buffers": [
                {
                    "name": b.name,
                    "dtype": b.dtype.value,
                    "elems": b.elems,
                    "stages": b.stages,
                    "callsite": b.callsite.to_dict(),
                }
                for b in self.buffers
            ],
            "statements": [s.to_dict() for s in self.statements],
        }

    def to_json(self) -> str:
        """canonical 序列化：排序键、固定缩进，同一 trace 产物字节一致。"""
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True, indent=2) + "\n"
