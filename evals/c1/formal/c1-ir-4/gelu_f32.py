from ascendc_ir import f32, gmptr, kernel, sync, ubuf
from ascendc_ir.pipes import mte2, mte3, v


@kernel(device="ascend950pr")
def gelu_f32(x: gmptr(f32), z: gmptr(f32)):
    TILE = 4096
    TILES = 8192 * 8192 // TILE
    x_local = ubuf(f32, TILE, stages=2)
    t1 = ubuf(f32, TILE, stages=2)
    t2 = ubuf(f32, TILE, stages=2)
    z_local = ubuf(f32, TILE, stages=2)
    for i in range(TILES):
        mte2.copy(x[i * TILE], x_local[i % 2])
        sync(mte2, v, on=(x_local[i % 2],), stage=i)
        v.mul(t1[i % 2], x_local[i % 2], x_local[i % 2])
        v.mul(t2[i % 2], t1[i % 2], x_local[i % 2])
        v.mul_scalar(t1[i % 2], t2[i % 2], 0.044715)
        v.add(t2[i % 2], x_local[i % 2], t1[i % 2])
        v.mul_scalar(t1[i % 2], t2[i % 2], -1.5957691216)
        v.exp(t2[i % 2], t1[i % 2])
        v.add_scalar(t1[i % 2], t2[i % 2], 1.0)
        v.duplicate(t2[i % 2], 1.0)
        v.div(t1[i % 2], t2[i % 2], t1[i % 2])
        v.mul(z_local[i % 2], x_local[i % 2], t1[i % 2])
        sync(v, mte3, on=(z_local[i % 2],), stage=i)
        mte3.copy(z_local[i % 2], z[i * TILE])
