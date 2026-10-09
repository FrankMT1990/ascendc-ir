cmake_minimum_required(VERSION 3.16)
project(c1hw LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

set(NPU_ARCH "ascend950")
set(BISHENG_NPU_ARCH "dav-3510")

if(NOT DEFINED ENV{ASCEND_HOME_PATH} OR "$ENV{ASCEND_HOME_PATH}" STREQUAL "")
    message(FATAL_ERROR "ASCEND_HOME_PATH is not set")
endif()
set(ASCEND_HOME_PATH "$ENV{ASCEND_HOME_PATH}")

find_program(BISHENG bisheng
    HINTS
        "${ASCEND_HOME_PATH}/bin"
        "${ASCEND_HOME_PATH}/compiler/ccec_compiler/bin"
        "${ASCEND_HOME_PATH}/toolkit/bin"
    REQUIRED)

set(_INC_CANDIDATES
    "${ASCEND_HOME_PATH}/include"
    "${ASCEND_HOME_PATH}/x86_64-linux/include"
    "${ASCEND_HOME_PATH}/x86_64-linux/asc/include"
    "${ASCEND_HOME_PATH}/asc/include"
)
set(ASCEND_INCLUDE_DIRS "")
foreach(_inc ${_INC_CANDIDATES})
    if(EXISTS "${_inc}")
        list(APPEND ASCEND_INCLUDE_DIRS "${_inc}")
    endif()
endforeach()

set(_LIB_CANDIDATES
    "${ASCEND_HOME_PATH}/lib64"
    "${ASCEND_HOME_PATH}/x86_64-linux/lib64"
)
set(ASCEND_LIB_DIRS "")
foreach(_lib ${_LIB_CANDIDATES})
    if(EXISTS "${_lib}")
        list(APPEND ASCEND_LIB_DIRS "${_lib}")
    endif()
endforeach()

execute_process(COMMAND python3 -c "import torch; print(torch.utils.cmake_prefix_path)"
    OUTPUT_VARIABLE TORCH_PREFIX OUTPUT_STRIP_TRAILING_WHITESPACE)
list(INSERT CMAKE_PREFIX_PATH 0 "${TORCH_PREFIX}")
find_package(Torch REQUIRED)
execute_process(COMMAND python3 -c "import torch_npu, os; print(os.path.dirname(torch_npu.__file__))"
    OUTPUT_VARIABLE TORCH_NPU_DIR OUTPUT_STRIP_TRAILING_WHITESPACE)
set(TORCH_NPU_INCLUDE_DIRS "${TORCH_NPU_DIR}/include")
find_package(Python3 REQUIRED COMPONENTS Interpreter Development)

set(KERNEL_SRCS
    kernels/floor_exp_kernel.cpp
    kernels/floor_sigmoid_kernel.cpp
    kernels/floor_gelu_kernel.cpp
    kernels/floor_mish_kernel.cpp
    kernels/floor_masked_scale_kernel.cpp
    kernels/floor_swi_glu_kernel.cpp
    kernels/floor_foreach_addcdiv_kernel.cpp
)

set(KERNEL_INCLUDE_FLAGS "")
foreach(_dir ${ASCEND_INCLUDE_DIRS})
    list(APPEND KERNEL_INCLUDE_FLAGS "-I${_dir}")
endforeach()

set(KERNEL_OBJECTS "")
foreach(_src ${KERNEL_SRCS})
    get_filename_component(_name ${_src} NAME_WE)
    set(_obj ${CMAKE_BINARY_DIR}/bisheng/${_name}.o)
    add_custom_command(
        OUTPUT ${_obj}
        COMMAND ${CMAKE_COMMAND} -E make_directory ${CMAKE_BINARY_DIR}/bisheng
        COMMAND ${BISHENG} --npu-arch=${BISHENG_NPU_ARCH} -xasc -std=c++17 -fPIC -c ${CMAKE_SOURCE_DIR}/${_src} -o ${_obj} ${KERNEL_INCLUDE_FLAGS}
        DEPENDS ${CMAKE_SOURCE_DIR}/${_src}
        COMMENT "bisheng ${_name}"
        VERBATIM
    )
    list(APPEND KERNEL_OBJECTS ${_obj})
endforeach()

add_library(_C SHARED
    ${CMAKE_SOURCE_DIR}/plugin.cpp
    ${KERNEL_OBJECTS})
target_include_directories(_C PRIVATE
    ${Python3_INCLUDE_DIRS}
    ${TORCH_INCLUDE_DIRS}
    ${TORCH_NPU_INCLUDE_DIRS}
    ${ASCEND_INCLUDE_DIRS})
target_compile_definitions(_C PRIVATE TORCH_EXTENSION_NAME=_C)
target_compile_options(_C PRIVATE -O3 ${TORCH_CXX_FLAGS})
target_link_directories(_C PRIVATE ${ASCEND_LIB_DIRS} ${TORCH_NPU_DIR}/lib)
target_link_libraries(_C PRIVATE ${TORCH_LIBRARIES} torch_npu ascendcl ascendc_runtime dl)
set_target_properties(_C PROPERTIES
    PREFIX ""
    OUTPUT_NAME "_C.abi3"
    SUFFIX ".so"
    LIBRARY_OUTPUT_DIRECTORY ${CMAKE_SOURCE_DIR}/c1hw)
