if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/SKIP")
    message(STATUS "Skip op_shiftright")
    return()
endif()
set(OP_SHIFTRIGHT_KERNEL_SRCS ${CMAKE_CURRENT_SOURCE_DIR}/op_kernel/op_shiftright_kernel.cpp)
set(OP_SHIFTRIGHT_PLUGIN_SRCS ${CMAKE_CURRENT_SOURCE_DIR}/op_plugin/op_shiftright_plugin.cpp)
register_direct_launch_op(
    "${OP_SHIFTRIGHT_KERNEL_SRCS}" op_kernel
    "${OP_SHIFTRIGHT_PLUGIN_SRCS}" op_kernel
)
