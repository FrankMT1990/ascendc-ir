from ascendc_ir import f32, gmptr, kernel, sync, ubuf
from ascendc_ir.pipes import mte2, mte3, v


@kernel(device="ascend950pr")
def bad_ascfile(x: gmptr(f32), z: gmptr(f32)):
    with open("hand_written.asc", "w") as f:
        f.write("placeholder")
    x_local = ubuf(f32, 2048, stages=1)
    mte2.copy(x[0], x_local)
    sync(mte2, v, on=(x_local,))
    v.abs(x_local, x_local)
    sync(v, mte3, on=x_local)
    mte3.copy(x_local, z[0])
