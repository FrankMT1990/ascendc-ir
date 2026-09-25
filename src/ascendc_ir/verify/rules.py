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

from ..model.core import BufRef, GmRef
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
    return "gm" if isinstance(ref, GmRef) else "ubuf"


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
    total = sum(b.total_bytes for b in kernel.buffers)
    if total <= device.ub_usable_bytes:
        return []
    largest = max(kernel.buffers, key=lambda b: b.total_bytes)
    breakdown = ", ".join(f"{b.name}={b.total_bytes}B" for b in kernel.buffers)
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
                        f"v.{stmt.op} 的操作数 {names} 直接引用了 GM 参数",
                        "先经 mte2.copy 搬入 ubuf buffer",
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
        if buf.stage_bytes % device.align_bytes != 0:
            per_align = device.align_bytes // buf.dtype.nbytes
            legal = ((buf.elems + per_align - 1) // per_align) * per_align
            diags.append(
                Diagnostic(
                    "V007", "block", buf.callsite,
                    f"buffer {buf.name} 单 stage {buf.stage_bytes}B 不是 {device.align_bytes}B 的整数倍",
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
