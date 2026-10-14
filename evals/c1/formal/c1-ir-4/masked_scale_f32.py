from ascendc_ir import f32, gmptr, kernel, sync, ubuf, u8
from ascendc_ir.pipes import mte2, mte3, v


@kernel(device="ascend950pr")
def masked_scale_f32(x: gmptr(f32), mask: gmptr(u8), z: gmptr(f32)):
    TILE = 4096
    TILES = 2048 * 2048 // TILE
    MB = TILE * 4 // 8
    x_local = ubuf(f32, TILE, stages=2)
    mask_local = ubuf(u8, MB, stages=2)
    zero_local = ubuf(f32, TILE, stages=2)
    z_local = ubuf(f32, TILE, stages=2)
    for i in range(TILES):
        mte2.copy(x[i * TILE], x_local[i % 2])
        mte2.copy(mask[i * MB], mask_local[i % 2])
        sync(mte2, v, on=(x_local[i % 2], mask_local[i % 2]), stage=i)
        v.duplicate(zero_local[i % 2], 0.0)
        v.select(z_local[i % 2], x_local[i % 2], zero_local[i % 2], mask_local[i % 2])
        sync(v, mte3, on=(z_local[i % 2],), stage=i)
        mte3.copy(z_local[i % 2], z[i * TILE])
