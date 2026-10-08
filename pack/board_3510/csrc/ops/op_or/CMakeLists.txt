if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/SKIP")
    message(STATUS "Skip op_or")
    return()
endif()
set(OP_OR_KERNEL_SRCS ${CMAKE_CURRENT_SOURCE_DIR}/op_kernel/op_or_kernel.cpp)
set(OP_OR_PLUGIN_SRCS ${CMAKE_CURRENT_SOURCE_DIR}/op_plugin/op_or_plugin.cpp)
register_direct_launch_op(
    "${OP_OR_KERNEL_SRCS}" op_kernel
    "${OP_OR_PLUGIN_SRCS}" op_kernel
)
