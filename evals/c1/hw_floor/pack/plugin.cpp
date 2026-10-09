#include <torch/all.h>
#include <torch/library.h>

#include "torch_npu/csrc/core/npu/NPUStream.h"
#include "torch_npu/csrc/framework/OpCommand.h"

#ifndef GM_ADDR
#define GM_ADDR void*
#endif

extern "C" {
void launch_floor_exp(GM_ADDR x, GM_ADDR z, void* stream);
void launch_floor_sigmoid(GM_ADDR x, GM_ADDR z, void* stream);
void launch_floor_gelu(GM_ADDR x, GM_ADDR z, void* stream);
void launch_floor_mish(GM_ADDR x, GM_ADDR z, void* stream);
void launch_floor_masked_scale(GM_ADDR x, GM_ADDR mask, GM_ADDR z, void* stream);
void launch_floor_swi_glu(GM_ADDR x0, GM_ADDR x1, GM_ADDR z, void* stream);
void launch_floor_foreach_addcdiv(GM_ADDR x1, GM_ADDR x2, GM_ADDR x3, GM_ADDR z, void* stream);
}

namespace c1hw {

TORCH_LIBRARY_FRAGMENT(c1hw, m)
{
    m.def("floor_exp(Tensor x) -> Tensor");
    m.def("floor_sigmoid(Tensor x) -> Tensor");
    m.def("floor_gelu(Tensor x) -> Tensor");
    m.def("floor_mish(Tensor x) -> Tensor");
    m.def("floor_masked_scale(Tensor x, Tensor mask) -> Tensor");
    m.def("floor_swi_glu(Tensor x) -> Tensor");
    m.def("floor_foreach_addcdiv(Tensor x1, Tensor x2, Tensor x3) -> Tensor");
}

#define LAUNCH_1IN(name, numel_check)                                                    \
    torch::Tensor name##_meta(const torch::Tensor& x)                                    \
    {                                                                                    \
        TORCH_CHECK(x.scalar_type() == torch::kFloat32, "x dtype");                      \
        numel_check;                                                                     \
        return torch::empty_like(x);                                                     \
    }                                                                                    \
    TORCH_LIBRARY_IMPL(c1hw, Meta, m) { m.impl(#name, name##_meta); }                   \
    torch::Tensor name##_npu(const torch::Tensor& x)                                     \
    {                                                                                    \
        const c10::OptionalDeviceGuard guard(x.device());                               \
        auto z = name##_meta(x);                                                         \
        auto stream = c10_npu::getCurrentNPUStream().stream(false);                      \
        auto acl_call = [=]() -> int {                                                   \
            launch_##name((GM_ADDR)x.data_ptr(), (GM_ADDR)z.data_ptr(), stream);         \
            return 0;                                                                    \
        };                                                                               \
        at_npu::native::OpCommand::RunOpApi(#name, acl_call);                            \
        return z;                                                                        \
    }                                                                                    \
    TORCH_LIBRARY_IMPL(c1hw, PrivateUse1, m) { m.impl(#name, name##_npu); }

LAUNCH_1IN(floor_exp, TORCH_CHECK(x.numel() == 2048 * 2048, "numel"))
LAUNCH_1IN(floor_sigmoid, TORCH_CHECK(x.numel() == 2048 * 2048, "numel"))
LAUNCH_1IN(floor_gelu, TORCH_CHECK(x.numel() == 8192 * 8192, "numel"))
LAUNCH_1IN(floor_mish, TORCH_CHECK(x.numel() == 2048 * 2048, "numel"))

torch::Tensor floor_masked_scale_meta(const torch::Tensor& x, const torch::Tensor& mask)
{
    TORCH_CHECK(x.scalar_type() == torch::kFloat32, "x dtype");
    TORCH_CHECK(mask.scalar_type() == torch::kUInt8, "mask dtype");
    TORCH_CHECK(x.numel() == 2048 * 2048, "numel");
    TORCH_CHECK(mask.numel() == x.numel() * 4 / 8, "mask numel");
    return torch::empty_like(x);
}
TORCH_LIBRARY_IMPL(c1hw, Meta, m) { m.impl("floor_masked_scale", floor_masked_scale_meta); }
torch::Tensor floor_masked_scale_npu(const torch::Tensor& x, const torch::Tensor& mask)
{
    const c10::OptionalDeviceGuard guard(x.device());
    auto z = floor_masked_scale_meta(x, mask);
    auto stream = c10_npu::getCurrentNPUStream().stream(false);
    auto acl_call = [=]() -> int {
        launch_floor_masked_scale((GM_ADDR)x.data_ptr(), (GM_ADDR)mask.data_ptr(), (GM_ADDR)z.data_ptr(), stream);
        return 0;
    };
    at_npu::native::OpCommand::RunOpApi("floor_masked_scale", acl_call);
    return z;
}
TORCH_LIBRARY_IMPL(c1hw, PrivateUse1, m) { m.impl("floor_masked_scale", floor_masked_scale_npu); }

torch::Tensor floor_swi_glu_meta(const torch::Tensor& x)
{
    TORCH_CHECK(x.scalar_type() == torch::kFloat32, "x dtype");
    TORCH_CHECK(x.numel() == 2048 * 4096, "numel");
    auto sizes = x.sizes().vec();
    sizes.back() /= 2;
    return torch::empty(sizes, x.options());
}
TORCH_LIBRARY_IMPL(c1hw, Meta, m) { m.impl("floor_swi_glu", floor_swi_glu_meta); }
torch::Tensor floor_swi_glu_npu(const torch::Tensor& x)
{
    const c10::OptionalDeviceGuard guard(x.device());
    auto z = floor_swi_glu_meta(x);
    auto stream = c10_npu::getCurrentNPUStream().stream(false);
    const char* x0 = static_cast<const char*>(x.data_ptr());
    const char* x1 = x0 + 2048 * 2048 * sizeof(float);
    auto acl_call = [=]() -> int {
        launch_floor_swi_glu((GM_ADDR)x0, (GM_ADDR)x1, (GM_ADDR)z.data_ptr(), stream);
        return 0;
    };
    at_npu::native::OpCommand::RunOpApi("floor_swi_glu", acl_call);
    return z;
}
TORCH_LIBRARY_IMPL(c1hw, PrivateUse1, m) { m.impl("floor_swi_glu", floor_swi_glu_npu); }

torch::Tensor floor_foreach_addcdiv_meta(const torch::Tensor& x1, const torch::Tensor& x2, const torch::Tensor& x3)
{
    TORCH_CHECK(x1.scalar_type() == torch::kFloat32, "dtype");
    TORCH_CHECK(x1.numel() == 2 * 1024 * 1024, "numel");
    TORCH_CHECK(x2.numel() == x1.numel() && x3.numel() == x1.numel(), "numel");
    return torch::empty_like(x1);
}
TORCH_LIBRARY_IMPL(c1hw, Meta, m) { m.impl("floor_foreach_addcdiv", floor_foreach_addcdiv_meta); }
torch::Tensor floor_foreach_addcdiv_npu(const torch::Tensor& x1, const torch::Tensor& x2, const torch::Tensor& x3)
{
    const c10::OptionalDeviceGuard guard(x1.device());
    auto z = floor_foreach_addcdiv_meta(x1, x2, x3);
    auto stream = c10_npu::getCurrentNPUStream().stream(false);
    auto acl_call = [=]() -> int {
        launch_floor_foreach_addcdiv((GM_ADDR)x1.data_ptr(), (GM_ADDR)x2.data_ptr(),
                                     (GM_ADDR)x3.data_ptr(), (GM_ADDR)z.data_ptr(), stream);
        return 0;
    };
    at_npu::native::OpCommand::RunOpApi("floor_foreach_addcdiv", acl_call);
    return z;
}
TORCH_LIBRARY_IMPL(c1hw, PrivateUse1, m) { m.impl("floor_foreach_addcdiv", floor_foreach_addcdiv_npu); }

}  // namespace c1hw

#include <torch/extension.h>
PYBIND11_MODULE(TORCH_EXTENSION_NAME, m) {}
