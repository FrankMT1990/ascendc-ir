# Copyright (c) 2026 Huawei Technologies Co., Ltd.
# This program is free software, you can redistribute it and/or modify it under the terms and conditions of
# CANN Open Software License Agreement Version 2.0 (the "License").
# Please refer to the License for details. You may not use this file except in compliance with the License.
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY, OR FITNESS FOR A PARTICULAR PURPOSE.
# See LICENSE in the root of the software repository for the full text of the License.

"""canonical JSON：同一输入两次 trace 字节一致，且可被 json 解析。"""

import json

from ascendc_ir import f32, gmptr, kernel, sync, ubuf
from ascendc_ir.pipes import mte2, mte3, v


def _trace_add():
    @kernel(device="ascend950pr")
    def add_custom(x: gmptr(f32), y: gmptr(f32), z: gmptr(f32)):
        TILE, TILES = 2048, 8
        x_local = ubuf(f32, TILE, stages=2)
        y_local = ubuf(f32, TILE, stages=2)
        z_local = ubuf(f32, TILE, stages=1)
        for i in range(TILES):
            mte2.copy(x[i * TILE], x_local[i % 2])
            mte2.copy(y[i * TILE], y_local[i % 2])
            sync(mte2, v, on=(x_local, y_local), stage=i)
            v.add(z_local, x_local[i % 2], y_local[i % 2])
            sync(v, mte3, on=z_local)
            mte3.copy(z_local, z[i * TILE])

    return add_custom.trace()


def test_canonical_json_is_stable():
    assert _trace_add().to_json() == _trace_add().to_json()


def test_canonical_json_roundtrip():
    doc = json.loads(_trace_add().to_json())
    assert doc["name"] == "add_custom"
    assert doc["device"] == "ascend950pr"
    assert len(doc["buffers"]) == 3
    assert len(doc["statements"]) == 48
    kinds = {s["kind"] for s in doc["statements"]}
    assert kinds == {"copy", "compute", "sync"}
