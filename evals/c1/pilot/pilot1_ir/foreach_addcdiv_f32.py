"""y = x1 + (x2 / x3) * 1。两个 [1024, 1024] 张量在连续父缓冲里逐元素独立计算。"""

from ascendc_ir import f32, gmptr, kernel, sync, ubuf
from ascendc_ir.pipes import mte2, mte3, v

_TILE = 8192
_COUNT = 2 * 1024 * 1024


@kernel(device="ascend950pr")
def foreach_addcdiv_f32(x1: gmptr(f32), x2: gmptr(f32), x3: gmptr(f32), z: gmptr(f32)):
    x1_local = ubuf(f32, _TILE)
    x2_local = ubuf(f32, _TILE)
    x3_local = ubuf(f32, _TILE)
    quot = ubuf(f32, _TILE)
    z_local = ubuf(f32, _TILE)
    for i in range(_COUNT // _TILE):
        mte2.copy(x1[i * _TILE], x1_local)
        mte2.copy(x2[i * _TILE], x2_local)
        mte2.copy(x3[i * _TILE], x3_local)
        sync(mte2, v, on=(x1_local, x2_local, x3_local), stage=i)
        v.div(quot, x2_local, x3_local)
        v.mul_scalar(quot, quot, 1.0)
        v.add(z_local, x1_local, quot)
        sync(v, mte3, on=z_local, stage=i)
        mte3.copy(z_local, z[i * _TILE])
