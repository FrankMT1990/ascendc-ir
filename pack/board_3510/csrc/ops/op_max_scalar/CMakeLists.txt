if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/SKIP")
    message(STATUS "Skip op_max_scalar")
    return()
endif()
set(OP_MAX_SCALAR_KERNEL_SRCS ${CMAKE_CURRENT_SOURCE_DIR}/op_kernel/op_max_scalar_kernel.cpp)
set(OP_MAX_SCALAR_PLUGIN_SRCS ${CMAKE_CURRENT_SOURCE_DIR}/op_plugin/op_max_scalar_plugin.cpp)
register_direct_launch_op(
    "${OP_MAX_SCALAR_KERNEL_SRCS}" op_kernel
    "${OP_MAX_SCALAR_PLUGIN_SRCS}" op_kernel
)
