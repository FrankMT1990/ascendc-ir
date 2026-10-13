from ascendc_ir import f32, gmptr, kernel, sync, ubuf, u8
from ascendc_ir.pipes import mte2, mte3, v


@kernel(device="ascend950pr")
def masked_scale_f32(x: gmptr(f32), mask: gmptr(u8), z: gmptr(f32)):
    N = 2048 * 2048
    TILE = 8192
    MB = TILE * 4 // 8
    src = ubuf(f32, TILE, stages=2)
    msk = ubuf(u8, MB, stages=2)
    zero = ubuf(f32, TILE, stages=2)
    dst = ubuf(f32, TILE, stages=2)
    for i in range(N // TILE):
        mte2.copy(x[i * TILE], src[i % 2])
        mte2.copy(mask[i * MB], msk[i % 2])
        sync(mte2, v, on=(src[i % 2], msk[i % 2]), stage=i)
        v.duplicate(zero[i % 2], 0.0)
        v.select(dst[i % 2], src[i % 2], zero[i % 2], msk[i % 2])
        sync(v, mte3, on=(dst[i % 2],), stage=i)
        mte3.copy(dst[i % 2], z[i * TILE])
