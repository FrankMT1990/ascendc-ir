"""宽图压力用例：6 路并行中间量 + 4 级汇合，13 个向量同时活跃。

z = ((x1*x2 + x2*x3) + (x3*x1 + x1 - x2)) + x3*x1*x2
比 gelu 的单链（1-2 个活跃中间）严苛得多：测寄存器压力下的融合行为。
"""
from ascendc_ir import f32, gmptr, kernel, sync, ubuf
from ascendc_ir.pipes import mte2, mte3, v

TILE = 2048
TILES = 1024


@kernel(device="ascend950pr")
def floor_foreach_addcdiv(x1: gmptr(f32), x2: gmptr(f32), x3: gmptr(f32), z: gmptr(f32)):
    t1 = ubuf(f32, TILE, stages=2)
    t2 = ubuf(f32, TILE, stages=2)
    t3 = ubuf(f32, TILE, stages=2)
    t4 = ubuf(f32, TILE, stages=2)
    t5 = ubuf(f32, TILE, stages=2)
    t6 = ubuf(f32, TILE, stages=2)
    a1 = ubuf(f32, TILE, stages=2)
    a2 = ubuf(f32, TILE, stages=2)
    a3 = ubuf(f32, TILE, stages=2)
    b1 = ubuf(f32, TILE, stages=2)
    x1_local = ubuf(f32, TILE, stages=2)
    x2_local = ubuf(f32, TILE, stages=2)
    x3_local = ubuf(f32, TILE, stages=2)
    z_local = ubuf(f32, TILE, stages=1)
    for i in range(TILES):
        mte2.copy(x1[i * TILE], x1_local[i % 2])
        mte2.copy(x2[i * TILE], x2_local[i % 2])
        mte2.copy(x3[i * TILE], x3_local[i % 2])
        sync(mte2, v, on=(x1_local, x2_local, x3_local), stage=i)
        v.mul(t1[i % 2], x1_local[i % 2], x2_local[i % 2])
        v.mul(t2[i % 2], x2_local[i % 2], x3_local[i % 2])
        v.mul(t3[i % 2], x3_local[i % 2], x1_local[i % 2])
        v.add(t4[i % 2], x1_local[i % 2], x2_local[i % 2])
        v.sub(t5[i % 2], x1_local[i % 2], x2_local[i % 2])
        v.mul(t6[i % 2], t3[i % 2], x2_local[i % 2])
        v.add(a1[i % 2], t1[i % 2], t2[i % 2])
        v.add(a2[i % 2], t3[i % 2], t4[i % 2])
        v.add(a3[i % 2], t5[i % 2], t6[i % 2])
        v.add(b1[i % 2], a1[i % 2], a2[i % 2])
        v.add(z_local, b1[i % 2], a3[i % 2])
        sync(v, mte3, on=z_local)
        mte3.copy(z_local, z[i * TILE])
