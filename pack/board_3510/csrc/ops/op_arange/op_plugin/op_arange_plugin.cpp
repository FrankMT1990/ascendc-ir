#include <torch/all.h>
#include <torch/library.h>

#include "torch_npu/csrc/core/npu/NPUStream.h"
#include "torch_npu/csrc/framework/OpCommand.h"
#include "../op_kernel/op_arange_launch.h"

namespace ir_board {

TORCH_LIBRARY_FRAGMENT(ir_board, m)
{
    m.def("op_arange(Tensor unused) -> Tensor");
}

torch::Tensor op_arange_meta(const torch::Tensor& unused)
{

    return torch::empty({64}, torch::TensorOptions().dtype(torch::kFloat32).device(unused.device()));
}

TORCH_LIBRARY_IMPL(ir_board, Meta, m)
{
    m.impl("op_arange", op_arange_meta);
}

torch::Tensor op_arange_npu(const torch::Tensor& unused)
{
    const c10::OptionalDeviceGuard guard(unused.device());
    auto z = op_arange_meta(unused);
    auto stream = c10_npu::getCurrentNPUStream().stream(false);
    auto acl_call = [=]() -> int {
        launch_op_arange((GM_ADDR)z.data_ptr(), stream);
        return 0;
    };
    at_npu::native::OpCommand::RunOpApi("op_arange", acl_call);
    return z;
}

TORCH_LIBRARY_IMPL(ir_board, PrivateUse1, m)
{
    m.impl("op_arange", op_arange_npu);
}

}  // namespace ir_board
