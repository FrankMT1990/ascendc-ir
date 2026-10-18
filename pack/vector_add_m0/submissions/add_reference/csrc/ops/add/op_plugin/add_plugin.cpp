/**
 * Copyright (c) 2026 Huawei Technologies Co., Ltd.
 * This file is part of the M0 handwritten-reference submission (see ADR 0014).
 * See LICENSE in the root of the software repository for the full text of the License.
 */

/*!
 * \file add_plugin.cpp
 * \brief M0 候选（手写对照版）的 torch 绑定：cann_bench.add(x, y) -> Tensor。
 *        冻结 shape：16384 个 f32；单核直调，无 tiling、无多核切分。
 */

#include <ATen/Operators.h>
#include <torch/all.h>
#include <torch/library.h>
#include "torch_npu/csrc/core/npu/NPUStream.h"
#include "torch_npu/csrc/framework/OpCommand.h"

#include "../op_kernel/add_launch.h"

namespace cann_bench {

constexpr int64_t FROZEN_NUMEL = 16384; // TILE=2048 × TILES=8

TORCH_LIBRARY_FRAGMENT(cann_bench, m)
{
    m.def("add(Tensor x, Tensor y) -> Tensor");
}

torch::Tensor add_meta(const torch::Tensor &x, const torch::Tensor &y)
{
    TORCH_CHECK(x.sizes() == y.sizes(), "The shapes of x and y must be the same.");
    return torch::empty_like(x);
}

TORCH_LIBRARY_IMPL(cann_bench, Meta, m)
{
    m.impl("add", add_meta);
}

torch::Tensor add_npu(const torch::Tensor &x, const torch::Tensor &y)
{
    const c10::OptionalDeviceGuard guard(x.device());
    TORCH_CHECK(x.scalar_type() == torch::kFloat32, "frozen shape: float32 only");
    TORCH_CHECK(x.numel() == FROZEN_NUMEL, "frozen shape: 16384 elements only");
    auto z = add_meta(x, y);
    auto stream = c10_npu::getCurrentNPUStream().stream(false);
    auto x_ptr = (GM_ADDR)x.data_ptr();
    auto y_ptr = (GM_ADDR)y.data_ptr();
    auto z_ptr = (GM_ADDR)z.data_ptr();

    auto acl_call = [=]() -> int {
        launch_add_custom(x_ptr, y_ptr, z_ptr, stream);
        return 0;
    };
    at_npu::native::OpCommand::RunOpApi("AddCustom", acl_call);
    return z;
}

TORCH_LIBRARY_IMPL(cann_bench, PrivateUse1, m)
{
    m.impl("add", add_npu);
}

} // namespace cann_bench
