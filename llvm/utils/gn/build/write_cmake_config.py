#!/usr/bin/env python3
r"""Emulates the bits of CMake's configure_file() function needed in LLVM.

The CMake build uses configure_file() for several things.  This emulates that
function for the GN build.  In the GN build, this runs at build time instead
of at generator time.

Takes a list of KEY=VALUE pairs (where VALUE can be empty).

The sequence `\` `n` in each VALUE is replaced by a newline character.

On each line, replaces '${KEY}' or '@KEY@' with VALUE.

Then, handles these special cases (note that FOO= sets the value of FOO to the
empty string, which is falsy, but FOO=0 sets it to '0' which is truthy):

1.) #cmakedefine01 FOO
    Checks if key FOO is set to a truthy value, and depending on that prints
    one of the following two lines:

        #define FOO 1
        #define FOO 0

2.) #cmakedefine FOO [...]
    Checks if key FOO is set to a truthy value, and depending on that prints
    one of the following two lines:

        #define FOO [...]
        /* #undef FOO */

Fails if any of the KEY=VALUE arguments aren't needed for processing the
input file, or if the input file references keys that weren't passed in.

The KEY=VALUE list is maintained by hand in the `values` of each
write_cmake_config() call in a BUILD.gn file. When a CMake configure_file()
template gains or loses a key, that list must be updated to match; see
"Syncing GN files from CMake files" in llvm/utils/gn/README.rst and
check_cmake_config_values.py.
"""

import argparse
import os
import re
import sys

# Matches e.g. '${FOO}' or '@FOO@' and captures FOO in group 1 or 2.
var_re = re.compile(r"\$\{([^}]*)\}|@([^@]*)@")


def template_keys(in_lines):
    """Returns the set of keys that the template lines reference."""
    keys = set()
    for in_line in in_lines:
        for m in var_re.finditer(in_line):
            keys.add(m.group(1) or m.group(2))
        if in_line.startswith("#cmakedefine01 ") or in_line.startswith("#cmakedefine "):
            parts = in_line.split()
            if len(parts) > 1 and not var_re.search(parts[1]):
                keys.add(parts[1])
    return keys


def report_mismatch(args, missing, unused):
    where = args.gn_target or "the write_cmake_config() call"
    if missing:
        print(
            "error: %s references keys missing from 'values' in %s:"
            % (args.input, where),
            file=sys.stderr,
        )
        print("    " + "\n    ".join(sorted(missing)), file=sys.stderr)
        print(
            '  add e.g. "%s=" (empty is false for #cmakedefine)' % sorted(missing)[0],
            file=sys.stderr,
        )
    if unused:
        print("unused values args:", file=sys.stderr)
        print("    " + "\n    ".join(sorted(unused)), file=sys.stderr)
        print(
            "error: %s does not reference these keys; remove them from 'values' in %s"
            % (args.input, where),
            file=sys.stderr,
        )
    print(
        "note: the CMake template changed; see 'Syncing GN files from CMake "
        "files'\n"
        "      in llvm/utils/gn/README.rst and run "
        "llvm/utils/gn/build/check_cmake_config_values.py",
        file=sys.stderr,
    )


def main():
    parser = argparse.ArgumentParser(
        epilog=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("input", help="input file")
    parser.add_argument("values", nargs="*", help="several KEY=VALUE pairs")
    parser.add_argument("-o", "--output", required=True, help="output file")
    parser.add_argument(
        "--gn-target", help="GN label of the caller, used in error messages"
    )
    args = parser.parse_args()

    values = {}
    for value in args.values:
        key, val = value.split("=", 1)
        if key in values:
            print('duplicate key "%s" in args' % key, file=sys.stderr)
            return 1
        values[key] = val.replace("\\n", "\n")
    unused_values = set(values.keys())
    missing_values = set()

    def lookup(key):
        if key not in values:
            missing_values.add(key)
            return ""
        unused_values.discard(key)
        return values[key]

    with open(args.input) as f:
        in_lines = f.readlines()
    out_lines = []
    for in_line in in_lines:

        def repl(m):
            return lookup(m.group(1) or m.group(2))

        in_line = var_re.sub(repl, in_line)
        if in_line.startswith("#cmakedefine01 "):
            _, var = in_line.split()
            if lookup(var) == "0":
                print('error: "%s=0" used with #cmakedefine01 %s' % (var, var))
                print("       '0' evaluates as truthy with #cmakedefine01")
                print('       use "%s=" instead' % var)
                return 1
            in_line = "#define %s %d\n" % (var, 1 if lookup(var) else 0)
        elif in_line.startswith("#cmakedefine "):
            _, var = in_line.split(None, 1)
            try:
                var, val = var.split(None, 1)
                in_line = "#define %s %s" % (var, val)  # val ends in \n.
            except:
                var = var.rstrip()
                in_line = "#define %s\n" % var
            if not lookup(var):
                in_line = "/* #undef %s */\n" % var
        out_lines.append(in_line)

    if missing_values or unused_values:
        report_mismatch(args, missing_values, unused_values)
        return 1

    output = "".join(out_lines)

    leftovers = var_re.findall(output)
    if leftovers:
        print(
            "unprocessed values:\n",
            "\n".join([x[0] or x[1] for x in leftovers]),
            file=sys.stderr,
        )
        return 1

    def read(filename):
        with open(args.output) as f:
            return f.read()

    if not os.path.exists(args.output) or read(args.output) != output:
        with open(args.output, "w") as f:
            f.write(output)
        os.chmod(args.output, os.stat(args.input).st_mode & 0o777)


if __name__ == "__main__":
    sys.exit(main())
