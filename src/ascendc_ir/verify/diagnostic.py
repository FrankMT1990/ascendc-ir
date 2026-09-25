# Copyright (c) 2026 Huawei Technologies Co., Ltd.
# This program is free software, you can redistribute it and/or modify it under the terms and conditions of
# CANN Open Software License Agreement Version 2.0 (the "License").
# Please refer to the License for details. You may not use this file except in compliance with the License.
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY, OR FITNESS FOR A PARTICULAR PURPOSE.
# See LICENSE in the root of the software repository for the full text of the License.

"""结构化诊断。格式约定见 docs/spec/verifier-rules.md。"""

from __future__ import annotations

import json
from dataclasses import dataclass

from ..model.core import Callsite


@dataclass(frozen=True)
class Diagnostic:
    id: str
    severity: str  # v0.2 只有 "block"
    callsite: Callsite
    message: str
    suggestion: str
    knowledge: str | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "severity": self.severity,
            "callsite": self.callsite.to_dict(),
            "message": self.message,
            "suggestion": self.suggestion,
            "knowledge": self.knowledge,
        }


def diagnostics_to_json(diags: list) -> str:
    return json.dumps([d.to_dict() for d in diags], ensure_ascii=False, sort_keys=True, indent=2) + "\n"
