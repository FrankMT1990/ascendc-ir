# Copyright (c) 2026 Huawei Technologies Co., Ltd.
# This program is free software, you can redistribute it and/or modify it under the terms and conditions of
# CANN Open Software License Agreement Version 2.0 (the "License").
# Please refer to the License for details. You may not use this file except in compliance with the License.
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY, OR FITNESS FOR A PARTICULAR PURPOSE.
# See LICENSE in the root of the software repository for the full text of the License.

"""claims.md v2.8 的可执行判词。

匹配顺序：归档未测 → 不成立 → 未分类未测 → 成立 → 不确定。
m3 不参与。rel ≥ +0.20 只用于调度敏感任务。
噪声底未给出时，不因执行时间判输。
"""

from __future__ import annotations

from decimal import Decimal

HEADROOM_WIN = Decimal("0.20")


def _decimal(value: float) -> Decimal:
    """用十进制比较阈值。

    先量化到 1e-9，使已经算成 float 的 1.2/1.0 − 1（二进制是 0.1999…）
    仍落在 +0.20 上。0.19 不会被抬过这条线。
    """
    return Decimal(str(value)).quantize(Decimal("1E-9"))


def classify_headroom(t_baseline: float, t_hw: float | None) -> str:
    """空隙 h = T_baseline / T_HW − 1。没有 T_HW 时为未分类。"""
    if t_hw is None:
        return "unclassified"
    if t_baseline <= 0 or t_hw <= 0:
        raise ValueError("基线时延和硬件时延下界必须为正")
    headroom = _decimal(t_baseline) / _decimal(t_hw) - 1
    return "sensitive" if headroom >= HEADROOM_WIN else "bandwidth"


def judge_task(
    ir_success: int,
    control_success: int,
    *,
    rel: float | None = None,
    kind: str = "unclassified",
    noise_floor: float | None = None,
    archives_complete: bool = True,
) -> str:
    if not archives_complete:
        return "未测"
    if ir_success <= control_success - 2:
        return "不成立"
    equal_and_enough = ir_success == control_success and ir_success >= 3
    if (
        kind == "sensitive"
        and equal_and_enough
        and noise_floor is not None
        and rel is not None
        and _decimal(rel) <= -_decimal(noise_floor)
    ):
        return "不成立"
    counts_win = ir_success >= 3 and control_success >= 3 and ir_success >= control_success
    if counts_win and kind == "unclassified":
        return "未测"
    if counts_win and kind == "bandwidth":
        return "成立"
    if counts_win and kind == "sensitive" and rel is not None and _decimal(rel) >= HEADROOM_WIN:
        return "成立"
    return "不确定"


def _is_archive_gap(item: dict) -> bool:
    """归档未测。显式 archive_gap 优先。

    带宽或调度敏感任务的判词「未测」只来自归档不齐；调用方把 judge_task 的
    字符串放进字典时不必再带标志。未分类的「未测」仍要显式 archive_gap 才能
    算归档，避免和「没有 T_HW」混成同一类。
    """
    if item.get("archive_gap"):
        return True
    return item["verdict"] == "未测" and item.get("kind") != "unclassified"


def judge_load(tasks: list[dict]) -> str:
    """tasks 每项含 verdict、kind。kind 在归档未测时可为 None。

    带宽任务的「不确定」不挡住整组成立。未分类或归档未测会挡住成立。
    """
    if not tasks:
        return "未测"
    if all(item["verdict"] == "未测" and _is_archive_gap(item) for item in tasks):
        return "未测"
    if any(item["verdict"] == "不成立" for item in tasks):
        return "不成立"
    sensitive_ok = all(item["verdict"] == "成立" for item in tasks if item.get("kind") == "sensitive")
    no_unclassified = all(item.get("kind") != "unclassified" for item in tasks)
    no_archive_gap = all(not _is_archive_gap(item) for item in tasks)
    if sensitive_ok and no_unclassified and no_archive_gap:
        return "成立"
    return "不确定"
