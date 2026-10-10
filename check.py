"""实验 Agent 本地自检：verify 诊断清零 + codegen 产出 .asc。

用法：python3 check.py workspace/exp_f32.py
Python < 3.11 时需要 pip install tomli。
"""

import importlib.util
import pathlib
import sys

try:
    import tomllib  # noqa: F401
except ModuleNotFoundError:
    try:
        import tomli as _tomli

        sys.modules["tomllib"] = _tomli
    except ModuleNotFoundError:
        print("ENV: 需要 Python>=3.11 或 `pip install tomli`")
        sys.exit(2)

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / "toolchain"))

from ascendc_ir.codegen import generate  # noqa: E402
from ascendc_ir.verify import verify  # noqa: E402


def main():
    p = pathlib.Path(sys.argv[1])
    task_id = p.stem
    spec = importlib.util.spec_from_file_location("k_" + task_id, str(p))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    fn = getattr(m, task_id)

    diags = verify(fn.trace())
    if diags:
        print(f"VERIFY DIAGS ({task_id}):")
        for d in diags:
            print(" ", d)
        sys.exit(1)

    asc = generate(fn.trace())
    out = pathlib.Path("generated") / f"{task_id}.asc"
    out.parent.mkdir(exist_ok=True)
    out.write_text(asc, encoding="utf-8")
    print(f"OK {task_id}: verify clean, codegen {len(asc.splitlines())} lines -> {out}")


if __name__ == "__main__":
    main()
