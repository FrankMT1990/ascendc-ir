# Copyright (c) 2026 Huawei Technologies Co., Ltd.
# This program is free software and you can redistribute it and/or modify it under the terms and conditions of
# CANN Open Software License Agreement Version 2.0 (the "License").
# You may refer to the License for details on the use of this software distributed under the License.
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY OR FITNESS FOR A PARTICULAR PURPOSE.
# See LICENSE in the root of the software repository for the full text of the License.

"""循环重卷：trace 期展开的语句序列，按仿射规律还原为「顺序多段」结构。

trace 期 `for i in range(TILES)` 被展开（ADR 0002），模型只保留平铺语句。
reroll 用 sync 的 stage（迭代号，见 ir-syntax.md）把语句序列切成若干段：

- ("plain", start, stmts)：无带 stage 的 sync 的直写段（每个槽位至多写一次）；
- ("loop", start, per, tiles, body, init_first)：单迭代模板 body（第 0 轮，位于全局
  语句下标 start 处），per 为周期、tiles 为轮数，其后各轮与首轮模板一致：结构
  （op / PIPE / 操作数个数 / 标量）相同、GM 偏移关于 i 仿射、第 i 轮 buffer 槽位
  等于 i % stages（第 0 轮必须是 0）。

段切分规则（ADR 0015，多循环支持）：带 stage 的 sync 按「stage 从 0 重新计数」
分属各个循环；两个 stage-0 sync 的间距即周期 per；循环体起点从段界开始逐位尝试，
取最小的能通过整环结构校验的候选（把直写语句误吸进循环需要逐语句结构+仿射全部
巧合，且误吸的 stride-0 语句逐轮重放是幂等的，不产生错码）。段间由发射端插入
PIPE_ALL 全屏障，跨段依赖不需要手工 sync。

失败处理（ADR 0009）：重卷失败返回 ok=False，由 generate() 拒绝生成；
不允许展开生成（展开会丢槽位下标与 WAR，产生错码）。
"""

from __future__ import annotations

from ..model.core import BufRef, GmRef
from ..model.stmts import ComputeStmt, CopyStmt, SyncStmt


def reroll(kernel) -> tuple:
    """返回 (sections, ok)。

    sections 为段列表：空列表仅在 ok=False 时出现。每个循环段自带 mmad_init_first
    （第 0 轮 mmad 清 L0C，其后各轮改为累加）。
    非 ok：无法安全生成，调用方必须拒绝。
    """
    stmts = list(kernel.statements)
    staged = [(i, s.stage) for i, s in enumerate(stmts) if isinstance(s, SyncStmt) and s.stage is not None]
    if not staged:
        if _has_slot_reuse(stmts):
            return [], False
        return [("plain", 0, stmts)], True
    sections = []
    prev_end = 0
    si = 0
    while si < len(staged):
        parsed = _parse_loop_at(stmts, staged, si, prev_end)
        if parsed is None:
            return [], False
        tiles, per, start, init_first = parsed
        if start > prev_end:
            plain = stmts[prev_end:start]
            if _has_slot_reuse(plain):
                return [], False
            sections.append(("plain", prev_end, plain))
        sections.append(("loop", start, per, tiles, stmts[start : start + per], init_first))
        prev_end = start + tiles * per
        si = _staged_consumed(staged, si, prev_end)
    if prev_end < len(stmts):
        tail = stmts[prev_end:]
        if _has_slot_reuse(tail):
            return [], False
        sections.append(("plain", prev_end, tail))
    return sections, True


def _staged_consumed(staged, si, upto):
    n = si
    while n < len(staged) and staged[n][0] < upto:
        n += 1
    return n


def _parse_loop_at(stmts, staged, si, prev_end):
    """从 staged[si]（必须是 stage 0）起解析一个循环，返回 (tiles, per, start, init_first)。

    per = 第 0 轮首个 staged sync 到第 1 轮首个 staged sync 的间距（循环至少两轮）。
    tiles 候选取观察到的 stage 值 +1（从大到小）：整环校验（各轮窗口内 stage 必须等于
    轮号、超出 span 的 sync 一律不属于本循环）会拒绝把后续循环吸进来的候选——
    span 外的 stage-0 sync 属于下一个循环，span 内窗口错位直接拒绝。最大的合法
    tiles 即真实轮数；更小的候选即使通过也会让余下 stage≠0 的 sync 无法续 parse
    而整体 fail closed。
    """
    pos0, stage0 = staged[si]
    if stage0 != 0:
        return None
    nxt = None
    for p, s in staged[si + 1 :]:
        if s == 1:
            nxt = p
            break
    if nxt is None:
        return None
    per = nxt - pos0
    if per <= 0:
        return None
    for tiles in sorted({s + 1 for _, s in staged[si:] if s >= 1}, reverse=True):
        for start in range(prev_end, pos0 + 1):
            if start + tiles * per > len(stmts):
                continue
            got = _loop_valid(stmts, staged, start, per, tiles)
            if got is not None:
                return (tiles, per, start, got)
    return None


def _loop_valid(stmts, staged, start, per, tiles):
    """校验以 stmts[start:start+per] 为模板、tiles 轮的循环；返回 init_first 或 None。"""
    body = stmts[start : start + per]
    for pos, stage in staged:
        if start <= pos < start + tiles * per:
            if stage != (pos - start) // per:
                return None
        elif pos >= start + tiles * per:
            break
    strides = _strides(body, stmts[start + per : start + 2 * per])
    if strides is None:
        return None
    init_first = _uses_init_first(body, stmts[start + per : start + 2 * per])
    for i in range(2, tiles):
        group = stmts[start + i * per : start + (i + 1) * per]
        if not _group_matches(body, group, i, strides):
            return None
        init_first = init_first or _uses_init_first(body, group)
    return init_first


def _has_slot_reuse(stmts) -> bool:
    """直写段只允许「每个槽位至多写一次」。

    既读又写同一槽位的语句（就地 RMW）不算复用证据——那不是被抹平的循环；
    它会在发射端被「生产 PIPE 必须唯一」拒绝，并带更准确的报错。
    """
    written = set()
    for stmt in stmts:
        refs = []
        if isinstance(stmt, CopyStmt) and isinstance(stmt.dst, BufRef):
            refs = [stmt.dst]
        elif isinstance(stmt, ComputeStmt) and isinstance(stmt.dst, BufRef):
            read_slots = {(s.buffer.name, s.stage) for s in stmt.srcs if isinstance(s, BufRef)}
            if _mmad_accumulates(stmt):
                read_slots.add((stmt.dst.buffer.name, stmt.dst.stage))
            if (stmt.dst.buffer.name, stmt.dst.stage) not in read_slots:
                refs = [stmt.dst]
        for ref in refs:
            key = (ref.buffer.name, ref.stage)
            if key in written:
                return True
            written.add(key)
    return False


def _same_structure(a, b) -> bool:
    """模板与第 i 轮的结构性一致：类型、PIPE、op、操作数个数、标量、sync 的 on。"""
    if type(a) is not type(b):
        return False
    if isinstance(a, CopyStmt):
        return a.pipe is b.pipe and a.form == b.form and a.scalars == b.scalars
    if isinstance(a, ComputeStmt):
        if not (a.op == b.op and a.pipe is b.pipe and len(a.srcs) == len(b.srcs)):
            return False
        if a.scalars == b.scalars:
            return True
        return _mmad_init_follows(a, b)
    if isinstance(a, SyncStmt):
        return (
            a.producer is b.producer
            and a.consumer is b.consumer
            and [x.name for x in a.on] == [x.name for x in b.on]
        )
    return False


def _strides(body, group1):
    """从第 0/1 轮求每个 GM 引用的偏移 stride；结构不一致返回 None。"""
    strides = {}
    for pos, (tmpl, stmt) in enumerate(zip(body, group1)):
        if not _same_structure(tmpl, stmt):
            return None
        for ref_pos, (r0, r1) in enumerate(_ref_pairs(tmpl, stmt)):
            if isinstance(r0, GmRef):
                if not isinstance(r1, GmRef) or r0.param is not r1.param:
                    return None
                stride = r1.offset - r0.offset
                if stride < 0:
                    return None
                strides[(pos, ref_pos)] = stride
            elif isinstance(r0, BufRef):
                if r0.stage != 0:
                    return None
                if not isinstance(r1, BufRef) or r0.buffer is not r1.buffer or r1.stage != 1 % r0.buffer.stages:
                    return None
        if isinstance(stmt, SyncStmt):
            if (tmpl.stage is None) != (stmt.stage is None):
                return None
            if tmpl.stage is not None and stmt.stage != 1:
                return None
    return strides


def _group_matches(body, group, i, strides) -> bool:
    for pos, (tmpl, stmt) in enumerate(zip(body, group)):
        if not _same_structure(tmpl, stmt):
            return False
        for ref_pos, (r0, ri) in enumerate(_ref_pairs(tmpl, stmt)):
            if isinstance(r0, GmRef):
                if not isinstance(ri, GmRef) or ri.param is not r0.param:
                    return False
                if ri.offset != r0.offset + i * strides[(pos, ref_pos)]:
                    return False
            elif isinstance(r0, BufRef):
                if not isinstance(ri, BufRef) or ri.buffer is not r0.buffer:
                    return False
                if ri.stage != i % r0.buffer.stages:
                    return False
        if isinstance(stmt, SyncStmt):
            if tmpl.stage is None:
                if stmt.stage is not None:
                    return False
            elif stmt.stage != i:
                return False
    return True


def _mmad_accumulates(stmt) -> bool:
    return isinstance(stmt, ComputeStmt) and stmt.op == "mmad" and len(stmt.scalars) == 4 and stmt.scalars[-1] == 0


def _mmad_init_follows(first, later) -> bool:
    """第 0 轮清 L0C，后面的轮次只改 init 标志、其余标量不变。"""
    if first.op != "mmad" or len(first.scalars) != 4 or len(later.scalars) != 4:
        return False
    return first.scalars[:-1] == later.scalars[:-1] and first.scalars[-1] == 1 and later.scalars[-1] == 0


def _uses_init_first(body, group) -> bool:
    return any(_mmad_init_follows(a, b) for a, b in zip(body, group) if isinstance(a, ComputeStmt))


def _ref_pairs(tmpl, stmt):
    """按位置对齐两条同构语句的引用。"""
    if isinstance(stmt, CopyStmt):
        return [(tmpl.src, stmt.src), (tmpl.dst, stmt.dst)]
    if isinstance(stmt, ComputeStmt):
        return [(tmpl.dst, stmt.dst)] + list(zip(tmpl.srcs, stmt.srcs))
    return []
