from ascendc_ir import f32, gmptr, kernel, sync, ubuf
from ascendc_ir.pipes import mte2, mte3, v

C_SRC = """
__ubuf__ float* x_local;
__gm__ float* x;
asc_add(reg, x_local, x_local, mask);
#include "c_api/asc_simd.h"
"""


@kernel(device="ascend950pr")
def bad_cstring(x: gmptr(f32), z: gmptr(f32)):
    x_local = ubuf(f32, 2048, stages=1)
    mte2.copy(x[0], x_local)
    sync(mte2, v, on=(x_local,))
    v.abs(x_local, x_local)
    sync(v, mte3, on=x_local)
    mte3.copy(x_local, z[0])
