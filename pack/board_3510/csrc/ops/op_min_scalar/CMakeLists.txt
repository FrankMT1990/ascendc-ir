if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/SKIP")
    message(STATUS "Skip op_min_scalar")
    return()
endif()
set(OP_MIN_SCALAR_KERNEL_SRCS ${CMAKE_CURRENT_SOURCE_DIR}/op_kernel/op_min_scalar_kernel.cpp)
set(OP_MIN_SCALAR_PLUGIN_SRCS ${CMAKE_CURRENT_SOURCE_DIR}/op_plugin/op_min_scalar_plugin.cpp)
register_direct_launch_op(
    "${OP_MIN_SCALAR_KERNEL_SRCS}" op_kernel
    "${OP_MIN_SCALAR_PLUGIN_SRCS}" op_kernel
)
