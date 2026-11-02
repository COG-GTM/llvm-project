# REQUIRES: x86, aarch64

## lld and llvm-objcopy (and therefore llvm-strip and llvm-install-name-tool)
## both generate ad-hoc code signatures through
## llvm::object::MachOAdHocCodeSignature. Check that rewriting an lld-signed
## binary with these tools produces a valid signature whose headers are byte
## for byte identical to lld's, so that the two tools cannot drift apart.

# RUN: rm -rf %t; split-file %s %t
# RUN: mkdir -p %t/objcopy %t/zeroed %t/regen %t/strip %t/int
# RUN: llvm-mc -filetype=obj -triple=arm64-apple-macos -o %t/main-arm64.o %t/main.s
# RUN: llvm-mc -filetype=obj -triple=x86_64-apple-macos -o %t/main-x86_64.o %t/main.s
# RUN: llvm-mc -filetype=obj -triple=arm64-apple-macos -o %t/foo-arm64.o %t/foo.s

# RUN: %lld -arch arm64 -lSystem -execute -o %t/a.out %t/main-arm64.o
# RUN: %lld -arch x86_64 -lSystem -execute -adhoc_codesign -o %t/x86.out %t/main-x86_64.o
# RUN: %lld -arch arm64 -dylib -install_name @rpath/libfoo.dylib -o %t/libfoo.dylib %t/foo-arm64.o
# RUN: %python %t/cs.py verify %t/a.out
# RUN: %python %t/cs.py verify %t/x86.out
# RUN: %python %t/cs.py verify %t/libfoo.dylib

## llvm-objcopy re-lays out __LINKEDIT, so the hashed contents may change, but
## the signature headers must be identical to lld's and the hashes valid.
# RUN: llvm-objcopy %t/a.out %t/objcopy/a.out
# RUN: %python %t/cs.py verify %t/objcopy/a.out
# RUN: %python %t/cs.py same-headers %t/a.out %t/objcopy/a.out
# RUN: llvm-objcopy %t/x86.out %t/objcopy/x86.out
# RUN: %python %t/cs.py verify %t/objcopy/x86.out
# RUN: %python %t/cs.py same-headers %t/x86.out %t/objcopy/x86.out
# RUN: llvm-objcopy %t/libfoo.dylib %t/objcopy/libfoo.dylib
# RUN: %python %t/cs.py verify %t/objcopy/libfoo.dylib
# RUN: %python %t/cs.py same-headers %t/libfoo.dylib %t/objcopy/libfoo.dylib

## Clobber the page hashes; llvm-objcopy must regenerate them from scratch.
# RUN: %python %t/cs.py zero %t/a.out %t/zeroed/a.out
# RUN: not %python %t/cs.py verify %t/zeroed/a.out
# RUN: llvm-objcopy %t/zeroed/a.out %t/regen/a.out
# RUN: cmp %t/objcopy/a.out %t/regen/a.out
# RUN: %python %t/cs.py zero %t/libfoo.dylib %t/zeroed/libfoo.dylib
# RUN: llvm-objcopy %t/zeroed/libfoo.dylib %t/regen/libfoo.dylib
# RUN: cmp %t/objcopy/libfoo.dylib %t/regen/libfoo.dylib

## llvm-strip and llvm-install-name-tool share the same writer.
# RUN: llvm-strip -o %t/strip/a.out %t/a.out
# RUN: %python %t/cs.py verify %t/strip/a.out
# RUN: cp %t/libfoo.dylib %t/int/libfoo.dylib
# RUN: llvm-install-name-tool -id @rpath/libbar.dylib %t/int/libfoo.dylib
# RUN: %python %t/cs.py verify %t/int/libfoo.dylib

#--- main.s
.globl _main
.text
_main:
  ret

#--- foo.s
.globl _foo
.text
_foo:
  ret

#--- cs.py
import hashlib
import struct
import sys

LC_CODE_SIGNATURE = 0x1D
CSMAGIC_EMBEDDED_SIGNATURE = 0xFADE0CC0
CSMAGIC_CODEDIRECTORY = 0xFADE0C02


def parse(data):
    assert struct.unpack_from("<I", data, 0)[0] == 0xFEEDFACF
    ncmds = struct.unpack_from("<I", data, 16)[0]
    off = 32
    for _ in range(ncmds):
        cmd, size = struct.unpack_from("<II", data, off)
        if cmd == LC_CODE_SIGNATURE:
            dataoff, datasize = struct.unpack_from("<II", data, off + 8)
            break
        off += size
    else:
        sys.exit("no LC_CODE_SIGNATURE")
    magic, length, count = struct.unpack_from(">III", data, dataoff)
    assert magic == CSMAGIC_EMBEDDED_SIGNATURE and count == 1
    assert length <= datasize and dataoff + datasize == len(data)
    _, cdoff = struct.unpack_from(">II", data, dataoff + 12)
    cd = dataoff + cdoff
    assert struct.unpack_from(">I", data, cd)[0] == CSMAGIC_CODEDIRECTORY
    hashoff, _, _, nslots, limit = struct.unpack_from(">5I", data, cd + 16)
    hashsize, _, _, pageshift = struct.unpack_from(">4B", data, cd + 36)
    hashes = cd + hashoff
    return dataoff, hashes, hashes + nslots * hashsize, limit, hashsize, 1 << pageshift


def read(path):
    return bytearray(open(path, "rb").read())


mode = sys.argv[1]
data = read(sys.argv[2])
dataoff, hashes, hashes_end, limit, hashsize, pagesize = parse(data)
if mode == "verify":
    assert limit == dataoff, "codeLimit must cover everything before the signature"
    for i, page in enumerate(range(0, limit, pagesize)):
        got = data[hashes + i * hashsize : hashes + (i + 1) * hashsize]
        want = hashlib.sha256(data[page : min(page + pagesize, limit)]).digest()
        if got != want:
            sys.exit("bad hash for page %d" % i)
elif mode == "same-headers":
    other = read(sys.argv[3])
    o_dataoff, o_hashes, o_hashes_end = parse(other)[:3]
    assert (dataoff, hashes, hashes_end) == (o_dataoff, o_hashes, o_hashes_end)
    assert data[dataoff:hashes] == other[dataoff:hashes], "header mismatch"
    assert data[hashes_end:] == other[hashes_end:], "trailing padding mismatch"
elif mode == "zero":
    data[hashes:hashes_end] = bytes(hashes_end - hashes)
    open(sys.argv[3], "wb").write(data)
else:
    sys.exit("unknown mode " + mode)
