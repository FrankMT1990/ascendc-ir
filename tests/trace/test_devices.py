# Copyright (c) 2026 Huawei Technologies Co., Ltd.
# This program is free software, you can redistribute it and/or modify it under the terms and conditions of
# CANN Open Software License Agreement Version 2.0 (the "License").
# Please refer to the License for details. You may not use this file except in compliance with the License.
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY, OR FITNESS FOR A PARTICULAR PURPOSE.
# See LICENSE in the root of the software repository for the full text of the License.

"""设备表加载与字段语义。"""

import pytest
from ascendc_ir.devices import load_device


def test_load_ascend950pr():
    dev = load_device("ascend950pr")
    assert dev.id == "ascend950pr"
    assert dev.npu_arch == 3510
    assert dev.ub_usable_bytes == 253952
    assert dev.align_bytes == 32
    assert dev.event_ids == 8
    assert dev.pathways[("gm", "ubuf")] == "mte2"
    assert dev.pathways[("ubuf", "gm")] == "mte3"
    assert "mte2" in dev.pipes


def test_unknown_device_fails_closed():
    with pytest.raises(FileNotFoundError):
        load_device("no_such_device")
