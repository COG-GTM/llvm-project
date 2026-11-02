// Check that every -arch spelling accepted by darwin::getArchTypeForMachOArchName
// is translated by MachO::TranslateArgs into the expected triple and CPU, and that
// spellings only handled by TranslateArgs are rejected. Update both functions
// and this test together.

// RUN: %clang --target=x86_64-apple-macosx10.9 -arch i386 -### -c %s 2>&1 \
// RUN:   | FileCheck %s --check-prefix=I386
// RUN: %clang --target=x86_64-apple-macosx10.9 -arch i486 -### -c %s 2>&1 \
// RUN:   | FileCheck %s --check-prefix=I486
// RUN: %clang --target=x86_64-apple-macosx10.9 -arch i586 -### -c %s 2>&1 \
// RUN:   | FileCheck %s --check-prefix=I586
// RUN: %clang --target=x86_64-apple-macosx10.9 -arch i686 -### -c %s 2>&1 \
// RUN:   | FileCheck %s --check-prefix=I686
// RUN: %clang --target=x86_64-apple-macosx10.9 -arch x86_64 -### -c %s 2>&1 \
// RUN:   | FileCheck %s --check-prefix=X86-64
// RUN: %clang --target=x86_64-apple-macosx10.9 -arch x86_64h -### -c %s 2>&1 \
// RUN:   | FileCheck %s --check-prefix=X86-64H
// RUN: %clang --target=x86_64-apple-macosx10.9 -arch arm -### -c %s 2>&1 \
// RUN:   | FileCheck %s --check-prefix=ARM
// RUN: %clang --target=x86_64-apple-macosx10.9 -arch armv4t -### -c %s 2>&1 \
// RUN:   | FileCheck %s --check-prefix=ARMV4T
// RUN: %clang --target=x86_64-apple-macosx10.9 -arch armv5 -### -c %s 2>&1 \
// RUN:   | FileCheck %s --check-prefix=ARMV5
// RUN: %clang --target=x86_64-apple-macosx10.9 -arch xscale -### -c %s 2>&1 \
// RUN:   | FileCheck %s --check-prefix=XSCALE
// RUN: %clang --target=x86_64-apple-macosx10.9 -arch armv6 -### -c %s 2>&1 \
// RUN:   | FileCheck %s --check-prefix=ARMV6
// RUN: %clang --target=x86_64-apple-macosx10.9 -arch armv6m -### -c %s 2>&1 \
// RUN:   | FileCheck %s --check-prefix=ARMV6M
// RUN: %clang --target=x86_64-apple-macosx10.9 -arch armv7 -### -c %s 2>&1 \
// RUN:   | FileCheck %s --check-prefix=ARMV7
// RUN: %clang --target=x86_64-apple-macosx10.9 -arch armv7em -### -c %s 2>&1 \
// RUN:   | FileCheck %s --check-prefix=ARMV7EM
// RUN: %clang --target=x86_64-apple-macosx10.9 -arch armv7k -### -c %s 2>&1 \
// RUN:   | FileCheck %s --check-prefix=ARMV7K
// RUN: %clang --target=x86_64-apple-macosx10.9 -arch armv7m -### -c %s 2>&1 \
// RUN:   | FileCheck %s --check-prefix=ARMV7M
// RUN: %clang --target=x86_64-apple-macosx10.9 -arch armv7s -### -c %s 2>&1 \
// RUN:   | FileCheck %s --check-prefix=ARMV7S
// RUN: %clang --target=x86_64-apple-macosx10.9 -arch arm64 -### -c %s 2>&1 \
// RUN:   | FileCheck %s --check-prefix=ARM64
// RUN: %clang --target=x86_64-apple-macosx10.9 -arch arm64e -### -c %s 2>&1 \
// RUN:   | FileCheck %s --check-prefix=ARM64E
// RUN: %clang --target=x86_64-apple-macosx10.9 -arch arm64_32 -### -c %s 2>&1 \
// RUN:   | FileCheck %s --check-prefix=ARM64-32

// I386: "-triple" "i386-apple-macosx10.9.0"
// I386-SAME: "-target-cpu" "yonah"
// I486: "-triple" "i486-apple-macosx10.9.0"
// I486-SAME: "-target-cpu" "i486"
// I586: "-triple" "i586-apple-macosx10.9.0"
// I586-SAME: "-target-cpu" "i586"
// I686: "-triple" "i686-apple-macosx10.9.0"
// I686-SAME: "-target-cpu" "i686"
// X86-64: "-triple" "x86_64-apple-macosx10.9.0"
// X86-64-SAME: "-target-cpu" "core2"
// X86-64H: "-triple" "x86_64h-apple-macosx10.9.0"
// X86-64H-SAME: "-target-cpu" "core-avx2"
// ARM: "-triple" "armv4t-apple-macosx10.9.0"
// ARM-SAME: "-target-cpu" "arm7tdmi"
// ARMV4T: "-triple" "armv4t-apple-macosx10.9.0"
// ARMV4T-SAME: "-target-cpu" "arm7tdmi"
// ARMV5: "-triple" "armv5e-apple-macosx10.9.0"
// ARMV5-SAME: "-target-cpu" "arm926ej-s"
// XSCALE: "-triple" "armv5e-apple-macosx10.9.0"
// XSCALE-SAME: "-target-cpu" "xscale"
// ARMV6: "-triple" "armv6k-apple-macosx10.9.0"
// ARMV6-SAME: "-target-cpu" "mpcore"
// ARMV6M: "-triple" "thumbv6m-apple-unknown-macho"
// ARMV6M-SAME: "-target-cpu" "cortex-m0"
// ARMV7: "-triple" "thumbv7-apple-macosx10.9.0"
// ARMV7-SAME: "-target-cpu" "generic"
// ARMV7EM: "-triple" "thumbv7em-apple-unknown-macho"
// ARMV7EM-SAME: "-target-cpu" "cortex-m4"
// ARMV7K: "-triple" "thumbv7k-apple-macosx10.9.0"
// ARMV7K-SAME: "-target-cpu" "cortex-a7"
// ARMV7M: "-triple" "thumbv7m-apple-unknown-macho"
// ARMV7M-SAME: "-target-cpu" "cortex-m3"
// ARMV7S: "-triple" "thumbv7s-apple-macosx10.9.0"
// ARMV7S-SAME: "-target-cpu" "swift"
// ARM64: "-triple" "arm64-apple-macosx10.9.0"
// ARM64-SAME: "-target-cpu" "apple-m1"
// ARM64E: "-triple" "arm64e-apple-macosx10.9.0"
// ARM64E-SAME: "-target-cpu" "apple-m1"
// ARM64-32: "-triple" "arm64_32-apple-macosx10.9.0"
// ARM64-32-SAME: "-target-cpu" "apple-s4"

// RUN: not %clang --target=x86_64-apple-macosx10.9 -arch ppc -### -c %s 2>&1 \
// RUN:   | FileCheck %s --check-prefix=INVALID -DARCH=ppc
// RUN: not %clang --target=x86_64-apple-macosx10.9 -arch ppc970 -### -c %s 2>&1 \
// RUN:   | FileCheck %s --check-prefix=INVALID -DARCH=ppc970
// RUN: not %clang --target=x86_64-apple-macosx10.9 -arch ppc64 -### -c %s 2>&1 \
// RUN:   | FileCheck %s --check-prefix=INVALID -DARCH=ppc64
// RUN: not %clang --target=x86_64-apple-macosx10.9 -arch pentium2 -### -c %s 2>&1 \
// RUN:   | FileCheck %s --check-prefix=INVALID -DARCH=pentium2
// INVALID: error: invalid arch name '-arch [[ARCH]]'
