# Copyright (c) 2026 Huawei Technologies Co., Ltd.
# This program is free software, you can redistribute it and/or modify it under the terms and conditions of
# CANN Open Software License Agreement Version 2.0 (the "License").
# Please refer to the License for details. You may not use this file except in compliance with the License.
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY, OR FITNESS FOR A PARTICULAR PURPOSE.
# See LICENSE in the root of the software repository for the full text of the License.

"""设备规格表加载。表结构见 docs/spec/device-spec.md。"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DeviceSpec:
    id: str
    npu_arch: int
    ub_usable_bytes: int
    l1_bytes: int
    align_bytes: int
    pipes: tuple
    event_ids: int
    pathways: dict


def load_device(device_id: str) -> DeviceSpec:
    path = Path(__file__).resolve().parent / f"{device_id}.toml"
    if not path.is_file():
        raise FileNotFoundError(f"未知设备 {device_id!r}：{path} 不存在")
    with path.open("rb") as f:
        raw = tomllib.load(f)
    dev = raw["device"]
    mem = raw["memory"]
    pipes = raw["pipes"]
    pathways = raw["pathways"]
    return DeviceSpec(
        id=dev["id"],
        npu_arch=dev["npu_arch"],
        ub_usable_bytes=mem["ub_usable_bytes"],
        l1_bytes=mem["l1_bytes"],
        align_bytes=mem["align_bytes"],
        pipes=tuple(pipes["available"]),
        event_ids=pipes["event_ids"],
        pathways={tuple(k.split("->")): v for k, v in pathways.items()},
    )
