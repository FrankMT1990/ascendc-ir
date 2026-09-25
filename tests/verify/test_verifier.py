# Copyright (c) 2026 Huawei Technologies Co., Ltd.
# This program is free software, you can redistribute it and/or modify it under the terms and conditions of
# CANN Open Software License Agreement Version 2.0 (the "License").
# Please refer to the License for details. You may not use this file except in compliance with the License.
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY, OR FITNESS FOR A PARTICULAR PURPOSE.
# See LICENSE in the root of the software repository for the full text of the License.

"""V001–V009 逐规则接受/拒绝用例。语义以 docs/spec/verifier-rules.md 为准。"""

import pytest
from ascendc_ir import f32, gmptr, kernel, sync, ubuf
from ascendc_ir.devices import DeviceSpec, load_device
from ascendc_ir.pipes import mte2, mte3, v
from ascendc_ir.verify import verify


def _legal_add():
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


def _ids(diags):
    return sorted(d.id for d in diags)


def test_legal_add_accepted():
    assert verify(_legal_add()) == []


def test_v001_wrong_pipe_rejected():
    @kernel(device="ascend950pr")
    def bad(x: gmptr(f32), z: gmptr(f32)):
        x_local = ubuf(f32, 64)
        mte3.copy(x[0], x_local[0])

    diags = verify(bad.trace())
    assert "V001" in _ids(diags)
    assert "mte3.copy" in next(d for d in diags if d.id == "V001").callsite.statement


def test_v002_ub_overflow_rejected():
    @kernel(device="ascend950pr")
    def bad(x: gmptr(f32), z: gmptr(f32)):
        big = ubuf(f32, 40000, stages=2)  # 320KB，超过 248KB

    diags = verify(bad.trace())
    assert _ids(diags) == ["V002"]
    assert "big" in diags[0].callsite.statement


def test_v003_sync_without_producer_rejected():
    @kernel(device="ascend950pr")
    def bad(x: gmptr(f32), z: gmptr(f32)):
        x_local = ubuf(f32, 64)
        z_local = ubuf(f32, 64)
        mte2.copy(x[0], x_local[0])
        sync(mte2, v, on=(x_local, z_local))  # z_local 尚未生产
        v.add(z_local, x_local, x_local)

    diags = verify(bad.trace())
    assert "V003" in _ids(diags)


def test_v003_sync_without_consumer_rejected():
    @kernel(device="ascend950pr")
    def bad(x: gmptr(f32), z: gmptr(f32)):
        x_local = ubuf(f32, 64)
        y_local = ubuf(f32, 64)
        mte2.copy(x[0], x_local[0])
        sync(mte2, v, on=(x_local, y_local))  # y_local 没有消费者
        v.add(x_local, x_local, x_local)

    diags = verify(bad.trace())
    assert "V003" in _ids(diags)


def test_v004_flipped_direction_rejected():
    @kernel(device="ascend950pr")
    def bad(x: gmptr(f32), z: gmptr(f32)):
        x_local = ubuf(f32, 64)
        z_local = ubuf(f32, 64)
        mte2.copy(x[0], x_local[0])
        sync(v, mte2, on=x_local)  # 方向颠倒：生产在 mte2
        v.add(z_local, x_local, x_local)

    diags = verify(bad.trace())
    assert "V004" in _ids(diags)


def test_v005_event_pressure_rejected():
    @kernel(device="ascend950pr")
    def bad(x: gmptr(f32), z: gmptr(f32)):
        bufs = [ubuf(f32, 8) for _ in range(9)]
        for b in bufs:
            mte2.copy(x[0], b[0])
        for b in bufs:
            sync(mte2, v, on=b)
        for b in bufs:
            v.add(b, b, b)

    diags = verify(bad.trace())
    assert "V005" in _ids(diags)


def test_v006_gm_operand_rejected():
    @kernel(device="ascend950pr")
    def bad(x: gmptr(f32), y: gmptr(f32), z: gmptr(f32)):
        x_local = ubuf(f32, 64)
        z_local = ubuf(f32, 64)
        mte2.copy(x[0], x_local[0])
        sync(mte2, v, on=x_local)
        v.add(z_local, x_local, y[0])  # y 是 GM 参数，不能直算

    diags = verify(bad.trace())
    assert "V006" in _ids(diags)
    assert "v.add" in next(d for d in diags if d.id == "V006").callsite.statement


def test_v007_misaligned_buffer_rejected():
    @kernel(device="ascend950pr")
    def bad(x: gmptr(f32), z: gmptr(f32)):
        x_local = ubuf(f32, 100)  # 400B，不是 32B 整数倍
        mte2.copy(x[0], x_local[0])

    diags = verify(bad.trace())
    assert "V007" in _ids(diags)
    assert "ubuf" in next(d for d in diags if d.id == "V007").callsite.statement


def test_v008_pipe_not_on_device_rejected():
    base = load_device("ascend950pr")
    spec = DeviceSpec(
        id=base.id,
        npu_arch=base.npu_arch,
        ub_usable_bytes=base.ub_usable_bytes,
        l1_bytes=base.l1_bytes,
        align_bytes=base.align_bytes,
        pipes=tuple(p for p in base.pipes if p != "mte2"),
        event_ids=base.event_ids,
        pathways=base.pathways,
    )
    diags = verify(_legal_add(), device=spec)
    assert "V008" in _ids(diags)
    assert "V001" not in _ids(diags)


def test_v009_missing_sync_rejected():
    @kernel(device="ascend950pr")
    def bad(x: gmptr(f32), y: gmptr(f32), z: gmptr(f32)):
        x_local = ubuf(f32, 64)
        y_local = ubuf(f32, 64)
        z_local = ubuf(f32, 64)
        mte2.copy(x[0], x_local[0])
        mte2.copy(y[0], y_local[0])
        v.add(z_local, x_local, y_local)  # 缺 mte2→v 的 sync

    diags = verify(bad.trace())
    assert "V009" in _ids(diags)
    assert "v.add" in next(d for d in diags if d.id == "V009").callsite.statement
