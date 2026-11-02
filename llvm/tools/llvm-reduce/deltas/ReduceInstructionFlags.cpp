//===- ReduceInstructionFlags.cpp - Specialized Delta Pass ----------------===//
//
// Part of the LLVM Project, under the Apache License v2.0 with LLVM Exceptions.
// See https://llvm.org/LICENSE.txt for license information.
// SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
//
//===----------------------------------------------------------------------===//
//
// Try to remove optimization flags on instructions
//
//===----------------------------------------------------------------------===//

#include "ReduceInstructionFlags.h"
#include "llvm/IR/InstIterator.h"
#include "llvm/IR/Instruction.h"
#include "llvm/IR/Instructions.h"
#include "llvm/IR/Operator.h"

using namespace llvm;

void llvm::visitReducibleInstructionFlags(Instruction &I,
                                         function_ref<bool()> ShouldDrop) {
  if (auto *OBO = dyn_cast<OverflowingBinaryOperator>(&I)) {
    if (OBO->hasNoSignedWrap() && ShouldDrop())
      I.setHasNoSignedWrap(false);
    if (OBO->hasNoUnsignedWrap() && ShouldDrop())
      I.setHasNoUnsignedWrap(false);
  } else if (auto *Trunc = dyn_cast<TruncInst>(&I)) {
    if (Trunc->hasNoSignedWrap() && ShouldDrop())
      Trunc->setHasNoSignedWrap(false);
    if (Trunc->hasNoUnsignedWrap() && ShouldDrop())
      Trunc->setHasNoUnsignedWrap(false);
  } else if (auto *PE = dyn_cast<PossiblyExactOperator>(&I)) {
    if (PE->isExact() && ShouldDrop())
      I.setIsExact(false);
  } else if (auto *NNI = dyn_cast<PossiblyNonNegInst>(&I)) {
    if (NNI->hasNonNeg() && ShouldDrop())
      NNI->setNonNeg(false);
  } else if (auto *PDI = dyn_cast<PossiblyDisjointInst>(&I)) {
    if (PDI->isDisjoint() && ShouldDrop())
      PDI->setIsDisjoint(false);
  } else if (auto *ICmp = dyn_cast<ICmpInst>(&I)) {
    if (ICmp->hasSameSign() && ShouldDrop())
      ICmp->setSameSign(false);
  } else if (auto *GEP = dyn_cast<GetElementPtrInst>(&I)) {
    GEPNoWrapFlags NW = GEP->getNoWrapFlags();
    if (NW.isInBounds() && ShouldDrop())
      NW = NW.withoutInBounds();
    if (NW.hasNoUnsignedSignedWrap() && ShouldDrop())
      NW = NW.withoutNoUnsignedSignedWrap();
    if (NW.hasNoUnsignedWrap() && ShouldDrop())
      NW = NW.withoutNoUnsignedWrap();
    if (NW != GEP->getNoWrapFlags())
      GEP->setNoWrapFlags(NW);
  } else if (auto *FPOp = dyn_cast<FPMathOperator>(&I)) {
    FastMathFlags Flags = FPOp->getFastMathFlags();

    if (Flags.allowReassoc() && ShouldDrop())
      Flags.setAllowReassoc(false);

    if (Flags.noNaNs() && ShouldDrop())
      Flags.setNoNaNs(false);

    if (Flags.noInfs() && ShouldDrop())
      Flags.setNoInfs(false);

    if (Flags.noSignedZeros() && ShouldDrop())
      Flags.setNoSignedZeros(false);

    if (Flags.allowReciprocal() && ShouldDrop())
      Flags.setAllowReciprocal(false);

    if (Flags.allowContract() && ShouldDrop())
      Flags.setAllowContract(false);

    if (Flags.approxFunc() && ShouldDrop())
      Flags.setApproxFunc(false);

    if (Flags != FPOp->getFastMathFlags())
      I.copyFastMathFlags(Flags);
  }
}

unsigned llvm::countReducibleInstructionFlags(const Instruction &I) {
  unsigned NumFlags = 0;
  // Never asks for a flag to be dropped, so I is not modified.
  visitReducibleInstructionFlags(const_cast<Instruction &>(I), [&NumFlags] {
    ++NumFlags;
    return false;
  });
  return NumFlags;
}

void llvm::reduceInstructionFlagsDeltaPass(Oracle &O,
                                           ReducerWorkItem &WorkItem) {
  for (Function &F : WorkItem.getModule())
    for (Instruction &I : instructions(F))
      visitReducibleInstructionFlags(I, [&O] { return !O.shouldKeep(); });
}
