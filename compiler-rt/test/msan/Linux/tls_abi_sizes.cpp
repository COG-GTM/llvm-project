// The MemorySanitizer pass (kParamTLSSize/kRetvalTLSSize in
// llvm/lib/Transforms/Instrumentation/MemorySanitizer.cpp) and the runtime
// (kMsanParamTlsSize/kMsanRetvalTlsSize in compiler-rt/lib/msan/msan.h) each
// hard-code the sizes of the shadow TLS arrays. Check that the arrays the pass
// declares are exactly as large as the ones the runtime defines, so that a
// one-sided change to either constant fails here.
//
// RUN: %clangxx_msan -fsanitize-memory-track-origins=2 -O0 %s -S -emit-llvm -o %t.ll
// RUN: %clangxx_msan -fsanitize-memory-track-origins=2 -O0 %s -o %t
// RUN: echo "RUNTIME SYMBOLS" > %t.syms
// RUN: llvm-nm -S %t >> %t.syms
// RUN: cat %t.ll %t.syms | FileCheck %s

// CHECK-DAG: @__msan_param_tls = external thread_local(initialexec) global {{\[}}[[#PARAM:]] x i64]
// CHECK-DAG: @__msan_retval_tls = external thread_local(initialexec) global {{\[}}[[#RETVAL:]] x i64]
// CHECK-DAG: @__msan_va_arg_tls = external thread_local(initialexec) global {{\[}}[[#VA_ARG:]] x i64]
// CHECK-DAG: @__msan_param_origin_tls = external thread_local(initialexec) global {{\[}}[[#PARAM_ORIGIN:]] x i32]
// CHECK-DAG: @__msan_va_arg_origin_tls = external thread_local(initialexec) global {{\[}}[[#VA_ARG_ORIGIN:]] x i32]

// CHECK-LABEL: RUNTIME SYMBOLS
// CHECK-DAG: {{^[0-9a-f]+ 0*}}[[#%x,mul(PARAM,8)]] {{[a-zA-Z]}} __msan_param_tls{{$}}
// CHECK-DAG: {{^[0-9a-f]+ 0*}}[[#%x,mul(RETVAL,8)]] {{[a-zA-Z]}} __msan_retval_tls{{$}}
// CHECK-DAG: {{^[0-9a-f]+ 0*}}[[#%x,mul(VA_ARG,8)]] {{[a-zA-Z]}} __msan_va_arg_tls{{$}}
// CHECK-DAG: {{^[0-9a-f]+ 0*}}[[#%x,mul(PARAM_ORIGIN,4)]] {{[a-zA-Z]}} __msan_param_origin_tls{{$}}
// CHECK-DAG: {{^[0-9a-f]+ 0*}}[[#%x,mul(VA_ARG_ORIGIN,4)]] {{[a-zA-Z]}} __msan_va_arg_origin_tls{{$}}

#include <stdarg.h>

__attribute__((noinline)) int sum(int n, ...) {
  va_list ap;
  va_start(ap, n);
  int s = 0;
  for (int i = 0; i < n; ++i)
    s += va_arg(ap, int);
  va_end(ap);
  return s;
}

__attribute__((noinline)) int add(int a, int b) { return a + b; }

int main() { return add(sum(2, 1, 2), -3); }
