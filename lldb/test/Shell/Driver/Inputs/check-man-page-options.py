"""Check that docs/man/lldb.rst documents exactly the options in `lldb --help`.

Usage: check-man-page-options.py <lldb.rst> <lldb --help output>
"""

import re
import sys


def normalize(option):
    # "--file <filename>" and "--repl=<flags>" become "--file" and "--repl=".
    return re.sub(r"<[^>]*>$", "", option)


def rst_options(path):
    options = set()
    with open(path) as f:
        for line in f:
            match = re.match(r"\.\. option::\s+(\S+)", line)
            if match:
                options.add(normalize(match.group(1)))
    return options


def help_options(path):
    options = set()
    with open(path) as f:
        for line in f:
            if line.startswith("EXAMPLES:"):
                break
            match = re.match(r"  (-\S+)", line)
            if match:
                options.add(normalize(match.group(1)))
    return options


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    documented = rst_options(sys.argv[1])
    accepted = help_options(sys.argv[2])
    if not documented or not accepted:
        sys.exit("error: no options found in %s or %s" % tuple(sys.argv[1:]))

    status = 0
    for option in sorted(documented - accepted):
        print("error: lldb.rst documents %s, which lldb does not accept" % option)
        status = 1
    for option in sorted(accepted - documented):
        print("error: lldb accepts %s, which lldb.rst does not document" % option)
        status = 1
    return status


if __name__ == "__main__":
    sys.exit(main())
