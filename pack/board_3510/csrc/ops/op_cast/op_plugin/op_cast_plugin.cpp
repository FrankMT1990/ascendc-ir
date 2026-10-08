#include <torch/all.h>
#include <torch/library.h>

#include "torch_npu/csrc/core/npu/NPUStream.h"
#include "torch_npu/csrc/framework/OpCommand.h"
#include "../op_kernel/op_cast_launch.h"

namespace ir_board {

TORCH_LIBRARY_FRAGMENT(ir_board, m)
{
    m.def("op_cast(Tensor x) -> Tensor");
}

torch::Tensor op_cast_meta(const torch::Tensor& x)
{

    TORCH_CHECK(x.scalar_type() == torch::kFloat16, "dtype");
    TORCH_CHECK(x.numel() == 64, "numel");
    return torch::empty({64}, x.options().dtype(torch::kFloat32));
}

TORCH_LIBRARY_IMPL(ir_board, Meta, m)
{
    m.impl("op_cast", op_cast_meta);
}

torch::Tensor op_cast_npu(const torch::Tensor& x)
{
    const c10::OptionalDeviceGuard guard(x.device());
    auto z = op_cast_meta(x);
    auto stream = c10_npu::getCurrentNPUStream().stream(false);
    auto acl_call = [=]() -> int {
        launch_op_cast((GM_ADDR)x.data_ptr(), (GM_ADDR)z.data_ptr(), stream);
        return 0;
    };
    at_npu::native::OpCommand::RunOpApi("op_cast", acl_call);
    return z;
}

TORCH_LIBRARY_IMPL(ir_board, PrivateUse1, m)
{
    m.impl("op_cast", op_cast_npu);
}

}  // namespace ir_board
