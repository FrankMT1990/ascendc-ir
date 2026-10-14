"""融合分析（emit 与 verify 共享）。

识别循环体内连续 v 管语句中的段内私有临时 buffer——这些 buffer 在代码生成时
提升为寄存器直通，不占 UB 分配。verify 的 V002 容量检查据此扣除。
"""

from ..catalog import BINARY_I32, SCALAR_I32, lowering_kind
from ..model.core import DType
from ..model.stmts import ComputeStmt, CopyStmt, SyncStmt


def fusible_op(stmt) -> bool:
    if not isinstance(stmt, ComputeStmt):
        return False
    if stmt.op in {"add", "select", "duplicate", "leakyrelu"}:
        return True
    kind = lowering_kind(stmt.op)
    if kind in {"reg_binary", "reg_unary", "reg_scalar"}:
        if stmt.op in BINARY_I32 or stmt.op in SCALAR_I32:
            return False
        return stmt.dst.buffer.dtype is DType.f32
    return False


def plan_fusion(body) -> list:
    """返回融合段列表；每段含 start/end/stmts/inputs/temps/outputs/name。

    判定（保守）：段内临时 buffer 的全部读写闭合于段内、不被任何 copy/sync
    语句引用、无段外写入。不满足任一条件的 buffer 作为段输出（真实 UB）。
    """
    n = len(body)
    refs = {}

    def touch(name, kind_key, j):
        rec = refs.setdefault(name, {"reads": [], "writes": [], "other": []})
        rec[kind_key].append(j)

    for j, st in enumerate(body):
        if isinstance(st, ComputeStmt):
            for s in st.srcs:
                touch(s.buffer.name, "reads", j)
            if st.dst is not None:
                touch(st.dst.buffer.name, "writes", j)
        elif isinstance(st, CopyStmt):
            if st.src is not None and hasattr(st.src, "buffer"):
                touch(st.src.buffer.name, "other", j)
            if st.dst is not None and hasattr(st.dst, "buffer"):
                touch(st.dst.buffer.name, "other", j)
        elif isinstance(st, SyncStmt):
            for b in st.on:
                touch(b.name, "other", j)

    plans = []
    j = 0
    while j < n:
        if not fusible_op(body[j]):
            j += 1
            continue
        a = j
        while j < n and fusible_op(body[j]):
            j += 1
        b = j
        if b - a < 2:
            continue
        seg = body[a:b]
        seg_writes = [st.dst.buffer for st in seg]
        seg_write_names = {buf.name for buf in seg_writes}
        if any(refs[name]["writes"] and (min(refs[name]["writes"]) < a or max(refs[name]["writes"]) >= b)
               for name in seg_write_names):
            continue
        temps, outputs = [], []
        for buf in seg_writes:
            if any(o.name == buf.name for o in outputs):
                continue
            rec = refs[buf.name]
            reads_outside = any(r < a or r >= b for r in rec["reads"])
            if rec["other"] or reads_outside:
                outputs.append(buf)
            else:
                temps.append(buf)
        if not outputs:
            continue
        inputs = []
        input_names = set()
        for st in seg:
            for s in st.srcs:
                if s.buffer.name not in seg_write_names and s.buffer.name not in input_names:
                    inputs.append(s.buffer)
                    input_names.add(s.buffer.name)
        plans.append({
            "start": a, "end": b, "stmts": seg,
            "inputs": inputs, "temps": temps, "outputs": outputs,
            "name": f"fused_vf_{len(plans)}",
        })
    return plans


def promoted_temp_names(body) -> set:
    """给定语句序列，返回将被提升为寄存器、不占 UB 分配的 buffer 名。"""
    names = set()
    for p in plan_fusion(body):
        names.update(b.name for b in p["temps"])
    return names
