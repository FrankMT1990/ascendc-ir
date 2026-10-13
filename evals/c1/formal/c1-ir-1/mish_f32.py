from ascendc_ir import f32, gmptr, kernel, sync, ubuf
from ascendc_ir.pipes import mte2, mte3, v

TILE = 4096
TILES = 1024


@kernel(device="ascend950pr")
def mish_f32(x: gmptr(f32), z: gmptr(f32)):
    x_local = ubuf(f32, TILE, stages=2)
    w_local = ubuf(f32, TILE, stages=2)
    r_local = ubuf(f32, TILE, stages=2)
    tanh_local = ubuf(f32, TILE, stages=2)
    one_local = ubuf(f32, TILE, stages=1)
    z_local = ubuf(f32, TILE, stages=2)
    for i in range(TILES):
        mte2.copy(x[i * TILE], x_local[i % 2])
        sync(mte2, v, on=(x_local[i % 2],), stage=i)
        v.exp(w_local[i % 2], x_local[i % 2])
        v.add_scalar(w_local[i % 2], w_local[i % 2], 1.0)
        v.ln(w_local[i % 2], w_local[i % 2])
        v.mul_scalar(r_local[i % 2], w_local[i % 2], -2.0)
        v.exp(r_local[i % 2], r_local[i % 2])
        v.duplicate(one_local, 1.0)
        v.sub(tanh_local[i % 2], one_local, r_local[i % 2])
        v.add_scalar(r_local[i % 2], r_local[i % 2], 1.0)
        v.div(tanh_local[i % 2], tanh_local[i % 2], r_local[i % 2])
        v.mul(z_local[i % 2], x_local[i % 2], tanh_local[i % 2])
        sync(v, mte3, on=(z_local[i % 2],), stage=i)
        mte3.copy(z_local[i % 2], z[i * TILE])
