from ascendc_ir import f32, gmptr, kernel, sync, ubuf
from ascendc_ir.pipes import mte2, mte3, v


@kernel(device="ascend950pr")
def foreach_addcdiv_f32(x1: gmptr(f32), x2: gmptr(f32), x3: gmptr(f32), z: gmptr(f32)):
    N = 2 * 1024 * 1024
    TILE = 4096
    nt = N // TILE
    b_1 = ubuf(f32, TILE, stages=2)
    b_2 = ubuf(f32, TILE, stages=2)
    b_3 = ubuf(f32, TILE, stages=2)
    b_out = ubuf(f32, TILE, stages=2)
    for i in range(nt):
        mte2.copy(x1[i * TILE], b_1[i % 2])
        mte2.copy(x2[i * TILE], b_2[i % 2])
        mte2.copy(x3[i * TILE], b_3[i % 2])
        sync(mte2, v, on=b_1[i % 2], stage=i)
        sync(mte2, v, on=b_2[i % 2], stage=i)
        sync(mte2, v, on=b_3[i % 2], stage=i)
        v.div(b_out[i % 2], b_2[i % 2], b_3[i % 2])
        v.mul_scalar(b_out[i % 2], b_out[i % 2], 1.0)
        v.add(b_out[i % 2], b_1[i % 2], b_out[i % 2])
        sync(v, mte3, on=b_out[i % 2], stage=i)
        mte3.copy(b_out[i % 2], z[i * TILE])
