from ascendc_ir import f32, gmptr, kernel, sync, ubuf
from ascendc_ir.pipes import mte2, mte3, v


@kernel(device="ascend950pr")
def foreach_addcdiv_f32(x1: gmptr(f32), x2: gmptr(f32), x3: gmptr(f32), z: gmptr(f32)):
    TILE = 2048
    TILES = 2 * 1024 * 1024 // TILE
    a = ubuf(f32, TILE, stages=2)
    b = ubuf(f32, TILE, stages=2)
    c = ubuf(f32, TILE, stages=2)
    q = ubuf(f32, TILE, stages=2)
    for i in range(TILES):
        s = i % 2
        mte2.copy(x1[i * TILE], a[s])
        mte2.copy(x2[i * TILE], b[s])
        mte2.copy(x3[i * TILE], c[s])
        sync(mte2, v, on=(a[s], b[s], c[s]), stage=i)
        v.div(q[s], b[s], c[s])
        v.add(q[s], a[s], q[s])
        sync(v, mte3, on=(q[s],), stage=i)
        mte3.copy(q[s], z[i * TILE])
