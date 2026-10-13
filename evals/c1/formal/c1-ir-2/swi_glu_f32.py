from ascendc_ir import f32, gmptr, kernel, sync, ubuf
from ascendc_ir.pipes import mte2, mte3, v


@kernel(device="ascend950pr")
def swi_glu_f32(x: gmptr(f32), z: gmptr(f32)):
    ROWS = 2048
    HALF = 2048
    a = ubuf(f32, HALF, stages=2)
    b = ubuf(f32, HALF, stages=2)
    t = ubuf(f32, HALF, stages=2)
    for i in range(ROWS):
        s = i % 2
        mte2.copy(x[i * 4096], a[s])
        mte2.copy(x[i * 4096 + 2048], b[s])
        sync(mte2, v, on=(a[s], b[s]), stage=i)
        v.mul_scalar(t[s], a[s], -1.0)
        v.exp(t[s], t[s])
        v.add_scalar(t[s], t[s], 1.0)
        v.log(t[s], t[s])
        v.mul_scalar(t[s], t[s], -1.0)
        v.exp(t[s], t[s])
        v.mul(t[s], a[s], t[s])
        v.mul(t[s], t[s], b[s])
        sync(v, mte3, on=(t[s],), stage=i)
        mte3.copy(t[s], z[i * 2048])
