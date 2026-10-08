if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/SKIP")
    message(STATUS "Skip op_rint")
    return()
endif()
set(OP_RINT_KERNEL_SRCS ${CMAKE_CURRENT_SOURCE_DIR}/op_kernel/op_rint_kernel.cpp)
set(OP_RINT_PLUGIN_SRCS ${CMAKE_CURRENT_SOURCE_DIR}/op_plugin/op_rint_plugin.cpp)
register_direct_launch_op(
    "${OP_RINT_KERNEL_SRCS}" op_kernel
    "${OP_RINT_PLUGIN_SRCS}" op_kernel
)
