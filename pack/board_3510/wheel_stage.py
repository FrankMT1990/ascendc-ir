"""把 cmake 写在源码树里的扩展复制进 setuptools 的 build lib。"""

from __future__ import annotations

import shutil
from pathlib import Path


def stage_built_extension(build_lib: Path, package_dir: Path, so_name: str = "_C.abi3.so") -> Path:
    """bdist_wheel 在编译前收集包文件。编译结果要补进 build lib，wheel 才会带上 .so。"""
    so = package_dir / so_name
    if not so.is_file():
        raise FileNotFoundError(so)
    dest = Path(build_lib) / package_dir.name
    dest.mkdir(parents=True, exist_ok=True)
    target = dest / so_name
    shutil.copy2(so, target)
    return target
