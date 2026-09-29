cmake_minimum_required(VERSION 3.16)
project(cann_bench LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

if(NOT DEFINED NPU_ARCH OR NPU_ARCH STREQUAL "")
    set(NPU_ARCH "ascend950")
endif()

# NPU_ARCH → Bisheng --npu-arch. This operator is RegBase and only builds for dav-3510.
if(NPU_ARCH STREQUAL "ascend910b" OR NPU_ARCH STREQUAL "ascend910_93")
    set(BISHENG_NPU_ARCH "dav-2201")
elseif(NPU_ARCH STREQUAL "ascend950")
    set(BISHENG_NPU_ARCH "dav-3510")
else()
    message(FATAL_ERROR "Unsupported NPU_ARCH=${NPU_ARCH}. Supported: ascend910b, ascend910_93, ascend950")
endif()
if(NOT BISHENG_NPU_ARCH STREQUAL "dav-3510")
    message(FATAL_ERROR "add_f32_16384 requires NPU_ARCH=ascend950 (dav-3510), got ${NPU_ARCH}")
endif()

include(${CMAKE_SOURCE_DIR}/cmake/ascend.cmake)
include(${CMAKE_SOURCE_DIR}/cmake/python.cmake)
include(${CMAKE_SOURCE_DIR}/cmake/torch.cmake)
include(${CMAKE_SOURCE_DIR}/cmake/torch_npu.cmake)
include(${CMAKE_SOURCE_DIR}/cmake/func.cmake)

set(ALL_KERNEL_SRCS "" CACHE INTERNAL "" FORCE)
set(ALL_PLUGIN_SRCS "" CACHE INTERNAL "" FORCE)
set(ALL_KERNEL_INCLUDE_DIRS "" CACHE INTERNAL "" FORCE)
set(ALL_PLUGIN_INCLUDE_DIRS "" CACHE INTERNAL "" FORCE)

add_subdirectory(csrc/ops)

if(ALL_KERNEL_SRCS STREQUAL "" OR ALL_PLUGIN_SRCS STREQUAL "")
    message(FATAL_ERROR "no direct-launch operator sources were registered")
endif()

set(_SAVED_CMAKE_CXX_COMPILER ${CMAKE_CXX_COMPILER})
set(CMAKE_CXX_COMPILER ${BISHENG})
set_source_files_properties(${ALL_KERNEL_SRCS} PROPERTIES
    LANGUAGE CXX
    COMPILE_FLAGS "--npu-arch=${BISHENG_NPU_ARCH} -xasc")
add_library(all_kernels_obj OBJECT ${ALL_KERNEL_SRCS})
target_include_directories(all_kernels_obj PRIVATE ${ALL_KERNEL_INCLUDE_DIRS} ${ASCEND_INCLUDE_DIRS})

set(CMAKE_CXX_COMPILER ${_SAVED_CMAKE_CXX_COMPILER})
add_library(all_plugins_obj OBJECT ${ALL_PLUGIN_SRCS})
target_include_directories(all_plugins_obj PRIVATE
    ${ALL_PLUGIN_INCLUDE_DIRS}
    ${TORCH_INCLUDE_DIRS}
    ${TORCH_NPU_INCLUDE_DIRS}
    ${ASCEND_INCLUDE_DIRS})
target_compile_options(all_plugins_obj PRIVATE -O3 ${TORCH_CXX_FLAGS})

set(EXTENSION_CPP ${CMAKE_SOURCE_DIR}/csrc/extension.cpp)
add_library(_C SHARED
    ${EXTENSION_CPP}
    $<TARGET_OBJECTS:all_kernels_obj>
    $<TARGET_OBJECTS:all_plugins_obj>)
target_include_directories(_C PRIVATE
    ${TORCH_INCLUDE_DIRS}
    ${TORCH_NPU_INCLUDE_DIRS}
    ${ASCEND_INCLUDE_DIRS})
target_compile_definitions(_C PRIVATE TORCH_EXTENSION_NAME=_C)
target_compile_options(_C PRIVATE ${TORCH_CXX_FLAGS})
target_link_directories(_C PRIVATE ${ASCEND_LIB_DIRS} ${TORCH_NPU_LIBRARIES})
target_link_libraries(_C PRIVATE
    ${TORCH_LIBRARIES}
    torch_npu
    ascendcl
    ascendc_runtime
    dl
)
set_target_properties(_C PROPERTIES
    PREFIX ""
    OUTPUT_NAME "_C.abi3"
    SUFFIX ".so"
    LIBRARY_OUTPUT_DIRECTORY ${CMAKE_SOURCE_DIR}/cann_bench
)
