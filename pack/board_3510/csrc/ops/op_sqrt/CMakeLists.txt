if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/SKIP")
    message(STATUS "Skip op_sqrt")
    return()
endif()
set(OP_SQRT_KERNEL_SRCS ${CMAKE_CURRENT_SOURCE_DIR}/op_kernel/op_sqrt_kernel.cpp)
set(OP_SQRT_PLUGIN_SRCS ${CMAKE_CURRENT_SOURCE_DIR}/op_plugin/op_sqrt_plugin.cpp)
register_direct_launch_op(
    "${OP_SQRT_KERNEL_SRCS}" op_kernel
    "${OP_SQRT_PLUGIN_SRCS}" op_kernel
)
