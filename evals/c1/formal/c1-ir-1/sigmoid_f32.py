from ascendc_ir import f32, gmptr, kernel, sync, ubuf
from ascendc_ir.pipes import mte2, mte3, v

TILE = 8192
TILES = 512


@kernel(device="ascend950pr")
def sigmoid_f32(x: gmptr(f32), z: gmptr(f32)):
    x_local = ubuf(f32, TILE, stages=2)
    t_local = ubuf(f32, TILE, stages=2)
    one_local = ubuf(f32, TILE, stages=1)
    z_local = ubuf(f32, TILE, stages=2)
    for i in range(TILES):
        mte2.copy(x[i * TILE], x_local[i % 2])
        sync(mte2, v, on=(x_local[i % 2],), stage=i)
        v.neg(t_local[i % 2], x_local[i % 2])
        v.exp(t_local[i % 2], t_local[i % 2])
        v.add_scalar(t_local[i % 2], t_local[i % 2], 1.0)
        v.duplicate(one_local, 1.0)
        v.div(z_local[i % 2], one_local, t_local[i % 2])
        sync(v, mte3, on=(z_local[i % 2],), stage=i)
        mte3.copy(z_local[i % 2], z[i * TILE])
