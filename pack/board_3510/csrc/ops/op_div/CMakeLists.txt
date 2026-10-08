if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/SKIP")
    message(STATUS "Skip op_div")
    return()
endif()
set(OP_DIV_KERNEL_SRCS ${CMAKE_CURRENT_SOURCE_DIR}/op_kernel/op_div_kernel.cpp)
set(OP_DIV_PLUGIN_SRCS ${CMAKE_CURRENT_SOURCE_DIR}/op_plugin/op_div_plugin.cpp)
register_direct_launch_op(
    "${OP_DIV_KERNEL_SRCS}" op_kernel
    "${OP_DIV_PLUGIN_SRCS}" op_kernel
)
