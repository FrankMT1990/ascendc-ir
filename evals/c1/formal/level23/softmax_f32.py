"""L2 softmax case2：z = softmax(x, dim=-1)，[2048,2048] f32，行=2048=tile。

数值：e=exp(x) 直接和（非稳定式；行和后广播除）。
"""
from ascendc_ir import f32, gmptr, kernel, sync, ubuf
from ascendc_ir.pipes import mte2, mte3, v

TILE = 2048
TILES = 2048


@kernel(device="ascend950pr")
def softmax_f32(x: gmptr(f32), z: gmptr(f32)):
    x_local = ubuf(f32, TILE, stages=2)
    e_local = ubuf(f32, TILE, stages=1)
    sum_vf = ubuf(f32, 64)
    z_local = ubuf(f32, TILE, stages=1)
    for i in range(TILES):
        mte2.copy(x[i * TILE], x_local[i % 2])
        sync(mte2, v, on=(x_local,), stage=i)
        v.exp(e_local, x_local[i % 2])
        v.repeat_reduce_sum(sum_vf, e_local)
        v.div(z_local, e_local, sum_vf)
        sync(v, mte3, on=z_local)
        mte3.copy(z_local, z[i * TILE])
