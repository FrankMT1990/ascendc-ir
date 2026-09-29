set(LEAKYRELU_F32_KERNEL_SRCS ${CMAKE_CURRENT_SOURCE_DIR}/op_kernel/leakyrelu_f32_kernel.cpp)
set(LEAKYRELU_F32_PLUGIN_SRCS ${CMAKE_CURRENT_SOURCE_DIR}/op_plugin/leakyrelu_f32_plugin.cpp)

register_direct_launch_op(
    "${LEAKYRELU_F32_KERNEL_SRCS}" op_kernel
    "${LEAKYRELU_F32_PLUGIN_SRCS}" op_kernel
)
