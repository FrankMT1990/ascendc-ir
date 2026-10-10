"""环境冒烟：确认 toolchain 可用。python3 check.py smoke.py 应输出 OK。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "toolchain"))

from ascendc_ir import f32, gmptr, kernel, sync, ubuf  # noqa: E402
from ascendc_ir.pipes import mte2, mte3, v  # noqa: E402
from ascendc_ir.verify import verify  # noqa: E402
from ascendc_ir.codegen import generate  # noqa: E402


@kernel(device="ascend950pr")
def smoke(x: gmptr(f32), z: gmptr(f32)):
    x_local = ubuf(f32, 2048, stages=1)
    z_local = ubuf(f32, 2048, stages=1)
    mte2.copy(x[0], x_local)
    sync(mte2, v, on=(x_local,))
    v.abs(z_local, x_local)
    sync(v, mte3, on=z_local)
    mte3.copy(z_local, z[0])


if __name__ == "__main__":
    d = verify(smoke.trace())
    asc = generate(smoke.trace())
    print(f"OK smoke: diags={len(d)}, asc {len(asc.splitlines())} lines")
