#!/usr/bin/env python3
# ===-- check_netbsd_syscalls.py --------------------------------------------===#
#
# Part of the LLVM Project, under the Apache License v2.0 with LLVM Exceptions.
# See https://llvm.org/LICENSE.txt for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# ===------------------------------------------------------------------------===#
#
# Checks that the two outputs of generate_netbsd_syscalls.awk are consistent:
#  - both carry the banner the generator currently emits,
#  - both come from the same generation (same date and syscalls.master
#    revision),
#  - the syscalls declared in the public header and defined in the .inc match.
#
# Regenerating needs a NetBSD syscalls.master, so this cannot rerun the
# generator; it catches hand edits to one output and stale generator changes.
#
# ===------------------------------------------------------------------------===#

import argparse
import os
import re
import sys

GENERATOR = "compiler-rt/utils/generate_netbsd_syscalls.awk"
HEADER = "compiler-rt/include/sanitizer/netbsd_syscall_hooks.h"
INC = "compiler-rt/lib/sanitizer_common/sanitizer_syscalls_netbsd.inc"

BANNER_KEYS = ("Generated date", "Generated from")


def read(root, path):
    with open(os.path.join(root, path), encoding="utf-8") as f:
        return f.read()


def awk_string(expr, variables):
    """Evaluates an awk concatenation of string literals and known variables."""
    out = []
    for literal, name in re.findall(r'"((?:[^"\\]|\\.)*)"|(\w+)', expr):
        if name:
            if name not in variables:
                return None
            out.append(variables[name])
        else:
            out.append(literal.replace('\\"', '"').replace("\\\\", "\\"))
    return "".join(out)


def expected_banner(generator):
    """Returns the static banner lines pbanner() emits, in order."""
    variables = dict(
        re.findall(r'^\s*(\w+) = "((?:[^"\\]|\\.)*)"\s*$', generator, re.M)
    )
    for name, expr in re.findall(r"^\s*(\w+) = (\"[^\n]*)$", generator, re.M):
        value = awk_string(expr, variables)
        if value is not None:
            variables[name] = value
    body = re.search(r"^function pbanner\(\)\n\{\n(.*?)^\}", generator, re.M | re.S)
    if not body:
        return None
    lines = []
    for expr in re.findall(r"^\s*pcmd\((.*)\)\s*$", body.group(1), re.M):
        if "strftime" in expr or "syscallmasterversion" in expr:
            continue
        line = awk_string(expr, variables)
        if line is None:
            return None
        lines.append(line)
    return lines


def banner_fields(text):
    fields = {}
    for key in BANNER_KEYS:
        m = re.search(r"^// %s: (.+)$" % re.escape(key), text, re.M)
        fields[key] = m.group(1).strip() if m else None
    return fields


def check(root):
    errors = []
    generator = read(root, GENERATOR)
    header = read(root, HEADER)
    inc = read(root, INC)

    banner = expected_banner(generator)
    if not banner:
        errors.append("%s: cannot find the pbanner() banner lines" % GENERATOR)
        banner = []
    for line in banner:
        m = re.match(r"// Generated with: (.+)$", line)
        if m and not os.path.isfile(os.path.join(root, m.group(1))):
            errors.append(
                "%s: generator path %r does not exist" % (GENERATOR, m.group(1))
            )

    for path, text in ((HEADER, header), (INC, inc)):
        if "// DO NOT EDIT! THIS FILE HAS BEEN GENERATED!" not in text:
            errors.append("%s: missing the DO NOT EDIT marker" % path)
        lines = text.splitlines()
        if banner:
            starts = [i for i, l in enumerate(lines) if l == banner[0]]
            if not starts or lines[starts[0] : starts[0] + len(banner)] != banner:
                errors.append(
                    "%s: banner does not match what %s emits:\n    %s"
                    % (path, GENERATOR, "\n    ".join(banner))
                )
        for key, value in banner_fields(text).items():
            if value is None:
                errors.append("%s: missing '// %s:' banner line" % (path, key))

    hfields, ifields = banner_fields(header), banner_fields(inc)
    for key in BANNER_KEYS:
        if hfields[key] and ifields[key] and hfields[key] != ifields[key]:
            errors.append(
                "%s differs between the outputs:\n    %s: %s\n    %s: %s"
                % (key, HEADER, hfields[key], INC, ifields[key])
            )

    for kind in ("pre", "post"):
        declared = set(
            re.findall(
                r"^void __sanitizer_syscall_%s_impl_(\w+)\(" % kind, header, re.M
            )
        )
        defined = set(re.findall(r"^%s_SYSCALL\((\w+)\)" % kind.upper(), inc, re.M))
        for name in sorted(declared - defined):
            errors.append(
                "%s: %s hook '%s' declared but not defined in %s"
                % (HEADER, kind, name, INC)
            )
        for name in sorted(defined - declared):
            errors.append(
                "%s: %s hook '%s' defined but not declared in %s"
                % (INC, kind, name, HEADER)
            )
        if not declared:
            errors.append("%s: no %s hooks found" % (HEADER, kind))

    return errors


def main():
    default_root = os.path.normpath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
    )
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=default_root, help="llvm-project checkout")
    args = parser.parse_args()
    errors = check(args.root)
    for e in errors:
        print("error: " + e, file=sys.stderr)
    if errors:
        print(
            "\nRegenerate both files together (see the banner in %s)." % HEADER,
            file=sys.stderr,
        )
        return 1
    print("NetBSD syscall hooks: header, .inc and generator are consistent.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
