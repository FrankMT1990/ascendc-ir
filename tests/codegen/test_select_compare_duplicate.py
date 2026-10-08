# Copyright (c) 2026 Huawei Technologies Co., Ltd.
# This program is free software, you can redistribute it and/or modify it under the terms and conditions of
# CANN Open Software License Agreement Version 2.0 (the "License").
# Please refer to the License for details. You may not use this file except in compliance with the License.
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY, OR FITNESS FOR A PARTICULAR PURPOSE.
# See LICENSE in the root of the software repository for the full text of the License.

"""样例驱动的 select / select_gt / duplicate 降级。"""

from ascendc_ir import f32, gmptr, kernel, sync, u8, ubuf
from ascendc_ir.codegen.emit import generate
from ascendc_ir.pipes import mte2, mte3, v
from ascendc_ir.verify import verify


def test_select_loads_packed_mask_not_update_mask():
    """对照 asc-devkit select.asc：谓词来自 UB packed bits，store 用 PAT_ALL。"""

    @kernel(device="ascend950pr")
    def select_custom(x: gmptr(f32), y: gmptr(f32), mask: gmptr(u8), z: gmptr(f32)):
        x_local = ubuf(f32, 64)
        y_local = ubuf(f32, 64)
        mask_local = ubuf(u8, 32)  # 64 * sizeof(float) / 8
        z_local = ubuf(f32, 64)
        mte2.copy(x[0], x_local)
        mte2.copy(y[0], y_local)
        mte2.copy(mask[0], mask_local)
        sync(mte2, v, on=(x_local, y_local, mask_local))
        v.select(z_local, x_local, y_local, mask_local)
        sync(v, mte3, on=z_local)
        mte3.copy(z_local, z[0])

    assert verify(select_custom.trace()) == []
    text = generate(select_custom.trace())
    assert "asc_loadalign_postupdate(vmask, mask_local, mask_rep_size);" in text
    assert "asc_select(reg_dst, reg_src0, reg_src1, vmask);" in text
    assert "asc_create_mask_b32(PAT_ALL)" in text
    assert "asc_update_mask_b32" not in text.split("select_vf(")[1].split("}")[0]


def test_select_gt_emits_asc_gt_then_select():
    """对照 compare.asc 场景1：比较掩码是 VF 内寄存器，Agent 不传 mask 缓冲。"""

    @kernel(device="ascend950pr")
    def compare_s1(x: gmptr(f32), y: gmptr(f32), z: gmptr(f32)):
        x_local = ubuf(f32, 64)
        y_local = ubuf(f32, 64)
        z_local = ubuf(f32, 64)
        mte2.copy(x[0], x_local)
        mte2.copy(y[0], y_local)
        sync(mte2, v, on=(x_local, y_local))
        v.select_gt(z_local, x_local, y_local)
        sync(v, mte3, on=z_local)
        mte3.copy(z_local, z[0])

    assert verify(compare_s1.trace()) == []
    text = generate(compare_s1.trace())
    assert "asc_gt(cmp_mask, reg_src0, reg_src1, vmask);" in text
    assert "asc_select(reg_dst, reg_src0, reg_src1, cmp_mask);" in text


def test_select_gt_scalar_emits_asc_gt_scalar():
    @kernel(device="ascend950pr")
    def compare_s2(x: gmptr(f32), y: gmptr(f32), z: gmptr(f32)):
        x_local = ubuf(f32, 64)
        y_local = ubuf(f32, 64)
        z_local = ubuf(f32, 64)
        mte2.copy(x[0], x_local)
        mte2.copy(y[0], y_local)
        sync(mte2, v, on=(x_local, y_local))
        v.select_gt_scalar(z_local, x_local, y_local, 0.0)
        sync(v, mte3, on=z_local)
        mte3.copy(z_local, z[0])

    text = generate(compare_s2.trace())
    assert "asc_gt_scalar(cmp_mask, reg_src0, value, vmask);" in text
    assert "asc_select(reg_dst, reg_src0, reg_src1, cmp_mask);" in text


def test_duplicate_emits_asc_duplicate_scalar():
    """对照 duplicate.asc：无源向量，只有 dst 与 scalar。"""

    @kernel(device="ascend950pr")
    def duplicate_custom(y: gmptr(f32)):
        y_local = ubuf(f32, 64)
        v.duplicate(y_local, 3.14)
        sync(v, mte3, on=y_local)
        mte3.copy(y_local, y[0])

    assert verify(duplicate_custom.trace()) == []
    text = generate(duplicate_custom.trace())
    assert "asc_duplicate_scalar(reg_dst, value, vmask);" in text
    assert "asc_load" not in text.split("duplicate_vf(")[1].split("}")[0]


def test_arange_emits_asc_arange():
    """对照 arange.asc：无源向量；asc_arange + PAT_ALL store；每 VL 递增 start。"""

    @kernel(device="ascend950pr")
    def arange_custom(y: gmptr(f32)):
        y_local = ubuf(f32, 64)
        v.arange(y_local, 0.0)
        sync(v, mte3, on=y_local)
        mte3.copy(y_local, y[0])

    assert verify(arange_custom.trace()) == []
    text = generate(arange_custom.trace())
    assert "asc_arange(reg_dst, start_value);" in text
    assert "asc_create_mask_b32(PAT_ALL)" in text
    assert "start_value += static_cast<float>(one_rep_size);" in text
    assert "asc_load" not in text.split("arange_vf(")[1].split("}")[0]


def test_select_lt_and_ne_follow_compare_samples():
    @kernel(device="ascend950pr")
    def cmp_custom(x: gmptr(f32), y: gmptr(f32), z: gmptr(f32)):
        x_local = ubuf(f32, 64)
        y_local = ubuf(f32, 64)
        z_local = ubuf(f32, 64)
        mte2.copy(x[0], x_local)
        mte2.copy(y[0], y_local)
        sync(mte2, v, on=(x_local, y_local))
        v.select_lt(z_local, x_local, y_local)
        sync(v, mte3, on=z_local)
        mte3.copy(z_local, z[0])

    text = generate(cmp_custom.trace())
    assert "asc_lt(cmp_mask, reg_src0, reg_src1, vmask);" in text
    assert "asc_select(reg_dst, reg_src0, reg_src1, cmp_mask);" in text


def test_select_eq_and_le_scalar_cover_remaining_compares():
    @kernel(device="ascend950pr")
    def eq_custom(x: gmptr(f32), y: gmptr(f32), z: gmptr(f32)):
        x_local = ubuf(f32, 64)
        y_local = ubuf(f32, 64)
        z_local = ubuf(f32, 64)
        mte2.copy(x[0], x_local)
        mte2.copy(y[0], y_local)
        sync(mte2, v, on=(x_local, y_local))
        v.select_eq(z_local, x_local, y_local)
        sync(v, mte3, on=z_local)
        mte3.copy(z_local, z[0])

    text = generate(eq_custom.trace())
    assert "asc_eq(cmp_mask, reg_src0, reg_src1, vmask);" in text

    @kernel(device="ascend950pr")
    def le_custom(x: gmptr(f32), y: gmptr(f32), z: gmptr(f32)):
        x_local = ubuf(f32, 64)
        y_local = ubuf(f32, 64)
        z_local = ubuf(f32, 64)
        mte2.copy(x[0], x_local)
        mte2.copy(y[0], y_local)
        sync(mte2, v, on=(x_local, y_local))
        v.select_le_scalar(z_local, x_local, y_local, 1.0)
        sync(v, mte3, on=z_local)
        mte3.copy(z_local, z[0])

    text = generate(le_custom.trace())
    assert "asc_le_scalar(cmp_mask, reg_src0, value, vmask);" in text


def test_xor_and_shift_scalar_use_int32_registers():
    from ascendc_ir import i32

    @kernel(device="ascend950pr")
    def xor_custom(x: gmptr(i32), y: gmptr(i32), z: gmptr(i32)):
        x_local = ubuf(i32, 64)
        y_local = ubuf(i32, 64)
        z_local = ubuf(i32, 64)
        mte2.copy(x[0], x_local)
        mte2.copy(y[0], y_local)
        sync(mte2, v, on=(x_local, y_local))
        v.xor(z_local, x_local, y_local)
        sync(v, mte3, on=z_local)
        mte3.copy(z_local, z[0])

    text = generate(xor_custom.trace())
    assert "vector_int32_t reg_dst;" in text
    assert "asc_xor(reg_dst, reg_src0, reg_src1, vmask);" in text
    assert "__gm__ int32_t*" in text

    @kernel(device="ascend950pr")
    def shift_custom(x: gmptr(i32), z: gmptr(i32)):
        x_local = ubuf(i32, 64)
        z_local = ubuf(i32, 64)
        mte2.copy(x[0], x_local)
        sync(mte2, v, on=x_local)
        v.shiftleft_scalar(z_local, x_local, 3)
        sync(v, mte3, on=z_local)
        mte3.copy(z_local, z[0])

    text = generate(shift_custom.trace())
    assert "asc_shiftleft_scalar(reg_dst, reg_src, value, vmask);" in text
    assert "shiftleft_scalar_vf(" in text
    assert ", 3);" in text
    assert "3f" not in text


def test_every_catalog_api_has_a_schedule_role():
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    catalog = json.loads((root / "src/ascendc_ir/catalog/api_3510.json").read_text(encoding="utf-8"))
    roles = json.loads((root / "src/ascendc_ir/catalog/schedule_roles.json").read_text(encoding="utf-8"))
    names = {item["name"][4:] if item["name"].startswith("asc_") else item["name"] for item in catalog["entries"]}
    listed = [item["name"] for item in roles["roles"]]
    assert len(listed) == len(set(listed)) == len(names)
    assert set(listed) == names
    lowered = [item for item in roles["roles"] if item["role"] == "lowered"]
    assert lowered and all(item.get("pattern") for item in lowered)
    assert roles["counts"]["no_sample"] + roles["counts"]["sample_unlowered"] + roles["counts"]["lowered"] + roles["counts"]["compiler"] == len(names)

