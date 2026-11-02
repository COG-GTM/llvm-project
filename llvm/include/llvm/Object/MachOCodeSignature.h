//===- MachOCodeSignature.h - Mach-O ad-hoc code signature ------*- C++ -*-===//
//
// Part of the LLVM Project, under the Apache License v2.0 with LLVM Exceptions.
// See https://llvm.org/LICENSE.txt for license information.
// SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
//
//===----------------------------------------------------------------------===//
//
// Layout and writer for the ad-hoc, linker-signed LC_CODE_SIGNATURE blob.
//
// This is the single implementation shared by LLD's CodeSignatureSection and
// llvm-objcopy's MachOWriter, so that a binary linked by lld and a binary
// rewritten by llvm-objcopy / llvm-strip / llvm-install-name-tool carry
// byte-identical signatures for identical contents.
//
//===----------------------------------------------------------------------===//

#ifndef LLVM_OBJECT_MACHOCODESIGNATURE_H
#define LLVM_OBJECT_MACHOCODESIGNATURE_H

#include "llvm/ADT/StringRef.h"
#include "llvm/BinaryFormat/MachO.h"
#include "llvm/Support/Compiler.h"
#include "llvm/Support/MathExtras.h"
#include <cstdint>

namespace llvm {
namespace object {

/// An ad-hoc code signature consisting of a SuperBlob with a single
/// CodeDirectory that holds one SHA-256 hash per 4 KiB page of the file
/// preceding the signature. The signature must be the last thing in the file.
struct MachOAdHocCodeSignature {
  static constexpr uint32_t Align = 16;
  static constexpr uint8_t BlockSizeShift = 12;
  static constexpr size_t BlockSize = (1 << BlockSizeShift); // 4 KiB
  static constexpr size_t HashSize = 256 / 8;
  static constexpr size_t BlobHeadersSize = llvm::alignTo<8>(
      sizeof(llvm::MachO::CS_SuperBlob) + sizeof(llvm::MachO::CS_BlobIndex));
  static constexpr uint32_t FixedHeadersSize =
      BlobHeadersSize + sizeof(llvm::MachO::CS_CodeDirectory);

  /// The code signing identifier written after the CodeDirectory, e.g. the
  /// output file name or install name with any directory components removed.
  StringRef Identifier;
  /// The file offset of the signature, i.e. the number of leading bytes of the
  /// file that are hashed.
  uint64_t CodeLimit = 0;

  MachOAdHocCodeSignature() = default;
  MachOAdHocCodeSignature(StringRef Identifier, uint64_t CodeLimit)
      : Identifier(Identifier), CodeLimit(CodeLimit) {}

  /// Size of the SuperBlob, CodeDirectory and padded identifier.
  static uint32_t getAllHeadersSize(StringRef Identifier) {
    return llvm::alignTo<Align>(FixedHeadersSize + Identifier.size() + 1);
  }
  uint32_t getAllHeadersSize() const { return getAllHeadersSize(Identifier); }
  /// Number of zero bytes (at least one) that terminate the identifier.
  uint32_t getIdentifierPad() const {
    return getAllHeadersSize() - FixedHeadersSize - Identifier.size();
  }
  uint32_t getBlockCount() const {
    return (CodeLimit + BlockSize - 1) / BlockSize;
  }
  /// Size of the headers plus the page hashes, without trailing padding.
  uint64_t getRawSize() const {
    return getAllHeadersSize() + getBlockCount() * HashSize;
  }
  /// Size of the signature as recorded in LC_CODE_SIGNATURE's datasize.
  uint64_t getSize() const { return llvm::alignTo<Align>(getRawSize()); }

  /// Write the SuperBlob, CodeDirectory and identifier to \p Buf, which points
  /// at the start of the signature (file offset CodeLimit). \p ExecSegBase and
  /// \p ExecSegLimit are the file offset and file size of the __TEXT segment.
  LLVM_ABI void writeHeaders(uint8_t *Buf, uint64_t ExecSegBase,
                             uint64_t ExecSegLimit, bool IsMainBinary) const;

  /// Hash every page of [FileStart, FileStart + CodeLimit) into the slots that
  /// follow the headers. Must be called after everything before the signature
  /// has been written to \p FileStart.
  LLVM_ABI void writeHashes(uint8_t *FileStart) const;
};

} // end namespace object
} // end namespace llvm

#endif // LLVM_OBJECT_MACHOCODESIGNATURE_H
