"""y = 1 / (1 + exp(-x))。用 exp(min(x, 0)) / (1 + exp(-abs(x)))，避免 exp 溢出。"""

from ascendc_ir import f32, gmptr, kernel, sync, ubuf
from ascendc_ir.pipes import mte2, mte3, v

_TILE = 8192
_COUNT = 2048 * 2048


@kernel(device="ascend950pr")
def sigmoid_f32(x: gmptr(f32), z: gmptr(f32)):
    x_local = ubuf(f32, _TILE)
    denom = ubuf(f32, _TILE)
    numer = ubuf(f32, _TILE)
    z_local = ubuf(f32, _TILE)
    for i in range(_COUNT // _TILE):
        mte2.copy(x[i * _TILE], x_local)
        sync(mte2, v, on=x_local, stage=i)
        v.abs(denom, x_local)
        v.neg(denom, denom)
        v.exp(numer, denom)
        v.add_scalar(denom, numer, 1.0)
        v.min_scalar(numer, x_local, 0.0)
        v.exp(numer, numer)
        v.div(z_local, numer, denom)
        sync(v, mte3, on=z_local, stage=i)
        mte3.copy(z_local, z[i * _TILE])
