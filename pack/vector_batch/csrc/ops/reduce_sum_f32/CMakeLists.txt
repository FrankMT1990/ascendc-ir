set(REDUCE_SUM_F32_KERNEL_SRCS ${CMAKE_CURRENT_SOURCE_DIR}/op_kernel/reduce_sum_f32_kernel.cpp)
set(REDUCE_SUM_F32_PLUGIN_SRCS ${CMAKE_CURRENT_SOURCE_DIR}/op_plugin/reduce_sum_f32_plugin.cpp)

register_direct_launch_op(
    "${REDUCE_SUM_F32_KERNEL_SRCS}" op_kernel
    "${REDUCE_SUM_F32_PLUGIN_SRCS}" op_kernel
)
