if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/SKIP")
    message(STATUS "Skip op_cast")
    return()
endif()
set(OP_CAST_KERNEL_SRCS ${CMAKE_CURRENT_SOURCE_DIR}/op_kernel/op_cast_kernel.cpp)
set(OP_CAST_PLUGIN_SRCS ${CMAKE_CURRENT_SOURCE_DIR}/op_plugin/op_cast_plugin.cpp)
register_direct_launch_op(
    "${OP_CAST_KERNEL_SRCS}" op_kernel
    "${OP_CAST_PLUGIN_SRCS}" op_kernel
)
