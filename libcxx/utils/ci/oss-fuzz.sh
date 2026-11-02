#!/bin/bash -eu

#
# This script runs the continuous fuzzing tests on OSS-Fuzz.
#
# It builds the libc++ headers and compiles every libcxx/test/libcxx/fuzzing/*.pass.cpp
# test into a standalone fuzzer named after the test (e.g. regex.pass.cpp -> ${OUT}/regex).
# It must be run from the root of the monorepo. See the "Fuzzing" section of
# libcxx/docs/TestingLibcxx.rst for how to run it locally.
#
# OSS-Fuzz provides the following environment variables:
#
#   CXX                 The C++ compiler to use (a recent Clang).
#   CXXFLAGS            Compiler flags, including the sanitizer and coverage flags
#                       (e.g. -fsanitize=address,fuzzer-no-link).
#   SANITIZER           The sanitizer being built (address, undefined, memory, ...).
#   OUT                 The directory where the fuzzer executables are written.
#   LIB_FUZZING_ENGINE  The flags used to link in the fuzzing engine (e.g. -fsanitize=fuzzer).
#
# The following environment variables are optional:
#
#   BUILD               The CMake build directory (defaults to cxx_build_dir).
#   INSTALL             The directory the headers are installed into (defaults to cxx_install_dir).
#

: "${CXX:?must be set to the C++ compiler}"
: "${CXXFLAGS?must be set (it may be empty)}"
: "${SANITIZER:?must be set (e.g. address or undefined)}"
: "${OUT:?must be set to the output directory for the fuzzers}"
: "${LIB_FUZZING_ENGINE:?must be set (e.g. -fsanitize=fuzzer)}"

if [[ ${SANITIZER} = *undefined* ]]; then
  CXXFLAGS="${CXXFLAGS} -fsanitize=unsigned-integer-overflow -fsanitize-trap=unsigned-integer-overflow"
fi

BUILD=${BUILD:-cxx_build_dir}
INSTALL=${INSTALL:-cxx_install_dir}
MONOREPO_ROOT=${PWD}

mkdir -p ${BUILD} ${OUT}
# Only the headers are built, so don't configure with the sanitizer flags: the
# CMake link checks would otherwise need the sanitizer runtimes.
CFLAGS= CXXFLAGS= cmake -S ${MONOREPO_ROOT}/runtimes -B ${BUILD} \
      -DLLVM_ENABLE_RUNTIMES="libcxx;libcxxabi;libunwind" \
      -DCMAKE_BUILD_TYPE=RelWithDebInfo \
      -DCMAKE_INSTALL_PREFIX="${INSTALL}"
cmake --build ${BUILD} --target install-cxx-headers

for test in libcxx/test/libcxx/fuzzing/*.pass.cpp; do
    exe="$(basename ${test})"
    exe="${exe%.pass.cpp}"
    ${CXX} ${CXXFLAGS} \
        -std=c++20 \
        -DLIBCPP_OSS_FUZZ \
        -D_LIBCPP_HAS_NO_VENDOR_AVAILABILITY_ANNOTATIONS \
        -nostdinc++ -cxx-isystem ${INSTALL}/include/c++/v1 \
        -lpthread -ldl \
        -o "${OUT}/${exe}" \
        ${test} \
        ${LIB_FUZZING_ENGINE}
done
