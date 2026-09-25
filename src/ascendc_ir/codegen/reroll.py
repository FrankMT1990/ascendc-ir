# Copyright (c) 2026 Huawei Technologies Co., Ltd.
# This program is free software, you can redistribute it and/or modify it under the terms and conditions of
# CANN Open Software License Agreement Version 2.0 (the "License").
# Please refer to the License for details. You may not use this file except in compliance with the License.
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY, OR FITNESS FOR A PARTICULAR PURPOSE.
# See LICENSE in the root of the software repository for the full text of the License.

"""循环重卷：trace 期展开的语句序列，按仿射规律还原为单迭代循环体。

trace 期 `for i in range(TILES)` 被展开（ADR 0002），模型只保留平铺语句。
reroll 用 sync 的 stage（迭代号，见 ir-syntax.md）推断 TILES，再验证每轮迭代
与首轮模板一致：结构（op / PIPE / 操作数个数 / 标量）相同、GM 偏移关于 i 仿射、
buffer 槽位等于 i % stages。

失败处理（ADR 0009）：重卷失败返回 ok=False，由 generate() 拒绝生成；
不允许展开生成（展开会丢槽位下标与 WAR，产生错码）。
"""

from __future__ import annotations

from ..model.core import BufRef, GmRef
from ..model.stmts import ComputeStmt, CopyStmt, SyncStmt


def reroll(kernel) -> tuple:
    """返回 (tiles, body, ok)。

    tiles == 1 且 ok：无循环的直写形态（每个槽位至多写一次）。
    tiles > 1 且 ok：body 为单迭代模板（第 0 轮）。
    非 ok：无法安全生成，调用方必须拒绝。
    """
    stmts = list(kernel.statements)
    stages = [s.stage for s in stmts if isinstance(s, SyncStmt) and s.stage is not None]
    tiles = max(stages) + 1 if stages else 1
    if tiles <= 1:
        # 直写形态只允许「每个槽位至多写一次」；否则是被抹平了 stage 的循环
        if _has_slot_reuse(stmts):
            return 1, [], False
        return 1, stmts, True
    if not stmts or len(stmts) % tiles != 0:
        return tiles, [], False
    per = len(stmts) // tiles
    body = stmts[:per]
    strides = _strides(body, stmts[per : 2 * per])
    if strides is None:
        return tiles, [], False
    for i in range(2, tiles):
        if not _group_matches(body, stmts[i * per : (i + 1) * per], i, strides):
            return tiles, [], False
    return tiles, body, True


def _has_slot_reuse(stmts) -> bool:
    written = set()
    for stmt in stmts:
        refs = []
        if isinstance(stmt, CopyStmt) and isinstance(stmt.dst, BufRef):
            refs = [stmt.dst]
        elif isinstance(stmt, ComputeStmt) and isinstance(stmt.dst, BufRef):
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
        return a.pipe is b.pipe
    if isinstance(a, ComputeStmt):
        return a.op == b.op and a.pipe is b.pipe and len(a.srcs) == len(b.srcs) and a.scalars == b.scalars
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


def _ref_pairs(tmpl, stmt):
    """按位置对齐两条同构语句的引用。"""
    if isinstance(stmt, CopyStmt):
        return [(tmpl.src, stmt.src), (tmpl.dst, stmt.dst)]
    if isinstance(stmt, ComputeStmt):
        return [(tmpl.dst, stmt.dst)] + list(zip(tmpl.srcs, stmt.srcs))
    return []
