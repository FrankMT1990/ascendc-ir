# Copyright (c) 2026 Huawei Technologies Co., Ltd.
# This program is free software, you can redistribute it and/or modify it under the terms and conditions of
# CANN Open Software License Agreement Version 2.0 (the "License").
# Please refer to the License for details. You may not use this file except in compliance with the License.
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY, OR FITNESS FOR A PARTICULAR PURPOSE.
# See LICENSE in the root of the software repository for the full text of the License.

"""给目录里的每一个 C API 标上调度角色。样例来自 asc-devkit examples 与 cann-samples 的 .asc。"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "src" / "ascendc_ir" / "catalog" / "api_3510.json"
OUT = ROOT / "src" / "ascendc_ir" / "catalog" / "schedule_roles.json"
SAMPLES = [
    Path(r"C:\Users\chenc\Projects\asc-devkit\examples"),
    Path(r"C:\Users\chenc\Projects\cann-samples"),
]
MANUAL = Path(r"C:\Users\chenc\Projects\asc-devkit\docs\zh\api\SIMD-API\c_api")

# 已经能生成 C 的调度名。比较类收成 select_*，不把寄存器掩码交给 Agent。
LOWERED = {
    "abs", "add", "add_scalar", "and", "arange", "ceil", "copy_gm2l1_dn2nz",
    "copy_gm2l1_nd2nz", "copy_l0c2gm", "copy_l12l0a", "copy_l12l0b", "div", "duplicate",
    "duplicate_scalar", "exp", "floor", "gt", "gt_scalar", "half2float", "leakyrelu",
    "ln", "log", "lt", "lt_scalar", "max", "max_scalar", "min", "min_scalar", "mmad",
    "mul", "mul_scalar", "ne", "ne_scalar", "neg", "not", "or", "prelu", "relu",
    "repeat_reduce_sum", "rint", "round", "select", "sqrt", "sub", "trunc",
    "eq", "eq_scalar", "ge", "ge_scalar", "le", "le_scalar",
    "xor", "shiftleft", "shiftright", "shiftleft_scalar", "shiftright_scalar",
}

# 样例里出现在编译器生成的 VF / 搬运参数里，Agent 不单独写。
COMPILER = {
    "loadalign", "loadalign_brc", "loadalign_postupdate", "loadalign_unpack", "loadalign_upsample",
    "set_gm2l1_nz_para", "set_l0c_copy_channel_para", "set_l0c_copy_config", "set_l0c_copy_nz_para",
    "set_l0c_copy_prequant", "storealign", "storealign_pack", "storealign_postupdate",
    "update_addr_reg_b16", "update_mask_b16", "update_mask_b32",
}

_BINARY = (
    "VF 循环：asc_update_mask_b32 作尾块掩码；asc_load 两个 f32 源；"
    "asc_{name}(dst, src0, src1, mask)；asc_store。调度：v.{name}(dst, src0, src1)。"
)
_UNARY = (
    "VF 循环：asc_update_mask_b32；asc_load 一个 f32 源；"
    "asc_{name}(dst, src, mask)；asc_store。调度：v.{name}(dst, src)。"
)
_SCALAR = (
    "VF 循环：asc_update_mask_b32；asc_load 一个 f32 源；"
    "asc_{name}(dst, src, scalar, mask)；asc_store。调度：v.{name}(dst, src, scalar)。"
)
_CMP = (
    "VF 循环：asc_update_mask_b32 只作尾块；asc_load 两个 f32；"
    "asc_{name}(cmp, src0, src1, tail)；asc_select(dst, src0, src1, cmp)；asc_storealign。"
    "比较掩码不进缓冲。调度：v.select_{op}(dst, src0, src1)。"
)
_CMP_SCALAR = (
    "VF 循环：尾块掩码；asc_load 两个 f32；"
    "asc_{name}(cmp, src0, scalar, tail)；asc_select(dst, src0, src1, cmp)；asc_storealign。"
    "调度：v.select_{op}(dst, src0, src1, scalar)。"
)

PATTERNS = {
    "add": _BINARY.format(name="add"),
    "sub": _BINARY.format(name="sub"),
    "mul": _BINARY.format(name="mul"),
    "div": _BINARY.format(name="div"),
    "max": _BINARY.format(name="max"),
    "min": _BINARY.format(name="min"),
    "and": _BINARY.format(name="and"),
    "or": _BINARY.format(name="or"),
    "prelu": _BINARY.format(name="prelu"),
    "abs": _UNARY.format(name="abs"),
    "ceil": _UNARY.format(name="ceil"),
    "exp": _UNARY.format(name="exp"),
    "floor": _UNARY.format(name="floor"),
    "ln": _UNARY.format(name="ln"),
    "log": _UNARY.format(name="log"),
    "neg": _UNARY.format(name="neg"),
    "not": _UNARY.format(name="not"),
    "relu": _UNARY.format(name="relu"),
    "rint": _UNARY.format(name="rint"),
    "round": _UNARY.format(name="round"),
    "sqrt": _UNARY.format(name="sqrt"),
    "trunc": _UNARY.format(name="trunc"),
    "add_scalar": _SCALAR.format(name="add_scalar"),
    "max_scalar": _SCALAR.format(name="max_scalar"),
    "min_scalar": _SCALAR.format(name="min_scalar"),
    "mul_scalar": _SCALAR.format(name="mul_scalar"),
    "leakyrelu": _SCALAR.format(name="leakyrelu").replace("v.leakyrelu", "v.leakyrelu"),
    "gt": _CMP.format(name="gt", op="gt"),
    "lt": _CMP.format(name="lt", op="lt"),
    "ne": _CMP.format(name="ne", op="ne"),
    "eq": _CMP.format(name="eq", op="eq"),
    "ge": _CMP.format(name="ge", op="ge"),
    "le": _CMP.format(name="le", op="le"),
    "gt_scalar": _CMP_SCALAR.format(name="gt_scalar", op="gt_scalar"),
    "lt_scalar": _CMP_SCALAR.format(name="lt_scalar", op="lt_scalar"),
    "ne_scalar": _CMP_SCALAR.format(name="ne_scalar", op="ne_scalar"),
    "eq_scalar": _CMP_SCALAR.format(name="eq_scalar", op="eq_scalar"),
    "ge_scalar": _CMP_SCALAR.format(name="ge_scalar", op="ge_scalar"),
    "le_scalar": _CMP_SCALAR.format(name="le_scalar", op="le_scalar"),
    "select": (
        "调度：v.select(dst, src0, src1, mask)。mask 是 ubuf 上的 u8，字节数 = f32 个数 * 4 / 8。"
        "VF：asc_loadalign 两个 f32；asc_loadalign_postupdate 载入掩码（步进 vf_len/8）；"
        "asc_select(dst, src0, src1, 该掩码)；asc_storealign 用 asc_create_mask_b32(PAT_ALL)。"
        "不用 asc_update_mask_b32 当选择条件。"
    ),
    "duplicate": (
        "调度：v.duplicate(dst, scalar)，无源向量。对应指令 asc_duplicate_scalar。"
        "VF：asc_update_mask_b32；asc_duplicate_scalar(dst, scalar, mask)；asc_storealign。不 load 源。"
    ),
    "duplicate_scalar": (
        "与 duplicate 同一条规则：调度名是 v.duplicate，发出的指令是 asc_duplicate_scalar。"
    ),
    "arange": (
        "调度：v.arange(dst, start)，无源向量。"
        "VF：asc_create_mask_b32(PAT_ALL)；每段 asc_arange(dst, start) 后 asc_storealign；start 增加本段 f32 个数。"
    ),
    "xor": (
        "VF 循环：asc_update_mask_b32 作尾块掩码；asc_load 两个 int32 源；"
        "asc_xor(dst, src0, src1, mask)；asc_store。调度：v.xor(dst, src0, src1)，缓冲为 i32。"
    ),
    "shiftleft": (
        "VF 循环：尾块掩码；asc_load 两个 int32（数据与移位量）；"
        "asc_shiftleft(dst, src, shift, mask)；asc_store。调度：v.shiftleft(dst, src, shift)，缓冲为 i32。"
    ),
    "shiftright": (
        "VF 循环：尾块掩码；asc_load 两个 int32；"
        "asc_shiftright(dst, src, shift, mask)；asc_store。调度：v.shiftright(dst, src, shift)，缓冲为 i32。"
    ),
    "shiftleft_scalar": (
        "VF 循环：尾块掩码；asc_load 一个 int32；"
        "asc_shiftleft_scalar(dst, src, int_shift, mask)；asc_store。"
        "调度：v.shiftleft_scalar(dst, src, shift)，shift 是整数，缓冲为 i32。"
    ),
    "shiftright_scalar": (
        "VF 循环：尾块掩码；asc_load 一个 int32；"
        "asc_shiftright_scalar(dst, src, int_shift, mask)；asc_store。"
        "调度：v.shiftright_scalar(dst, src, shift)，缓冲为 i32。"
    ),
    "half2float": (
        "调度名是 v.cast(dst_f32, src_f16)，两边元素个数相同。发出的不是 asc_cast。"
        "VF：vlds(src, ptr, 0, UNPK_B16)；asc_half2float(dst, src, mask)；asc_storealign。"
        "不用 asc_loadalign_unpack，也不带 ASC_POSITION_EVEN。"
    ),
    "repeat_reduce_sum": (
        "调度：v.repeat_reduce_sum(dst, src)。src 为 f32 且元素数是 64 的倍数；dst 必须是 8 个 f32。"
        "VF：累加器清 0；每段 asc_loadalign、asc_reduce_sum、asc_add 进累加器；asc_storealign 写出 8 个通道。主机再把通道相加。"
    ),
    "copy_gm2l1_nd2nz": (
        "调度：mte2.nd2nz(gm, l1, rows, cols, row_stride=cols)。仅 f16。"
        "先 asc_set_gm2l1_nz_para，再 asc_copy_gm2l1_nd2nz(l1, gm, row_stride*2, NORMAL_FIRST_VICTIM, rows, cols, 0, false)。"
        "row_stride 大于 cols 时表示 GM 行宽，用来搬 K 方向的一段。"
    ),
    "copy_gm2l1_dn2nz": (
        "调度：mte2.dn2nz(gm, l1, rows, cols, row_stride=cols)。参数和 nd2nz 相同，指令换成 asc_copy_gm2l1_dn2nz。"
    ),
    "copy_l12l0a": (
        "调度：mte1.l12l0a(l1, l0a, rows, cols)。仅 f16。"
        "asc_copy_l12l0a(l0a, l1, 0, 0, ceil(rows/16), ceil(cols/16), ceil(rows/16), ceil(rows/16))。"
    ),
    "copy_l12l0b": (
        "调度：mte1.l12l0b(l1, l0b, rows, cols)。rows 是 N、cols 是这一段 K。"
        "asc_copy_l12l0b(l0b, l1, 0, 0, ceil(rows/16), ceil(cols/16), ceil(rows/16), ceil(rows/16))。"
    ),
    "copy_l0c2gm": (
        "调度：fix.l0c2gm(l0c, gm, rows, cols)。l0c 与 gm 都是 f32，rows 是 M、cols 是 N。"
        "asc_set_l0c_copy_nz_para(1, 0, 0) 后 asc_copy_l0c2gm(gm, l0c, cols, rows, cols, align16(rows), "
        "NORMAL_FIRST_VICTIM, DISABLE, NoQuant, NONE, false, true, false, false)。nz2nd 打开，写回行优先。"
    ),
    "mmad": (
        "调度：m.mmad(l0c, l0a, l0b, m, k, n, init)。A/B 为 f16，L0C 为 f32。B 按 (n, k) 存放，结果是 A @ B.T。"
        "asc_mmad(l0c, l0a, l0b, m, k, n, DISABLE, true, false, init)。"
        "K 分块时第 0 轮 init 为真，其后为假，并且在累加前发 asc_sync_pipe(PIPE_M)。"
    ),
}


def _short(name: str) -> str:
    return name[4:] if name.startswith("asc_") else name


def _snake(name: str) -> str:
    name = re.sub(r"_(ISASI|deprecated|flexible_scalar)$", "", name)
    special = {
        "Adds": "add_scalar",
        "Maxs": "max_scalar",
        "Mins": "min_scalar",
        "Muls": "mul_scalar",
        "AddC": "addc",
        "AbsSub": "abs_sub",
        "LeakyRelu": "leakyrelu",
        "Select": "select",
        "Duplicate": "duplicate",
        "Arange": "arange",
        "Compare": "gt",
        "Compares": "gt_scalar",
        "Mmad": "mmad",
        "MmadMx": "mmad_mx",
        "Gather": "gather",
        "DataCopy_GMToL1_ND2NZ": "copy_gm2l1_nd2nz",
        "DataCopy_GMToL1_DN2NZ": "copy_gm2l1_dn2nz",
        "DataCopy_L0CToGM": "copy_l0c2gm",
        "Fixpipe_L0CToGM": "copy_l0c2gm",
        "LoadData": "copy_l12l0a",
        "LoadData_2D": "copy_l12l0a",
        "LoadDataWithTranspose": "copy_l12l0a_transpose",
    }
    if name in special:
        return special[name]
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name)
    text = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", text)
    return text.lower()


def _basic_pages() -> dict[str, str]:
    """基础 API 页文件名 -> 对应的 C API 短名。只保留目录里真实存在的 C API。"""
    root = Path(r"C:\Users\chenc\Projects\asc-devkit\docs\zh\api\SIMD-API\basic_api")
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    cnames = {_short(item["name"]) for item in catalog["entries"]}
    found: dict[str, str] = {}
    if not root.is_dir():
        return found
    for path in root.rglob("*.md"):
        stem = path.stem
        if not stem[:1].isupper() or stem.endswith("_res") or "overview" in stem.lower():
            continue
        c_api = _snake(stem)
        if c_api in cnames:
            found[stem] = c_api
    return found


def _sample_names() -> dict[str, list[str]]:
    found: dict[str, set[str]] = defaultdict(set)
    pat = re.compile(r"\basc_([A-Za-z0-9_]+)\s*\(")
    decl = re.compile(r"(?:__simd_callee__|__aicore__|inline)\s+")
    for root in SAMPLES:
        if not root.is_dir():
            continue
        for path in root.rglob("*.asc"):
            text = path.read_text(encoding="utf-8", errors="replace")
            for match in pat.finditer(text):
                found[match.group(1)].add(path.name)
    if MANUAL.is_dir():
        for path in MANUAL.rglob("*.md"):
            text = path.read_text(encoding="utf-8", errors="replace")
            start = text.find("调用示例")
            if start < 0:
                continue
            body = text[start:]
            nxt = body.find("\n## ")
            if nxt > 0:
                body = body[:nxt]
            for match in pat.finditer(body):
                line_start = body.rfind("\n", 0, match.start()) + 1
                line = body[line_start:match.end()]
                if decl.search(line):
                    continue
                found[match.group(1)].add(path.name)
    return {name: sorted(paths) for name, paths in found.items()}


def main() -> None:
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    names = sorted({_short(item["name"]) for item in catalog["entries"]})
    basics = _basic_pages()
    basic_of = {}
    for basic, c_api in basics.items():
        basic_of.setdefault(c_api, basic)
    samples = _sample_names()
    roles = []
    for name in names:
        evidence = samples.get(name, [])
        if name in LOWERED:
            role = "lowered"
        elif name in COMPILER:
            role = "compiler"
        elif evidence:
            role = "sample_unlowered"
        else:
            role = "no_sample"
        item = {"name": name, "role": role, "samples": evidence[:3], "basic_api": basic_of.get(name)}
        if role == "lowered":
            rule = PATTERNS[name]
            basic = basic_of.get(name)
            if basic:
                rule = f"基础 API {basic} 与 asc_{name} 是同一条指令。{rule}"
            item["pattern"] = rule
        roles.append(item)
    missing = sorted(name for name in names if name in LOWERED and name not in PATTERNS)
    if missing:
        raise SystemExit(f"lowered 但没有生成规则: {missing}")
    payload = {
        "catalog_count": len(names),
        "roles": roles,
        "counts": {role: sum(1 for item in roles if item["role"] == role) for role in ("lowered", "compiler", "sample_unlowered", "no_sample")},
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    pairs = [{"basic_api": basic, "c_api": c_api, "lowered": c_api in LOWERED} for basic, c_api in sorted(basics.items())]
    map_path = ROOT / "src" / "ascendc_ir" / "catalog" / "basic_to_c_api.json"
    map_path.write_text(
        json.dumps({"rule": "基础 API 大驼峰与 C API 的 asc_ 下划线名是同一条指令。带 s 的标量接口对应 *_scalar。搬运接口按通路别名对应。", "pairs": pairs}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(payload["counts"], "basic_pairs", len(pairs))


if __name__ == "__main__":
    main()
