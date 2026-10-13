from ascendc_ir import f32, gmptr, kernel, sync, ubuf
from ascendc_ir.pipes import mte2, mte3, v

TILE = 8192
TILES = 8192


@kernel(device="ascend950pr")
def gelu_f32(x: gmptr(f32), z: gmptr(f32)):
    x_local = ubuf(f32, TILE, stages=2)
    t_local = ubuf(f32, TILE, stages=2)
    z_local = ubuf(f32, TILE, stages=2)
    for i in range(TILES):
        mte2.copy(x[i * TILE], x_local[i % 2])
        sync(mte2, v, on=(x_local[i % 2],), stage=i)
        v.mul(t_local[i % 2], x_local[i % 2], x_local[i % 2])
        v.mul(t_local[i % 2], t_local[i % 2], x_local[i % 2])
        v.mul_scalar(t_local[i % 2], t_local[i % 2], 0.044715)
        v.add(t_local[i % 2], x_local[i % 2], t_local[i % 2])
        v.mul_scalar(t_local[i % 2], t_local[i % 2], 1.5957691216)
        v.neg(t_local[i % 2], t_local[i % 2])
        v.exp(t_local[i % 2], t_local[i % 2])
        v.add_scalar(t_local[i % 2], t_local[i % 2], 1.0)
        v.div(z_local[i % 2], x_local[i % 2], t_local[i % 2])
        sync(v, mte3, on=(z_local[i % 2],), stage=i)
        mte3.copy(z_local[i % 2], z[i * TILE])
