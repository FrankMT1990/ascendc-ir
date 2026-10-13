from ascendc_ir import f32, gmptr, kernel, sync, ubuf
from ascendc_ir.pipes import mte2, mte3, v


@kernel(device="ascend950pr")
def foreach_addcdiv_f32(x1: gmptr(f32), x2: gmptr(f32), x3: gmptr(f32), z: gmptr(f32)):
    N = 2 * 1024 * 1024
    TILE = 4096
    a = ubuf(f32, TILE, stages=2)
    b = ubuf(f32, TILE, stages=2)
    c = ubuf(f32, TILE, stages=2)
    d = ubuf(f32, TILE, stages=2)
    for i in range(N // TILE):
        mte2.copy(x1[i * TILE], a[i % 2])
        mte2.copy(x2[i * TILE], b[i % 2])
        mte2.copy(x3[i * TILE], c[i % 2])
        sync(mte2, v, on=(a[i % 2], b[i % 2], c[i % 2]), stage=i)
        v.div(d[i % 2], b[i % 2], c[i % 2])
        v.add(d[i % 2], a[i % 2], d[i % 2])
        sync(v, mte3, on=(d[i % 2],), stage=i)
        mte3.copy(d[i % 2], z[i * TILE])
