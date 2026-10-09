import os
import subprocess
import sys
from pathlib import Path

from setuptools import Extension, setup
from setuptools.command.build_ext import build_ext

PACKAGE_NAME = "c1hw"
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
        # 3acb588 的教训：build_py 先于 build_ext，把 .so 补拷进 build lib
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
    package_data={PACKAGE_NAME: ["_C.abi3.so"]},
    ext_modules=[Extension("c1hw._C", sources=[])],
    cmdclass={"build_ext": CMakeBuild},
    python_requires=">=3.8",
    options={"bdist_wheel": {"py_limited_api": "cp38"}},
)
