// Checks that the TLS shadow arrays referenced by instrumented code are exactly
// as large as the ones defined by the runtime. The instrumentation pass
// (llvm/lib/Transforms/Instrumentation/DataFlowSanitizer.cpp) and the runtime
// (compiler-rt/lib/dfsan/dfsan.cpp) each hard-code these sizes, and the linker
// does not diagnose a mismatch.
//
// RUN: %clang_dfsan -mllvm -dfsan-track-origins=1 -S -emit-llvm %s -o %t.ll
// RUN: %clang_dfsan -mllvm -dfsan-track-origins=1 %s -o %t
// RUN: llvm-nm -S --defined-only %t > %t.nm
// RUN: cat %t.ll %t.nm | FileCheck %s

// Sizes the instrumentation pass expects.
// CHECK-DAG: @__dfsan_arg_tls = external thread_local(initialexec) global {{\[}}[[#ARG:]] x i64]
// CHECK-DAG: @__dfsan_retval_tls = external thread_local(initialexec) global {{\[}}[[#RETVAL:]] x i64]
// CHECK-DAG: @__dfsan_arg_origin_tls = external thread_local(initialexec) global {{\[}}[[#ARG_ORIGIN:]] x i32]
// CHECK-DAG: @__dfsan_retval_origin_tls = external thread_local(initialexec) global i32

// Sizes (in bytes, hex) of the arrays the runtime defines.
// CHECK-DAG: {{^[0-9a-f]+ 0*}}[[#%x,mul(ARG,8)]] {{[[:alpha:]]}} __dfsan_arg_tls{{$}}
// CHECK-DAG: {{^[0-9a-f]+ 0*}}[[#%x,mul(RETVAL,8)]] {{[[:alpha:]]}} __dfsan_retval_tls{{$}}
// CHECK-DAG: {{^[0-9a-f]+ 0*}}[[#%x,mul(ARG_ORIGIN,4)]] {{[[:alpha:]]}} __dfsan_arg_origin_tls{{$}}
// CHECK-DAG: {{^[0-9a-f]+ 0*}}4 {{[[:alpha:]]}} __dfsan_retval_origin_tls{{$}}

int f(int a, int b) { return a + b; }

int main(int argc, char *argv[]) { return f(argc, 0) - argc; }
