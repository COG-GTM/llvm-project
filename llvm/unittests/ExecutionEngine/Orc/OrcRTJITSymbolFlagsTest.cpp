//===- OrcRTJITSymbolFlagsTest.cpp - Check ORC runtime flag compatibility -===//
//
// Part of the LLVM Project, under the Apache License v2.0 with LLVM Exceptions.
// See https://llvm.org/LICENSE.txt for license information.
// SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
//
//===----------------------------------------------------------------------===//
//
// The ORC runtime in compiler-rt/lib/orc keeps its own copy of JITSymbolFlags
// (orc_rt::JITSymbolFlags in executor_symbol_def.h). Symbol definitions are
// SPS-serialized between the JIT and the executor, so the two definitions must
// agree bit for bit. Check that here, so that a change to llvm::JITSymbolFlags
// is caught even by builds that do not include compiler-rt.
//
//===----------------------------------------------------------------------===//

#include "llvm/ExecutionEngine/JITSymbol.h"
#include "llvm/ExecutionEngine/Orc/Shared/ExecutorSymbolDef.h"
#include "llvm/ExecutionEngine/Orc/Shared/SimplePackedSerialization.h"
#include "gtest/gtest.h"

#include "orc/executor_symbol_def.h"

#include <memory>
#include <type_traits>

using namespace llvm;

namespace {

using LLVMFlags = llvm::JITSymbolFlags;
using RTFlags = orc_rt::JITSymbolFlags;

static_assert(
    std::is_same_v<LLVMFlags::UnderlyingType, RTFlags::UnderlyingType>,
    "JITSymbolFlags::UnderlyingType differs from the ORC runtime");
static_assert(
    std::is_same_v<LLVMFlags::TargetFlagsType, RTFlags::TargetFlagsType>,
    "JITSymbolFlags::TargetFlagsType differs from the ORC runtime");

#define CHECK_FLAG(Name)                                                       \
  static_assert(static_cast<LLVMFlags::UnderlyingType>(LLVMFlags::Name) ==     \
                    static_cast<RTFlags::UnderlyingType>(RTFlags::Name),       \
                "JITSymbolFlags::" #Name " differs from the ORC runtime "      \
                "(compiler-rt/lib/orc/executor_symbol_def.h)");
CHECK_FLAG(None)
CHECK_FLAG(HasError)
CHECK_FLAG(Weak)
CHECK_FLAG(Common)
CHECK_FLAG(Absolute)
CHECK_FLAG(Exported)
CHECK_FLAG(Callable)
CHECK_FLAG(MaterializationSideEffectsOnly)
#undef CHECK_FLAG

// Catches flags added to llvm::JITSymbolFlags but not to the ORC runtime.
static_assert(static_cast<LLVMFlags::UnderlyingType>(
                  LLVMFlags::LLVM_BITMASK_LARGEST_ENUMERATOR) ==
                  static_cast<RTFlags::UnderlyingType>(
                      RTFlags::ORC_RT_BITMASK_LARGEST_ENUMERATOR),
              "Largest JITSymbolFlags value differs from the ORC runtime "
              "(compiler-rt/lib/orc/executor_symbol_def.h)");

constexpr unsigned AllFlagsMask =
    (static_cast<unsigned>(LLVMFlags::LLVM_BITMASK_LARGEST_ENUMERATOR) << 1) -
    1;

// Serialize In with SerT's SPS implementation, deserialize into Out with
// DeserT's.
template <typename SerT, typename DeserT, typename T, typename U>
static void serializeAs(const T &In, U &Out) {
  size_t Size = SerT::size(In);
  auto Buffer = std::make_unique<char[]>(Size);
  typename SerT::OutputBuffer OB(Buffer.get(), Size);
  ASSERT_TRUE(SerT::serialize(OB, In));
  typename DeserT::InputBuffer IB(Buffer.get(), Size);
  ASSERT_TRUE(DeserT::deserialize(IB, Out));
}

struct LLVMSPS {
  using Traits =
      orc::shared::SPSSerializationTraits<orc::shared::SPSExecutorSymbolDef,
                                          orc::ExecutorSymbolDef>;
  using OutputBuffer = orc::shared::SPSOutputBuffer;
  using InputBuffer = orc::shared::SPSInputBuffer;
  static size_t size(const orc::ExecutorSymbolDef &D) {
    return Traits::size(D);
  }
  static bool serialize(OutputBuffer &OB, const orc::ExecutorSymbolDef &D) {
    return Traits::serialize(OB, D);
  }
  static bool deserialize(InputBuffer &IB, orc::ExecutorSymbolDef &D) {
    return Traits::deserialize(IB, D);
  }
};

struct RTSPS {
  using Traits = orc_rt::SPSSerializationTraits<orc_rt::SPSExecutorSymbolDef,
                                                orc_rt::ExecutorSymbolDef>;
  using OutputBuffer = orc_rt::SPSOutputBuffer;
  using InputBuffer = orc_rt::SPSInputBuffer;
  static size_t size(const orc_rt::ExecutorSymbolDef &D) {
    return Traits::size(D);
  }
  static bool serialize(OutputBuffer &OB, const orc_rt::ExecutorSymbolDef &D) {
    return Traits::serialize(OB, D);
  }
  static bool deserialize(InputBuffer &IB, orc_rt::ExecutorSymbolDef &D) {
    return Traits::deserialize(IB, D);
  }
};

TEST(OrcRTJITSymbolFlagsTest, NamedFlagsDecodeInRuntime) {
  struct {
    LLVMFlags::FlagNames LLVMFlag;
    RTFlags::FlagNames RTFlag;
  } Pairs[] = {
      {LLVMFlags::None, RTFlags::None},
      {LLVMFlags::HasError, RTFlags::HasError},
      {LLVMFlags::Weak, RTFlags::Weak},
      {LLVMFlags::Common, RTFlags::Common},
      {LLVMFlags::Absolute, RTFlags::Absolute},
      {LLVMFlags::Exported, RTFlags::Exported},
      {LLVMFlags::Callable, RTFlags::Callable},
      {LLVMFlags::MaterializationSideEffectsOnly,
       RTFlags::MaterializationSideEffectsOnly},
  };

  for (auto &P : Pairs) {
    orc::ExecutorSymbolDef In(orc::ExecutorAddr(0x1000),
                              LLVMFlags(P.LLVMFlag, /*TargetFlags=*/7));
    orc_rt::ExecutorSymbolDef Out;
    serializeAs<LLVMSPS, RTSPS>(In, Out);
    EXPECT_EQ(Out, orc_rt::ExecutorSymbolDef(orc_rt::ExecutorAddr(0x1000),
                                             RTFlags(P.RTFlag, 7)))
        << "llvm::JITSymbolFlags 0x" << std::hex
        << static_cast<unsigned>(P.LLVMFlag)
        << " decoded differently by the ORC runtime";
  }
}

TEST(OrcRTJITSymbolFlagsTest, AllFlagCombinationsRoundTrip) {
  for (unsigned Raw = 0; Raw <= AllFlagsMask; ++Raw) {
    for (unsigned Target : {0u, 1u, 0xffu}) {
      auto LLVMFlag = static_cast<LLVMFlags::FlagNames>(Raw);
      auto RTFlag = static_cast<RTFlags::FlagNames>(Raw);

      // JIT -> executor.
      orc::ExecutorSymbolDef LLVMDef(orc::ExecutorAddr(0xdeadbeef + Raw),
                                     LLVMFlags(LLVMFlag, Target));
      orc_rt::ExecutorSymbolDef RTOut;
      serializeAs<LLVMSPS, RTSPS>(LLVMDef, RTOut);
      EXPECT_EQ(RTOut.getAddress().getValue(), LLVMDef.getAddress().getValue());
      EXPECT_EQ(RTOut.getFlags().getRawFlagsValue(), Raw);
      EXPECT_EQ(RTOut.getFlags().getTargetFlags(), Target);

      // Executor -> JIT.
      orc_rt::ExecutorSymbolDef RTDef(orc_rt::ExecutorAddr(0xcafef00d + Raw),
                                      RTFlags(RTFlag, Target));
      orc::ExecutorSymbolDef LLVMOut;
      serializeAs<RTSPS, LLVMSPS>(RTDef, LLVMOut);
      EXPECT_EQ(LLVMOut.getAddress().getValue(), RTDef.getAddress().getValue());
      EXPECT_EQ(LLVMOut.getFlags(), LLVMFlags(LLVMFlag, Target));
    }
  }
}

} // namespace
