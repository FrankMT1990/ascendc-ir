if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/SKIP")
    message(STATUS "Skip op_arange")
    return()
endif()
set(OP_ARANGE_KERNEL_SRCS ${CMAKE_CURRENT_SOURCE_DIR}/op_kernel/op_arange_kernel.cpp)
set(OP_ARANGE_PLUGIN_SRCS ${CMAKE_CURRENT_SOURCE_DIR}/op_plugin/op_arange_plugin.cpp)
register_direct_launch_op(
    "${OP_ARANGE_KERNEL_SRCS}" op_kernel
    "${OP_ARANGE_PLUGIN_SRCS}" op_kernel
)
