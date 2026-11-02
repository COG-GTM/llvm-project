//===- ReduceInstructionFlags.h - Specialized Delta Pass --------*- C++ -*-===//
//
// Part of the LLVM Project, under the Apache License v2.0 with LLVM Exceptions.
// See https://llvm.org/LICENSE.txt for license information.
// SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
//
//===----------------------------------------------------------------------===//

#ifndef LLVM_TOOLS_LLVM_REDUCE_DELTAS_REDUCEINSTRUCTIONFLAGS_H
#define LLVM_TOOLS_LLVM_REDUCE_DELTAS_REDUCEINSTRUCTIONFLAGS_H

#include "Delta.h"
#include "llvm/ADT/STLFunctionalExtras.h"

namespace llvm {
class Instruction;

/// Call \p ShouldDrop once for each optimization flag set on \p I and clear
/// the flag when it returns true. \p I is left untouched if \p ShouldDrop
/// never returns true.
///
/// This is the single list of reducible IR instruction flags. It is shared by
/// reduceInstructionFlagsDeltaPass() and the IR complexity score, so every flag
/// the pass can drop also lowers the score.
void visitReducibleInstructionFlags(Instruction &I,
                                    function_ref<bool()> ShouldDrop);

/// Return the number of reducible optimization flags set on \p I.
unsigned countReducibleInstructionFlags(const Instruction &I);

void reduceInstructionFlagsDeltaPass(Oracle &O, ReducerWorkItem &WorkItem);
} // namespace llvm

#endif
