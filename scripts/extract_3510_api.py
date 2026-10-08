# Copyright (c) 2026 Huawei Technologies Co., Ltd.
# This program is free software, you can redistribute it and/or modify it under the terms and conditions of
# CANN Open Software License Agreement Version 2.0 (the "License").
# Please refer to the License for details. You may not use this file except in compliance with the License.
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY, OR FITNESS FOR A PARTICULAR PURPOSE.
# See LICENSE in the root of the software repository for the full text of the License.

"""从 asc-devkit 的 3510 C API 头文件抽出向量计算与矩阵计算声明。

只扫公开声明，不扫 impl。寄存器 load/store 记为编译器内部，不进入 Agent 可写词汇。
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEVKIT = Path(r"C:\Users\chenc\Projects\asc-devkit")
OUT = ROOT / "src" / "ascendc_ir" / "catalog" / "api_3510.json"

_DECL = re.compile(
    r"(?:__aicore__|__simd_callee__)\s+inline\s+"
    r"(?P<ret>void|vector_[A-Za-z0-9_]+|[A-Za-z_][A-Za-z0-9_]*)\s+"
    r"(?P<name>asc_[A-Za-z0-9_]+)\s*\((?P<params>.*?)\)\s*;",
    re.S,
)

_VECTOR_DTYPE = {
    "vector_float": "f32",
    "vector_half": "f16",
    "vector_bfloat16_t": "bf16",
    "vector_int8_t": "i8",
    "vector_uint8_t": "u8",
    "vector_int16_t": "i16",
    "vector_uint16_t": "u16",
    "vector_int32_t": "i32",
    "vector_uint32_t": "u32",
}


def _strip_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    text = re.sub(r"//.*?$", "", text, flags=re.M)
    return text


def _base_type(param: str) -> str:
    body = param.replace("&", " ").strip()
    parts = body.split()
    if len(parts) >= 2 and parts[-1].replace("*", "").isidentifier():
        return " ".join(parts[:-1]).replace(" ", "")
    return body.replace(" ", "")


def _group(path: Path) -> str:
    rel = path.as_posix()
    if "cube_compute" in rel:
        return "matrix_compute"
    if "cube_datamove" in rel:
        return "matrix_move"
    if "/compute/" in rel or rel.endswith("reg_convert.h"):
        return "vector_compute"
    if any(token in rel for token in ("/load/", "/store/", "/gather/", "/scatter/", "reg_copy", "reg_sync")):
        return "vector_move"
    return "vector_other"


def _kind(group: str, name: str, ret: str, params: list[str]) -> tuple[str, str | None]:
    if group == "matrix_compute":
        return ("matrix_compute", None)
    if group == "matrix_move":
        return ("matrix_move", None)
    if group == "vector_move":
        return ("vector_move", None)
    types = [_base_type(p) for p in params]
    if (
        ret == "void"
        and types
        and types[0] in _VECTOR_DTYPE
        and "&" in params[0]
        and types[-1] == "vector_bool"
    ):
        body = types[1:-1]
        if any(t == "vector_bool" for t in body):
            return ("vector_other", _VECTOR_DTYPE[types[0]])
        vecs = [t for t in body if t.startswith("vector_")]
        scalars = [t for t in body if not t.startswith("vector_")]
        dtype = _VECTOR_DTYPE[types[0]]
        if vecs and all(t == types[0] for t in vecs):
            if len(vecs) == 2 and not scalars:
                return ("reg_binary", dtype)
            if len(vecs) == 1 and not scalars:
                return ("reg_unary", dtype)
            if len(vecs) == 1 and len(scalars) == 1:
                return ("reg_scalar", dtype)
    return ("vector_other", None)


def _files() -> list[Path]:
    include = DEVKIT / "include" / "c_api"
    found = []
    found.extend((include / "reg_compute").rglob("*.h"))
    found.append(include / "cube_compute" / "cube_compute.h")
    found.append(include / "cube_datamove" / "cube_datamove.h")
    return sorted(found)


def main() -> None:
    entries = []
    seen = set()
    for path in _files():
        text = _strip_comments(path.read_text(encoding="utf-8", errors="replace"))
        group = _group(path)
        rel = path.relative_to(DEVKIT).as_posix()
        for match in _DECL.finditer(text):
            params = [p.strip() for p in match.group("params").split(",") if p.strip()]
            kind, dtype = _kind(group, match.group("name"), match.group("ret"), params)
            key = (match.group("name"), kind, dtype, tuple(params))
            if key in seen:
                continue
            seen.add(key)
            entries.append(
                {
                    "name": match.group("name"),
                    "group": group,
                    "kind": kind,
                    "dtype": dtype,
                    "params": params,
                    "file": rel,
                }
            )
    entries.sort(key=lambda item: (item["group"], item["name"], item["kind"], item["dtype"] or "", item["file"]))
    payload = {
        "arch": 3510,
        "header_commit": "579cf014ea1f1354d4fbc547cc9cca11057b444b",
        "header_root": "asc-devkit/include/c_api",
        "entries": entries,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"entries={len(entries)} names={len({e['name'] for e in entries})} -> {OUT}")


if __name__ == "__main__":
    main()
