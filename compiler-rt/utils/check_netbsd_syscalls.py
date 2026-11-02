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
#  - both carry, in order, the banner the generator currently emits,
#  - both come from the same generation (same date and syscalls.master
#    revision),
#  - the public __sanitizer_syscall_{pre,post}_* macros, the _impl_
#    declarations in the header and the .inc definitions name the same
#    syscalls under the same preprocessor guards.
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

WRAPPER_GUARDS = {
    "#ifndef SANITIZER_NETBSD_SYSCALL_HOOKS_H",
    "#if SANITIZER_NETBSD",
}


def read(root, path):
    with open(os.path.join(root, path), encoding="utf-8") as f:
        return f.read()


def awk_tokens(expr):
    for literal, name in re.findall(r'"((?:[^"\\]|\\.)*)"|(\w+)', expr):
        if name:
            yield None, name
        else:
            yield literal.replace('\\"', '"').replace("\\\\", "\\"), None


def awk_string(expr, variables):
    """Evaluates an awk concatenation of string literals and known variables."""
    out = []
    for literal, name in awk_tokens(expr):
        if name is not None:
            if name not in variables:
                return None
            out.append(variables[name])
        else:
            out.append(literal)
    return "".join(out)


def expected_banner(generator):
    """Returns pbanner()'s lines, in order, as (key, text) pairs.

    Static lines have key None and their exact text. Lines whose value is
    computed at generation time (date, syscalls.master revision) have the
    literal prefix as text and the banner key (e.g. "Generated date") as key.
    """
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
        prefix, dynamic = [], False
        for literal, name in awk_tokens(expr):
            if name is None:
                prefix.append(literal)
            elif name in variables:
                prefix.append(variables[name])
            else:
                dynamic = True
                break
        text = "".join(prefix)
        if dynamic:
            key = text.strip().lstrip("/").strip().rstrip(":").strip()
            if not key:
                return None
            lines.append((key, text))
        else:
            lines.append((None, text))
    return lines


def match_banner(lines, banner):
    """Returns {key: value} if `banner` appears contiguously in `lines`."""
    for i, line in enumerate(lines):
        if line != banner[0][1] and banner[0][0] is None:
            continue
        fields = {}
        for (key, text), actual in zip(banner, lines[i:]):
            if key is None:
                if actual != text:
                    break
            elif actual.startswith(text) and actual[len(text) :].strip():
                fields[key] = actual[len(text) :].strip()
            else:
                break
        else:
            if len(lines) - i >= len(banner):
                return fields
    return None


def logical_lines(text):
    return re.sub(r"\\\n", " ", text).splitlines()


def hooks(text, pattern):
    """Maps each hook name matched by `pattern` to its preprocessor guards."""
    stack, found = [], {}
    for line in logical_lines(text):
        stripped = line.strip()
        if re.match(r"#\s*if", stripped):
            stack.append(re.sub(r"\s+", " ", stripped))
        elif re.match(r"#\s*else", stripped) and stack:
            stack[-1] = "#else of " + stack[-1]
        elif re.match(r"#\s*elif", stripped) and stack:
            stack[-1] = "%s after %s" % (re.sub(r"\s+", " ", stripped), stack[-1])
        elif re.match(r"#\s*endif", stripped) and stack:
            stack.pop()
        m = re.match(pattern, line)
        if m:
            guards = tuple(g for g in stack if g not in WRAPPER_GUARDS)
            found.setdefault(m.group(1), []).append((guards, m))
    return found


def compare_hooks(errors, label, left, right):
    (lpath, lhooks), (rpath, rhooks) = left, right
    for name in sorted(set(lhooks) - set(rhooks)):
        errors.append(
            "%s: %s '%s' has no counterpart in %s" % (lpath, label, name, rpath)
        )
    for name in sorted(set(rhooks) - set(lhooks)):
        errors.append(
            "%s: %s '%s' has no counterpart in %s" % (rpath, label, name, lpath)
        )
    for name in sorted(set(lhooks) & set(rhooks)):
        lg = sorted(g for g, _ in lhooks[name])
        rg = sorted(g for g, _ in rhooks[name])
        if lg != rg:
            errors.append(
                "%s '%s' is guarded differently:\n    %s: %s\n    %s: %s"
                % (label, name, lpath, lg, rpath, rg)
            )


def check(root):
    errors = []
    generator = read(root, GENERATOR)
    header = read(root, HEADER)
    inc = read(root, INC)

    banner = expected_banner(generator)
    if not banner:
        errors.append("%s: cannot find the pbanner() banner lines" % GENERATOR)
        banner = []
    for key, text in banner:
        m = re.match(r"// Generated with: (.+)$", text)
        if key is None and m and not os.path.isfile(os.path.join(root, m.group(1))):
            errors.append(
                "%s: generator path %r does not exist" % (GENERATOR, m.group(1))
            )

    fields = {}
    for path, text in ((HEADER, header), (INC, inc)):
        if "// DO NOT EDIT! THIS FILE HAS BEEN GENERATED!" not in text:
            errors.append("%s: missing the DO NOT EDIT marker" % path)
        if not banner:
            continue
        found = match_banner(text.splitlines(), banner)
        if found is None:
            errors.append(
                "%s: banner does not match what %s emits:\n    %s"
                % (
                    path,
                    GENERATOR,
                    "\n    ".join(t + ("<value>" if k else "") for k, t in banner),
                )
            )
        else:
            fields[path] = found

    if HEADER in fields and INC in fields:
        for key in fields[HEADER]:
            if fields[HEADER][key] != fields[INC].get(key):
                errors.append(
                    "%s differs between the outputs:\n    %s: %s\n    %s: %s"
                    % (key, HEADER, fields[HEADER][key], INC, fields[INC].get(key))
                )

    for kind in ("pre", "post"):
        public = hooks(
            header, r"#define __sanitizer_syscall_%s_(?!impl_)(\w+)\((.*)$" % kind
        )
        declared = hooks(header, r"void __sanitizer_syscall_%s_impl_(\w+)\(" % kind)
        defined = hooks(inc, r"%s_SYSCALL\((\w+)\)" % kind.upper())
        for name, entries in sorted(public.items()):
            for _, m in entries:
                if not re.search(
                    r"\b__sanitizer_syscall_%s_impl_%s\(" % (kind, re.escape(name)),
                    m.group(2),
                ):
                    errors.append(
                        "%s: public %s hook '%s' does not call "
                        "__sanitizer_syscall_%s_impl_%s"
                        % (HEADER, kind, name, kind, name)
                    )
        compare_hooks(
            errors,
            "%s hook" % kind,
            ("%s (public macros)" % HEADER, public),
            ("%s (impl declarations)" % HEADER, declared),
        )
        compare_hooks(
            errors,
            "%s hook" % kind,
            ("%s (impl declarations)" % HEADER, declared),
            ("%s (definitions)" % INC, defined),
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
