if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/SKIP")
    message(STATUS "Skip op_ceil")
    return()
endif()
set(OP_CEIL_KERNEL_SRCS ${CMAKE_CURRENT_SOURCE_DIR}/op_kernel/op_ceil_kernel.cpp)
set(OP_CEIL_PLUGIN_SRCS ${CMAKE_CURRENT_SOURCE_DIR}/op_plugin/op_ceil_plugin.cpp)
register_direct_launch_op(
    "${OP_CEIL_KERNEL_SRCS}" op_kernel
    "${OP_CEIL_PLUGIN_SRCS}" op_kernel
)
