from ascendc_ir import f32, gmptr, kernel, sync, ubuf
from ascendc_ir.pipes import mte2, mte3, v


@kernel(device="ascend950pr")
def swi_glu_f32(x: gmptr(f32), z: gmptr(f32)):
    R = 2048
    W = 2048
    TILE = W
    b_x0 = ubuf(f32, TILE, stages=2)
    b_x1 = ubuf(f32, TILE, stages=2)
    b_t = ubuf(f32, TILE, stages=2)
    b_one = ubuf(f32, TILE, stages=2)
    b_out = ubuf(f32, TILE, stages=2)
    for i in range(R):
        mte2.copy(x[i * (2 * W)], b_x0[i % 2])
        mte2.copy(x[i * (2 * W) + W], b_x1[i % 2])
        sync(mte2, v, on=b_x0[i % 2], stage=i)
        sync(mte2, v, on=b_x1[i % 2], stage=i)
        v.neg(b_t[i % 2], b_x0[i % 2])
        v.exp(b_t[i % 2], b_t[i % 2])
        v.add_scalar(b_t[i % 2], b_t[i % 2], 1.0)
        v.duplicate(b_one[i % 2], 1.0)
        v.div(b_t[i % 2], b_one[i % 2], b_t[i % 2])
        v.mul(b_t[i % 2], b_x0[i % 2], b_t[i % 2])
        v.mul(b_out[i % 2], b_t[i % 2], b_x1[i % 2])
        sync(v, mte3, on=b_out[i % 2], stage=i)
        mte3.copy(b_out[i % 2], z[i * W])
