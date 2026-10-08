if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/SKIP")
    message(STATUS "Skip op_floor")
    return()
endif()
set(OP_FLOOR_KERNEL_SRCS ${CMAKE_CURRENT_SOURCE_DIR}/op_kernel/op_floor_kernel.cpp)
set(OP_FLOOR_PLUGIN_SRCS ${CMAKE_CURRENT_SOURCE_DIR}/op_plugin/op_floor_plugin.cpp)
register_direct_launch_op(
    "${OP_FLOOR_KERNEL_SRCS}" op_kernel
    "${OP_FLOOR_PLUGIN_SRCS}" op_kernel
)
