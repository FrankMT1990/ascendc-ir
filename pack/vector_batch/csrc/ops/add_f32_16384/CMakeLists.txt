# add_f32_16384 self-registration
set(ADD_F32_16384_KERNEL_SRCS ${CMAKE_CURRENT_SOURCE_DIR}/op_kernel/add_f32_16384_kernel.cpp)
set(ADD_F32_16384_PLUGIN_SRCS ${CMAKE_CURRENT_SOURCE_DIR}/op_plugin/add_f32_16384_plugin.cpp)

register_direct_launch_op(
    "${ADD_F32_16384_KERNEL_SRCS}" op_kernel
    "${ADD_F32_16384_PLUGIN_SRCS}" op_kernel
)
