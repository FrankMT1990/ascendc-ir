"""C1 harness：.asc 内核解析、launch 包装与直调 pack 组装构建。

把 Agent 产出的 .asc（IR 臂经 codegen，或对照臂直接提交）统一包装成
launch 函数 + torch 插件 + CMake pack，用 bisheng 构建 wheel 并安装。
"""

import re
import subprocess
from pathlib import Path

TASK_SIGNATURES = {
    "exp_f32": [("float*", "x"), ("float*", "z")],
    "sigmoid_f32": [("float*", "x"), ("float*", "z")],
    "gelu_f32": [("float*", "x"), ("float*", "z")],
    "mish_f32": [("float*", "x"), ("float*", "z")],
    "masked_scale_f32": [("float*", "x"), ("uint8_t*", "mask"), ("float*", "z")],
    "swi_glu_f32": [("float*", "x"), ("float*", "z")],
    "foreach_addcdiv_f32": [("float*", "x1"), ("float*", "x2"), ("float*", "x3"), ("float*", "z")],
}

_RE_KERNEL = re.compile(
    r"(__vector__\s+)?__global__\s+(__aicore__\s+)?(__vector__\s+)?void\s+(\w+)\s*\(([^)]*)\)", re.S)


_TYPE_ALIASES = {
    "unsigned char": "uint8_t",
    "unsigned int": "uint32_t",
    "unsigned short": "uint16_t",
    "unsigned long": "uint64_t",
    "char": "int8_t",
    "short": "int16_t",
    "int": "int32_t",
    "long": "int64_t",
}


def parse_kernel(asc_text: str):
    m = _RE_KERNEL.search(asc_text)
    if not m:
        return None
    name = m.group(4)
    params = []
    for p in m.group(5).split(","):
        p = p.strip()
        if not p or "*" not in p:
            continue
        ty, nm = p.rsplit("*", 1)
        ty = ty.strip()
        for prefix in ("__gm__", "__ubuf__", "__cbuf__", "const "):
            if ty.startswith(prefix):
                ty = ty[len(prefix):].strip()
        ty = _TYPE_ALIASES.get(ty, ty)
        params.append((ty + "*", nm.strip()))
    return name, params


def _ctype(ptype):
    return {"float*": "float", "uint8_t*": "uint8_t", "half*": "half", "int32_t*": "int32_t"}.get(ptype, ptype.rstrip("*"))


def gen_kernel_cpp(asc_text: str, task_id: str, pack_dir: Path) -> Path:
    name, params = parse_kernel(asc_text)
    if (name, params) is None:
        raise ValueError(f"{task_id}: cannot parse kernel signature")
    expected = TASK_SIGNATURES[task_id]
    if [(t, n) for t, n in params] != expected:
        raise ValueError(f"{task_id}: kernel signature {params} != task spec {expected}")
    cast = ", ".join(f"(__gm__ {_ctype(t)}*){n}" for t, n in params)
    launch_params = ", ".join(f"GM_ADDR {n}" for t, n in params)
    cpp = f"""{asc_text.rstrip()}

#ifndef GM_ADDR
#define GM_ADDR void*
#endif

extern "C" void launch_{task_id}({launch_params}, void* stream)
{{
    {name}<<<1, 0, stream>>>({cast});
}}
"""
    out = pack_dir / "kernels" / f"{task_id}_kernel.cpp"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(cpp, encoding="utf-8", newline="\n")
    return out


_PLUGIN_META = {
    "exp_f32": ('TORCH_CHECK(x.scalar_type() == torch::kFloat32, "x dtype"); TORCH_CHECK(x.numel() == 2048*2048, "numel"); return torch::empty_like(x);', "x"),
    "sigmoid_f32": ('TORCH_CHECK(x.scalar_type() == torch::kFloat32, "x dtype"); TORCH_CHECK(x.numel() == 2048*2048, "numel"); return torch::empty_like(x);', "x"),
    "gelu_f32": ('TORCH_CHECK(x.scalar_type() == torch::kFloat32, "x dtype"); TORCH_CHECK(x.numel() == 8192*8192, "numel"); return torch::empty_like(x);', "x"),
    "mish_f32": ('TORCH_CHECK(x.scalar_type() == torch::kFloat32, "x dtype"); TORCH_CHECK(x.numel() == 2048*2048, "numel"); return torch::empty_like(x);', "x"),
    "masked_scale_f32": ('TORCH_CHECK(x.scalar_type() == torch::kFloat32, "x dtype"); TORCH_CHECK(mask.scalar_type() == torch::kUInt8, "mask dtype"); TORCH_CHECK(x.numel() == 2048*2048, "numel"); TORCH_CHECK(mask.numel() == x.numel()*4/8, "mask numel"); return torch::empty_like(x);', "x, mask"),
    "swi_glu_f32": ('TORCH_CHECK(x.scalar_type() == torch::kFloat32, "x dtype"); TORCH_CHECK(x.numel() == 2048*4096, "numel"); auto s = x.sizes().vec(); s.back() /= 2; return torch::empty(s, x.options());', "x"),
    "foreach_addcdiv_f32": ('TORCH_CHECK(x1.scalar_type() == torch::kFloat32, "dtype"); TORCH_CHECK(x1.numel() == 2*1024*1024, "numel"); TORCH_CHECK(x2.numel() == x1.numel() && x3.numel() == x1.numel(), "numel"); return torch::empty_like(x1);', "x1, x2, x3"),
}


def gen_plugin(task_ids, pack_dir: Path, ns="c1run") -> Path:
    lines_decl, lines_def, impls = [], [], []
    for t in task_ids:
        params = TASK_SIGNATURES[t]
        inputs = params[:-1]                      # torch op 只暴露输入；z 由 meta 分配
        zname = params[-1][1]
        in_names = [n for _, n in inputs]
        launch_decl = ", ".join(f"GM_ADDR {n}" for _, n in params)
        lines_decl.append(f"void launch_{t}({launch_decl}, void* stream);")
        lines_def.append(f'    m.def("{t}(Tensor {" , Tensor ".join(in_names)}) -> Tensor");')
        meta_body = _PLUGIN_META[t][0]
        in_sig = ", ".join(f"torch::Tensor& {n}" for n in in_names)
        call_args = ", ".join(f"(GM_ADDR){n}.data_ptr()" for n in in_names) + f", (GM_ADDR){zname}.data_ptr()"
        impls.append(f"""
torch::Tensor {t}_meta({in_sig})
{{
    {meta_body}
}}
TORCH_LIBRARY_IMPL({ns}, Meta, m) {{ m.impl("{t}", {t}_meta); }}
torch::Tensor {t}_npu({in_sig})
{{
    const c10::OptionalDeviceGuard guard({in_names[0]}.device());
    auto {zname} = {t}_meta({", ".join(in_names)});
    auto stream = c10_npu::getCurrentNPUStream().stream(false);
    auto acl_call = [=]() -> int {{
        launch_{t}({call_args}, stream);
        return 0;
    }};
    at_npu::native::OpCommand::RunOpApi("{t}", acl_call);
    return {zname};
}}
TORCH_LIBRARY_IMPL({ns}, PrivateUse1, m) {{ m.impl("{t}", {t}_npu); }}""")
    cpp = f"""#include <torch/all.h>
#include <torch/library.h>

#include "torch_npu/csrc/core/npu/NPUStream.h"
#include "torch_npu/csrc/framework/OpCommand.h"

#ifndef GM_ADDR
#define GM_ADDR void*
#endif

extern "C" {{
{chr(10).join(lines_decl)}
}}

namespace {ns} {{

TORCH_LIBRARY_FRAGMENT({ns}, m)
{{
{chr(10).join(lines_def)}
}}
{''.join(impls)}

}}  // namespace {ns}

#include <torch/extension.h>
PYBIND11_MODULE(TORCH_EXTENSION_NAME, m) {{}}
"""
    out = pack_dir / "plugin.cpp"
    out.write_text(cpp, encoding="utf-8", newline="\n")
    return out


CMAKE_TEMPLATE = """cmake_minimum_required(VERSION 3.16)
project({pkg} LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

set(NPU_ARCH "ascend950")
set(BISHENG_NPU_ARCH "dav-3510")

if(NOT DEFINED ENV{{ASCEND_HOME_PATH}} OR "$ENV{{ASCEND_HOME_PATH}}" STREQUAL "")
    message(FATAL_ERROR "ASCEND_HOME_PATH is not set")
endif()
set(ASCEND_HOME_PATH "$ENV{{ASCEND_HOME_PATH}}")

find_program(BISHENG bisheng
    HINTS "${{ASCEND_HOME_PATH}}/bin" "${{ASCEND_HOME_PATH}}/compiler/ccec_compiler/bin" "${{ASCEND_HOME_PATH}}/toolkit/bin"
    REQUIRED)

set(_INC_CANDIDATES
    "${{ASCEND_HOME_PATH}}/include"
    "${{ASCEND_HOME_PATH}}/x86_64-linux/include"
    "${{ASCEND_HOME_PATH}}/x86_64-linux/asc/include"
    "${{ASCEND_HOME_PATH}}/asc/include")
set(ASCEND_INCLUDE_DIRS "")
foreach(_inc ${{_INC_CANDIDATES}})
    if(EXISTS "${{_inc}}")
        list(APPEND ASCEND_INCLUDE_DIRS "${{_inc}}")
    endif()
endforeach()

set(_LIB_CANDIDATES "${{ASCEND_HOME_PATH}}/lib64" "${{ASCEND_HOME_PATH}}/x86_64-linux/lib64")
set(ASCEND_LIB_DIRS "")
foreach(_lib ${{_LIB_CANDIDATES}})
    if(EXISTS "${{_lib}}")
        list(APPEND ASCEND_LIB_DIRS "${{_lib}}")
    endif()
endforeach()

execute_process(COMMAND python3 -c "import torch; print(torch.utils.cmake_prefix_path)"
    OUTPUT_VARIABLE TORCH_PREFIX OUTPUT_STRIP_TRAILING_WHITESPACE)
list(INSERT CMAKE_PREFIX_PATH 0 "${{TORCH_PREFIX}}")
find_package(Torch REQUIRED)
execute_process(COMMAND python3 -c "import torch_npu, os; print(os.path.dirname(torch_npu.__file__))"
    OUTPUT_VARIABLE TORCH_NPU_DIR OUTPUT_STRIP_TRAILING_WHITESPACE)
set(TORCH_NPU_INCLUDE_DIRS "${{TORCH_NPU_DIR}}/include")
find_package(Python3 REQUIRED COMPONENTS Interpreter Development)

set(KERNEL_SRCS {kernel_srcs})

set(KERNEL_INCLUDE_FLAGS "")
foreach(_dir ${{ASCEND_INCLUDE_DIRS}})
    list(APPEND KERNEL_INCLUDE_FLAGS "-I${{_dir}}")
endforeach()

set(KERNEL_OBJECTS "")
foreach(_src ${{KERNEL_SRCS}})
    get_filename_component(_name ${{_src}} NAME_WE)
    set(_obj ${{CMAKE_BINARY_DIR}}/bisheng/${{_name}}.o)
    add_custom_command(
        OUTPUT ${{_obj}}
        COMMAND ${{CMAKE_COMMAND}} -E make_directory ${{CMAKE_BINARY_DIR}}/bisheng
        COMMAND ${{BISHENG}} --npu-arch=${{BISHENG_NPU_ARCH}} -xasc -std=c++17 -fPIC -c ${{CMAKE_SOURCE_DIR}}/${{_src}} -o ${{_obj}} ${{KERNEL_INCLUDE_FLAGS}}
        DEPENDS ${{CMAKE_SOURCE_DIR}}/${{_src}}
        COMMENT "bisheng ${{_name}}"
        VERBATIM)
    list(APPEND KERNEL_OBJECTS ${{_obj}})
endforeach()

add_library(_C SHARED ${{CMAKE_SOURCE_DIR}}/plugin.cpp ${{KERNEL_OBJECTS}})
target_include_directories(_C PRIVATE
    ${{Python3_INCLUDE_DIRS}} ${{TORCH_INCLUDE_DIRS}} ${{TORCH_NPU_INCLUDE_DIRS}} ${{ASCEND_INCLUDE_DIRS}})
target_compile_definitions(_C PRIVATE TORCH_EXTENSION_NAME=_C)
target_compile_options(_C PRIVATE -O3 ${{TORCH_CXX_FLAGS}})
target_link_directories(_C PRIVATE ${{ASCEND_LIB_DIRS}} ${{TORCH_NPU_DIR}}/lib)
target_link_libraries(_C PRIVATE ${{TORCH_LIBRARIES}} torch_npu ascendcl ascendc_runtime dl)
set_target_properties(_C PROPERTIES
    PREFIX "" OUTPUT_NAME "_C.abi3" SUFFIX ".so"
    LIBRARY_OUTPUT_DIRECTORY ${{CMAKE_SOURCE_DIR}}/{pkg})
"""

SETUP_TEMPLATE = """import subprocess
from pathlib import Path
from setuptools import Extension, setup
from setuptools.command.build_ext import build_ext

PACKAGE_NAME = "{pkg}"
ROOT = Path(__file__).parent.resolve()


class CMakeBuild(build_ext):
    def run(self):
        for ext in self.extensions:
            self.build_extension(ext)

    def build_extension(self, ext):
        build_temp = Path(self.build_temp).resolve()
        build_temp.mkdir(parents=True, exist_ok=True)
        subprocess.check_call(["cmake", str(ROOT)], cwd=build_temp)
        subprocess.check_call(["cmake", "--build", str(build_temp)], cwd=build_temp)
        pkg = Path(self.build_lib) / PACKAGE_NAME
        pkg.mkdir(parents=True, exist_ok=True)
        src_so = ROOT / PACKAGE_NAME / "_C.abi3.so"
        if src_so.exists():
            import shutil
            shutil.copy2(src_so, pkg / "_C.abi3.so")


setup(
    name=PACKAGE_NAME,
    version="1.0.0",
    packages=[PACKAGE_NAME],
    package_data={{PACKAGE_NAME: ["_C.abi3.so"]}},
    ext_modules=[Extension(PACKAGE_NAME + "._C", sources=[])],
    cmdclass={{"build_ext": CMakeBuild}},
    python_requires=">=3.8",
    options={{"bdist_wheel": {{"py_limited_api": "cp38"}}}},
)
"""

INIT_TEMPLATE = """import torch

try:
    from . import _C
except ImportError as e:
    raise ImportError("Cannot import _C.") from e
"""


def assemble_pack(asc_by_task: dict, pack_dir: Path, pkg="c1run"):
    """asc_by_task: {task_id: asc_text}。组装 pack 目录并返回构建好的 wheel 路径。"""
    (pack_dir / pkg).mkdir(parents=True, exist_ok=True)
    (pack_dir / pkg / "__init__.py").write_text(INIT_TEMPLATE, encoding="utf-8", newline="\n")
    kernel_files = []
    for task_id, asc_text in asc_by_task.items():
        kernel_files.append(gen_kernel_cpp(asc_text, task_id, pack_dir))
    gen_plugin(sorted(asc_by_task.keys()), pack_dir)
    rel = [str(k.relative_to(pack_dir)).replace("\\", "/") for k in kernel_files]
    (pack_dir / "CMakeLists.txt").write_text(
        CMAKE_TEMPLATE.format(pkg=pkg, kernel_srcs=" ".join(rel)), encoding="utf-8", newline="\n")
    (pack_dir / "setup.py").write_text(SETUP_TEMPLATE.format(pkg=pkg), encoding="utf-8", newline="\n")
    return pack_dir


def build_pack(pack_dir: Path, log_path: Path):
    """构建 wheel 并安装（pip）。返回 (ok, wheel_path|None)。构建输出完整落日志。"""
    r = subprocess.run(
        ["bash", "-c",
         f"cd {pack_dir} && rm -rf build dist {pack_dir.name}/_C.abi3.so && mkdir -p dist && "
         f"python3 setup.py bdist_wheel --dist-dir dist 2>&1 && "
         f"pip install --force-reinstall --no-deps dist/*.whl 2>&1"],
        capture_output=True, text=True)
    log_path.write_text(r.stdout + "\n=== stderr ===\n" + r.stderr, encoding="utf-8")
    if r.returncode != 0:
        return False, None
    wheels = sorted((pack_dir / "dist").glob("*.whl"))
    if not wheels:
        return False, None
    return True, wheels[-1]
