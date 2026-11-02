//===- MachOCodeSignature.cpp - Mach-O ad-hoc code signature --------------===//
//
// Part of the LLVM Project, under the Apache License v2.0 with LLVM Exceptions.
// See https://llvm.org/LICENSE.txt for license information.
// SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
//
//===----------------------------------------------------------------------===//

#include "llvm/Object/MachOCodeSignature.h"
#include "llvm/ADT/ArrayRef.h"
#include "llvm/Support/Endian.h"
#include "llvm/Support/Parallel.h"
#include "llvm/Support/SHA256.h"
#include <algorithm>
#include <cstring>

#if defined(__APPLE__)
#include <sys/mman.h>

#define COMMON_DIGEST_FOR_OPENSSL
#include <CommonCrypto/CommonDigest.h>
#endif

using namespace llvm;
using namespace llvm::MachO;
using namespace llvm::object;
using namespace llvm::support::endian;

static_assert((MachOAdHocCodeSignature::BlobHeadersSize % 8) == 0);
static_assert((MachOAdHocCodeSignature::FixedHeadersSize % 8) == 0);

// Reads `Len` bytes at `Data` and writes the 32-byte SHA256 checksum to `Out`.
static void sha256(const uint8_t *Data, size_t Len, uint8_t *Out) {
#if defined(__APPLE__)
  // FIXME: Make LLVM's SHA256 faster and use it unconditionally. See PR56121
  // for some notes on this.
  CC_SHA256(Data, Len, Out);
#else
  std::array<uint8_t, 32> Hash = SHA256::hash(ArrayRef<uint8_t>(Data, Len));
  static_assert(Hash.size() == MachOAdHocCodeSignature::HashSize);
  memcpy(Out, Hash.data(), Hash.size());
#endif
}

void MachOAdHocCodeSignature::writeHeaders(uint8_t *Buf, uint64_t ExecSegBase,
                                           uint64_t ExecSegLimit,
                                           bool IsMainBinary) const {
  uint32_t SignatureSize = static_cast<uint32_t>(getSize());
  auto *SuperBlob = reinterpret_cast<CS_SuperBlob *>(Buf);
  write32be(&SuperBlob->magic, CSMAGIC_EMBEDDED_SIGNATURE);
  write32be(&SuperBlob->length, SignatureSize);
  write32be(&SuperBlob->count, 1);
  auto *BlobIndex = reinterpret_cast<CS_BlobIndex *>(&SuperBlob[1]);
  write32be(&BlobIndex->type, CSSLOT_CODEDIRECTORY);
  write32be(&BlobIndex->offset, BlobHeadersSize);
  auto *CodeDirectory =
      reinterpret_cast<CS_CodeDirectory *>(Buf + BlobHeadersSize);
  write32be(&CodeDirectory->magic, CSMAGIC_CODEDIRECTORY);
  write32be(&CodeDirectory->length, SignatureSize - BlobHeadersSize);
  write32be(&CodeDirectory->version, CS_SUPPORTSEXECSEG);
  write32be(&CodeDirectory->flags, CS_ADHOC | CS_LINKER_SIGNED);
  write32be(&CodeDirectory->hashOffset,
            sizeof(CS_CodeDirectory) + Identifier.size() + getIdentifierPad());
  write32be(&CodeDirectory->identOffset, sizeof(CS_CodeDirectory));
  CodeDirectory->nSpecialSlots = 0;
  write32be(&CodeDirectory->nCodeSlots, getBlockCount());
  write32be(&CodeDirectory->codeLimit, CodeLimit);
  CodeDirectory->hashSize = static_cast<uint8_t>(HashSize);
  CodeDirectory->hashType = kSecCodeSignatureHashSHA256;
  CodeDirectory->platform = 0;
  CodeDirectory->pageSize = BlockSizeShift;
  CodeDirectory->spare2 = 0;
  CodeDirectory->scatterOffset = 0;
  CodeDirectory->teamOffset = 0;
  CodeDirectory->spare3 = 0;
  CodeDirectory->codeLimit64 = 0;
  write64be(&CodeDirectory->execSegBase, ExecSegBase);
  write64be(&CodeDirectory->execSegLimit, ExecSegLimit);
  write64be(&CodeDirectory->execSegFlags,
            IsMainBinary ? CS_EXECSEG_MAIN_BINARY : 0);
  auto *Id = reinterpret_cast<char *>(&CodeDirectory[1]);
  memcpy(Id, Identifier.data(), Identifier.size());
  memset(Id + Identifier.size(), 0, getIdentifierPad());
}

void MachOAdHocCodeSignature::writeHashes(uint8_t *FileStart) const {
  uint8_t *Hashes = FileStart + CodeLimit + getAllHeadersSize();
  parallelFor(0, getBlockCount(), [&](size_t I) {
    sha256(FileStart + I * BlockSize,
           std::min(static_cast<size_t>(CodeLimit - I * BlockSize), BlockSize),
           Hashes + I * HashSize);
  });
#if defined(__APPLE__)
  // This is macOS-specific work-around and makes no sense for any
  // other host OS. See https://openradar.appspot.com/FB8914231
  //
  // The macOS kernel maintains a signature-verification cache to
  // quickly validate applications at time of execve(2).  The trouble
  // is that for the kernel creates the cache entry at the time of the
  // mmap(2) call, before we have a chance to write either the code to
  // sign or the signature header+hashes.  The fix is to invalidate
  // all cached data associated with the output file, thus discarding
  // the bogus prematurely-cached signature.
  msync(FileStart, CodeLimit + getSize(), MS_INVALIDATE);
#endif
}
