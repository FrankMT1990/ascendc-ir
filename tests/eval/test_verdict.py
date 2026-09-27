# Copyright (c) 2026 Huawei Technologies Co., Ltd.
# This program is free software, you can redistribute it and/or modify it under the terms and conditions of
# CANN Open Software License Agreement Version 2.0 (the "License").
# Please refer to the License for details. You may not use this file except in compliance with the License.
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY, OR FITNESS FOR A PARTICULAR PURPOSE.
# See LICENSE in the root of the software repository for the full text of the License.

"""v2.8 判词的接受与拒绝案例。"""

import pytest

from ascendc_ir.eval import classify_headroom, judge_load, judge_task
from evals.m4_m5.run_injection import single_point_shortfall


def test_headroom_classes():
    assert classify_headroom(1.3, 1.0) == "sensitive"
    assert classify_headroom(1.2, 1.0) == "sensitive"
    assert classify_headroom(1.19, 1.0) == "bandwidth"
    assert classify_headroom(1.0, None) == "unclassified"


def test_headroom_rejects_non_positive():
    with pytest.raises(ValueError):
        classify_headroom(1.0, 0.0)


def test_success_deficit_of_two_loses_before_class():
    assert judge_task(3, 5, kind="unclassified") == "不成立"
    assert judge_task(3, 5, kind="bandwidth", rel=0.5) == "不成立"


def test_one_success_short_is_uncertain():
    assert judge_task(4, 5, kind="sensitive", rel=0.4) == "不确定"
    assert judge_task(4, 5, kind="bandwidth") == "不确定"


def test_bandwidth_win_ignores_rel():
    assert judge_task(5, 5, kind="bandwidth", rel=-0.1) == "成立"
    assert judge_task(5, 4, kind="bandwidth", rel=0.0) == "成立"


def test_sensitive_needs_twenty_percent():
    assert judge_task(5, 5, kind="sensitive", rel=0.20) == "成立"
    assert judge_task(5, 5, kind="sensitive", rel=1.2 / 1.0 - 1) == "成立"
    assert judge_task(5, 5, kind="sensitive", rel=0.19) == "不确定"


def test_noise_floor_loss_only_when_sealed():
    assert judge_task(5, 5, kind="sensitive", rel=-0.08, noise_floor=0.05) == "不成立"
    assert judge_task(5, 5, kind="sensitive", rel=-0.08, noise_floor=None) == "不确定"


def test_unclassified_with_enough_successes_is_unmeasured():
    assert judge_task(5, 5, kind="unclassified", rel=0.5) == "未测"


def test_incomplete_archive_is_unmeasured():
    assert judge_task(0, 5, archives_complete=False) == "未测"


def test_load_bandwidth_uncertainty_does_not_block():
    tasks = [
        {"verdict": "成立", "kind": "sensitive"},
        {"verdict": "不确定", "kind": "bandwidth"},
    ]
    assert judge_load(tasks) == "成立"


def test_load_fails_if_any_task_fails():
    tasks = [
        {"verdict": "成立", "kind": "sensitive"},
        {"verdict": "不成立", "kind": "bandwidth"},
    ]
    assert judge_load(tasks) == "不成立"


def test_load_unclassified_blocks_win():
    tasks = [
        {"verdict": "成立", "kind": "bandwidth"},
        {"verdict": "未测", "kind": "unclassified"},
    ]
    assert judge_load(tasks) == "不确定"


def test_load_all_archive_gaps_are_unmeasured():
    tasks = [{"verdict": "未测", "kind": None, "archive_gap": True}]
    assert judge_load(tasks) == "未测"


def test_load_archive_gap_survives_task_string():
    """judge_task 只返回「未测」时，负载级仍要认出归档不齐。"""
    bandwidth_gap = {
        "verdict": judge_task(5, 5, kind="bandwidth", archives_complete=False),
        "kind": "bandwidth",
    }
    assert judge_load([bandwidth_gap, dict(bandwidth_gap)]) == "未测"
    win = {"verdict": judge_task(5, 5, kind="sensitive", rel=0.25), "kind": "sensitive"}
    assert judge_load([win, bandwidth_gap]) == "不确定"
    sensitive_gap = {
        "verdict": judge_task(5, 5, kind="sensitive", archives_complete=False),
        "kind": "sensitive",
    }
    assert judge_load([sensitive_gap]) == "未测"


def test_single_point_count_ignores_multi_rule_samples():
    injected = [
        {"expect_ids": ["V001"]},
        {"expect_ids": ["V001"]},
        {"expect_ids": ["V001", "V004"]},
        {"expect_ids": ["V004"]},
        {"expect_ids": ["V004"]},
    ]
    short = single_point_shortfall(injected)
    assert short["V001"] == 2
    assert short["V004"] == 2
    assert "V008" not in single_point_shortfall([{"expect_ids": ["V008"]}])
