from ascendc_ir import f32, gmptr, kernel, sync, ubuf
from ascendc_ir.pipes import mte2, mte3, v


@kernel(device="ascend950pr")
def mish_f32(x: gmptr(f32), z: gmptr(f32)):
    N = 2048 * 2048
    TILE = 8192
    src = ubuf(f32, TILE, stages=2)
    t1 = ubuf(f32, TILE, stages=2)
    one = ubuf(f32, TILE, stages=2)
    for i in range(N // TILE):
        mte2.copy(x[i * TILE], src[i % 2])
        sync(mte2, v, on=(src[i % 2],), stage=i)
        v.duplicate(one[i % 2], 1.0)
        v.exp(t1[i % 2], src[i % 2])
        v.add_scalar(t1[i % 2], t1[i % 2], 1.0)
        v.ln(t1[i % 2], t1[i % 2])
        v.mul_scalar(t1[i % 2], t1[i % 2], -2.0)
        v.exp(t1[i % 2], t1[i % 2])
        v.add_scalar(t1[i % 2], t1[i % 2], 1.0)
        v.div(t1[i % 2], one[i % 2], t1[i % 2])
        v.mul_scalar(t1[i % 2], t1[i % 2], 2.0)
        v.sub(t1[i % 2], t1[i % 2], one[i % 2])
        v.mul(t1[i % 2], t1[i % 2], src[i % 2])
        sync(v, mte3, on=(t1[i % 2],), stage=i)
        mte3.copy(t1[i % 2], z[i * TILE])
