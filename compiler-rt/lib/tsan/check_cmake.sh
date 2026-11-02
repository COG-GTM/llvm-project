#!/usr/bin/env bash
set -u
set -e

ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
LLVM_SRC="$( cd "$ROOT/../../../llvm" && pwd )"
if [ -f "$ROOT/llvm-build/build.ninja" ]; then
  cd $ROOT/llvm-build
else
  mkdir -p $ROOT/llvm-build
  cd $ROOT/llvm-build
  CC=clang CXX=clang++ cmake -G Ninja -DLLVM_ENABLE_PROJECTS=clang -DLLVM_ENABLE_RUNTIMES=compiler-rt -DLLVM_ENABLE_WERROR=ON -DCMAKE_BUILD_TYPE=Release -DLLVM_ENABLE_ASSERTIONS=ON "$LLVM_SRC"
fi
ninja
# Per-sanitizer check targets only exist in the runtimes sub-build.
ninja -C runtimes/runtimes-bins check-sanitizer
ninja -C runtimes/runtimes-bins check-tsan
ninja -C runtimes/runtimes-bins check-asan
ninja -C runtimes/runtimes-bins check-msan
ninja -C runtimes/runtimes-bins check-lsan
