# Copyright (c) 2026 Huawei Technologies Co., Ltd.
# This program is free software, you can redistribute it and/or modify it under the terms and conditions of
# CANN Open Software License Agreement Version 2.0 (the "License").
# Please refer to the License for details. You may not use this file except in compliance with the License.
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY, OR FITNESS FOR A PARTICULAR PURPOSE.
# See LICENSE in the root of the software repository for the full text of the License.

"""V001–V010 规则实现。规则语义以 docs/spec/verifier-rules.md 为准，两者必须同步修改。

2026-09-25 评审修复：
- V003：消费方改为「至少一个」；同一条语句既读又写同一槽位时先计消费再结束窗口。
- V005：未决 sync 按 (生产PIPE, 消费PIPE) 对分别计数——每对 PIPE 各有独立 event_ids。
- V006：结果侧 GM 引用同样进入诊断（与 ADR 0007 的透传一致）。
- V010：新增——读取从未写入过的槽位。
"""

from __future__ import annotations

from ..catalog import known, lowering_kind, signature_text
from ..model.core import BufRef, DType, GmRef, Pipe
from ..model.stmts import ComputeStmt, CopyStmt, SyncStmt
from .diagnostic import Diagnostic


def _writes(stmt) -> list:
    if isinstance(stmt, CopyStmt):
        return [stmt.dst] if isinstance(stmt.dst, BufRef) else []
    if isinstance(stmt, ComputeStmt):
        return [stmt.dst] if isinstance(stmt.dst, BufRef) else []
    return []


def _reads(stmt) -> list:
    if isinstance(stmt, CopyStmt):
        return [stmt.src] if isinstance(stmt.src, BufRef) else []
    if isinstance(stmt, ComputeStmt):
        return [s for s in stmt.srcs if isinstance(s, BufRef)]
    return []


def _space(ref) -> str:
    return "gm" if isinstance(ref, GmRef) else ref.buffer.space.value


def _slot_of(stmt, buf) -> int | None:
    return None if stmt.stage is None else stmt.stage % buf.stages


def _matches(ref, buf, slot) -> bool:
    return ref.buffer is buf and (slot is None or ref.stage == slot)


def _resolve_syncs(kernel) -> list:
    """对每个 SyncStmt 解析生产/消费调用，供 V003/V004 共用。

    生产方：sync 之前最近一次写入该槽位的调用。
    消费方：sync 之后、下一次写入同一槽位之前读取该槽位的调用（至少一个）。
    同一条语句既读又写同一槽位时，读发生在写之前：先计入消费，再结束窗口。
    """
    stmts = kernel.statements
    resolved = []
    for idx, stmt in enumerate(stmts):
        if not isinstance(stmt, SyncStmt):
            continue
        edges = []
        for buf in stmt.on:
            slot = _slot_of(stmt, buf)
            producer = None
            for j in range(idx - 1, -1, -1):
                if any(_matches(w, buf, slot) for w in _writes(stmts[j])):
                    producer = stmts[j]
                    break
            consumers = []
            for j in range(idx + 1, len(stmts)):
                if any(_matches(r, buf, slot) for r in _reads(stmts[j])):
                    consumers.append(stmts[j])
                if any(_matches(w, buf, slot) for w in _writes(stmts[j])):
                    break
            edges.append({"buffer": buf, "slot": slot, "producer": producer, "consumers": consumers})
        resolved.append((stmt, edges))
    return resolved


def _sync_covers(sync_stmt, buf, slot, producer_pipe, consumer_pipe) -> bool:
    if sync_stmt.producer != producer_pipe or sync_stmt.consumer != consumer_pipe:
        return False
    for on_buf in sync_stmt.on:
        if on_buf is buf:
            sync_slot = _slot_of(sync_stmt, buf)
            if sync_slot is None or slot is None or sync_slot == slot:
                return True
    return False


def v001_pathway(kernel, device) -> list:
    diags = []
    for stmt in kernel.statements:
        if not isinstance(stmt, CopyStmt):
            continue
        key = (_space(stmt.src), _space(stmt.dst))
        expected = device.pathways.get(key)
        if expected is None:
            diags.append(
                Diagnostic(
                    "V001", "block", stmt.callsite,
                    f"通路 {key[0]}->{key[1]} 在设备 {device.id} 上不存在",
                    f"该设备可用通路：{sorted(device.pathways)}",
                )
            )
        elif expected != stmt.pipe.value:
            diags.append(
                Diagnostic(
                    "V001", "block", stmt.callsite,
                    f"{key[0]}->{key[1]} 搬运在设备 {device.id} 上属于 PIPE {expected}，当前写的是 {stmt.pipe.value}",
                    f"改用 {expected}.copy(...)",
                )
            )
    return diags


def v002_ub_capacity(kernel, device) -> list:
    ub = [b for b in kernel.buffers if b.space.value == "ubuf"]
    total = sum(b.total_bytes for b in ub)
    if total <= device.ub_usable_bytes:
        return []
    largest = max(ub, key=lambda b: b.total_bytes)
    breakdown = ", ".join(f"{b.name}={b.total_bytes}B" for b in ub)
    return [
        Diagnostic(
            "V002", "block", largest.callsite,
            f"UB 总占用 {total}B 超过设备 {device.id} 可用 {device.ub_usable_bytes}B（{breakdown}）",
            f"减小 {largest.name} 的 elems 或 stages",
        )
    ]


def v003_sync_pairing(kernel, device) -> list:
    diags = []
    for stmt, edges in _resolve_syncs(kernel):
        for edge in edges:
            name = edge["buffer"].name
            if edge["producer"] is None:
                diags.append(
                    Diagnostic(
                        "V003", "block", stmt.callsite,
                        f"sync 的 on 中 {name} 在该 sync 之前没有生产调用",
                        f"先生产 {name}，或从 on 中移除",
                    )
                )
            if len(edge["consumers"]) < 1:
                diags.append(
                    Diagnostic(
                        "V003", "block", stmt.callsite,
                        f"sync 的 on 中 {name} 没有下游消费调用",
                        f"补一个消费调用，或从 on 中移除 {name}",
                    )
                )
    return diags


def v004_sync_direction(kernel, device) -> list:
    diags = []
    for stmt, edges in _resolve_syncs(kernel):
        for edge in edges:
            name = edge["buffer"].name
            producer = edge["producer"]
            if producer is not None and producer.pipe != stmt.producer:
                diags.append(
                    Diagnostic(
                        "V004", "block", stmt.callsite,
                        f"{name} 的生产调用在 PIPE {producer.pipe.value}，sync 声明的生产 PIPE 是 {stmt.producer.value}",
                        f"改为 sync({producer.pipe.value}, {stmt.consumer.value}, ...)",
                    )
                )
            for cons in edge["consumers"]:
                if cons.pipe != stmt.consumer:
                    diags.append(
                        Diagnostic(
                            "V004", "block", stmt.callsite,
                            f"{name} 的消费调用在 PIPE {cons.pipe.value}，sync 声明的消费 PIPE 是 {stmt.consumer.value}",
                            f"改为 sync({stmt.producer.value}, {cons.pipe.value}, ...)",
                        )
                    )
    return diags


def v005_event_pressure(kernel, device) -> list:
    """未决 sync 按 (生产PIPE, 消费PIPE) 对分别计数：每对 PIPE 各有 event_ids 个独立 event。"""
    pending = {}
    for stmt in kernel.statements:
        if isinstance(stmt, SyncStmt):
            key = (stmt.producer, stmt.consumer)
            unresolved = [(buf, _slot_of(stmt, buf)) for buf in stmt.on]
            pending.setdefault(key, []).append((stmt, unresolved))
            if len(pending[key]) > device.event_ids:
                return [
                    Diagnostic(
                        "V005", "block", stmt.callsite,
                        f"PIPE 对 {key[0].value}→{key[1].value} 上未决 sync 数达到 {len(pending[key])}，"
                        f"超过每对 PIPE 的 event_ids={device.event_ids}",
                        "合并交接（一个 sync 的 on 携带多个 buffer），或提前消费",
                    )
                ]
        else:
            reads = _reads(stmt)
            if reads:
                for key, pend_list in pending.items():
                    still = []
                    for sync_stmt, unresolved in pend_list:
                        left = [(b, s) for (b, s) in unresolved if not any(_matches(r, b, s) for r in reads)]
                        if left:
                            still.append((sync_stmt, left))
                    pending[key] = still
    return []


def v006_compute_spaces(kernel, device) -> list:
    diags = []
    for stmt in kernel.statements:
        if isinstance(stmt, ComputeStmt):
            if isinstance(stmt.dst, GmRef):
                diags.append(
                    Diagnostic(
                        "V006", "block", stmt.callsite,
                        f"v.{stmt.op} 的结果直接写入了 GM 参数 {stmt.dst.param.name}",
                        "先写入 ubuf buffer，再经 mte3.copy 搬出",
                    )
                )
            bad = [s for s in stmt.srcs if isinstance(s, GmRef)]
            if bad:
                names = ", ".join(s.param.name for s in bad)
                diags.append(
                    Diagnostic(
                        "V006", "block", stmt.callsite,
                        f"{stmt.op} 的操作数 {names} 直接引用了 GM 参数",
                        "先搬进片上 buffer，再计算",
                    )
                )
            if stmt.pipe is Pipe.V:
                for ref in (stmt.dst, *stmt.srcs):
                    if isinstance(ref, BufRef) and ref.buffer.space.value != "ubuf":
                        diags.append(
                            Diagnostic(
                                "V006", "block", stmt.callsite,
                                f"向量计算 {stmt.op} 使用了 {ref.buffer.space.value} 上的 {ref.buffer.name}",
                                "向量计算只读写 ubuf；矩阵乘使用 l0a、l0b 和 l0c",
                            )
                        )
    return diags


def v007_alignment(kernel, device) -> list:
    copied = set()
    for stmt in kernel.statements:
        if isinstance(stmt, CopyStmt):
            for ref in (stmt.src, stmt.dst):
                if isinstance(ref, BufRef):
                    copied.add(ref.buffer.name)
    diags = []
    for buf in kernel.buffers:
        if buf.name not in copied:
            continue
        align = device.l0_align_bytes if buf.space.value in {"l0a", "l0b", "l0c"} else device.align_bytes
        if buf.stage_bytes % align != 0:
            per_align = align // buf.dtype.nbytes
            legal = ((buf.elems + per_align - 1) // per_align) * per_align
            diags.append(
                Diagnostic(
                    "V007", "block", buf.callsite,
                    f"buffer {buf.name} 单 stage {buf.stage_bytes}B 不是 {align}B 的整数倍",
                    f"elems 改为 {legal}（{buf.dtype.value} 每 {per_align} 个元素对齐一次）",
                )
            )
    return diags


def v008_device_guard(kernel, device) -> list:
    diags = []
    for stmt in kernel.statements:
        pipes = []
        if isinstance(stmt, (CopyStmt, ComputeStmt)):
            pipes = [stmt.pipe]
        elif isinstance(stmt, SyncStmt):
            pipes = [stmt.producer, stmt.consumer]
        for p in pipes:
            if p.value not in device.pipes:
                diags.append(
                    Diagnostic(
                        "V008", "block", stmt.callsite,
                        f"PIPE {p.value} 在设备 {device.id} 上不存在",
                        f"该设备可用 PIPE：{sorted(device.pipes)}",
                    )
                )
    return diags


def v009_cross_pipe_read(kernel, device) -> list:
    """跨 PIPE 读取必须先经 sync：读之前、最近一次写之后，存在覆盖该槽位的 sync。"""
    stmts = kernel.statements
    diags = []
    for idx, stmt in enumerate(stmts):
        if isinstance(stmt, SyncStmt):
            continue
        for ref in _reads(stmt):
            writer = None
            for j in range(idx - 1, -1, -1):
                if any(_matches(w, ref.buffer, ref.stage) for w in _writes(stmts[j])):
                    writer = stmts[j]
                    break
            if writer is None:
                continue
            p, q = writer.pipe, stmt.pipe
            if p == q:
                continue
            covered = False
            for j in range(idx - 1, -1, -1):
                if stmts[j] is writer:
                    break
                if isinstance(stmts[j], SyncStmt) and _sync_covers(stmts[j], ref.buffer, ref.stage, p, q):
                    covered = True
                    break
            if not covered:
                diags.append(
                    Diagnostic(
                        "V009", "block", stmt.callsite,
                        f"读取 {ref.buffer.name} 前缺少 {p.value}→{q.value} 的 sync",
                        f"在写入之后、本次读取之前插入 sync({p.value}, {q.value}, on={ref.buffer.name}, ...)",
                        "knowledge/ops/ascendc/runbooks/precision/shared_ub_cross_pipeline_per_direction_sync.md",
                    )
                )
    return diags


def v010_read_without_producer(kernel, device) -> list:
    """读取从未写入过的槽位。V009 要求存在最近一次写入；不存在时由本条接管。"""
    stmts = kernel.statements
    diags = []
    for idx, stmt in enumerate(stmts):
        if isinstance(stmt, SyncStmt):
            continue
        for ref in _reads(stmt):
            written = any(
                _matches(w, ref.buffer, ref.stage)
                for j in range(idx)
                for w in _writes(stmts[j])
            )
            if not written:
                diags.append(
                    Diagnostic(
                        "V010", "block", stmt.callsite,
                        f"读取 {ref.buffer.name}，但此前没有任何写入",
                        f"先生产 {ref.buffer.name}，或检查槽位下标",
                    )
                )
    return diags


def _align16(value: int) -> int:
    return (value + 15) // 16 * 16


def _buf_space(ref) -> str | None:
    return ref.buffer.space.value if isinstance(ref, BufRef) else None


def v011_onchip_capacity(kernel, device) -> list:
    """L1 / L0 各自单独计容量，不和 UB 混在一起。"""
    limits = {
        "l1": device.l1_bytes,
        "l0a": device.l0a_bytes,
        "l0b": device.l0b_bytes,
        "l0c": device.l0c_bytes,
    }
    diags = []
    for space, limit in limits.items():
        group = [b for b in kernel.buffers if b.space.value == space]
        total = sum(b.total_bytes for b in group)
        if not group or total <= limit:
            continue
        largest = max(group, key=lambda b: b.total_bytes)
        breakdown = ", ".join(f"{b.name}={b.total_bytes}B" for b in group)
        diags.append(
            Diagnostic(
                "V011", "block", largest.callsite,
                f"{space} 总占用 {total}B 超过设备 {device.id} 可用 {limit}B（{breakdown}）",
                f"减小 {largest.name} 的 elems 或 stages",
            )
        )
    return diags


def v012_cube_contract(kernel, device) -> list:
    """矩阵搬运和 mmad 的地址空间、dtype 与逻辑形状必须和 3510 的 f16 样例一致。"""
    diags = []
    diags.extend(_check_no_mix(kernel))
    for index, stmt in enumerate(kernel.statements):
        if isinstance(stmt, CopyStmt) and stmt.form != "linear":
            diags.extend(_check_cube_copy(stmt))
        elif isinstance(stmt, ComputeStmt) and stmt.op == "mmad":
            diags.extend(_check_mmad(stmt))
            diags.extend(_check_mmad_links(kernel.statements, index, stmt))
    return diags


def _check_no_mix(kernel) -> list:
    spaces = {buf.space.value for buf in kernel.buffers}
    if "ubuf" not in spaces or spaces <= {"ubuf"}:
        return []
    mixed = next(buf for buf in kernel.buffers if buf.space.value != "ubuf")
    return [
        Diagnostic(
            "V012", "block", mixed.callsite,
            f"同一个核里同时有 ubuf 和 {mixed.space.value} 上的 {mixed.name}",
            "向量核只放 ubuf；矩阵核只放 L1 和 L0。Cube 结果进 UB 的样例用的是 __mix__(1, 2)，这套单核调度还没有这个启动方式",
        )
    ]


def _need(stmt, ok: bool, message: str, suggestion: str, sink: list) -> None:
    if not ok:
        sink.append(Diagnostic("V012", "block", stmt.callsite, message, suggestion))


def _check_cube_copy(stmt: CopyStmt) -> list:
    diags = []
    forms = {
        "nd2nz": (Pipe.MTE2, "gm", "l1"),
        "dn2nz": (Pipe.MTE2, "gm", "l1"),
        "l12l0a": (Pipe.MTE1, "l1", "l0a"),
        "l12l0b": (Pipe.MTE1, "l1", "l0b"),
        "l0c2gm": (Pipe.FIX, "l0c", "gm"),
    }
    spec = forms.get(stmt.form)
    _need(stmt, spec is not None, f"不认识的搬运形式 {stmt.form}", "使用 linear、nd2nz、l12l0a、l12l0b 或 l0c2gm", diags)
    if spec is None or len(diags):
        return diags
    pipe, src_space, dst_space = spec
    _need(stmt, stmt.pipe is pipe, f"{stmt.form} 属于 PIPE {pipe.value}，当前写的是 {stmt.pipe.value}", f"改用对应的 pipe 方法", diags)
    _need(stmt, _space(stmt.src) == src_space and _space(stmt.dst) == dst_space,
          f"{stmt.form} 的地址空间应为 {src_space}->{dst_space}，当前是 {_space(stmt.src)}->{_space(stmt.dst)}",
          "按 GM→L1→L0A/L0B→L0C→GM 这条通路改 buffer", diags)
    if len(stmt.scalars) not in (2, 3) or not all(isinstance(x, int) and x > 0 for x in stmt.scalars):
        _need(stmt, False, f"{stmt.form} 需要两个正整数行列", "传入 rows 和 cols", diags)
        return diags
    if len(stmt.scalars) == 3 and (stmt.form not in {"nd2nz", "dn2nz"} or stmt.scalars[2] < stmt.scalars[1]):
        _need(stmt, False, "只有 nd2nz 可以带行距，而且行距不能小于这一块的列数", "row_stride 省略，或设成不小于 cols", diags)
        return diags
    rows, cols = stmt.scalars[0], stmt.scalars[1]
    need = _align16(rows) * _align16(cols)
    bufs = [ref.buffer for ref in (stmt.src, stmt.dst) if isinstance(ref, BufRef)]
    for buf in bufs:
        _need(
            stmt, buf.elems >= need,
            f"{buf.name} 有 {buf.elems} 个元素，装不下对齐后的 {rows}×{cols}（需要 {need}）",
            f"把 {buf.name} 的 elems 至少改为 {need}", diags,
        )
    if stmt.form in {"nd2nz", "dn2nz"} and isinstance(stmt.src, GmRef) and isinstance(stmt.dst, BufRef):
        dst = stmt.dst.buffer
        _need(stmt, dst.dtype is DType.f16 and stmt.src.param.dtype is dst.dtype,
              "nd2nz 这一批只生成 f16。f32 样例的 C0 是 8，还要转置，不能套 f16 的公式",
              "A/B 改成 f16，或等 f32 转置通路单独降级", diags)
    if stmt.form in {"l12l0a", "l12l0b"} and isinstance(stmt.src, BufRef) and isinstance(stmt.dst, BufRef):
        _need(stmt, stmt.src.buffer.dtype is stmt.dst.buffer.dtype,
              f"{stmt.form} 的 L1 与 L0 dtype 不一致", "让源和目的使用同一个 dtype", diags)
        _need(stmt, stmt.dst.buffer.dtype is DType.f16,
              f"{stmt.form} 这一批只生成 f16。f32 的 K 方向粒度是 8",
              "改成 f16，或等 f32 通路单独降级", diags)
    if stmt.form == "l0c2gm" and isinstance(stmt.src, BufRef) and isinstance(stmt.dst, GmRef):
        _need(stmt, stmt.src.buffer.dtype is DType.f32 and stmt.dst.param.dtype is DType.f32,
              "l0c2gm 这一批只把 f32 的 L0C 写回 f32 的 GM", "结果 buffer 和 GM 参数都用 f32", diags)
    return diags


def _check_mmad(stmt: ComputeStmt) -> list:
    diags = []
    _need(stmt, stmt.pipe is Pipe.M, "mmad 属于 PIPE m", "使用 m.mmad(...)", diags)
    _need(stmt, len(stmt.srcs) == 2, "mmad 需要 A 和 B 两个源", "写成 m.mmad(c, a, b, m, k, n)", diags)
    if len(stmt.scalars) != 4 or not all(isinstance(x, int) for x in stmt.scalars):
        _need(stmt, False, "mmad 需要整数 m、k、n 和 init 标志", "使用 m.mmad(c, a, b, m, k, n, init=True)", diags)
        return diags
    m, k, n, init = stmt.scalars
    _need(stmt, m > 0 and k > 0 and n > 0 and init in (0, 1),
          f"mmad 的 m、k、n 必须为正，init 只能是 0 或 1，得到 {(m, k, n, init)}",
          "检查三个维度，init 用 True 或 False", diags)
    _need(stmt, _buf_space(stmt.dst) == "l0c" and isinstance(stmt.dst, BufRef) and stmt.dst.buffer.dtype is DType.f32,
          "mmad 的目的必须是 f32 的 l0c", "用 l0c(f32, ...) 承接结果", diags)
    if len(stmt.srcs) == 2:
        a, b = stmt.srcs
        _need(stmt, _buf_space(a) == "l0a" and _buf_space(b) == "l0b",
              "mmad 的 A 必须在 l0a，B 必须在 l0b", "先 l12l0a / l12l0b，再 mmad", diags)
        if isinstance(a, BufRef) and isinstance(b, BufRef):
            _need(stmt, a.buffer.dtype is DType.f16 and b.buffer.dtype is DType.f16,
                  "mmad 这一批只生成 f16 乘 f16、结果 f32。f32 输入的 K 方向粒度是 8，不是 16",
                  "A 和 B 都用 f16", diags)
            _need(stmt, a.buffer.elems >= _align16(m) * _align16(k),
                  f"A 的元素个数装不下对齐后的 {m}×{k}", "按对齐后的 M×K 分配 l0a", diags)
            _need(stmt, b.buffer.elems >= _align16(n) * _align16(k),
                  f"B 的元素个数装不下对齐后的 {n}×{k}。B 按 (n, k) 存放", "按对齐后的 N×K 分配 l0b", diags)
    if isinstance(stmt.dst, BufRef) and m > 0 and n > 0:
        _need(stmt, stmt.dst.buffer.elems >= _align16(m) * _align16(n),
              f"L0C 装不下对齐后的 {m}×{n}", "按对齐后的 M×N 分配 l0c", diags)
    return diags


def _producer_copy_forms(stmts, end: int, buf, forms: tuple):
    for form in forms:
        found = _producer_copy(stmts, end, buf, form)
        if found is not None:
            return found
    return None


def _producer_copy(stmts, end: int, buf, form: str):
    for index in range(end - 1, -1, -1):
        stmt = stmts[index]
        if (
            isinstance(stmt, CopyStmt)
            and stmt.form == form
            and isinstance(stmt.dst, BufRef)
            and stmt.dst.buffer is buf
        ):
            return stmt
    return None


def _check_mmad_links(stmts, index: int, stmt: ComputeStmt) -> list:
    """搬运的行列必须和这次 mmad 的 m、k、n 相同，否则会按小块搬运、按大块计算。"""
    if len(stmt.scalars) != 4 or len(stmt.srcs) != 2:
        return []
    m, k, n, init = stmt.scalars
    if not all(isinstance(x, int) and x > 0 for x in (m, k, n)):
        return []
    diags = []
    a, b = stmt.srcs
    _link_shape(diags, stmt, _producer_copy(stmts, index, getattr(a, "buffer", None), "l12l0a"), (m, k), "l12l0a", "m, k")
    _link_shape(diags, stmt, _producer_copy(stmts, index, getattr(b, "buffer", None), "l12l0b"), (n, k), "l12l0b", "n, k")
    if isinstance(a, BufRef):
        load = _producer_copy(stmts, index, a.buffer, "l12l0a")
        if load is not None and isinstance(load.src, BufRef):
            _link_shape(diags, stmt, _producer_copy_forms(stmts, index, load.src.buffer, ("nd2nz", "dn2nz")), (m, k), "A 的 nd2nz", "m, k")
    if isinstance(b, BufRef):
        load = _producer_copy(stmts, index, b.buffer, "l12l0b")
        if load is not None and isinstance(load.src, BufRef):
            _link_shape(diags, stmt, _producer_copy_forms(stmts, index, load.src.buffer, ("nd2nz", "dn2nz")), (n, k), "B 的 nd2nz", "n, k")
    if isinstance(stmt.dst, BufRef):
        for later in stmts[index + 1 :]:
            if isinstance(later, ComputeStmt) and later.op == "mmad" and getattr(later.dst, "buffer", None) is stmt.dst.buffer:
                break
            if isinstance(later, CopyStmt) and later.form == "l0c2gm" and getattr(later.src, "buffer", None) is stmt.dst.buffer:
                _link_shape(diags, later, later, (m, n), "l0c2gm", "m, n")
                break
    if init == 0 and isinstance(stmt.dst, BufRef):
        prior = any(
            isinstance(prev, ComputeStmt)
            and prev.op == "mmad"
            and isinstance(prev.dst, BufRef)
            and prev.dst.buffer is stmt.dst.buffer
            for prev in stmts[:index]
        )
        _need(stmt, prior, "init 为假时会把 L0C 里的旧值累加进来，但这块 L0C 还没有写过", "第一次 mmad 用 init=True", diags)
    return diags


def _link_shape(diags, stmt, producer, expected, what: str, names: str) -> None:
    if producer is None or len(getattr(producer, "scalars", ())) < 2:
        return
    if tuple(producer.scalars[:2]) != expected:
        diags.append(
            Diagnostic(
                "V012", "block", stmt.callsite,
                f"{what} 的行列是 {tuple(producer.scalars[:2])}，和 mmad 的 {names}={expected} 不一致",
                "让搬运的 rows、cols 和 mmad 的 m、k、n 用同一组数",
            )
        )


def v013_catalog_lowering(kernel, device) -> list:
    """目录里有、但这一批没有降级模板的计算，明确拒绝，不猜重载。"""
    diags = []
    for stmt in kernel.statements:
        if not isinstance(stmt, ComputeStmt):
            continue
        kind = lowering_kind(stmt.op)
        if kind in {"reg_binary", "reg_unary", "reg_scalar"} and stmt.pipe is not Pipe.V:
            diags.append(
                Diagnostic(
                    "V013", "block", stmt.callsite,
                    f"{stmt.op} 是向量逐元素运算，当前写在 PIPE {stmt.pipe.value}",
                    "改用 v." + stmt.op,
                )
            )
            continue
        if kind is not None:
            continue
        if known(stmt.op):
            diags.append(
                Diagnostic(
                    "V013", "block", stmt.callsite,
                    f"{stmt.op} 已在 3510 头文件目录中，这一批没有逐元素或 mmad 降级模板。签名：{signature_text(stmt.op)}",
                    "不要改用别的重载硬套。要这条指令，先补与头文件一致的模板",
                )
            )
        else:
            diags.append(
                Diagnostic(
                    "V013", "block", stmt.callsite,
                    f"3510 的向量/矩阵目录里没有 {stmt.op}",
                    "改用目录里的名字，或先把声明补进 catalog",
                )
            )
    return diags
