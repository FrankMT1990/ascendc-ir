from ascendc_ir import f32, gmptr, kernel, sync, ubuf
from ascendc_ir.pipes import mte2, mte3, v


@kernel(device="ascend950pr")
def sigmoid_f32(x: gmptr(f32), z: gmptr(f32)):
    N = 2048 * 2048
    TILE = 8192
    src = ubuf(f32, TILE, stages=2)
    dst = ubuf(f32, TILE, stages=2)
    one = ubuf(f32, TILE, stages=2)
    for i in range(N // TILE):
        mte2.copy(x[i * TILE], src[i % 2])
        sync(mte2, v, on=(src[i % 2],), stage=i)
        v.duplicate(one[i % 2], 1.0)
        v.neg(dst[i % 2], src[i % 2])
        v.exp(dst[i % 2], dst[i % 2])
        v.add_scalar(dst[i % 2], dst[i % 2], 1.0)
        v.div(dst[i % 2], one[i % 2], dst[i % 2])
        sync(v, mte3, on=(dst[i % 2],), stage=i)
        mte3.copy(dst[i % 2], z[i * TILE])
