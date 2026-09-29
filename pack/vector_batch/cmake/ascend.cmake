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

set(_ASCEND_INCLUDE_CANDIDATES
    "${ASCEND_HOME_PATH}/include"
    "${ASCEND_HOME_PATH}/aarch64-linux/include"
    "${ASCEND_HOME_PATH}/arm64-linux/include"
    "${ASCEND_HOME_PATH}/x86_64-linux/include"
    "${ASCEND_HOME_PATH}/compiler/ascendc/include"
    "${ASCEND_HOME_PATH}/compiler/include"
)
set(ASCEND_INCLUDE_DIRS "")
foreach(_inc ${_ASCEND_INCLUDE_CANDIDATES})
    if(EXISTS "${_inc}")
        list(APPEND ASCEND_INCLUDE_DIRS "${_inc}")
    endif()
endforeach()

set(_ASCEND_LIB_CANDIDATES
    "${ASCEND_HOME_PATH}/lib64"
    "${ASCEND_HOME_PATH}/aarch64-linux/lib64"
    "${ASCEND_HOME_PATH}/arm64-linux/lib64"
    "${ASCEND_HOME_PATH}/x86_64-linux/lib64"
)
set(ASCEND_LIB_DIRS "")
foreach(_lib ${_ASCEND_LIB_CANDIDATES})
    if(EXISTS "${_lib}")
        list(APPEND ASCEND_LIB_DIRS "${_lib}")
    endif()
endforeach()

message(STATUS "BISHENG: ${BISHENG}")
message(STATUS "ASCEND_HOME_PATH: ${ASCEND_HOME_PATH}")
