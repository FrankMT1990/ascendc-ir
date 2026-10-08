import os
import subprocess
import sys
from pathlib import Path

from setuptools import Extension, setup
from setuptools.command.build_ext import build_ext

PACKAGE_NAME = "ir_board"
VERSION = "1.0.0"
ROOT = Path(__file__).parent.resolve()


class CMakeBuild(build_ext):
    def run(self):
        for ext in self.extensions:
            self.build_extension(ext)

    def build_extension(self, ext):
        build_temp = Path(self.build_temp).resolve()
        build_temp.mkdir(parents=True, exist_ok=True)
        npu_arch = os.environ.get("NPU_ARCH", "ascend950")
        cfg = "Debug" if self.debug else "Release"
        cmake_args = [
            f"-DCMAKE_BUILD_TYPE={cfg}",
            f"-DNPU_ARCH={npu_arch}",
            f"-DPYTHON_EXECUTABLE={sys.executable}",
            f"-DCMAKE_LIBRARY_OUTPUT_DIRECTORY={ROOT / 'ir_board'}",
        ]
        subprocess.check_call(["cmake", str(ROOT), *cmake_args], cwd=build_temp)
        subprocess.check_call(["cmake", "--build", str(build_temp), "--config", cfg], cwd=build_temp)


setup(
    name=PACKAGE_NAME,
    version=VERSION,
    packages=[PACKAGE_NAME],
    package_data={PACKAGE_NAME: ["_C.abi3.so"]},
    ext_modules=[Extension("ir_board._C", sources=[])],
    cmdclass={"build_ext": CMakeBuild},
    python_requires=">=3.8",
    options={"bdist_wheel": {"py_limited_api": "cp38"}},
)
