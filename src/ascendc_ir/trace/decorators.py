# Copyright (c) 2026 Huawei Technologies Co., Ltd.
# This program is free software, you can redistribute it and/or modify it under the terms and conditions of
# CANN Open Software License Agreement Version 2.0 (the "License").
# Please refer to the License for details. You may not use this file except in compliance with the License.
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY, OR FITNESS FOR A PARTICULAR PURPOSE.
# See LICENSE in the root of the software repository for the full text of the License.

"""@kernel 装饰器：trace 出 Kernel 模型。"""

from __future__ import annotations

import functools
import inspect

from ..model.core import GmParam
from .api import GmParamSpec
from .builder import TraceBuilder, _active


def kernel(device: str):
    """声明内核与目标设备。被装饰函数调用 `.trace()` 得到 Kernel 模型。"""

    def wrap(fn):
        sig = inspect.signature(fn)

        @functools.wraps(fn)
        def launcher(*args, **kwargs):
            raise NotImplementedError("v0.2 只支持 .trace()；启动与代码生成在后续版本")

        def trace():
            builder = TraceBuilder(fn.__name__, device)
            token = _active.set(builder)
            try:
                params = []
                for pname, parameter in sig.parameters.items():
                    spec = parameter.annotation
                    if not isinstance(spec, GmParamSpec):
                        raise TypeError(f"参数 {pname} 的注解必须是 gmptr(<dtype>)，得到 {spec!r}")
                    p = GmParam(pname, spec.dtype)
                    builder.kernel.params.append(p)
                    params.append(p)
                fn(*params)
            finally:
                _active.reset(token)
            return builder.kernel

        launcher.trace = trace
        return launcher

    return wrap
