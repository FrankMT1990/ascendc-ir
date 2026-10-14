from ascendc_ir import f32, gmptr, kernel, sync, ubuf
from ascendc_ir.pipes import mte2, mte3, v


@kernel(device="ascend950pr")
def foreach_addcdiv_f32(x1: gmptr(f32), x2: gmptr(f32), x3: gmptr(f32), z: gmptr(f32)):
    TILE = 2048
    TILES = 2 * 1024 * 1024 // TILE
    a_local = ubuf(f32, TILE, stages=2)
    b_local = ubuf(f32, TILE, stages=2)
    c_local = ubuf(f32, TILE, stages=2)
    t = ubuf(f32, TILE, stages=2)
    z_local = ubuf(f32, TILE, stages=2)
    for i in range(TILES):
        mte2.copy(x1[i * TILE], a_local[i % 2])
        mte2.copy(x2[i * TILE], b_local[i % 2])
        mte2.copy(x3[i * TILE], c_local[i % 2])
        sync(mte2, v, on=(a_local[i % 2], b_local[i % 2], c_local[i % 2]), stage=i)
        v.div(t[i % 2], b_local[i % 2], c_local[i % 2])
        v.add(z_local[i % 2], a_local[i % 2], t[i % 2])
        sync(v, mte3, on=(z_local[i % 2],), stage=i)
        mte3.copy(z_local[i % 2], z[i * TILE])
