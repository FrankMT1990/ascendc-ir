#include <torch/all.h>
#include <torch/library.h>

#include "torch_npu/csrc/core/npu/NPUStream.h"
#include "torch_npu/csrc/framework/OpCommand.h"
#include "../op_kernel/reduce_sum_f32_launch.h"

namespace cann_bench {

constexpr int64_t kInCount = 256;
constexpr int64_t kOutCount = 8;

TORCH_LIBRARY_FRAGMENT(cann_bench, m)
{
    m.def("reduce_sum_f32(Tensor x) -> Tensor");
}

torch::Tensor reduce_sum_f32_meta(const torch::Tensor& x)
{
    TORCH_CHECK(x.scalar_type() == torch::kFloat32, "reduce_sum_f32: x must be float32");
    TORCH_CHECK(x.numel() == kInCount, "reduce_sum_f32: expected 256 elements");
    return torch::empty({kOutCount}, x.options());
}

TORCH_LIBRARY_IMPL(cann_bench, Meta, m)
{
    m.impl("reduce_sum_f32", reduce_sum_f32_meta);
}

torch::Tensor reduce_sum_f32_npu(const torch::Tensor& x)
{
    const c10::OptionalDeviceGuard guard(x.device());
    TORCH_CHECK(x.is_contiguous(), "reduce_sum_f32: x must be contiguous");
    auto y = reduce_sum_f32_meta(x);
    auto stream = c10_npu::getCurrentNPUStream().stream(false);
    auto acl_call = [=]() -> int {
        launch_reduce_sum_f32_kernel((GM_ADDR)x.data_ptr(), (GM_ADDR)y.data_ptr(), stream);
        return 0;
    };
    at_npu::native::OpCommand::RunOpApi("ReduceSumF32", acl_call);
    return y;
}

TORCH_LIBRARY_IMPL(cann_bench, PrivateUse1, m)
{
    m.impl("reduce_sum_f32", reduce_sum_f32_npu);
}

}  // namespace cann_bench
