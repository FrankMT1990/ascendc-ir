"""y = exp(1.5 * x)，自然指数，shift = 0。"""

from ascendc_ir import f32, gmptr, kernel, sync, ubuf
from ascendc_ir.pipes import mte2, mte3, v

_TILE = 8192
_COUNT = 2048 * 2048


@kernel(device="ascend950pr")
def exp_f32(x: gmptr(f32), z: gmptr(f32)):
    x_local = ubuf(f32, _TILE)
    scaled = ubuf(f32, _TILE)
    z_local = ubuf(f32, _TILE)
    for i in range(_COUNT // _TILE):
        mte2.copy(x[i * _TILE], x_local)
        sync(mte2, v, on=x_local, stage=i)
        v.mul_scalar(scaled, x_local, 1.5)
        v.exp(z_local, scaled)
        sync(v, mte3, on=z_local, stage=i)
        mte3.copy(z_local, z[i * _TILE])
