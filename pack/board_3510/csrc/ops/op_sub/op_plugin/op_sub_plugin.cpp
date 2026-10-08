#include <torch/all.h>
#include <torch/library.h>

#include "torch_npu/csrc/core/npu/NPUStream.h"
#include "torch_npu/csrc/framework/OpCommand.h"
#include "../op_kernel/op_sub_launch.h"

namespace ir_board {

TORCH_LIBRARY_FRAGMENT(ir_board, m)
{
    m.def("op_sub(Tensor x, Tensor y) -> Tensor");
}

torch::Tensor op_sub_meta(const torch::Tensor& x, const torch::Tensor& y)
{

    TORCH_CHECK(x.scalar_type() == torch::kFloat32, "x dtype");
    TORCH_CHECK(y.scalar_type() == torch::kFloat32, "y dtype");
    TORCH_CHECK(x.numel() == 64 && y.numel() == 64, "numel");
    return torch::empty({64}, x.options());
}

TORCH_LIBRARY_IMPL(ir_board, Meta, m)
{
    m.impl("op_sub", op_sub_meta);
}

torch::Tensor op_sub_npu(const torch::Tensor& x, const torch::Tensor& y)
{
    const c10::OptionalDeviceGuard guard(x.device());
    auto z = op_sub_meta(x, y);
    auto stream = c10_npu::getCurrentNPUStream().stream(false);
    auto acl_call = [=]() -> int {
        launch_op_sub((GM_ADDR)x.data_ptr(), (GM_ADDR)y.data_ptr(), (GM_ADDR)z.data_ptr(), stream);
        return 0;
    };
    at_npu::native::OpCommand::RunOpApi("op_sub", acl_call);
    return z;
}

TORCH_LIBRARY_IMPL(ir_board, PrivateUse1, m)
{
    m.impl("op_sub", op_sub_npu);
}

}  // namespace ir_board
