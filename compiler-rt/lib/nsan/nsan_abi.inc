/*===-- NSan instrumentation/runtime ABI ------------------------*- C++ -*-===*\
|*
|* Part of the LLVM Project, under the Apache License v2.0 with LLVM Exceptions.
|* See https://llvm.org/LICENSE.txt for license information.
|* SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
|*
\*===----------------------------------------------------------------------===*/
/*
 * Values shared by the NumericalStabilitySanitizer instrumentation pass and
 * the nsan runtime. Changing any of them changes the ABI between instrumented
 * code and the runtime.
 *
 * This file has two identical copies:
 *   llvm/include/llvm/Transforms/Instrumentation/NumericalStabilitySanitizerABI.inc
 *   compiler-rt/lib/nsan/nsan_abi.inc
 * compiler-rt/test/nsan/check-same-abi.test fails if they differ, so always
 * edit both together.
 *
 * Define the macros you need before including this file; undefined macros
 * expand to nothing and all of them are undefined at the end.
 *
 * NSAN_ABI_CONSTANT(Name, Value):
 *   ShadowScale            ratio of shadow to application memory.
 *   MaxVectorWidth         maximum number of vector lanes passed in shadow
 *                          argument and return slots.
 *   MaxNumArgs             maximum number of arguments passed in
 *                          __nsan_shadow_args_ptr.
 *   MaxShadowTypeSizeBytes size of the largest shadow type (fp128).
 *   __nsan_shadow_ret_ptr has MaxVectorWidth * MaxShadowTypeSizeBytes bytes
 *   and __nsan_shadow_args_ptr has
 *   MaxVectorWidth * MaxNumArgs * MaxShadowTypeSizeBytes bytes.
 *
 * NSAN_CHECK_TYPE(Name):
 *   Kind of location passed as the check type argument of the
 *   __nsan_internal_check_* functions, numbered from 0 in declaration order.
 *
 * NSAN_CONTINUATION_TYPE(Name, Value):
 *   Return value of the __nsan_internal_check_* functions, telling the
 *   instrumented code whether to keep using the shadow value or to resume from
 *   the application value.
 */

#ifndef NSAN_ABI_CONSTANT
#define NSAN_ABI_CONSTANT(Name, Value)
#endif
#ifndef NSAN_CHECK_TYPE
#define NSAN_CHECK_TYPE(Name)
#endif
#ifndef NSAN_CONTINUATION_TYPE
#define NSAN_CONTINUATION_TYPE(Name, Value)
#endif

NSAN_ABI_CONSTANT(ShadowScale, 2)
NSAN_ABI_CONSTANT(MaxVectorWidth, 8)
NSAN_ABI_CONSTANT(MaxNumArgs, 128)
NSAN_ABI_CONSTANT(MaxShadowTypeSizeBytes, 16)

NSAN_CHECK_TYPE(Unknown)
NSAN_CHECK_TYPE(Ret)
NSAN_CHECK_TYPE(Arg)
NSAN_CHECK_TYPE(Load)
NSAN_CHECK_TYPE(Store)
NSAN_CHECK_TYPE(Insert)
/* Only reported by the runtime (user-initiated checks and fcmp warnings). */
NSAN_CHECK_TYPE(User)
NSAN_CHECK_TYPE(Fcmp)

NSAN_CONTINUATION_TYPE(ContinueWithShadow, 0)
NSAN_CONTINUATION_TYPE(ResumeFromValue, 1)

#undef NSAN_ABI_CONSTANT
#undef NSAN_CHECK_TYPE
#undef NSAN_CONTINUATION_TYPE
