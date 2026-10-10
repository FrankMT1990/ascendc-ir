"""y = 0.5 * x * (1 + tanh(0.7978845608 * (x + 0.044715 * x^3)))。

tanh(u) = 2 * sigmoid(2u) - 1，sigmoid 用不溢出的 exp 组合。
"""

from ascendc_ir import f32, gmptr, kernel, sync, ubuf
from ascendc_ir.pipes import mte2, mte3, v

_TILE = 8192
_COUNT = 8192 * 8192
_C = 0.044715
_K = 0.7978845608


@kernel(device="ascend950pr")
def gelu_f32(x: gmptr(f32), z: gmptr(f32)):
    x_local = ubuf(f32, _TILE)
    a = ubuf(f32, _TILE)
    b = ubuf(f32, _TILE)
    c = ubuf(f32, _TILE)
    z_local = ubuf(f32, _TILE)
    for i in range(_COUNT // _TILE):
        mte2.copy(x[i * _TILE], x_local)
        sync(mte2, v, on=x_local, stage=i)
        v.mul(a, x_local, x_local)
        v.mul(b, a, x_local)
        v.mul_scalar(a, b, _C)
        v.add(b, x_local, a)
        v.mul_scalar(a, b, _K)
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
        v.add_scalar(a, a, 1.0)
        v.mul(b, x_local, a)
        v.mul_scalar(z_local, b, 0.5)
        sync(v, mte3, on=z_local, stage=i)
        mte3.copy(z_local, z[i * _TILE])
