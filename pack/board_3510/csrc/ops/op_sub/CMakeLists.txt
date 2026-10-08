if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/SKIP")
    message(STATUS "Skip op_sub")
    return()
endif()
set(OP_SUB_KERNEL_SRCS ${CMAKE_CURRENT_SOURCE_DIR}/op_kernel/op_sub_kernel.cpp)
set(OP_SUB_PLUGIN_SRCS ${CMAKE_CURRENT_SOURCE_DIR}/op_plugin/op_sub_plugin.cpp)
register_direct_launch_op(
    "${OP_SUB_KERNEL_SRCS}" op_kernel
    "${OP_SUB_PLUGIN_SRCS}" op_kernel
)
