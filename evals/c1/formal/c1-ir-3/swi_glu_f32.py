from ascendc_ir import f32, gmptr, kernel, sync, ubuf
from ascendc_ir.pipes import mte2, mte3, v


@kernel(device="ascend950pr")
def swi_glu_f32(x: gmptr(f32), z: gmptr(f32)):
    ROWS = 2048
    HALF = 2048
    a = ubuf(f32, HALF, stages=2)
    b = ubuf(f32, HALF, stages=2)
    t = ubuf(f32, HALF, stages=2)
    one = ubuf(f32, HALF, stages=2)
    for i in range(ROWS):
        mte2.copy(x[i * 4096], a[i % 2])
        mte2.copy(x[i * 4096 + 2048], b[i % 2])
        sync(mte2, v, on=(a[i % 2], b[i % 2]), stage=i)
        v.duplicate(one[i % 2], 1.0)
        v.neg(t[i % 2], a[i % 2])
        v.exp(t[i % 2], t[i % 2])
        v.add_scalar(t[i % 2], t[i % 2], 1.0)
        v.div(t[i % 2], one[i % 2], t[i % 2])
        v.mul(t[i % 2], a[i % 2], t[i % 2])
        v.mul(t[i % 2], t[i % 2], b[i % 2])
        sync(v, mte3, on=(t[i % 2],), stage=i)
        mte3.copy(t[i % 2], z[i * 2048])
