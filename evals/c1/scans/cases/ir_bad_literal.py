from ascendc_ir import f32, gmptr, kernel, sync, ubuf
from ascendc_ir.pipes import mte2, mte3, v

KERNEL = "asc_add"


@kernel(device="ascend950pr")
def bad_literal(x: gmptr(f32), z: gmptr(f32)):
    x_local = ubuf(f32, 2048, stages=1)
    mte2.copy(x[0], x_local)
    sync(mte2, v, on=(x_local,))
    v.compute(KERNEL.strip(), x_local, (x_local,))
    sync(v, mte3, on=x_local)
    mte3.copy(x_local, z[0])
