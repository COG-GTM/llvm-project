#!/usr/bin/env python3
#
# ===- check_x86_cpu_model_abi.py - X86 __cpu_model ABI consistency check --===#
#
# Part of the LLVM Project, under the Apache License v2.0 with LLVM Exceptions.
# See https://llvm.org/LICENSE.txt for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# ===-----------------------------------------------------------------------===#

"""Check that compiler-rt's X86 __cpu_model enums match X86TargetParser.def.

Clang lowers __builtin_cpu_is, __builtin_cpu_supports and X86 function
multiversioning to field indices and bit positions in __cpu_model and
__cpu_features2, taking the values from llvm/TargetParser/X86TargetParser.def.
compiler-rt/lib/builtins/cpu_model/x86.c fills those structures at runtime
using its own copies of the ProcessorVendors, ProcessorTypes,
ProcessorSubtypes and ProcessorFeatures enums. This script parses both files
and reports every difference so that the two copies cannot drift silently.

Usage:
  check_x86_cpu_model_abi.py [--def X86TargetParser.def] [--x86-c x86.c]

Paths default to the files in the monorepo checkout containing this script.
Exits with status 0 when the files agree and 1 otherwise.
"""

import argparse
import os
import re
import sys

# compiler-rt names that intentionally differ from the X86TargetParser.def
# ENUM name for the same ABI bit.
COMPILER_RT_FEATURE_ALIASES = {
    "LAHF_LM": "SAHF",
    "LM": "64BIT",
}

# Clang reads __cpu_model.__cpu_features[1] plus __cpu_features2[3], i.e. 128
# feature bits in total (see CodeGenFunction::EmitX86CpuSupports).
MAX_FEATURE_BITS = 128

_DEF_ENTRY_RE = re.compile(r"^\s*(X86_\w+)\s*\(([^)]*)\)", re.M)
_PP_DIRECTIVE_RE = re.compile(r"^[ \t]*#(?:[^\n]*\\\n)*[^\n]*", re.M)


def _strip_comments(text):
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
    return re.sub(r"//[^\n]*", "", text)


def parse_def(path):
    """Return the ABI-relevant entries of X86TargetParser.def.

    Vendors, types and subtypes are numbered from 1 in declaration order
    (index 0 is the *_DUMMY entry of the enums in X86TargetParser.h).
    Features map ENUM -> ABI_VALUE for X86_FEATURE_COMPAT and
    X86_MICROARCH_LEVEL entries.
    """
    vendors, types, subtypes, features = [], [], [], []
    with open(path) as f:
        text = _PP_DIRECTIVE_RE.sub("", _strip_comments(f.read()))
    for m in _DEF_ENTRY_RE.finditer(text):
        macro = m.group(1)
        args = [a.strip() for a in m.group(2).split(",")]
        if macro == "X86_VENDOR":
            vendors.append(args[0])
        elif macro == "X86_CPU_TYPE":
            types.append(args[0])
        elif macro == "X86_CPU_SUBTYPE":
            subtypes.append(args[0])
        elif macro in ("X86_FEATURE_COMPAT", "X86_MICROARCH_LEVEL"):
            features.append((args[0], int(args[3], 0)))
    return {
        "vendors": {name: i + 1 for i, name in enumerate(vendors)},
        "types": {name: i + 1 for i, name in enumerate(types)},
        "subtypes": {name: i + 1 for i, name in enumerate(subtypes)},
        "features": features,
    }


def parse_c_enum(text, enum_name, path):
    m = re.search(r"\benum\s+%s\s*\{(.*?)\}\s*;" % enum_name, text, re.S)
    if not m:
        raise ValueError("%s: enum %s not found" % (path, enum_name))
    values = {}
    next_value = 0
    for item in m.group(1).split(","):
        item = item.strip()
        if not item:
            continue
        name, _, value = (p.strip() for p in item.partition("="))
        if value:
            next_value = int(value, 0)
        if name in values:
            raise ValueError("%s: duplicate enumerator %s" % (path, name))
        values[name] = next_value
        next_value += 1
    return values


def parse_compiler_rt(path):
    with open(path) as f:
        text = _strip_comments(f.read())
    return {
        "vendors": parse_c_enum(text, "ProcessorVendors", path),
        "types": parse_c_enum(text, "ProcessorTypes", path),
        "subtypes": parse_c_enum(text, "ProcessorSubtypes", path),
        "features": parse_c_enum(text, "ProcessorFeatures", path),
    }


def _compare_indexed(kind, enum_name, def_vals, rt_vals, trailer, errors):
    """Compare a 1-based vendor/type/subtype enum including its trailer."""
    expected = dict(def_vals)
    expected[trailer] = len(def_vals) + 1
    for name, value in sorted(expected.items(), key=lambda kv: kv[1]):
        if name not in rt_vals:
            errors.append(
                "%s %s = %d is in X86TargetParser.def but missing from "
                "compiler-rt enum %s" % (kind, name, value, enum_name)
            )
        elif rt_vals[name] != value:
            errors.append(
                "%s %s: X86TargetParser.def value %d != compiler-rt value %d"
                % (kind, name, value, rt_vals[name])
            )
    for name, value in sorted(rt_vals.items(), key=lambda kv: kv[1]):
        if name not in expected:
            errors.append(
                "%s %s = %d is in compiler-rt enum %s but missing from "
                "X86TargetParser.def" % (kind, name, value, enum_name)
            )


def check(def_path, x86_c_path):
    d = parse_def(def_path)
    rt = parse_compiler_rt(x86_c_path)
    errors = []

    # compiler-rt's ProcessorVendors ends with VENDOR_OTHER, VENDOR_MAX while
    # X86TargetParser.h ends with VENDOR_OTHER only.
    rt_vendors = dict(rt["vendors"])
    rt_vendors.pop("VENDOR_MAX", None)
    _compare_indexed(
        "vendor",
        "ProcessorVendors",
        d["vendors"],
        rt_vendors,
        "VENDOR_OTHER",
        errors,
    )
    _compare_indexed(
        "CPU type",
        "ProcessorTypes",
        d["types"],
        rt["types"],
        "CPU_TYPE_MAX",
        errors,
    )
    _compare_indexed(
        "CPU subtype",
        "ProcessorSubtypes",
        d["subtypes"],
        rt["subtypes"],
        "CPU_SUBTYPE_MAX",
        errors,
    )

    def_features = {}
    seen_abi = {}
    for name, abi in d["features"]:
        if abi in seen_abi:
            errors.append(
                "feature %s: ABI_VALUE %d already used by %s in "
                "X86TargetParser.def" % (name, abi, seen_abi[abi])
            )
        seen_abi.setdefault(abi, name)
        if abi >= MAX_FEATURE_BITS:
            errors.append(
                "feature %s: ABI_VALUE %d does not fit in the %d bits of "
                "__cpu_features/__cpu_features2" % (name, abi, MAX_FEATURE_BITS)
            )
        def_features[name] = abi

    rt_features = {}
    rt_max = None
    for name, value in rt["features"].items():
        if name == "CPU_FEATURE_MAX":
            rt_max = value
            continue
        if not name.startswith("FEATURE_"):
            errors.append(
                "compiler-rt enum ProcessorFeatures entry %s lacks the "
                "FEATURE_ prefix" % name
            )
            continue
        base = name[len("FEATURE_") :]
        rt_features[COMPILER_RT_FEATURE_ALIASES.get(base, base)] = (name, value)

    for name, abi in sorted(def_features.items(), key=lambda kv: kv[1]):
        if name not in rt_features:
            errors.append(
                "feature %s (ABI_VALUE %d) is in X86TargetParser.def but "
                "missing from compiler-rt enum ProcessorFeatures" % (name, abi)
            )
        elif rt_features[name][1] != abi:
            errors.append(
                "feature %s: X86TargetParser.def ABI_VALUE %d != compiler-rt "
                "%s = %d" % (name, abi, rt_features[name][0], rt_features[name][1])
            )
    for name, (rt_name, value) in sorted(rt_features.items(), key=lambda kv: kv[1][1]):
        if name not in def_features:
            errors.append(
                "feature %s = %d is in compiler-rt enum ProcessorFeatures but "
                "has no X86_FEATURE_COMPAT/X86_MICROARCH_LEVEL entry in "
                "X86TargetParser.def" % (rt_name, value)
            )

    if rt_max is None:
        errors.append("compiler-rt enum ProcessorFeatures lacks CPU_FEATURE_MAX")
    elif def_features and rt_max <= max(def_features.values()):
        errors.append(
            "compiler-rt CPU_FEATURE_MAX = %d must be greater than the largest "
            "X86TargetParser.def ABI_VALUE %d" % (rt_max, max(def_features.values()))
        )

    return d, errors


def main(argv=None):
    root = os.path.normpath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
    )
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--def",
        dest="def_path",
        default=os.path.join(
            root, "llvm", "include", "llvm", "TargetParser", "X86TargetParser.def"
        ),
        help="path to llvm/include/llvm/TargetParser/X86TargetParser.def",
    )
    parser.add_argument(
        "--x86-c",
        dest="x86_c_path",
        default=os.path.join(
            root, "compiler-rt", "lib", "builtins", "cpu_model", "x86.c"
        ),
        help="path to compiler-rt/lib/builtins/cpu_model/x86.c",
    )
    args = parser.parse_args(argv)

    d, errors = check(args.def_path, args.x86_c_path)
    for e in errors:
        print("error: %s" % e, file=sys.stderr)
    if errors:
        print(
            "error: compiler-rt/lib/builtins/cpu_model/x86.c and "
            "X86TargetParser.def are out of sync (%d problem(s))" % len(errors),
            file=sys.stderr,
        )
        return 1
    print(
        "OK: %d vendors, %d CPU types, %d CPU subtypes, %d features match"
        % (len(d["vendors"]), len(d["types"]), len(d["subtypes"]), len(d["features"]))
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
