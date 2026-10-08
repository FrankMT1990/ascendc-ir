if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/SKIP")
    message(STATUS "Skip op_abs")
    return()
endif()
set(OP_ABS_KERNEL_SRCS ${CMAKE_CURRENT_SOURCE_DIR}/op_kernel/op_abs_kernel.cpp)
set(OP_ABS_PLUGIN_SRCS ${CMAKE_CURRENT_SOURCE_DIR}/op_plugin/op_abs_plugin.cpp)
register_direct_launch_op(
    "${OP_ABS_KERNEL_SRCS}" op_kernel
    "${OP_ABS_PLUGIN_SRCS}" op_kernel
)
