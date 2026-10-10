"""y = x0 * sigmoid(x0) * x1。

x 为行优先 [2048, 4096]，末维对半：第 i 行 x0 = x[i, :2048]，x1 = x[i, 2048:]。
z 为 [2048, 2048]。
"""

from ascendc_ir import f32, gmptr, kernel, sync, ubuf
from ascendc_ir.pipes import mte2, mte3, v

_ROWS = 2048
_HALF = 2048
_ROW = 4096


@kernel(device="ascend950pr")
def swi_glu_f32(x: gmptr(f32), z: gmptr(f32)):
    x0_local = ubuf(f32, _HALF)
    x1_local = ubuf(f32, _HALF)
    a = ubuf(f32, _HALF)
    b = ubuf(f32, _HALF)
    z_local = ubuf(f32, _HALF)
    for i in range(_ROWS):
        mte2.copy(x[i * _ROW], x0_local)
        mte2.copy(x[i * _ROW + _HALF], x1_local)
        sync(mte2, v, on=(x0_local, x1_local), stage=i)
        v.abs(a, x0_local)
        v.neg(a, a)
        v.exp(b, a)
        v.add_scalar(a, b, 1.0)
        v.min_scalar(b, x0_local, 0.0)
        v.exp(b, b)
        v.div(b, b, a)
        v.mul(a, x0_local, b)
        v.mul(z_local, a, x1_local)
        sync(v, mte3, on=z_local, stage=i)
        mte3.copy(z_local, z[i * _HALF])
