#include <torch/all.h>
#include <torch/library.h>

#include "torch_npu/csrc/core/npu/NPUStream.h"
#include "torch_npu/csrc/framework/OpCommand.h"
#include "../op_kernel/op_mmad_launch.h"

namespace ir_board {

TORCH_LIBRARY_FRAGMENT(ir_board, m)
{
    m.def("op_mmad(Tensor a, Tensor b) -> Tensor");
}

torch::Tensor op_mmad_meta(const torch::Tensor& a, const torch::Tensor& b)
{

    TORCH_CHECK(a.scalar_type() == torch::kFloat16 && b.scalar_type() == torch::kFloat16, "dtype");
    TORCH_CHECK(a.numel() == 1024 && b.numel() == 1024, "numel");
    return torch::empty({32, 32}, a.options().dtype(torch::kFloat32));
}

TORCH_LIBRARY_IMPL(ir_board, Meta, m)
{
    m.impl("op_mmad", op_mmad_meta);
}

torch::Tensor op_mmad_npu(const torch::Tensor& a, const torch::Tensor& b)
{
    const c10::OptionalDeviceGuard guard(a.device());
    auto z = op_mmad_meta(a, b);
    auto stream = c10_npu::getCurrentNPUStream().stream(false);
    auto acl_call = [=]() -> int {
        launch_op_mmad((GM_ADDR)a.data_ptr(), (GM_ADDR)b.data_ptr(), (GM_ADDR)z.data_ptr(), stream);
        return 0;
    };
    at_npu::native::OpCommand::RunOpApi("op_mmad", acl_call);
    return z;
}

TORCH_LIBRARY_IMPL(ir_board, PrivateUse1, m)
{
    m.impl("op_mmad", op_mmad_npu);
}

}  // namespace ir_board
