# Copyright (c) 2026 Huawei Technologies Co., Ltd.
# This program is free software, you can redistribute it and/or modify it under the terms and conditions of
# CANN Open Software License Agreement Version 2.0 (the "License").
# Please refer to the License for details. You may not use this file except in compliance with the License.
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY, OR FITNESS FOR A PARTICULAR PURPOSE.
# See LICENSE in the root of the software repository for the full text of the License.

"""代码生成：golden diff、fail-closed 行为、直写形态。"""

from pathlib import Path

import pytest
from ascendc_ir import f32, gmptr, kernel, sync, ubuf
from ascendc_ir.codegen import CodegenError, generate
from ascendc_ir.pipes import mte2, mte3, v

GOLDEN = Path(__file__).resolve().parents[2] / "examples" / "vector_add" / "add_golden.asc"


def _add_kernel():
    from examples.vector_add.add import add_custom

    return add_custom.trace()


def test_add_matches_golden():
    assert generate(_add_kernel()) == GOLDEN.read_text(encoding="utf-8")


def test_generated_structure():
    out = generate(_add_kernel())
    assert "asc_init();" in out
    assert "for (uint32_t i = 0; i < 8; i++)" in out
    # WAR：x/y 双缓冲复用前等待
    assert "if (i >= 2) { asc_sync_wait(PIPE_V, PIPE_MTE2, EVENT_ID0); }" in out
    # WAR：z 单缓冲覆写前等待
    assert "if (i >= 1) { asc_sync_wait(PIPE_MTE3, PIPE_V, EVENT_ID3); }" in out
    # 前向交接
    assert "asc_sync_notify(PIPE_MTE2, PIPE_V, EVENT_ID2);" in out
    assert "asc_sync_wait(PIPE_V, PIPE_MTE3, EVENT_ID4);" in out
    # 5 条 event 通道，不超硬件上限
    assert "EVENT_ID5" not in out


def test_verifier_blocks_codegen():
    @kernel(device="ascend950pr")
    def bad(x: gmptr(f32), y: gmptr(f32), z: gmptr(f32)):
        x_local = ubuf(f32, 64)
        y_local = ubuf(f32, 64)
        z_local = ubuf(f32, 64)
        mte2.copy(x[0], x_local[0])
        mte2.copy(y[0], y_local[0])
        v.add(z_local, x_local, y_local)  # 缺 sync，V009 应阻断

    with pytest.raises(CodegenError, match="V009"):
        generate(bad.trace())


def test_unsupported_compute_op_fails_closed():
    @kernel(device="ascend950pr")
    def reduce_kernel(x: gmptr(f32), y: gmptr(f32)):
        x_local = ubuf(f32, 64)
        y_local = ubuf(f32, 8)
        mte2.copy(x[0], x_local[0])
        sync(mte2, v, on=x_local)
        v.repeat_reduce_sum(y_local[0], x_local[0])
        sync(v, mte3, on=y_local)
        mte3.copy(y_local[0], y[0])

    with pytest.raises(CodegenError, match="repeat_reduce_sum"):
        generate(reduce_kernel.trace())


def test_reroll_failure_fails_closed():
    @kernel(device="ascend950pr")
    def bad(x: gmptr(f32), z: gmptr(f32)):
        a = ubuf(f32, 64)
        b = ubuf(f32, 64)
        for i in range(2):
            mte2.copy(x[i * 64], a[0])
            sync(mte2, v, on=a, stage=i)
            v.add(b, a, a)
            if i == 0:
                v.add(b, b, b)  # 首轮多一条语句，破坏仿射规律

    with pytest.raises(CodegenError, match="重卷失败"):
        generate(bad.trace())


def test_single_tile_straight_line():
    @kernel(device="ascend950pr")
    def add1(x: gmptr(f32), y: gmptr(f32), z: gmptr(f32)):
        x_local = ubuf(f32, 2048)
        y_local = ubuf(f32, 2048)
        z_local = ubuf(f32, 2048)
        mte2.copy(x[0], x_local[0])
        mte2.copy(y[0], y_local[0])
        sync(mte2, v, on=(x_local, y_local))
        v.add(z_local, x_local[0], y_local[0])
        sync(v, mte3, on=z_local)
        mte3.copy(z_local, z[0])

    out = generate(add1.trace())
    assert "for (" not in out
    assert "if (i >=" not in out
    assert "asc_sync_notify(PIPE_MTE2, PIPE_V, EVENT_ID0);" in out
    assert "asc_add(z_local, x_local, y_local, 32, 1, 1, 1, 8, 8, 8);" in out
