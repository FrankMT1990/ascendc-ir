#include <torch/all.h>
#include <torch/library.h>

#include "torch_npu/csrc/core/npu/NPUStream.h"
#include "torch_npu/csrc/framework/OpCommand.h"
#include "../op_kernel/cast_half_to_float_launch.h"

namespace cann_bench {

constexpr int64_t kElementCount = 1024;

TORCH_LIBRARY_FRAGMENT(cann_bench, m)
{
    m.def("cast_half_to_float(Tensor x) -> Tensor");
}

torch::Tensor cast_half_to_float_meta(const torch::Tensor& x)
{
    TORCH_CHECK(x.scalar_type() == torch::kFloat16, "cast_half_to_float: x must be float16");
    TORCH_CHECK(x.numel() == kElementCount, "cast_half_to_float: expected 1024 elements");
    return torch::empty(x.sizes(), x.options().dtype(torch::kFloat32));
}

TORCH_LIBRARY_IMPL(cann_bench, Meta, m)
{
    m.impl("cast_half_to_float", cast_half_to_float_meta);
}

torch::Tensor cast_half_to_float_npu(const torch::Tensor& x)
{
    const c10::OptionalDeviceGuard guard(x.device());
    TORCH_CHECK(x.is_contiguous(), "cast_half_to_float: x must be contiguous");
    auto y = cast_half_to_float_meta(x);
    auto stream = c10_npu::getCurrentNPUStream().stream(false);
    auto acl_call = [=]() -> int {
        launch_cast_half_to_float_kernel((GM_ADDR)x.data_ptr(), (GM_ADDR)y.data_ptr(), stream);
        return 0;
    };
    at_npu::native::OpCommand::RunOpApi("CastHalfToFloat", acl_call);
    return y;
}

TORCH_LIBRARY_IMPL(cann_bench, PrivateUse1, m)
{
    m.impl("cast_half_to_float", cast_half_to_float_npu);
}

}  // namespace cann_bench
