set(LLVM_LIBC_MPFR_INSTALL_PATH "" CACHE PATH "Path to where MPFR is installed (e.g. C:/src/install or ~/src/install)")

# MPFR versions older than this lack mpfr_{acos,asin,atan,cos,sin,tan}pi and
# mpfr_{exp2m1,exp10m1,log2p1,log10p1}. MPFRWrapper/MPCommon.cpp then falls back
# to composed, not correctly rounded, reference implementations.
set(LIBC_MPFR_RECOMMENDED_VERSION "4.2.0")
set(LIBC_MPFR_FALLBACK_FUNCTIONS
    "acospi, asinpi, atanpi, cospi, sinpi, tanpi, exp2m1, exp10m1, log2p1, log10p1")
option(LLVM_LIBC_MPFR_STRICT_VERSION
       "Fail configuration if the MPFR used by the libc math tests is older than ${LIBC_MPFR_RECOMMENDED_VERSION}"
       OFF)

if(LLVM_LIBC_MPFR_INSTALL_PATH)
  set(LIBC_TESTS_CAN_USE_MPFR TRUE)
elseif(LIBC_TARGET_OS_IS_GPU OR LLVM_LIBC_FULL_BUILD)
  # In full build mode, the MPFR library should be built using our own facilities,
  # which is currently not possible.
  set(LIBC_TESTS_CAN_USE_MPFR FALSE)
else()
  try_compile(
    LIBC_TESTS_CAN_USE_MPFR
    ${CMAKE_CURRENT_BINARY_DIR}
    SOURCES
      ${LIBC_SOURCE_DIR}/utils/MPFRWrapper/check_mpfr.cpp
    COMPILE_DEFINITIONS
      ${LIBC_COMPILE_OPTIONS_DEFAULT}
    LINK_LIBRARIES
      -lmpfr -lgmp -latomic
  )
endif()

if(LIBC_TESTS_CAN_USE_MPFR)
  set(mpfr_version_check_flags "")
  if(LLVM_LIBC_MPFR_INSTALL_PATH)
    set(mpfr_version_check_flags
        "-DINCLUDE_DIRECTORIES=${LLVM_LIBC_MPFR_INSTALL_PATH}/include")
  endif()
  set(mpfr_version_check_binary
      ${CMAKE_CURRENT_BINARY_DIR}/libc_mpfr_version_check.bin)
  file(REMOVE ${mpfr_version_check_binary})
  try_compile(
    mpfr_version_check_compiled
    ${CMAKE_CURRENT_BINARY_DIR}
    SOURCES
      ${LIBC_SOURCE_DIR}/utils/MPFRWrapper/check_mpfr_version.cpp
    COMPILE_DEFINITIONS
      ${LIBC_COMPILE_OPTIONS_DEFAULT}
    CMAKE_FLAGS
      ${mpfr_version_check_flags}
    COPY_FILE
      ${mpfr_version_check_binary}
  )
  set(LIBC_MPFR_VERSION "")
  if(mpfr_version_check_compiled AND EXISTS ${mpfr_version_check_binary})
    file(STRINGS ${mpfr_version_check_binary} mpfr_version_info
         REGEX "INFO:mpfr_version\\[[^]]*\\]" LIMIT_COUNT 1)
    if(mpfr_version_info MATCHES "INFO:mpfr_version\\[([0-9]+(\\.[0-9]+)*)")
      set(LIBC_MPFR_VERSION "${CMAKE_MATCH_1}")
    endif()
  endif()

  if(LLVM_LIBC_MPFR_STRICT_VERSION)
    set(mpfr_version_message_mode FATAL_ERROR)
  else()
    set(mpfr_version_message_mode WARNING)
  endif()

  if(NOT LIBC_MPFR_VERSION)
    message(${mpfr_version_message_mode}
      "Could not determine the MPFR version used by the libc math tests. "
      "MPFR >= ${LIBC_MPFR_RECOMMENDED_VERSION} is required for correctly "
      "rounded reference results for: ${LIBC_MPFR_FALLBACK_FUNCTIONS}.")
  elseif(LIBC_MPFR_VERSION VERSION_LESS LIBC_MPFR_RECOMMENDED_VERSION)
    message(${mpfr_version_message_mode}
      "MPFR ${LIBC_MPFR_VERSION} is older than ${LIBC_MPFR_RECOMMENDED_VERSION}. "
      "The libc math tests for ${LIBC_MPFR_FALLBACK_FUNCTIONS} will be checked "
      "against approximate, not correctly rounded, reference implementations. "
      "Install MPFR >= ${LIBC_MPFR_RECOMMENDED_VERSION} (or point "
      "LLVM_LIBC_MPFR_INSTALL_PATH at one) for full coverage.")
  else()
    message(STATUS "Using MPFR ${LIBC_MPFR_VERSION} for libc math tests")
  endif()
endif()
