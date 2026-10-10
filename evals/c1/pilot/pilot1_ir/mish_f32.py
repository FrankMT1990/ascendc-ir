"""y = x * tanh(ln(1 + exp(x)))。

softplus(x) = ln(1 + exp(-abs(x))) + max(x, 0)，再套 tanh。
"""

from ascendc_ir import f32, gmptr, kernel, sync, ubuf
from ascendc_ir.pipes import mte2, mte3, v

_TILE = 8192
_COUNT = 2048 * 2048


@kernel(device="ascend950pr")
def mish_f32(x: gmptr(f32), z: gmptr(f32)):
    x_local = ubuf(f32, _TILE)
    a = ubuf(f32, _TILE)
    b = ubuf(f32, _TILE)
    c = ubuf(f32, _TILE)
    z_local = ubuf(f32, _TILE)
    for i in range(_COUNT // _TILE):
        mte2.copy(x[i * _TILE], x_local)
        sync(mte2, v, on=x_local, stage=i)
        v.abs(a, x_local)
        v.neg(a, a)
        v.exp(a, a)
        v.add_scalar(a, a, 1.0)
        v.ln(a, a)
        v.max_scalar(b, x_local, 0.0)
        v.add(a, a, b)
        v.mul_scalar(b, a, 2.0)
        v.abs(c, b)
        v.neg(c, c)
        v.exp(a, c)
        v.add_scalar(c, a, 1.0)
        v.min_scalar(a, b, 0.0)
        v.exp(a, a)
        v.div(a, a, c)
        v.mul_scalar(a, a, 2.0)
        v.add_scalar(a, a, -1.0)
        v.mul(z_local, x_local, a)
        sync(v, mte3, on=z_local, stage=i)
        mte3.copy(z_local, z[i * _TILE])
