# Copyright (c) 2026 Huawei Technologies Co., Ltd.
# This program is free software, you can redistribute it and/or modify it under the terms and conditions of
# CANN Open Software License Agreement Version 2.0 (the "License").
# Please refer to the License for details. You may not use this file except in compliance with the License.
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY, OR FITNESS FOR A PARTICULAR PURPOSE.
# See LICENSE in the root of the software repository for the full text of the License.

"""生成 pack/board_3510 的批量上板核。每个核只覆盖一条已经能生成的降级。"""

import importlib.util
import json
import shutil
from pathlib import Path

from ascendc_ir import f16, f32, gmptr, i32, kernel, sync, u8, ubuf
from ascendc_ir.codegen.emit import generate
from ascendc_ir.pipes import mte2, mte3, v
from ascendc_ir.verify import verify

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "pack" / "board_3510"
HARNESS = ROOT / "pack" / "vector_batch"
N = 64


def _load_example(rel: str, qual: str):
    spec = importlib.util.spec_from_file_location(qual, ROOT / rel)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _trace(src: str, name: str):
    ns = {
        "kernel": kernel,
        "gmptr": gmptr,
        "ubuf": ubuf,
        "sync": sync,
        "mte2": mte2,
        "mte3": mte3,
        "v": v,
        "f32": f32,
        "f16": f16,
        "i32": i32,
        "u8": u8,
    }
    exec(src, ns)
    fn = ns[name]
    traced = fn.trace()
    blocked = [d for d in verify(traced) if d.severity == "block"]
    if blocked:
        detail = "; ".join(f"{d.id}: {d.message}" for d in blocked)
        raise SystemExit(f"{name} 检查未过: {detail}")
    return generate(traced)


def _call(op: str, args: str) -> str:
    if op in {"and", "or", "not"}:
        return f'getattr(v, "{op}")({args})'
    return f"v.{op}({args})"


def _binary(op: str, dt: str) -> str:
    vcall = _call(op, "z_local, x_local, y_local")
    return f"""
@kernel(device="ascend950pr")
def op_{op}(x: gmptr({dt}), y: gmptr({dt}), z: gmptr({dt})):
    x_local = ubuf({dt}, {N})
    y_local = ubuf({dt}, {N})
    z_local = ubuf({dt}, {N})
    mte2.copy(x[0], x_local)
    mte2.copy(y[0], y_local)
    sync(mte2, v, on=(x_local, y_local))
    {vcall}
    sync(v, mte3, on=z_local)
    mte3.copy(z_local, z[0])
"""


def _unary(op: str, dt: str, call: str) -> str:
    return f"""
@kernel(device="ascend950pr")
def op_{op}(x: gmptr({dt}), z: gmptr({dt})):
    x_local = ubuf({dt}, {N})
    z_local = ubuf({dt}, {N})
    mte2.copy(x[0], x_local)
    sync(mte2, v, on=x_local)
    {call}
    sync(v, mte3, on=z_local)
    mte3.copy(z_local, z[0])
"""


def _select() -> str:
    return f"""
@kernel(device="ascend950pr")
def op_select(x: gmptr(f32), y: gmptr(f32), mask: gmptr(u8), z: gmptr(f32)):
    x_local = ubuf(f32, {N})
    y_local = ubuf(f32, {N})
    mask_local = ubuf(u8, {N // 2})
    z_local = ubuf(f32, {N})
    mte2.copy(x[0], x_local)
    mte2.copy(y[0], y_local)
    mte2.copy(mask[0], mask_local)
    sync(mte2, v, on=(x_local, y_local, mask_local))
    v.select(z_local, x_local, y_local, mask_local)
    sync(v, mte3, on=z_local)
    mte3.copy(z_local, z[0])
"""


def _cast() -> str:
    return f"""
@kernel(device="ascend950pr")
def op_cast(x: gmptr(f16), z: gmptr(f32)):
    x_local = ubuf(f16, {N})
    z_local = ubuf(f32, {N})
    mte2.copy(x[0], x_local)
    sync(mte2, v, on=x_local)
    v.cast(z_local, x_local)
    sync(v, mte3, on=z_local)
    mte3.copy(z_local, z[0])
"""


def _reduce() -> str:
    return f"""
@kernel(device="ascend950pr")
def op_repeat_reduce_sum(x: gmptr(f32), z: gmptr(f32)):
    x_local = ubuf(f32, {N})
    z_local = ubuf(f32, 8)
    mte2.copy(x[0], x_local)
    sync(mte2, v, on=x_local)
    v.repeat_reduce_sum(z_local, x_local)
    sync(v, mte3, on=z_local)
    mte3.copy(z_local, z[0])
"""


def _fill(op: str, call: str) -> str:
    return f"""
@kernel(device="ascend950pr")
def op_{op}(z: gmptr(f32)):
    z_local = ubuf(f32, {N})
    {call}
    sync(v, mte3, on=z_local)
    mte3.copy(z_local, z[0])
"""


SPECS = []

for op in ("add", "sub", "mul", "div", "max", "min", "and", "or", "prelu"):
    SPECS.append({"name": op, "kind": "bin", "token": f"asc_{op}(", "src": _binary(op, "f32"), "sig": "f32,f32->f32"})

for op in ("abs", "ceil", "exp", "floor", "ln", "log", "neg", "not", "relu", "rint", "round", "sqrt", "trunc"):
    SPECS.append({
        "name": op,
        "kind": "unary",
        "token": f"asc_{op}(",
        "src": _unary(op, "f32", _call(op, "z_local, x_local")),
        "sig": "f32->f32",
    })

for op, literal in (
    ("add_scalar", "1.5"),
    ("max_scalar", "1.0"),
    ("min_scalar", "1.0"),
    ("mul_scalar", "2.0"),
):
    SPECS.append({
        "name": op,
        "kind": "unary",
        "token": f"asc_{op}(",
        "src": _unary(op, "f32", _call(op, f"z_local, x_local, {literal}")),
        "sig": "f32->f32",
        "literal": literal,
    })

SPECS.append({
    "name": "leakyrelu",
    "kind": "unary",
    "token": "asc_leakyrelu(",
    "src": _unary("leakyrelu", "f32", "v.leakyrelu(z_local, x_local, 0.1)"),
    "sig": "f32->f32",
    "literal": "0.1",
})

SPECS.append({"name": "select", "kind": "select", "token": "asc_select(", "src": _select(), "sig": "f32,f32,u8->f32"})

for op in ("gt", "lt", "ne", "eq", "ge", "le"):
    SPECS.append({
        "name": f"select_{op}",
        "kind": "bin",
        "token": f"asc_{op}(",
        "src": _binary(f"select_{op}", "f32").replace(
            f"v.select_{op}(z_local, x_local, y_local)",
            f"v.select_{op}(z_local, x_local, y_local)",
        ),
        "sig": "f32,f32->f32",
    })

for op in ("gt", "lt", "ne", "eq", "ge", "le"):
    src = _binary(f"select_{op}_scalar", "f32").replace(
        f"v.select_{op}_scalar(z_local, x_local, y_local)",
        f"v.select_{op}_scalar(z_local, x_local, y_local, 1.0)",
    )
    SPECS.append({
        "name": f"select_{op}_scalar",
        "kind": "bin",
        "token": f"asc_{op}_scalar(",
        "src": src,
        "sig": "f32,f32->f32",
        "literal": "1.0",
    })

SPECS.append({
    "name": "duplicate",
    "kind": "fill",
    "token": "asc_duplicate_scalar(",
    "src": _fill("duplicate", "v.duplicate(z_local, 3.0)"),
    "sig": "->f32",
    "literal": "3.0",
})
SPECS.append({
    "name": "arange",
    "kind": "fill",
    "token": "asc_arange(",
    "src": _fill("arange", "v.arange(z_local, 0.0)"),
    "sig": "->f32",
    "literal": "0.0",
})

for op in ("xor", "shiftleft", "shiftright"):
    SPECS.append({"name": op, "kind": "i32_bin", "token": f"asc_{op}(", "src": _binary(op, "i32"), "sig": "i32,i32->i32"})

for op in ("shiftleft_scalar", "shiftright_scalar"):
    SPECS.append({
        "name": op,
        "kind": "i32_unary",
        "token": f"asc_{op}(",
        "src": _unary(op, "i32", _call(op, "z_local, x_local, 3")),
        "sig": "i32->i32",
        "literal": "3",
    })

SPECS.append({"name": "cast", "kind": "cast", "token": "asc_half2float(", "src": _cast(), "sig": "f16->f32"})
SPECS.append({
    "name": "repeat_reduce_sum",
    "kind": "reduce",
    "token": "asc_reduce_sum(",
    "src": _reduce(),
    "sig": "f32->f32x8",
})


def _plugin(spec: dict) -> str:
    name = f"op_{spec['name']}"
    sig = spec["sig"]
    if sig == "f32,f32->f32":
        schema = f"{name}(Tensor x, Tensor y) -> Tensor"
        formals = "const torch::Tensor& x, const torch::Tensor& y"
        checks = """
    TORCH_CHECK(x.scalar_type() == torch::kFloat32, "x dtype");
    TORCH_CHECK(y.scalar_type() == torch::kFloat32, "y dtype");
    TORCH_CHECK(x.numel() == 64 && y.numel() == 64, "numel");
    return torch::empty({64}, x.options());"""
        ptrs = "(GM_ADDR)x.data_ptr(), (GM_ADDR)y.data_ptr(), (GM_ADDR)z.data_ptr()"
        guard = "x"
    elif sig == "f32->f32":
        schema = f"{name}(Tensor x) -> Tensor"
        formals = "const torch::Tensor& x"
        checks = """
    TORCH_CHECK(x.scalar_type() == torch::kFloat32, "x dtype");
    TORCH_CHECK(x.numel() == 64, "numel");
    return torch::empty({64}, x.options());"""
        ptrs = "(GM_ADDR)x.data_ptr(), (GM_ADDR)z.data_ptr()"
        guard = "x"
    elif sig == "f32,f32,u8->f32":
        schema = f"{name}(Tensor x, Tensor y, Tensor mask) -> Tensor"
        formals = "const torch::Tensor& x, const torch::Tensor& y, const torch::Tensor& mask"
        checks = """
    TORCH_CHECK(x.scalar_type() == torch::kFloat32 && y.scalar_type() == torch::kFloat32, "dtype");
    TORCH_CHECK(mask.scalar_type() == torch::kUInt8, "mask dtype");
    TORCH_CHECK(x.numel() == 64 && y.numel() == 64 && mask.numel() == 32, "numel");
    return torch::empty({64}, x.options());"""
        ptrs = "(GM_ADDR)x.data_ptr(), (GM_ADDR)y.data_ptr(), (GM_ADDR)mask.data_ptr(), (GM_ADDR)z.data_ptr()"
        guard = "x"
    elif sig == "->f32":
        schema = f"{name}(Tensor unused) -> Tensor"
        formals = "const torch::Tensor& unused"
        checks = """
    return torch::empty({64}, torch::TensorOptions().dtype(torch::kFloat32).device(unused.device()));"""
        ptrs = "(GM_ADDR)z.data_ptr()"
        guard = "unused"
    elif sig == "i32,i32->i32":
        schema = f"{name}(Tensor x, Tensor y) -> Tensor"
        formals = "const torch::Tensor& x, const torch::Tensor& y"
        checks = """
    TORCH_CHECK(x.scalar_type() == torch::kInt32 && y.scalar_type() == torch::kInt32, "dtype");
    TORCH_CHECK(x.numel() == 64 && y.numel() == 64, "numel");
    return torch::empty({64}, x.options());"""
        ptrs = "(GM_ADDR)x.data_ptr(), (GM_ADDR)y.data_ptr(), (GM_ADDR)z.data_ptr()"
        guard = "x"
    elif sig == "i32->i32":
        schema = f"{name}(Tensor x) -> Tensor"
        formals = "const torch::Tensor& x"
        checks = """
    TORCH_CHECK(x.scalar_type() == torch::kInt32, "dtype");
    TORCH_CHECK(x.numel() == 64, "numel");
    return torch::empty({64}, x.options());"""
        ptrs = "(GM_ADDR)x.data_ptr(), (GM_ADDR)z.data_ptr()"
        guard = "x"
    elif sig == "f16->f32":
        schema = f"{name}(Tensor x) -> Tensor"
        formals = "const torch::Tensor& x"
        checks = """
    TORCH_CHECK(x.scalar_type() == torch::kFloat16, "dtype");
    TORCH_CHECK(x.numel() == 64, "numel");
    return torch::empty({64}, x.options().dtype(torch::kFloat32));"""
        ptrs = "(GM_ADDR)x.data_ptr(), (GM_ADDR)z.data_ptr()"
        guard = "x"
    elif sig == "f32->f32x8":
        schema = f"{name}(Tensor x) -> Tensor"
        formals = "const torch::Tensor& x"
        checks = """
    TORCH_CHECK(x.scalar_type() == torch::kFloat32, "dtype");
    TORCH_CHECK(x.numel() == 64, "numel");
    return torch::empty({8}, x.options());"""
        ptrs = "(GM_ADDR)x.data_ptr(), (GM_ADDR)z.data_ptr()"
        guard = "x"
    elif sig == "f16,f16->f32":
        schema = f"{name}(Tensor a, Tensor b) -> Tensor"
        formals = "const torch::Tensor& a, const torch::Tensor& b"
        checks = """
    TORCH_CHECK(a.scalar_type() == torch::kFloat16 && b.scalar_type() == torch::kFloat16, "dtype");
    TORCH_CHECK(a.numel() == 1024 && b.numel() == 1024, "numel");
    return torch::empty({32, 32}, a.options().dtype(torch::kFloat32));"""
        ptrs = "(GM_ADDR)a.data_ptr(), (GM_ADDR)b.data_ptr(), (GM_ADDR)z.data_ptr()"
        guard = "a"
    else:
        raise SystemExit(sig)
    launch = f"launch_{name}({ptrs}, stream)"
    return f"""#include <torch/all.h>
#include <torch/library.h>

#include "torch_npu/csrc/core/npu/NPUStream.h"
#include "torch_npu/csrc/framework/OpCommand.h"
#include "../op_kernel/{name}_launch.h"

namespace ir_board {{

TORCH_LIBRARY_FRAGMENT(ir_board, m)
{{
    m.def("{schema}");
}}

torch::Tensor {name}_meta({formals})
{{
{checks}
}}

TORCH_LIBRARY_IMPL(ir_board, Meta, m)
{{
    m.impl("{name}", {name}_meta);
}}

torch::Tensor {name}_npu({formals})
{{
    const c10::OptionalDeviceGuard guard({guard}.device());
    auto z = {name}_meta({", ".join(p.split("&")[-1].strip().rstrip(")") for p in formals.split(","))});
    auto stream = c10_npu::getCurrentNPUStream().stream(false);
    auto acl_call = [=]() -> int {{
        {launch};
        return 0;
    }};
    at_npu::native::OpCommand::RunOpApi("{name}", acl_call);
    return z;
}}

TORCH_LIBRARY_IMPL(ir_board, PrivateUse1, m)
{{
    m.impl("{name}", {name}_npu);
}}

}}  // namespace ir_board
"""


def _launch_header(name: str, params: str) -> str:
    return f"""#ifndef {name.upper()}_LAUNCH_H
#define {name.upper()}_LAUNCH_H

#ifndef GM_ADDR
#define GM_ADDR void*
#endif

extern "C" {{
void launch_{name}({params});
}}

#endif
"""


def _launch_params(sig: str) -> str:
    if sig in {"f32,f32->f32", "i32,i32->i32"}:
        return "GM_ADDR x, GM_ADDR y, GM_ADDR z, void* stream"
    if sig in {"f32->f32", "i32->i32", "f16->f32", "f32->f32x8"}:
        return "GM_ADDR x, GM_ADDR z, void* stream"
    if sig == "f32,f32,u8->f32":
        return "GM_ADDR x, GM_ADDR y, GM_ADDR mask, GM_ADDR z, void* stream"
    if sig == "->f32":
        return "GM_ADDR z, void* stream"
    if sig == "f16,f16->f32":
        return "GM_ADDR a, GM_ADDR b, GM_ADDR c, void* stream"
    raise SystemExit(sig)


def _launch_body(spec: dict, c_func: str) -> str:
    name = f"op_{spec['name']}"
    sig = spec["sig"]
    if sig == "f32,f32->f32":
        call = f"{c_func}<<<1, 0, stream>>>((__gm__ float*)x, (__gm__ float*)y, (__gm__ float*)z);"
        args = "GM_ADDR x, GM_ADDR y, GM_ADDR z, void* stream"
    elif sig == "f32->f32":
        call = f"{c_func}<<<1, 0, stream>>>((__gm__ float*)x, (__gm__ float*)z);"
        args = "GM_ADDR x, GM_ADDR z, void* stream"
    elif sig == "->f32":
        call = f"{c_func}<<<1, 0, stream>>>((__gm__ float*)z);"
        args = "GM_ADDR z, void* stream"
    elif sig == "f32,f32,u8->f32":
        call = f"{c_func}<<<1, 0, stream>>>((__gm__ float*)x, (__gm__ float*)y, (__gm__ uint8_t*)mask, (__gm__ float*)z);"
        args = "GM_ADDR x, GM_ADDR y, GM_ADDR mask, GM_ADDR z, void* stream"
    elif sig == "i32,i32->i32":
        call = f"{c_func}<<<1, 0, stream>>>((__gm__ int32_t*)x, (__gm__ int32_t*)y, (__gm__ int32_t*)z);"
        args = "GM_ADDR x, GM_ADDR y, GM_ADDR z, void* stream"
    elif sig == "i32->i32":
        call = f"{c_func}<<<1, 0, stream>>>((__gm__ int32_t*)x, (__gm__ int32_t*)z);"
        args = "GM_ADDR x, GM_ADDR z, void* stream"
    elif sig == "f16->f32":
        call = f"{c_func}<<<1, 0, stream>>>((__gm__ half*)x, (__gm__ float*)z);"
        args = "GM_ADDR x, GM_ADDR z, void* stream"
    elif sig == "f32->f32x8":
        call = f"{c_func}<<<1, 0, stream>>>((__gm__ float*)x, (__gm__ float*)z);"
        args = "GM_ADDR x, GM_ADDR z, void* stream"
    elif sig == "f16,f16->f32":
        call = f"{c_func}<<<1, 0, stream>>>((__gm__ half*)a, (__gm__ half*)b, (__gm__ float*)c);"
        args = "GM_ADDR a, GM_ADDR b, GM_ADDR c, void* stream"
    else:
        raise SystemExit(sig)
    return f"""#include "{name}_launch.h"

extern "C" void launch_{name}({args})
{{
    {call}
}}
"""


def _write_op(spec: dict, text: str, c_func: str) -> None:
    name = f"op_{spec['name']}"
    if spec["token"] not in text:
        raise SystemExit(f"{name} 生成结果里没有 {spec['token']}")
    op_dir = PACK / "csrc" / "ops" / name
    kernel_dir = op_dir / "op_kernel"
    plugin_dir = op_dir / "op_plugin"
    kernel_dir.mkdir(parents=True, exist_ok=True)
    plugin_dir.mkdir(parents=True, exist_ok=True)
    (kernel_dir / f"{name}_kernel.cpp").write_text(text + "\n" + _launch_body(spec, c_func), encoding="utf-8", newline="\n")
    (kernel_dir / f"{name}_launch.h").write_text(_launch_header(name, _launch_params(spec["sig"])), encoding="utf-8", newline="\n")
    (plugin_dir / f"{name}_plugin.cpp").write_text(_plugin(spec), encoding="utf-8", newline="\n")
    (op_dir / "CMakeLists.txt").write_text(
        "\n".join([
            f'if(EXISTS "${{CMAKE_CURRENT_SOURCE_DIR}}/SKIP")',
            f'    message(STATUS "Skip {name}")',
            "    return()",
            "endif()",
            f"set({name.upper()}_KERNEL_SRCS ${{CMAKE_CURRENT_SOURCE_DIR}}/op_kernel/{name}_kernel.cpp)",
            f"set({name.upper()}_PLUGIN_SRCS ${{CMAKE_CURRENT_SOURCE_DIR}}/op_plugin/{name}_plugin.cpp)",
            "register_direct_launch_op(",
            f'    "${{{name.upper()}_KERNEL_SRCS}}" op_kernel',
            f'    "${{{name.upper()}_PLUGIN_SRCS}}" op_kernel',
            ")",
            "",
        ]),
        encoding="utf-8",
        newline="\n",
    )


def _copy_harness() -> None:
    cmake_dst = PACK / "cmake"
    if cmake_dst.exists():
        shutil.rmtree(cmake_dst)
    shutil.copytree(HARNESS / "cmake", cmake_dst)
    setup = (HARNESS / "setup.py").read_text(encoding="utf-8").replace("cann_bench", "ir_board")
    (PACK / "setup.py").write_text(setup, encoding="utf-8", newline="\n")
    build = (HARNESS / "build.sh").read_text(encoding="utf-8").replace("cann_bench", "ir_board")
    build = build.replace('DIST_DIR="${SCRIPT_DIR}/dist"\nrm -rf "${DIST_DIR}"', 'rm -rf "${SCRIPT_DIR}/build" "${SCRIPT_DIR}/dist" "${SCRIPT_DIR}/ir_board/_C.abi3.so"\nDIST_DIR="${SCRIPT_DIR}/dist"\nrm -rf "${DIST_DIR}"')
    (PACK / "build.sh").write_text(build, encoding="utf-8", newline="\n")
    wheel = (HARNESS / "scripts" / "build_wheel.sh").read_text(encoding="utf-8")
    (PACK / "scripts" / "build_wheel.sh").write_text(wheel, encoding="utf-8", newline="\n")
    cmake = (HARNESS / "CMakeLists.txt").read_text(encoding="utf-8")
    cmake = cmake.replace("project(cann_bench LANGUAGES CXX)", "project(ir_board LANGUAGES CXX)")
    cmake = cmake.replace("add_f32_16384 requires", "ir_board requires")
    cmake = cmake.replace("LIBRARY_OUTPUT_DIRECTORY ${CMAKE_SOURCE_DIR}/cann_bench", "LIBRARY_OUTPUT_DIRECTORY ${CMAKE_SOURCE_DIR}/ir_board")
    (PACK / "CMakeLists.txt").write_text(cmake, encoding="utf-8", newline="\n")
    (PACK / "csrc" / "extension.cpp").write_text(
        """#ifndef TORCH_EXTENSION_NAME
#define TORCH_EXTENSION_NAME _C
#endif

#include <torch/extension.h>

PYBIND11_MODULE(TORCH_EXTENSION_NAME, m) {}
""",
        encoding="utf-8",
        newline="\n",
    )
    (PACK / "csrc" / "ops" / "CMakeLists.txt").write_text(
        """file(GLOB SUB_DIRS LIST_DIRECTORIES true ${CMAKE_CURRENT_SOURCE_DIR}/*)
foreach(SUB_DIR ${SUB_DIRS})
    if(IS_DIRECTORY ${SUB_DIR})
        add_subdirectory(${SUB_DIR})
    endif()
endforeach()
""",
        encoding="utf-8",
        newline="\n",
    )


def _write_init(names: list[str]) -> None:
    lines = [
        "import torch",
        "",
        "try:",
        "    from . import _C",
        "except ImportError as e:",
        '    raise ImportError("Cannot import _C. Install the ir_board package first.") from e',
        "",
    ]
    for name in names:
        lines.append(f"def {name}(*args):")
        lines.append(f"    return torch.ops.ir_board.{name}(*args)")
        lines.append("")
    (PACK / "ir_board" / "__init__.py").write_text("\n".join(lines), encoding="utf-8", newline="\n")


def _write_readme(names: list[str]) -> None:
    listed = "、".join(f"`{name}`" for name in names)
    text = f"""# 3510 一次上板：批量核对现有 IR

单核。设备是 Ascend 950，CANN 9.1.0，架构 `dav-3510`。不要改核里的计算。不要用开发套件的头文件覆盖这套 CANN。

本包覆盖当前已经能生成 C 的降级：f32 逐元素、比较后选择、`select`、`duplicate`、`arange`、f16 转 f32、64 个数求和、int32 的异或和移位，以及 K 分两段的 f16 矩阵乘。`dn2nz` 没有单独的核，这次不测。加、leakyrelu、cast、求和以前用别的核测过，这里用 IR 重新生成的小核再对一次数。

```bash
bash build.sh --soc=ascend950 --install
python3 scripts/check_ir.py
```

某个核编译失败时：把编译器原文写进该核目录的 `SKIP` 文件（例如 `csrc/ops/op_exp/SKIP`），再执行上面的两条命令。`build.sh` 会丢掉上一次的构建目录。缺符号就记下符号名，继续剩下的核。

数值脚本会打印每一条的 `bit` 或 `max_abs`。退出码 0 表示打印出来的核都对上了。被 SKIP 的核不在这次数值结果里。

核：{listed}。

结果写进本目录的 `RESULTS.md`，推到分支 `board-3510`。
"""
    (PACK / "README.md").write_text(text, encoding="utf-8", newline="\n")


def main() -> None:
    ops = PACK / "csrc" / "ops"
    if ops.exists():
        shutil.rmtree(ops)
    ops.mkdir(parents=True)
    (PACK / "ir_board").mkdir(exist_ok=True)
    (PACK / "scripts").mkdir(exist_ok=True)
    _copy_harness()
    manifest = []
    for spec in SPECS:
        name = f"op_{spec['name']}"
        text = _trace(spec["src"], name)
        _write_op(spec, text, name)
        manifest.append({
            "name": name,
            "op": spec["name"],
            "kind": spec["kind"],
            "token": spec["token"],
            "literal": spec.get("literal"),
        })
    mmad = _load_example("examples/matmul/mmad.py", "mmad_example").mmad_custom
    mmad_text = generate(mmad.trace())
    (PACK / "mmad_custom.asc").write_text(mmad_text, encoding="utf-8", newline="\n")
    mmad_spec = {"name": "mmad", "kind": "mmad", "token": "asc_mmad(", "sig": "f16,f16->f32"}
    _write_op(mmad_spec, mmad_text, "mmad_custom")
    manifest.append({"name": "op_mmad", "op": "mmad", "kind": "mmad", "token": "asc_mmad(", "literal": None})
    mul = _load_example("examples/vector_mul/mul.py", "mul_example").mul_custom
    (PACK / "mul_custom.asc").write_text(generate(mul.trace()), encoding="utf-8", newline="\n")
    (PACK / "ops.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    names = [item["name"] for item in manifest]
    _write_init(names)
    _write_readme(names)
    print(len(names), "kernels")


if __name__ == "__main__":
    main()
