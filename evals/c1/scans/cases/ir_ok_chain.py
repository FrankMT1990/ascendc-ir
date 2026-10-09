from ascendc_ir import f32, gmptr, kernel, sync, ubuf
from ascendc_ir.pipes import mte2, mte3, v


@kernel(device="ascend950pr")
def sigmoid_custom(x: gmptr(f32), z: gmptr(f32)):
    TILE, TILES = 2048, 8
    x_local = ubuf(f32, TILE, stages=2)
    neg_local = ubuf(f32, TILE, stages=1)
    den_local = ubuf(f32, TILE, stages=1)
    one_local = ubuf(f32, TILE, stages=1)
    z_local = ubuf(f32, TILE, stages=1)
    for i in range(TILES):
        mte2.copy(x[i * TILE], x_local[i % 2])
        sync(mte2, v, on=(x_local,), stage=i)
        v.neg(neg_local, x_local[i % 2])
        v.exp(neg_local, neg_local)
        v.add_scalar(den_local, neg_local, 1.0)
        v.duplicate(one_local, 1.0)
        v.div(z_local, one_local, den_local)
        sync(v, mte3, on=z_local)
        mte3.copy(z_local, z[i * TILE])
