"""y = x * m * scale，scale = 1。m 为 select 的位打包掩码，等价于按掩码在 x 与 0 之间选择。"""

from ascendc_ir import f32, gmptr, kernel, sync, u8, ubuf
from ascendc_ir.pipes import mte2, mte3, v

_TILE = 8192
_COUNT = 2048 * 2048
_MASK = _TILE * 4 // 8


@kernel(device="ascend950pr")
def masked_scale_f32(x: gmptr(f32), mask: gmptr(u8), z: gmptr(f32)):
    x_local = ubuf(f32, _TILE)
    mask_local = ubuf(u8, _MASK)
    scaled = ubuf(f32, _TILE)
    zeros = ubuf(f32, _TILE)
    z_local = ubuf(f32, _TILE)
    for i in range(_COUNT // _TILE):
        mte2.copy(x[i * _TILE], x_local)
        mte2.copy(mask[i * _MASK], mask_local)
        sync(mte2, v, on=(x_local, mask_local), stage=i)
        v.mul_scalar(scaled, x_local, 1.0)
        v.duplicate(zeros, 0.0)
        v.select(z_local, scaled, zeros, mask_local)
        sync(v, mte3, on=z_local, stage=i)
        mte3.copy(z_local, z[i * _TILE])
