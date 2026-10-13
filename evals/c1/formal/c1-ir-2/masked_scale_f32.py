from ascendc_ir import f32, gmptr, kernel, sync, ubuf, u8
from ascendc_ir.pipes import mte2, mte3, v


@kernel(device="ascend950pr")
def masked_scale_f32(x: gmptr(f32), mask: gmptr(u8), z: gmptr(f32)):
    TILE = 4096
    MB = TILE * 4 // 8
    TILES = 2048 * 2048 // TILE
    x_local = ubuf(f32, TILE, stages=2)
    mask_local = ubuf(u8, MB, stages=2)
    zeros = ubuf(f32, TILE, stages=2)
    y = ubuf(f32, TILE, stages=2)
    for i in range(TILES):
        s = i % 2
        mte2.copy(x[i * TILE], x_local[s])
        mte2.copy(mask[i * MB], mask_local[s])
        sync(mte2, v, on=(x_local[s], mask_local[s]), stage=i)
        v.duplicate(zeros[s], 0.0)
        v.select(y[s], x_local[s], zeros[s], mask_local[s])
        sync(v, mte3, on=(y[s],), stage=i)
        mte3.copy(y[s], z[i * TILE])
