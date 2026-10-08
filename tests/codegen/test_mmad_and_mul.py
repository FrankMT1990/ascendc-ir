# Copyright (c) 2026 Huawei Technologies Co., Ltd.
# This program is free software, you can redistribute it and/or modify it under the terms and conditions of
# CANN Open Software License Agreement Version 2.0 (the "License").
# Please refer to the License for details. You may not use this file except in compliance with the License.
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY, OR FITNESS FOR A PARTICULAR PURPOSE.
# See LICENSE in the root of the software repository for the full text of the License.

"""3510 矩阵乘与逐元素乘法的生成结果。"""

import importlib.util
from pathlib import Path

from ascendc_ir import f16, f32, gmptr, kernel, l0a, l0b, l0c, l1buf, sync, ubuf
from ascendc_ir.catalog import entries, known, short_name
from ascendc_ir.codegen.emit import CodegenError, generate
from ascendc_ir.pipes import fix, m, mte1, mte2, v
from ascendc_ir.verify import verify

_ROOT = Path(__file__).resolve().parents[2]


def _load(rel: str, name: str):
    spec = importlib.util.spec_from_file_location(name, _ROOT / rel)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


mmad_custom = _load("examples/matmul/mmad.py", "mmad_example").mmad_custom
mul_custom = _load("examples/vector_mul/mul.py", "mul_example").mul_custom


def test_catalog_covers_matrix_and_vector_names():
    names = {short_name(item["name"]) for item in entries()}
    assert len(names) >= 600
    assert "mmad" in names
    assert "copy_gm2l1_nd2nz" in names
    assert "mul" in names
    assert known("mmad")
    assert not known("not_a_real_ascend_op")


def test_mmad_lowers_one_cube_pipeline():
    text = generate(mmad_custom.trace())
    assert "__global__ __cube__ void mmad_custom" in text
    assert text.count("asc_mmad(") == 2
    assert "asc_sync_pipe(PIPE_M);" in text
    assert ", 16, 0, false);" in text
    assert "64ULL" in text
    # 单缓冲复用 L1/L0 时，第二轮写回前必须等上一轮消费（对照 asc-devkit mmad_double_buffer 的 lock）。
    assert "asc_sync_notify(PIPE_MTE1, PIPE_MTE2, EVENT_ID0);" in text
    assert "asc_sync_wait(PIPE_MTE1, PIPE_MTE2, EVENT_ID0);" in text
    assert "asc_sync_notify(PIPE_M, PIPE_MTE1, EVENT_ID0);" in text
    assert "asc_sync_wait(PIPE_M, PIPE_MTE1, EVENT_ID0);" in text
    for token in (
        "asc_copy_gm2l1_nd2nz",
        "asc_copy_l12l0a",
        "asc_copy_l12l0b",
        "asc_copy_l0c2gm",
        "asc_set_gm2l1_nz_para",
        "__cbuf__",
        "__ca__",
        "__cb__",
        "__cc__",
    ):
        assert token in text
    assert "asc_loadalign_unpack" not in text


def test_l1_double_buffer_emits_slot_war():
    """对照 asc-devkit 00_mmad_double_buffer：L1 stages=2 时按槽位发 WAR。"""
    m_dim = n_dim = 32
    k_tile = 16
    k_dim = 64
    tiles = k_dim // k_tile

    @kernel(device="ascend950pr")
    def mmad_db(a: gmptr(f16), b: gmptr(f16), c: gmptr(f32)):
        a_l1 = l1buf(f16, m_dim * k_tile, stages=2)
        b_l1 = l1buf(f16, n_dim * k_tile, stages=2)
        a_l0 = l0a(f16, m_dim * k_tile)
        b_l0 = l0b(f16, n_dim * k_tile)
        c_l0 = l0c(f32, m_dim * n_dim)
        for kt in range(tiles):
            mte2.nd2nz(a[kt * k_tile], a_l1[kt % 2], m_dim, k_tile, row_stride=k_dim)
            mte2.nd2nz(b[kt * k_tile], b_l1[kt % 2], n_dim, k_tile, row_stride=k_dim)
            sync(mte2, mte1, on=(a_l1, b_l1), stage=kt)
            mte1.l12l0a(a_l1[kt % 2], a_l0, m_dim, k_tile)
            mte1.l12l0b(b_l1[kt % 2], b_l0, n_dim, k_tile)
            sync(mte1, m, on=(a_l0, b_l0), stage=kt)
            m.mmad(c_l0, a_l0, b_l0, m_dim, k_tile, n_dim, init=(kt == 0))
        sync(m, fix, on=c_l0)
        fix.l0c2gm(c_l0, c[0], m_dim, n_dim)

    assert verify(mmad_db.trace()) == []
    text = generate(mmad_db.trace())
    assert "__cbuf__ half a_l1[1024];" in text or "a_l1[1024]" in text or "[1024]" in text
    assert "a_l1 + 512" in text or "+ 512" in text
    assert "asc_sync_notify(PIPE_MTE1, PIPE_MTE2, EVENT_ID0);" in text
    assert "asc_sync_notify(PIPE_MTE1, PIPE_MTE2, EVENT_ID1);" in text
    assert "asc_sync_wait(PIPE_MTE1, PIPE_MTE2, EVENT_ID0);" in text
    assert "asc_sync_wait(PIPE_MTE1, PIPE_MTE2, EVENT_ID1);" in text
    assert text.count("asc_mmad(") == 4
    assert text.count("asc_sync_pipe(PIPE_M);") == 3


def test_board_pack_matches_generator():
    pack = _ROOT / "pack" / "board_3510"
    assert (pack / "mmad_custom.asc").read_text(encoding="utf-8") == generate(mmad_custom.trace())
    assert (pack / "mul_custom.asc").read_text(encoding="utf-8") == generate(mul_custom.trace())


def test_board_pack_covers_each_lowered_kernel():
    import json

    pack = _ROOT / "pack" / "board_3510"
    manifest = json.loads((pack / "ops.json").read_text(encoding="utf-8"))
    checker = (pack / "scripts" / "check_ir.py").read_text(encoding="utf-8")
    assert len(manifest) == 50
    names = [item["op"] for item in manifest]
    assert len(names) == len(set(names))
    for item in manifest:
        cpp = pack / "csrc" / "ops" / item["name"] / "op_kernel" / f"{item['name']}_kernel.cpp"
        assert item["token"] in cpp.read_text(encoding="utf-8")
        if item["kind"] not in {"mmad", "reduce"}:
            assert f'"{item["op"]}"' in checker


def test_mul_lowers_reg_binary():
    text = generate(mul_custom.trace())
    assert "asc_mul(reg_dst, reg_src0, reg_src1, vmask);" in text
    assert "__vector__ __global__ __aicore__ void mul_custom" in text


def test_unlowered_catalog_op_is_rejected_with_signature():
    @kernel(device="ascend950pr")
    def bad(x: gmptr(f32), z: gmptr(f32)):
        x_local = ubuf(f32, 64)
        z_local = ubuf(f32, 64)
        v.compute("reduce_sum", z_local, (x_local,))

    diags = verify(bad.trace())
    hit = next(d for d in diags if d.id == "V013")
    assert "reduce_sum" in hit.message
    assert "asc_reduce_sum" in hit.message


def test_axpy_is_not_templated():
    """axpy：asc-devkit examples/ 无独立样例；cann-samples 的 axpy 是 Muls+Add 组合，不发明单指令角色。"""

    @kernel(device="ascend950pr")
    def bad(x: gmptr(f32), y: gmptr(f32), z: gmptr(f32)):
        x_local = ubuf(f32, 64)
        y_local = ubuf(f32, 64)
        z_local = ubuf(f32, 64)
        v.compute("axpy", z_local, (x_local,), (1.0,))

    ids = [d.message for d in verify(bad.trace()) if d.id == "V013"]
    assert any("axpy" in message for message in ids)
    assert not hasattr(v, "axpy")


def test_shape_mismatch_and_uninit_accumulate_are_rejected():
    @kernel(device="ascend950pr")
    def bad(a: gmptr(f16), b: gmptr(f16), c: gmptr(f32)):
        a_l1 = l1buf(f16, 32 * 32)
        b_l1 = l1buf(f16, 32 * 32)
        a_l0 = l0a(f16, 32 * 32)
        b_l0 = l0b(f16, 32 * 32)
        c_l0 = l0c(f32, 32 * 32)
        mte2.nd2nz(a[0], a_l1, 16, 16)
        mte2.nd2nz(b[0], b_l1, 16, 16)
        sync(mte2, mte1, on=(a_l1, b_l1))
        mte1.l12l0a(a_l1, a_l0, 16, 16)
        mte1.l12l0b(b_l1, b_l0, 16, 16)
        sync(mte1, m, on=(a_l0, b_l0))
        m.mmad(c_l0, a_l0, b_l0, 32, 32, 32, init=False)
        sync(m, fix, on=c_l0)
        fix.l0c2gm(c_l0, c[0], 32, 32)

    messages = [d.message for d in verify(bad.trace()) if d.id == "V012"]
    assert any("nd2nz" in message and "32" in message for message in messages)
    assert any("init 为假" in message for message in messages)


def test_ub_and_cube_mix_is_rejected_before_codegen():
    @kernel(device="ascend950pr")
    def bad(x: gmptr(f32), a: gmptr(f16)):
        scratch = ubuf(f32, 64)
        a_l1 = l1buf(f16, 32 * 32)
        mte2.copy(x[0], scratch)
        mte2.nd2nz(a[0], a_l1, 32, 32)

    diags = verify(bad.trace())
    assert any(d.id == "V012" and "ubuf" in d.message for d in diags)
    try:
        generate(bad.trace())
    except CodegenError:
        return
    raise AssertionError("混用 UB 和 Cube 的核不应生成")
