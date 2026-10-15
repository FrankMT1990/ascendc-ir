"""L2 maximum case2：z = max(x, y)，[2048,2048] f32 同形逐元素。"""
from ascendc_ir import f32, gmptr, kernel, sync, ubuf
from ascendc_ir.pipes import mte2, mte3, v

TILE = 8192
TILES = 512


@kernel(device="ascend950pr")
def maximum_f32(x: gmptr(f32), y: gmptr(f32), z: gmptr(f32)):
    x_local = ubuf(f32, TILE, stages=2)
    y_local = ubuf(f32, TILE, stages=2)
    z_local = ubuf(f32, TILE, stages=1)
    for i in range(TILES):
        mte2.copy(x[i * TILE], x_local[i % 2])
        mte2.copy(y[i * TILE], y_local[i % 2])
        sync(mte2, v, on=(x_local, y_local), stage=i)
        v.max(z_local, x_local[i % 2], y_local[i % 2])
        sync(v, mte3, on=z_local)
        mte3.copy(z_local, z[i * TILE])
