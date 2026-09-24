# Copyright (c) 2026 Huawei Technologies Co., Ltd.
# This program is free software, you can redistribute it and/or modify it under the terms and conditions of
# CANN Open Software License Agreement Version 2.0 (the "License").
# Please refer to the License for details. You may not use this file except in compliance with the License.
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY, OR FITNESS FOR A PARTICULAR PURPOSE.
# See LICENSE in the root of the software repository for the full text of the License.

"""调用点记录：诊断定位依赖 file/line/function/statement 的准确性。"""

from pathlib import Path

from ascendc_ir import f32, gmptr, kernel, sync, ubuf
from ascendc_ir.pipes import mte2, mte3, v


def _trace_add():
    @kernel(device="ascend950pr")
    def add_custom(x: gmptr(f32), y: gmptr(f32), z: gmptr(f32)):
        TILE, TILES = 2048, 2
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


def test_callsites_point_into_user_function():
    k = _trace_add()
    this_file = str(Path(__file__).resolve())
    for stmt in k.statements:
        cs = stmt.callsite
        assert cs.file == this_file
        assert cs.function == "add_custom"
        assert cs.line > 0
        assert cs.statement


def test_buffer_callsite_records_declaration_line():
    k = _trace_add()
    x_local = k.buffers[0]
    assert x_local.callsite.function == "add_custom"
    assert "x_local" in x_local.callsite.statement
    assert "ubuf" in x_local.callsite.statement


def test_callsite_distinguishes_statements():
    k = _trace_add()
    lines = [s.callsite.line for s in k.statements[:6]]
    # 同一迭代内六条语句的调用点行号互不相同
    assert len(set(lines)) == 6
