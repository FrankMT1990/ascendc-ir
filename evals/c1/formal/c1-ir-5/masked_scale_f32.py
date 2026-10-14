from ascendc_ir import f32, gmptr, kernel, sync, ubuf, u8
from ascendc_ir.pipes import mte2, mte3, v


@kernel(device="ascend950pr")
def masked_scale_f32(x: gmptr(f32), mask: gmptr(u8), z: gmptr(f32)):
    N = 2048 * 2048
    TILE = 4096
    nt = N // TILE
    NB = TILE * 4 // 8
    b_x = ubuf(f32, TILE, stages=2)
    mk = ubuf(u8, NB, stages=2)
    b_zero = ubuf(f32, TILE, stages=2)
    b_out = ubuf(f32, TILE, stages=2)
    for i in range(nt):
        mte2.copy(x[i * TILE], b_x[i % 2])
        mte2.copy(mask[i * NB], mk[i % 2])
        sync(mte2, v, on=b_x[i % 2], stage=i)
        sync(mte2, v, on=mk[i % 2], stage=i)
        v.duplicate(b_zero[i % 2], 0.0)
        v.select(b_out[i % 2], b_x[i % 2], b_zero[i % 2], mk[i % 2])
        sync(v, mte3, on=b_out[i % 2], stage=i)
        mte3.copy(b_out[i % 2], z[i * TILE])
