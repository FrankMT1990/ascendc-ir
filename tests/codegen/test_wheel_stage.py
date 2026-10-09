# Copyright (c) 2026 Huawei Technologies Co., Ltd.
# This program is free software, you can redistribute it and/or modify it under the terms and conditions of
# CANN Open Software License Agreement Version 2.0 (the "License").
# Please refer to the License for details. You may not use this file except in compliance with the License.
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY, OR FITNESS FOR A PARTICULAR PURPOSE.
# See LICENSE in the root of the software repository for the full text of the License.

"""安装包必须带上编译出的扩展，不能只留下源码树里的 .so。"""

import importlib.util
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]


def _stage():
    path = _ROOT / "pack" / "board_3510" / "wheel_stage.py"
    spec = importlib.util.spec_from_file_location("wheel_stage", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.stage_built_extension


def test_stage_copies_so_into_build_lib(tmp_path):
    package = tmp_path / "ir_board"
    package.mkdir()
    so = package / "_C.abi3.so"
    so.write_bytes(b"fake-extension")
    build_lib = tmp_path / "build" / "lib"
    staged = _stage()(build_lib, package)
    assert staged == build_lib / "ir_board" / "_C.abi3.so"
    assert staged.read_bytes() == b"fake-extension"


def test_stage_refuses_a_missing_so(tmp_path):
    package = tmp_path / "ir_board"
    package.mkdir()
    try:
        _stage()(tmp_path / "lib", package)
    except FileNotFoundError as exc:
        assert "_C.abi3.so" in str(exc)
    else:
        raise AssertionError("missing extension should fail")
