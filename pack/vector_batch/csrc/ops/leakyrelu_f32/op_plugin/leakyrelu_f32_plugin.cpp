#include <torch/all.h>
#include <torch/library.h>

#include "torch_npu/csrc/core/npu/NPUStream.h"
#include "torch_npu/csrc/framework/OpCommand.h"
#include "../op_kernel/leakyrelu_f32_launch.h"

namespace cann_bench {

constexpr int64_t kElementCount = 16384;

TORCH_LIBRARY_FRAGMENT(cann_bench, m)
{
    m.def("leakyrelu_f32(Tensor x) -> Tensor");
}

torch::Tensor leakyrelu_f32_meta(const torch::Tensor& x)
{
    TORCH_CHECK(x.scalar_type() == torch::kFloat32, "leakyrelu_f32: x must be float32");
    TORCH_CHECK(x.numel() == kElementCount, "leakyrelu_f32: expected 16384 elements");
    return torch::empty_like(x);
}

TORCH_LIBRARY_IMPL(cann_bench, Meta, m)
{
    m.impl("leakyrelu_f32", leakyrelu_f32_meta);
}

torch::Tensor leakyrelu_f32_npu(const torch::Tensor& x)
{
    const c10::OptionalDeviceGuard guard(x.device());
    TORCH_CHECK(x.is_contiguous(), "leakyrelu_f32: x must be contiguous");
    auto y = leakyrelu_f32_meta(x);
    auto stream = c10_npu::getCurrentNPUStream().stream(false);
    auto acl_call = [=]() -> int {
        launch_leakyrelu_f32_kernel((GM_ADDR)x.data_ptr(), (GM_ADDR)y.data_ptr(), stream);
        return 0;
    };
    at_npu::native::OpCommand::RunOpApi("LeakyReluF32", acl_call);
    return y;
}

TORCH_LIBRARY_IMPL(cann_bench, PrivateUse1, m)
{
    m.impl("leakyrelu_f32", leakyrelu_f32_npu);
}

}  // namespace cann_bench
