//===- MachOCodeSignatureTest.cpp - Mach-O ad-hoc code signature tests ----===//
//
// Part of the LLVM Project, under the Apache License v2.0 with LLVM Exceptions.
// See https://llvm.org/LICENSE.txt for license information.
// SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
//
//===----------------------------------------------------------------------===//

#include "llvm/Object/MachOCodeSignature.h"
#include "llvm/ADT/ArrayRef.h"
#include "llvm/Support/Endian.h"
#include "llvm/Support/SHA256.h"
#include "gtest/gtest.h"
#include <algorithm>
#include <string>
#include <vector>

using namespace llvm;
using namespace llvm::MachO;
using namespace llvm::object;
using namespace llvm::support::endian;

namespace {

using Sig = MachOAdHocCodeSignature;

TEST(MachOCodeSignatureTest, FormatConstants) {
  EXPECT_EQ(Sig::Align, 16u);
  EXPECT_EQ(Sig::BlockSizeShift, 12u);
  EXPECT_EQ(Sig::BlockSize, 4096u);
  EXPECT_EQ(Sig::HashSize, 32u);
  EXPECT_EQ(Sig::BlobHeadersSize, 24u);
  EXPECT_EQ(Sig::FixedHeadersSize, 112u);
}

TEST(MachOCodeSignatureTest, Layout) {
  Sig S("a.out", 0x2010);
  EXPECT_EQ(S.getAllHeadersSize(), 128u);
  EXPECT_EQ(S.getIdentifierPad(), 11u);
  EXPECT_EQ(S.getBlockCount(), 3u);
  EXPECT_EQ(S.getRawSize(), 128u + 3 * 32);
  EXPECT_EQ(S.getSize(), 224u);

  // The identifier always gets at least one NUL terminator, so an identifier
  // that would exactly fill the headers spills into another 16 bytes.
  std::string Name(16, 'x');
  Sig Exact(Name, 0x4000);
  EXPECT_EQ(Exact.getAllHeadersSize(), 144u);
  EXPECT_EQ(Exact.getIdentifierPad(), 16u);
  EXPECT_EQ(Exact.getBlockCount(), 4u);

  Sig Empty("", 0);
  EXPECT_EQ(Empty.getAllHeadersSize(), 128u);
  EXPECT_EQ(Empty.getBlockCount(), 0u);
  EXPECT_EQ(Empty.getSize(), 128u);
}

TEST(MachOCodeSignatureTest, WriteHeadersAndHashes) {
  const uint64_t CodeLimit = 2 * Sig::BlockSize + 0x30;
  Sig S("libfoo.dylib", CodeLimit);
  std::vector<uint8_t> File(CodeLimit + S.getSize(), 0xcc);
  for (uint64_t I = 0; I < CodeLimit; ++I)
    File[I] = static_cast<uint8_t>(I * 7 + 3);

  uint8_t *Blob = File.data() + CodeLimit;
  S.writeHeaders(Blob, /*ExecSegBase=*/0, /*ExecSegLimit=*/0x1000,
                 /*IsMainBinary=*/false);
  S.writeHashes(File.data());

  auto *SuperBlob = reinterpret_cast<const CS_SuperBlob *>(Blob);
  EXPECT_EQ(read32be(&SuperBlob->magic), (uint32_t)CSMAGIC_EMBEDDED_SIGNATURE);
  EXPECT_EQ(read32be(&SuperBlob->length), S.getSize());
  EXPECT_EQ(read32be(&SuperBlob->count), 1u);
  auto *Index = reinterpret_cast<const CS_BlobIndex *>(&SuperBlob[1]);
  EXPECT_EQ(read32be(&Index->type), (uint32_t)CSSLOT_CODEDIRECTORY);
  EXPECT_EQ(read32be(&Index->offset), Sig::BlobHeadersSize);

  auto *CD =
      reinterpret_cast<const CS_CodeDirectory *>(Blob + Sig::BlobHeadersSize);
  EXPECT_EQ(read32be(&CD->magic), (uint32_t)CSMAGIC_CODEDIRECTORY);
  EXPECT_EQ(read32be(&CD->length), S.getSize() - Sig::BlobHeadersSize);
  EXPECT_EQ(read32be(&CD->version), (uint32_t)CS_SUPPORTSEXECSEG);
  EXPECT_EQ(read32be(&CD->flags), (uint32_t)(CS_ADHOC | CS_LINKER_SIGNED));
  EXPECT_EQ(read32be(&CD->identOffset), sizeof(CS_CodeDirectory));
  EXPECT_EQ(read32be(&CD->hashOffset),
            S.getAllHeadersSize() - Sig::BlobHeadersSize);
  EXPECT_EQ(CD->nSpecialSlots, 0u);
  EXPECT_EQ(read32be(&CD->nCodeSlots), 3u);
  EXPECT_EQ(read32be(&CD->codeLimit), CodeLimit);
  EXPECT_EQ(CD->hashSize, Sig::HashSize);
  EXPECT_EQ(CD->hashType, (uint8_t)kSecCodeSignatureHashSHA256);
  EXPECT_EQ(CD->pageSize, Sig::BlockSizeShift);
  EXPECT_EQ(read64be(&CD->execSegBase), 0u);
  EXPECT_EQ(read64be(&CD->execSegLimit), 0x1000u);
  EXPECT_EQ(read64be(&CD->execSegFlags), 0u);

  const char *Id = reinterpret_cast<const char *>(&CD[1]);
  EXPECT_EQ(StringRef(Id), "libfoo.dylib");
  for (uint32_t I = 0; I < S.getIdentifierPad(); ++I)
    EXPECT_EQ(Id[S.Identifier.size() + I], 0) << "pad byte " << I;

  const uint8_t *Hashes = Blob + S.getAllHeadersSize();
  for (uint32_t I = 0; I < S.getBlockCount(); ++I) {
    size_t Len =
        std::min<size_t>(CodeLimit - I * Sig::BlockSize, Sig::BlockSize);
    std::array<uint8_t, 32> Expected =
        SHA256::hash(ArrayRef<uint8_t>(File.data() + I * Sig::BlockSize, Len));
    EXPECT_TRUE(std::equal(Expected.begin(), Expected.end(),
                           Hashes + I * Sig::HashSize))
        << "page " << I;
  }

  // The space between the last hash and the aligned end is left untouched.
  for (uint64_t I = S.getRawSize(); I < S.getSize(); ++I)
    EXPECT_EQ(Blob[I], 0xcc);
}

TEST(MachOCodeSignatureTest, MainBinaryFlag) {
  Sig S("a.out", 0x10);
  std::vector<uint8_t> File(0x10 + S.getSize());
  S.writeHeaders(File.data() + 0x10, 0, 0x10, /*IsMainBinary=*/true);
  auto *CD = reinterpret_cast<const CS_CodeDirectory *>(File.data() + 0x10 +
                                                        Sig::BlobHeadersSize);
  EXPECT_EQ(read64be(&CD->execSegFlags), (uint64_t)CS_EXECSEG_MAIN_BINARY);
}

} // namespace
