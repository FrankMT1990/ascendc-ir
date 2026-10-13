from ascendc_ir import f32, gmptr, kernel, sync, ubuf, u8
from ascendc_ir.pipes import mte2, mte3, v

TILE = 8192
MASK_TILE = 4096
TILES = 512


@kernel(device="ascend950pr")
def masked_scale_f32(x: gmptr(f32), mask: gmptr(u8), z: gmptr(f32)):
    x_local = ubuf(f32, TILE, stages=2)
    mask_local = ubuf(u8, MASK_TILE, stages=2)
    zero_local = ubuf(f32, TILE, stages=1)
    z_local = ubuf(f32, TILE, stages=2)
    for i in range(TILES):
        v.duplicate(zero_local, 0.0)
        mte2.copy(x[i * TILE], x_local[i % 2])
        mte2.copy(mask[i * MASK_TILE], mask_local[i % 2])
        sync(mte2, v, on=(x_local[i % 2], mask_local[i % 2]), stage=i)
        v.select(z_local[i % 2], x_local[i % 2], zero_local, mask_local[i % 2])
        sync(v, mte3, on=(z_local[i % 2],), stage=i)
        mte3.copy(z_local[i % 2], z[i * TILE])
