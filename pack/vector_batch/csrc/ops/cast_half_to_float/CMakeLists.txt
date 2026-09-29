set(CAST_HALF_TO_FLOAT_KERNEL_SRCS ${CMAKE_CURRENT_SOURCE_DIR}/op_kernel/cast_half_to_float_kernel.cpp)
set(CAST_HALF_TO_FLOAT_PLUGIN_SRCS ${CMAKE_CURRENT_SOURCE_DIR}/op_plugin/cast_half_to_float_plugin.cpp)

register_direct_launch_op(
    "${CAST_HALF_TO_FLOAT_KERNEL_SRCS}" op_kernel
    "${CAST_HALF_TO_FLOAT_PLUGIN_SRCS}" op_kernel
)
