from ascendc_ir import f32, gmptr, kernel, sync, ubuf
from ascendc_ir.pipes import mte2, mte3, v


@kernel(device="ascend950pr")
def gelu_f32(x: gmptr(f32), z: gmptr(f32)):
    TILE = 8192
    TILES = 8192 * 8192 // TILE
    x_local = ubuf(f32, TILE, stages=2)
    t = ubuf(f32, TILE, stages=2)
    w = ubuf(f32, TILE, stages=2)
    for i in range(TILES):
        s = i % 2
        mte2.copy(x[i * TILE], x_local[s])
        sync(mte2, v, on=(x_local[s],), stage=i)
        v.mul(t[s], x_local[s], x_local[s])
        v.mul(t[s], t[s], x_local[s])
        v.mul_scalar(t[s], t[s], 0.044715)
        v.add(t[s], x_local[s], t[s])
        v.mul_scalar(t[s], t[s], 0.7978845608)
        v.mul_scalar(t[s], t[s], 2.0)
        v.exp(t[s], t[s])
        v.add_scalar(w[s], t[s], 1.0)
        v.log(t[s], w[s])
        v.mul_scalar(t[s], t[s], -1.0)
        v.exp(t[s], t[s])
        v.mul_scalar(t[s], t[s], -1.0)
        v.add_scalar(t[s], t[s], 1.0)
        v.mul(t[s], x_local[s], t[s])
        sync(v, mte3, on=(t[s],), stage=i)
        mte3.copy(t[s], z[i * TILE])
