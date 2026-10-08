if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/SKIP")
    message(STATUS "Skip op_mmad")
    return()
endif()
set(OP_MMAD_KERNEL_SRCS ${CMAKE_CURRENT_SOURCE_DIR}/op_kernel/op_mmad_kernel.cpp)
set(OP_MMAD_PLUGIN_SRCS ${CMAKE_CURRENT_SOURCE_DIR}/op_plugin/op_mmad_plugin.cpp)
register_direct_launch_op(
    "${OP_MMAD_KERNEL_SRCS}" op_kernel
    "${OP_MMAD_PLUGIN_SRCS}" op_kernel
)
