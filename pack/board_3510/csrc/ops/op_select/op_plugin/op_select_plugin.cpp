#include <torch/all.h>
#include <torch/library.h>

#include "torch_npu/csrc/core/npu/NPUStream.h"
#include "torch_npu/csrc/framework/OpCommand.h"
#include "../op_kernel/op_select_launch.h"

namespace ir_board {

TORCH_LIBRARY_FRAGMENT(ir_board, m)
{
    m.def("op_select(Tensor x, Tensor y, Tensor mask) -> Tensor");
}

torch::Tensor op_select_meta(const torch::Tensor& x, const torch::Tensor& y, const torch::Tensor& mask)
{

    TORCH_CHECK(x.scalar_type() == torch::kFloat32 && y.scalar_type() == torch::kFloat32, "dtype");
    TORCH_CHECK(mask.scalar_type() == torch::kUInt8, "mask dtype");
    TORCH_CHECK(x.numel() == 64 && y.numel() == 64 && mask.numel() == 32, "numel");
    return torch::empty({64}, x.options());
}

TORCH_LIBRARY_IMPL(ir_board, Meta, m)
{
    m.impl("op_select", op_select_meta);
}

torch::Tensor op_select_npu(const torch::Tensor& x, const torch::Tensor& y, const torch::Tensor& mask)
{
    const c10::OptionalDeviceGuard guard(x.device());
    auto z = op_select_meta(x, y, mask);
    auto stream = c10_npu::getCurrentNPUStream().stream(false);
    auto acl_call = [=]() -> int {
        launch_op_select((GM_ADDR)x.data_ptr(), (GM_ADDR)y.data_ptr(), (GM_ADDR)mask.data_ptr(), (GM_ADDR)z.data_ptr(), stream);
        return 0;
    };
    at_npu::native::OpCommand::RunOpApi("op_select", acl_call);
    return z;
}

TORCH_LIBRARY_IMPL(ir_board, PrivateUse1, m)
{
    m.impl("op_select", op_select_npu);
}

}  // namespace ir_board
