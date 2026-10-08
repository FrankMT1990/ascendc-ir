if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/SKIP")
    message(STATUS "Skip op_not")
    return()
endif()
set(OP_NOT_KERNEL_SRCS ${CMAKE_CURRENT_SOURCE_DIR}/op_kernel/op_not_kernel.cpp)
set(OP_NOT_PLUGIN_SRCS ${CMAKE_CURRENT_SOURCE_DIR}/op_plugin/op_not_plugin.cpp)
register_direct_launch_op(
    "${OP_NOT_KERNEL_SRCS}" op_kernel
    "${OP_NOT_PLUGIN_SRCS}" op_kernel
)
