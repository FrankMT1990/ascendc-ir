from ascendc_ir import f32, gmptr, kernel, sync, ubuf
from ascendc_ir.pipes import mte2, mte3, v

TILE = 4096
TILES = 512


@kernel(device="ascend950pr")
def foreach_addcdiv_f32(x1: gmptr(f32), x2: gmptr(f32), x3: gmptr(f32), z: gmptr(f32)):
    x1_local = ubuf(f32, TILE, stages=2)
    x2_local = ubuf(f32, TILE, stages=2)
    x3_local = ubuf(f32, TILE, stages=2)
    z_local = ubuf(f32, TILE, stages=2)
    for i in range(TILES):
        mte2.copy(x1[i * TILE], x1_local[i % 2])
        mte2.copy(x2[i * TILE], x2_local[i % 2])
        mte2.copy(x3[i * TILE], x3_local[i % 2])
        sync(mte2, v, on=(x1_local[i % 2], x2_local[i % 2], x3_local[i % 2]), stage=i)
        v.div(z_local[i % 2], x2_local[i % 2], x3_local[i % 2])
        v.mul_scalar(z_local[i % 2], z_local[i % 2], 1.0)
        v.add(z_local[i % 2], x1_local[i % 2], z_local[i % 2])
        sync(v, mte3, on=(z_local[i % 2],), stage=i)
        mte3.copy(z_local[i % 2], z[i * TILE])
