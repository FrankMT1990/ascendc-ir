from ascendc_ir import f32, gmptr, kernel, sync, ubuf
from ascendc_ir.pipes import mte2, mte3, v


@kernel(device="ascend950pr")
def swi_glu_f32(x: gmptr(f32), z: gmptr(f32)):
    HALF = 2048
    ROWS = 2048
    x0_local = ubuf(f32, HALF, stages=2)
    x1_local = ubuf(f32, HALF, stages=2)
    t1 = ubuf(f32, HALF, stages=2)
    t2 = ubuf(f32, HALF, stages=2)
    z_local = ubuf(f32, HALF, stages=2)
    for i in range(ROWS):
        mte2.copy(x[i * (2 * HALF)], x0_local[i % 2])
        mte2.copy(x[i * (2 * HALF) + HALF], x1_local[i % 2])
        sync(mte2, v, on=(x0_local[i % 2], x1_local[i % 2]), stage=i)
        v.mul_scalar(t1[i % 2], x0_local[i % 2], -1.0)
        v.exp(t2[i % 2], t1[i % 2])
        v.add_scalar(t1[i % 2], t2[i % 2], 1.0)
        v.duplicate(t2[i % 2], 1.0)
        v.div(t1[i % 2], t2[i % 2], t1[i % 2])
        v.mul(t1[i % 2], x0_local[i % 2], t1[i % 2])
        v.mul(z_local[i % 2], t1[i % 2], x1_local[i % 2])
        sync(v, mte3, on=(z_local[i % 2],), stage=i)
        mte3.copy(z_local[i % 2], z[i * HALF])
