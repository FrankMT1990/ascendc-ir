# Copyright (c) 2026 Huawei Technologies Co., Ltd.
# This program is free software, you can redistribute it and/or modify it under the terms and conditions of
# CANN Open Software License Agreement Version 2.0 (the "License").
# Please refer to the License for details. You may not use this file except in compliance with the License.
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY, OR FITNESS FOR A PARTICULAR PURPOSE.
# See LICENSE in the root of the software repository for the full text of the License.

"""代码生成：golden diff、fail-closed 行为、event 分配、直写形态。"""

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
    # 循环按槽位展开：event id 与槽位偏移均为编译期字面量（复审核对项）
    assert "for (uint32_t i = 0; i < 8; i += 2)" in out
    assert "?" not in out  # 无运行时三元表达式
    # WAR：x/y 双缓冲按槽位一个字面量 event（同一 id 上 notify/wait 严格交替）
    assert "if (i >= 2) { asc_sync_wait(PIPE_V, PIPE_MTE2, EVENT_ID0); }" in out
    assert "if (i + 1 >= 2) { asc_sync_wait(PIPE_V, PIPE_MTE2, EVENT_ID1); }" in out
    assert "asc_copy_gm2ub(x_local, x + i * 2048, 1, 256, 0, 0);" in out
    assert "asc_copy_gm2ub(x_local + 2048, x + (i + 1) * 2048, 1, 256, 0, 0);" in out
    # WAR：z 单缓冲，槽位 0 条件等待、槽位 1 无条件等待
    assert "if (i >= 1) { asc_sync_wait(PIPE_MTE3, PIPE_V, EVENT_ID0); }" in out
    # 前向交接：event id 按 PIPE 对独立分配
    assert "asc_sync_notify(PIPE_MTE2, PIPE_V, EVENT_ID0);" in out
    assert "asc_sync_wait(PIPE_V, PIPE_MTE3, EVENT_ID0);" in out
    # 每对 PIPE 不超 8 个 id
    assert "EVENT_ID8" not in out


def test_war_release_after_last_read():
    """两条计算读同一槽位：释放在最后一次消费之后，每轮每个 buffer 只发一次（复审第 1 条）。"""

    @kernel(device="ascend950pr")
    def two_reads(x: gmptr(f32), y: gmptr(f32), z: gmptr(f32), w: gmptr(f32)):
        TILE, TILES = 2048, 4
        x_local = ubuf(f32, TILE, stages=2)
        y_local = ubuf(f32, TILE, stages=2)
        z_local = ubuf(f32, TILE, stages=1)
        w_local = ubuf(f32, TILE, stages=1)
        for i in range(TILES):
            mte2.copy(x[i * TILE], x_local[i % 2])
            mte2.copy(y[i * TILE], y_local[i % 2])
            sync(mte2, v, on=(x_local, y_local), stage=i)
            v.add(z_local, x_local[i % 2], y_local[i % 2])
            v.add(w_local, x_local[i % 2], y_local[i % 2])
            sync(v, mte3, on=z_local)
            mte3.copy(z_local, z[i * TILE])
            sync(v, mte3, on=w_local)
            mte3.copy(w_local, w[i * TILE])

    out = generate(two_reads.trace())
    lines = out.splitlines()
    add_idx = [n for n, line in enumerate(lines) if "asc_add(" in line]
    notify_idx = [n for n, line in enumerate(lines) if "asc_sync_notify(PIPE_V, PIPE_MTE2" in line]
    # 每个子迭代释放 x/y 各一次（共 2×2=4 条）；每个 buffer 每轮只发一次
    assert len(notify_idx) == 4
    for k in range(2):
        sub = notify_idx[2 * k : 2 * k + 2]
        for n in sub:
            assert sum(1 for a in add_idx if a < n) == 2 * (k + 1)  # 两条 add 都读完才释放


def test_war_release_deduped_for_repeated_src():
    """v.add(z, x, x)：同一 buffer 重复读，每个子迭代只释放一次（评审第 1 条附带）。"""

    @kernel(device="ascend950pr")
    def ok(x: gmptr(f32), z: gmptr(f32)):
        TILE, TILES = 2048, 4
        x_local = ubuf(f32, TILE, stages=2)
        z_local = ubuf(f32, TILE, stages=1)
        for i in range(TILES):
            mte2.copy(x[i * TILE], x_local[i % 2])
            sync(mte2, v, on=x_local, stage=i)
            v.add(z_local, x_local[i % 2], x_local[i % 2])
            sync(v, mte3, on=z_local)
            mte3.copy(z_local, z[i * TILE])

    out = generate(ok.trace())
    # 按槽位展开后两个子迭代各一次释放；未去重则为四次
    assert out.count("asc_sync_notify(PIPE_V, PIPE_MTE2") == 2


def test_gm_base_offset_preserved():
    """仿射 GM 地址保留第 0 轮基址（评审第 2 条）。"""

    @kernel(device="ascend950pr")
    def off(x: gmptr(f32), z: gmptr(f32)):
        a = ubuf(f32, 64)
        b = ubuf(f32, 64)
        for i in range(2):
            mte2.copy(x[8 + i * 64], a[0])
            sync(mte2, v, on=a, stage=i)
            v.add(b, a, a)
            sync(v, mte3, on=b)
            mte3.copy(b, z[i * 64])

    out = generate(off.trace())
    assert "x + 8 + i * 64" in out


def test_gm_constant_nonzero_offset_preserved():
    """stride 为 0 但偏移非 0：每轮都读 x[8]（评审第 2 条）。"""

    @kernel(device="ascend950pr")
    def off(x: gmptr(f32), z: gmptr(f32)):
        a = ubuf(f32, 64)
        b = ubuf(f32, 64)
        for i in range(2):
            mte2.copy(x[8], a[0])
            sync(mte2, v, on=a, stage=i)
            v.add(b, a, a)
            sync(v, mte3, on=b)
            mte3.copy(b, z[i * 64])

    out = generate(off.trace())
    assert "x + 8" in out
    assert "x + 8 + i" not in out


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


def test_reroll_op_mismatch_rejected():
    """两轮结构相同但 op 不同（add vs cast），必须拒绝（评审第 4 条）。"""

    @kernel(device="ascend950pr")
    def bad(x: gmptr(f32), z: gmptr(f32)):
        a = ubuf(f32, 64)
        b = ubuf(f32, 64)
        for i in range(2):
            mte2.copy(x[i * 64], a[0])
            sync(mte2, v, on=a, stage=i)
            if i == 0:
                v.add(b, a, a)
            else:
                v.cast(b, a)
            sync(v, mte3, on=b)
            mte3.copy(b, z[i * 64])

    with pytest.raises(CodegenError, match="重卷失败"):
        generate(bad.trace())


def test_straight_line_slot_reuse_rejected():
    """sync 全不写 stage 且槽位复用：不是单 tile，拒绝生成（评审第 3 条）。"""

    @kernel(device="ascend950pr")
    def bad(x: gmptr(f32), z: gmptr(f32)):
        a = ubuf(f32, 64)
        b = ubuf(f32, 64)
        mte2.copy(x[0], a[0])
        sync(mte2, v, on=a)
        v.add(b, a, a)
        mte2.copy(x[64], a[0])  # 槽位复用但没有迭代号标记
        sync(mte2, v, on=a)
        v.add(b, a, a)

    with pytest.raises(CodegenError, match="重卷失败"):
        generate(bad.trace())


def test_inplace_rmw_gets_clear_error():
    """直写形态的就地改写（RMW）：检查器放行，codegen 以「生产 PIPE 唯一」拒绝（复审第 2 条）。"""

    @kernel(device="ascend950pr")
    def rmw(x: gmptr(f32), z: gmptr(f32)):
        a = ubuf(f32, 64)
        mte2.copy(x[0], a[0])
        sync(mte2, v, on=a)
        v.add(a, a, a)  # 就地改写：生产 PIPE 变成 {mte2, v}
        sync(v, mte3, on=a)
        mte3.copy(a, z[0])

    with pytest.raises(CodegenError, match="就地改写"):
        generate(rmw.trace())


def test_tiles_not_divisible_by_stages_rejected():
    """按槽位展开要求 TILES 被流水深度整除（复审衍生约束）。"""

    @kernel(device="ascend950pr")
    def odd(x: gmptr(f32), z: gmptr(f32)):
        a = ubuf(f32, 64, stages=2)
        b = ubuf(f32, 64)
        for i in range(3):
            mte2.copy(x[i * 64], a[i % 2])
            sync(mte2, v, on=a, stage=i)
            v.add(b, a[i % 2], a[i % 2])
            sync(v, mte3, on=b)
            mte3.copy(b, z[i * 64])

    with pytest.raises(CodegenError, match="整除"):
        generate(odd.trace())


def test_repeat_uint8_guard():
    """asc_add 的 repeat 是 uint8_t：单 stage 超 255×256B 拒绝（评审核对项）。"""

    @kernel(device="ascend950pr")
    def big(x: gmptr(f32), z: gmptr(f32)):
        a = ubuf(f32, 16448)  # 65792B → repeat 257
        b = ubuf(f32, 16448)
        mte2.copy(x[0], a[0])
        sync(mte2, v, on=a)
        v.add(b, a, a)
        sync(v, mte3, on=b)
        mte3.copy(b, z[0])

    with pytest.raises(CodegenError, match="255"):
        generate(big.trace())


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
