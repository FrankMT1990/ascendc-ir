if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/SKIP")
    message(STATUS "Skip op_shiftleft_scalar")
    return()
endif()
set(OP_SHIFTLEFT_SCALAR_KERNEL_SRCS ${CMAKE_CURRENT_SOURCE_DIR}/op_kernel/op_shiftleft_scalar_kernel.cpp)
set(OP_SHIFTLEFT_SCALAR_PLUGIN_SRCS ${CMAKE_CURRENT_SOURCE_DIR}/op_plugin/op_shiftleft_scalar_plugin.cpp)
register_direct_launch_op(
    "${OP_SHIFTLEFT_SCALAR_KERNEL_SRCS}" op_kernel
    "${OP_SHIFTLEFT_SCALAR_PLUGIN_SRCS}" op_kernel
)
