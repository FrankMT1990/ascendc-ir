#include <torch/all.h>
#include <torch/library.h>

#include "torch_npu/csrc/core/npu/NPUStream.h"
#include "torch_npu/csrc/framework/OpCommand.h"
#include "../op_kernel/add_f32_16384_launch.h"

namespace cann_bench {

constexpr int64_t kElementCount = 16384;

TORCH_LIBRARY_FRAGMENT(cann_bench, m)
{
    m.def("add_f32_16384(Tensor x, Tensor y) -> Tensor");
}

torch::Tensor add_f32_16384_meta(const torch::Tensor& x, const torch::Tensor& y)
{
    TORCH_CHECK(x.scalar_type() == torch::kFloat32, "add_f32_16384: x must be float32");
    TORCH_CHECK(y.scalar_type() == torch::kFloat32, "add_f32_16384: y must be float32");
    TORCH_CHECK(x.sizes() == y.sizes(), "add_f32_16384: x and y must have the same shape");
    TORCH_CHECK(x.numel() == kElementCount, "add_f32_16384: expected 16384 elements");
    return torch::empty_like(x);
}

TORCH_LIBRARY_IMPL(cann_bench, Meta, m)
{
    m.impl("add_f32_16384", add_f32_16384_meta);
}

torch::Tensor add_f32_16384_npu(const torch::Tensor& x, const torch::Tensor& y)
{
    const c10::OptionalDeviceGuard guard(x.device());
    TORCH_CHECK(x.is_contiguous(), "add_f32_16384: x must be contiguous");
    TORCH_CHECK(y.is_contiguous(), "add_f32_16384: y must be contiguous");
    TORCH_CHECK(x.device() == y.device(), "add_f32_16384: x and y must be on the same device");
    auto z = add_f32_16384_meta(x, y);
    auto stream = c10_npu::getCurrentNPUStream().stream(false);
    auto x_ptr = (GM_ADDR)x.data_ptr();
    auto y_ptr = (GM_ADDR)y.data_ptr();
    auto z_ptr = (GM_ADDR)z.data_ptr();

    auto acl_call = [=]() -> int {
        launch_add_f32_16384_kernel(x_ptr, y_ptr, z_ptr, stream);
        return 0;
    };
    at_npu::native::OpCommand::RunOpApi("AddF32_16384", acl_call);
    return z;
}

TORCH_LIBRARY_IMPL(cann_bench, PrivateUse1, m)
{
    m.impl("add_f32_16384", add_f32_16384_npu);
}

}  // namespace cann_bench
