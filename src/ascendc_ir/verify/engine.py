# Copyright (c) 2026 Huawei Technologies Co., Ltd.
# This program is free software, you can redistribute it and/or modify it under the terms and conditions of
# CANN Open Software License Agreement Version 2.0 (the "License").
# Please refer to the License for details. You may not use this file except in compliance with the License.
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY, OR FITNESS FOR A PARTICULAR PURPOSE.
# See LICENSE in the root of the software repository for the full text of the License.

"""检查器入口：verify(kernel) -> list[Diagnostic]。"""

from __future__ import annotations

from ..devices import load_device
from .rules import (
    v001_pathway,
    v002_ub_capacity,
    v003_sync_pairing,
    v004_sync_direction,
    v005_event_pressure,
    v006_compute_spaces,
    v007_alignment,
    v008_device_guard,
    v009_cross_pipe_read,
    v010_read_without_producer,
)

RULES = [
    v001_pathway,
    v002_ub_capacity,
    v003_sync_pairing,
    v004_sync_direction,
    v005_event_pressure,
    v006_compute_spaces,
    v007_alignment,
    v008_device_guard,
    v009_cross_pipe_read,
    v010_read_without_producer,
]


def verify(kernel, device=None) -> list:
    """运行全部规则，按 (file, line, id) 排序；同一调用点的重复诊断去重。

    trace 展开后，循环体每一轮都会产生诊断；它们的 callsite 与 message 相同，
    对 agent 只报一次。
    """
    dev = device if device is not None else load_device(kernel.device)
    diags = []
    for rule in RULES:
        diags.extend(rule(kernel, dev))
    seen = set()
    unique = []
    for d in diags:
        key = (d.id, d.callsite.file, d.callsite.line, d.message)
        if key not in seen:
            seen.add(key)
            unique.append(d)
    unique.sort(key=lambda d: (d.callsite.file, d.callsite.line, d.id))
    return unique
