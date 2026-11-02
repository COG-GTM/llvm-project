//===- MachOLayoutBuilder.h -------------------------------------*- C++ -*-===//
//
// Part of the LLVM Project, under the Apache License v2.0 with LLVM Exceptions.
// See https://llvm.org/LICENSE.txt for license information.
// SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
//
//===----------------------------------------------------------------------===//

#ifndef LLVM_LIB_OBJCOPY_MACHO_MACHOLAYOUTBUILDER_H
#define LLVM_LIB_OBJCOPY_MACHO_MACHOLAYOUTBUILDER_H

#include "MachOObject.h"
#include "llvm/ObjCopy/MachO/MachOObjcopy.h"
#include "llvm/Object/MachOCodeSignature.h"

namespace llvm {
namespace objcopy {
namespace macho {

class MachOLayoutBuilder {
  Object &O;
  bool Is64Bit;
  StringRef OutputFileName;
  uint64_t PageSize;
  // When the binary has an LC_CODE_SIGNATURE load command, the signature is
  // the last component of __LINKEDIT and is regenerated from the rewritten
  // contents.
  object::MachOAdHocCodeSignature CodeSignature;

  // Points to the __LINKEDIT segment if it exists.
  MachO::macho_load_command *LinkEditLoadCommand = nullptr;
  StringTableBuilder StrTableBuilder;

  uint32_t computeSizeOfCmds() const;
  void constructStringTable();
  void updateSymbolIndexes();
  void updateDySymTab(MachO::macho_load_command &MLC);
  uint64_t layoutSegments();
  uint64_t layoutRelocations(uint64_t Offset);
  Error layoutTail(uint64_t Offset);

  static StringTableBuilder::Kind getStringTableBuilderKind(const Object &O,
                                                            bool Is64Bit);

public:
  MachOLayoutBuilder(Object &O, bool Is64Bit, StringRef OutputFileName,
                     uint64_t PageSize)
      : O(O), Is64Bit(Is64Bit), OutputFileName(OutputFileName),
        PageSize(PageSize),
        StrTableBuilder(getStringTableBuilderKind(O, Is64Bit)) {}

  // Recomputes and updates fields in the given object such as file offsets.
  Error layout();

  StringTableBuilder &getStringTableBuilder() { return StrTableBuilder; }

  const object::MachOAdHocCodeSignature &getCodeSignature() const {
    return CodeSignature;
  }
};

} // end namespace macho
} // end namespace objcopy
} // end namespace llvm

#endif // LLVM_LIB_OBJCOPY_MACHO_MACHOLAYOUTBUILDER_H
