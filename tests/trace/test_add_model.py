# Copyright (c) 2026 Huawei Technologies Co., Ltd.
# This program is free software, you can redistribute it and/or modify it under the terms and conditions of
# CANN Open Software License Agreement Version 2.0 (the "License").
# Please refer to the License for details. You may not use this file except in compliance with the License.
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY, OR FITNESS FOR A PARTICULAR PURPOSE.
# See LICENSE in the root of the software repository for the full text of the License.

"""trace 出的模型结构：参数、buffer、语句计数与顺序。"""

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


def test_params_and_buffers():
    k = _trace_add()
    assert k.name == "add_custom"
    assert k.device == "ascend950pr"
    assert [(p.name, p.dtype.value) for p in k.params] == [("x", "f32"), ("y", "f32"), ("z", "f32")]
    assert [(b.name, b.stages) for b in k.buffers] == [("x_local", 2), ("y_local", 2), ("z_local", 1)]


def test_statement_count_and_order():
    k = _trace_add()
    assert len(k.statements) == 8 * 6
    first_iter = [s.to_dict()["kind"] for s in k.statements[:6]]
    assert first_iter == ["copy", "copy", "sync", "compute", "sync", "copy"]


def test_statement_details():
    k = _trace_add()
    copy0 = k.statements[0]
    assert copy0.pipe.value == "mte2"
    assert copy0.src.to_dict() == {"param": "x", "offset": 0}
    assert copy0.dst.to_dict() == {"buffer": "x_local", "stage": 0}
    copy1 = k.statements[1]
    assert copy1.dst.to_dict() == {"buffer": "y_local", "stage": 0}
    sync0 = k.statements[2]
    assert (sync0.producer.value, sync0.consumer.value) == ("mte2", "v")
    assert [b.name for b in sync0.on] == ["x_local", "y_local"]
    assert sync0.stage == 0
    add0 = k.statements[3]
    assert add0.op == "add"
    assert add0.dst.to_dict() == {"buffer": "z_local", "stage": 0}
    # 第二轮迭代：x_local/y_local 复用 stage 1
    copy6 = k.statements[6]
    assert copy6.src.to_dict() == {"param": "x", "offset": 2048}
    assert copy6.dst.to_dict() == {"buffer": "x_local", "stage": 1}
    sync8 = k.statements[8]
    assert sync8.stage == 1


def test_ubuf_name_fallback():
    @kernel(device="ascend950pr")
    def unnamed(x: gmptr(f32)):
        ubuf(f32, 64)

    k = unnamed.trace()
    assert k.buffers[0].name == "buf_0"
