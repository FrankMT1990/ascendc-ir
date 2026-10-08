if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/SKIP")
    message(STATUS "Skip op_log")
    return()
endif()
set(OP_LOG_KERNEL_SRCS ${CMAKE_CURRENT_SOURCE_DIR}/op_kernel/op_log_kernel.cpp)
set(OP_LOG_PLUGIN_SRCS ${CMAKE_CURRENT_SOURCE_DIR}/op_plugin/op_log_plugin.cpp)
register_direct_launch_op(
    "${OP_LOG_KERNEL_SRCS}" op_kernel
    "${OP_LOG_PLUGIN_SRCS}" op_kernel
)
