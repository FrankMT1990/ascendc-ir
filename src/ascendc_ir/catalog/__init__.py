# Copyright (c) 2026 Huawei Technologies Co., Ltd.
# This program is free software, you can redistribute it and/or modify it under the terms and conditions of
# CANN Open Software License Agreement Version 2.0 (the "License").
# Please refer to the License for details. You may not use this file except in compliance with the License.
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY, OR FITNESS FOR A PARTICULAR PURPOSE.
# See LICENSE in the root of the software repository for the full text of the License.

"""3510 向量与矩阵 C API 目录。由 scripts/extract_3510_api.py 从 asc-devkit 头文件生成。"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

_PATH = Path(__file__).resolve().parent / "api_3510.json"

# 签名已核对为「目的、两个同类型源、mask」，且 mask 只是尾块谓词、不读目的寄存器。
# select 的谓词是选择条件，不能套尾块掩码；见 SPECIAL。
# madd / mula / abs_sub / exp_sub 可能读目的寄存器，不套用这个模板。
BINARY_F32 = frozenset({"add", "sub", "mul", "div", "max", "min", "and", "or", "prelu"})

# 签名已核对为「目的、一个源、mask」且语义是逐元素的 f32 运算。归约和 duplicate 不在这里。
UNARY_F32 = frozenset(
    {"abs", "ceil", "exp", "floor", "ln", "log", "neg", "not", "relu", "rint", "round", "sqrt", "trunc"}
)

# 签名已核对为「目的、一个源、一个 float、mask」，且不把目的寄存器当累加器。
# axpy 在样例里是 mul_scalar+add 组合，或 C++ Reg API；无独立 asc_axpy C 调度角色，不套模板。
SCALAR_F32 = frozenset({"add_scalar", "max_scalar", "min_scalar", "mul_scalar"})

# 头文件里的规范形是 vector_int32_t，mask 仍是尾块。移位标量在签名里是 int16_t，按整数传入。
BINARY_I32 = frozenset({"xor", "shiftleft", "shiftright"})
SCALAR_I32 = frozenset({"shiftleft_scalar", "shiftright_scalar"})

# 已有专门降级，不走上面的通用模板。
# select / select_gt* / duplicate / arange 按 asc-devkit 02_simd_c_api 样例角色降级。
SPECIAL = frozenset({
    "add",
    "leakyrelu",
    "cast",
    "repeat_reduce_sum",
    "datablock_reduce_sum",
    "mmad",
    "select",
    "select_gt",
    "select_gt_scalar",
    "select_lt",
    "select_lt_scalar",
    "select_ne",
    "select_ne_scalar",
    "select_eq",
    "select_eq_scalar",
    "select_ge",
    "select_ge_scalar",
    "select_le",
    "select_le_scalar",
    "duplicate",
    "arange",
})


def short_name(asc_name: str) -> str:
    return asc_name[4:] if asc_name.startswith("asc_") else asc_name


@lru_cache(maxsize=1)
def load() -> dict:
    return json.loads(_PATH.read_text(encoding="utf-8"))


def entries() -> list:
    return load()["entries"]


def by_short(name: str) -> list:
    return [item for item in entries() if short_name(item["name"]) == name]


def known(name: str) -> bool:
    return bool(by_short(name))


def signature_text(name: str, limit: int = 3) -> str:
    found = by_short(name)
    if not found:
        return ""
    lines = []
    for item in found[:limit]:
        params = ", ".join(item["params"])
        lines.append(f"{item['name']}({params})")
    extra = len(found) - limit
    if extra > 0:
        lines.append(f"另有 {extra} 个重载")
    return "；".join(lines)


def lowering_kind(name: str) -> str | None:
    """返回这一批会生成 C 的模板名。没有模板时返回 None，调用方必须拒绝，不能猜重载。"""
    if name in SPECIAL:
        return "special"
    if name in BINARY_F32:
        return "reg_binary"
    if name in UNARY_F32:
        return "reg_unary"
    if name in SCALAR_F32 or name in SCALAR_I32:
        return "reg_scalar"
    if name in BINARY_I32:
        return "reg_binary"
    return None


def reg_c_dtype(name: str) -> str | None:
    """通用寄存器模板使用的元素类型。比较和专用模板不走这里。"""
    if name in BINARY_I32 or name in SCALAR_I32:
        return "i32"
    if name in BINARY_F32 or name in UNARY_F32 or name in SCALAR_F32:
        return "f32"
    return None
