# Copyright (c) 2026 Huawei Technologies Co., Ltd.
# This program is free software and you can redistribute it and/or modify it under the terms and conditions of
# CANN Open Software License Agreement Version 2.0 (the "License").
# You may refer to the License for details on the use of this software distributed under the License.
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY OR FITNESS FOR A PARTICULAR PURPOSE.
# See LICENSE in the root of the software repository for the full text of the License.

"""ADR 0015/0016：多循环段 + gather/brc/reduce_max/arange_i32/strided 搬运的单测。"""

import pytest

from ascendc_ir import f32, gmptr, i32, kernel, sync, ubuf
from ascendc_ir.codegen.emit import CodegenError, generate
from ascendc_ir.pipes import mte2, mte3, v


def test_two_sequential_loops():
    """两段循环：段间 PIPE_ALL 屏障 + 循环 1/2 标签。"""

    @kernel(device="ascend950pr")
    def two_loops(x: gmptr(f32), s: gmptr(f32), z: gmptr(f32)):
        TILE, ROWS, GROUPS = 64, 128, 2
        x_local = ubuf(f32, TILE, stages=2)
        acc = ubuf(f32, 64)
        g_local = ubuf(f32, TILE, stages=2)
        out_local = ubuf(f32, TILE, stages=2)
        for i in range(ROWS):
            mte2.copy(x[i * TILE], x_local[i % 2])
            sync(mte2, v, on=x_local, stage=i)
            v.repeat_reduce_sum(acc, x_local[i % 2])
            sync(v, mte3, on=acc, stage=i)
            mte3.copy_strided(acc, s[i * 64], 1, 256, 0, 0)
        for i in range(GROUPS):
            mte2.copy(s[i * 64], g_local[i % 2])
            sync(mte2, v, on=g_local, stage=i)
            v.mul(out_local[i % 2], g_local[i % 2], g_local[i % 2])
            sync(v, mte3, on=out_local, stage=i)
            mte3.copy(out_local[i % 2], z[i * TILE])

    out = generate(two_loops.trace())
    assert "asc_sync_pipe(PIPE_ALL);" in out
    assert "// 循环 1 prologue i = 0" in out
    assert "// 循环 2 prologue i = 0" in out
    assert "for (uint32_t i = 0; i < 128; i += 2)" in out
    assert "for (uint32_t i = 0; i < 2; i += 2)" in out or "for (uint32_t i = 0; i < 2; i ++)" in out or "// 循环 2 epilogue" in out


def test_preloop_plain_section():
    """前导直写段（γ 预载）+ 循环段：屏障不出现在 plain→loop 边界。"""

    @kernel(device="ascend950pr")
    def preloop(x: gmptr(f32), g: gmptr(f32), z: gmptr(f32)):
        TILE, TILES = 64, 4
        gamma = ubuf(f32, 64)
        x_local = ubuf(f32, TILE, stages=2)
        z_local = ubuf(f32, TILE, stages=1)
        mte2.copy(g[0], gamma)
        sync(mte2, v, on=gamma)
        for i in range(TILES):
            mte2.copy(x[i * TILE], x_local[i % 2])
            sync(mte2, v, on=(x_local, gamma), stage=i)
            v.mul(z_local, x_local[i % 2], gamma)
            sync(v, mte3, on=z_local, stage=i)
            mte3.copy(z_local, z[i * TILE])

    out = generate(preloop.trace())
    assert "asc_sync_pipe(PIPE_ALL);" not in out
    assert "// 循环之后" not in out
    assert "asc_copy_gm2ub(gamma, g, 1, 256, 0, 0);" in out
    assert "asc_copy_gm2ub(x_local, x + i * 64, 1, 256, 0, 0);" in out
    assert "asc_sync_notify(PIPE_MTE2, PIPE_V, EVENT_ID0);" in out


def test_gather_emission():
    @kernel(device="ascend950pr")
    def gathered(x: gmptr(f32), y: gmptr(i32), z: gmptr(f32)):
        N = 128
        table = ubuf(f32, 256)
        idx = ubuf(i32, N)
        dst = ubuf(f32, N)
        mte2.copy(x[0], table)
        mte2.copy(y[0], idx)
        sync(mte2, v, on=(table, idx))
        v.gather(dst, table, idx)
        sync(v, mte3, on=dst)
        mte3.copy(dst, z[0])

    out = generate(gathered.trace())
    assert "gather_vf(table, idx, dst, 128);" in out
    assert "asc_gather(reg_dst, table, reg_idx, vmask);" in out
    assert "asc_loadalign(reg_idx, idx + i * one_rep_size);" in out


def test_gather_rejects_mismatched_idx():
    @kernel(device="ascend950pr")
    def bad(x: gmptr(f32), y: gmptr(i32), z: gmptr(f32)):
        table = ubuf(f32, 256)
        idx = ubuf(i32, 64)
        dst = ubuf(f32, 128)
        mte2.copy(x[0], table)
        mte2.copy(y[0], idx, 1, 256, 0, 0)
        sync(mte2, v, on=(table, idx))
        v.gather(dst, table, idx)
        sync(v, mte3, on=dst)
        mte3.copy(dst, z[0])

    with pytest.raises(CodegenError, match="索引元素个数"):
        generate(bad.trace())


def test_brc_emission_loop_affine():
    @kernel(device="ascend950pr")
    def brcd(x: gmptr(f32), g: gmptr(f32), z: gmptr(f32)):
        TILE, TILES = 64, 4
        gamma = ubuf(f32, 64)
        gb = ubuf(f32, 64)
        x_local = ubuf(f32, TILE, stages=2)
        z_local = ubuf(f32, TILE, stages=1)
        mte2.copy(g[0], gamma)
        sync(mte2, v, on=gamma)
        for i in range(TILES):
            mte2.copy(x[i * TILE], x_local[i % 2])
            sync(mte2, v, on=(x_local, gamma), stage=i)
            v.brc(gb, gamma, 0, 1)
            v.mul(z_local, x_local[i % 2], gb)
            sync(v, mte3, on=z_local, stage=i)
            mte3.copy(z_local, z[i * TILE])

    out = generate(brcd.trace())
    assert "brc_vf(gamma, gb, i);" in out
    assert "asc_loadalign_brc(reg_dst, src, offset);" in out
    assert "brc_vf(gamma, gb, 0);" in out or "brc_vf(gamma, gb, 1);" in out


def test_reduce_max_emission():
    @kernel(device="ascend950pr")
    def rmax(x: gmptr(f32), z: gmptr(f32)):
        TILE = 64
        x_local = ubuf(f32, TILE)
        m_local = ubuf(f32, 64)
        mte2.copy(x[0], x_local)
        sync(mte2, v, on=x_local)
        v.repeat_reduce_max(m_local, x_local)
        sync(v, mte3, on=m_local)
        mte3.copy_strided(m_local, z[0], 1, 256, 0, 0)

    out = generate(rmax.trace())
    assert "reduce_max_vf(x_local, m_local, 64);" in out
    assert "asc_reduce_max(dst_reg, src_reg, vmask);" in out
    assert "asc_duplicate_scalar(acc_reg, -3.402823466e+38f);" in out
    assert "asc_duplicate(bcast_reg, acc_reg, vmask);" in out


def test_arange_i32_emission():
    @kernel(device="ascend950pr")
    def ramp(z: gmptr(i32)):
        idx = ubuf(i32, 128)
        v.arange_i32(idx, 0)
        sync(v, mte3, on=idx)
        mte3.copy(idx, z[0])

    out = generate(ramp.trace())
    assert "arange_i32_vf(idx, 128, 0);" in out
    assert "vector_int32_t reg_dst;" in out


def test_strided_copy_emission():
    @kernel(device="ascend950pr")
    def colcopy(x: gmptr(f32), z: gmptr(f32)):
        COLS, ROWS = 8, 64
        col = ubuf(f32, ROWS)
        out_col = ubuf(f32, ROWS)
        for j in range(COLS):
            mte2.copy_strided(x[j], col, ROWS, 4, 8192, 4)
            sync(mte2, v, on=col, stage=j)
            v.mul(out_col, col, col)
            sync(v, mte3, on=out_col, stage=j)
            mte3.copy_strided(out_col, z[j], ROWS, 4, 4, 4096)

    out = generate(colcopy.trace())
    assert "asc_copy_gm2ub(col, x + j * 1, 64, 4, 8192, 4);" in out
    assert "asc_copy_ub2gm(z + j * 1, out_col, 64, 4, 4, 4096);" in out


def test_strided_copy_alignment_guard():
    @kernel(device="ascend950pr")
    def bad(x: gmptr(f32), z: gmptr(f32)):
        col = ubuf(f32, 64)
        mte2.copy_strided(x[0], col, 64, 4, 8192, 8)
        sync(mte2, v, on=col)
        mte3.copy(col, z[0])

    with pytest.raises(CodegenError, match="dst_stride"):
        generate(bad.trace())
