#include <torch/all.h>
#include <torch/library.h>

#include "torch_npu/csrc/core/npu/NPUStream.h"
#include "torch_npu/csrc/framework/OpCommand.h"
#include "../op_kernel/op_repeat_reduce_sum_launch.h"

namespace ir_board {

TORCH_LIBRARY_FRAGMENT(ir_board, m)
{
    m.def("op_repeat_reduce_sum(Tensor x) -> Tensor");
}

torch::Tensor op_repeat_reduce_sum_meta(const torch::Tensor& x)
{

    TORCH_CHECK(x.scalar_type() == torch::kFloat32, "dtype");
    TORCH_CHECK(x.numel() == 64, "numel");
    return torch::empty({8}, x.options());
}

TORCH_LIBRARY_IMPL(ir_board, Meta, m)
{
    m.impl("op_repeat_reduce_sum", op_repeat_reduce_sum_meta);
}

torch::Tensor op_repeat_reduce_sum_npu(const torch::Tensor& x)
{
    const c10::OptionalDeviceGuard guard(x.device());
    auto z = op_repeat_reduce_sum_meta(x);
    auto stream = c10_npu::getCurrentNPUStream().stream(false);
    auto acl_call = [=]() -> int {
        launch_op_repeat_reduce_sum((GM_ADDR)x.data_ptr(), (GM_ADDR)z.data_ptr(), stream);
        return 0;
    };
    at_npu::native::OpCommand::RunOpApi("op_repeat_reduce_sum", acl_call);
    return z;
}

TORCH_LIBRARY_IMPL(ir_board, PrivateUse1, m)
{
    m.impl("op_repeat_reduce_sum", op_repeat_reduce_sum_npu);
}

}  // namespace ir_board
