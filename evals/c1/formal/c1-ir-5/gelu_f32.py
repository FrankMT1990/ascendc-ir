from ascendc_ir import f32, gmptr, kernel, sync, ubuf
from ascendc_ir.pipes import mte2, mte3, v


@kernel(device="ascend950pr")
def gelu_f32(x: gmptr(f32), z: gmptr(f32)):
    N = 8192 * 8192
    TILE = 8192
    nt = N // TILE
    b_x = ubuf(f32, TILE, stages=2)
    b_t = ubuf(f32, TILE, stages=2)
    b_out = ubuf(f32, TILE, stages=2)
    for i in range(nt):
        mte2.copy(x[i * TILE], b_x[i % 2])
        sync(mte2, v, on=b_x[i % 2], stage=i)
        v.mul(b_t[i % 2], b_x[i % 2], b_x[i % 2])
        v.mul(b_t[i % 2], b_t[i % 2], b_x[i % 2])
        v.mul_scalar(b_t[i % 2], b_t[i % 2], 0.044715)
        v.add(b_t[i % 2], b_t[i % 2], b_x[i % 2])
        v.mul_scalar(b_t[i % 2], b_t[i % 2], -1.5957691216)
        v.exp(b_t[i % 2], b_t[i % 2])
        v.add_scalar(b_t[i % 2], b_t[i % 2], 1.0)
        v.div(b_out[i % 2], b_x[i % 2], b_t[i % 2])
        sync(v, mte3, on=b_out[i % 2], stage=i)
        mte3.copy(b_out[i % 2], z[i * TILE])
