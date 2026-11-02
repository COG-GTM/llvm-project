#!/usr/bin/env python3
"""Checks write_cmake_config() `values` lists against their CMake templates.

The GN build recreates CMake configure_file() outputs (config.h,
llvm-config.h, __config_site, lit.site.cfg.py, ...) with write_cmake_config(),
and every call site lists the KEY=VALUE pairs the template needs by hand.
write_cmake_config.py fails at build time if the template references a key
that isn't passed, or if a passed key is unused. sync_source_lists_from_cmake.py
only looks at source lists, so this script reports that kind of drift instead.

For each write_cmake_config() call (and each call of a local template that
wraps it with `input = invoker.input`) whose `input` is a string literal, this
collects every "KEY=..." string literal in the call and compares that set with
the keys the input template references (${KEY}, @KEY@, #cmakedefine KEY,
#cmakedefine01 KEY).

This is a static, best-effort check: keys set in any `if` branch count as
passed, and calls with computed inputs are skipped (pass -v to list them).
The build itself remains the source of truth.

Exits with status 1 if any difference was found.
"""

import argparse
import os
import re
import sys

import write_cmake_config

gn_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(gn_dir)))
secondary = os.path.join(gn_dir, "secondary")

string_re = re.compile(r'"((?:[^"\\]|\\.)*)"')
key_re = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)=")
call_re = re.compile(r"\b([A-Za-z_]\w*)\s*\(([^()]*)\)\s*\{")
input_literal_re = re.compile(r'^\s*input\s*=\s*"([^"$]*)"\s*$', re.MULTILINE)
input_invoker_re = re.compile(r"^\s*input\s*=\s*invoker\.input\s*$", re.MULTILINE)


def strip_comments(text):
    """Blanks out GN '#' comments, keeping string literals and offsets."""
    out = []
    for line in text.splitlines(True):
        in_str = False
        i = 0
        while i < len(line):
            c = line[i]
            if c == "\\" and in_str:
                i += 2
                continue
            if c == '"':
                in_str = not in_str
            elif c == "#" and not in_str:
                line = line[:i] + " " * (len(line.rstrip("\n")) - i) + "\n"
                break
            i += 1
        out.append(line)
    return "".join(out)


def find_calls(text):
    """Yields (name, arg, body_start, body_end) for top-level-or-nested calls."""
    for m in call_re.finditer(text):
        depth = 0
        in_str = False
        i = m.end() - 1
        while i < len(text):
            c = text[i]
            if in_str:
                if c == "\\":
                    i += 1
                elif c == '"':
                    in_str = False
            elif c == '"':
                in_str = True
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        yield m.group(1), m.group(2).strip(), m.end(), i


def literal_keys(body):
    keys = set()
    for m in string_re.finditer(body):
        k = key_re.match(m.group(1))
        if k:
            keys.add(k.group(1))
    return keys


def wrapper_templates(text):
    """Returns {template name: keys} for templates wrapping write_cmake_config."""
    wrappers = {}
    for name, arg, start, end in find_calls(text):
        if name != "template":
            continue
        body = text[start:end]
        for inner, _, istart, iend in find_calls(body):
            ibody = body[istart:iend]
            if inner == "write_cmake_config" and input_invoker_re.search(ibody):
                wrappers[arg.strip('"')] = literal_keys(ibody)
    return wrappers


def rel(path):
    return os.path.relpath(path, repo_root).replace(os.sep, "/")


def resolve_input(gn_file, inp):
    if inp.startswith("//"):
        return os.path.join(repo_root, inp[2:])
    gn_rel_dir = os.path.relpath(os.path.dirname(gn_file), secondary)
    if gn_rel_dir.startswith(".."):
        return None  # Relative input in a file outside secondary/.
    return os.path.join(repo_root, gn_rel_dir, inp)


def gn_files():
    for root, _, files in os.walk(gn_dir):
        for f in sorted(files):
            if f == "BUILD.gn" or f.endswith(".gni"):
                yield os.path.join(root, f)


def check(verbose=False):
    """Prints a report and returns True if any difference was found."""
    found = False
    unchecked = []
    for gn_file in sorted(gn_files()):
        with open(gn_file) as f:
            text = strip_comments(f.read())
        if "write_cmake_config" not in text:
            continue
        wrappers = wrapper_templates(text)
        for name, arg, start, end in find_calls(text):
            if name != "write_cmake_config" and name not in wrappers:
                continue
            body = text[start:end]
            call = "%s(%s)" % (name, arg)
            m = input_literal_re.search(body)
            if not m:
                if not input_invoker_re.search(body):
                    unchecked.append("%s: %s" % (rel(gn_file), call))
                continue
            template = resolve_input(gn_file, m.group(1))
            if template is None:
                unchecked.append("%s: %s" % (rel(gn_file), call))
                continue
            if not os.path.exists(template):
                found = True
                print("%s: %s" % (rel(gn_file), call))
                print("  input %s does not exist" % rel(template))
                continue
            passed = literal_keys(body) | wrappers.get(name, set())
            with open(template) as f:
                wanted = write_cmake_config.template_keys(f.readlines())
            missing = sorted(wanted - passed)
            unused = sorted(passed - wanted)
            if not missing and not unused:
                continue
            found = True
            print("%s: %s, input %s" % (rel(gn_file), call, rel(template)))
            for k in missing:
                print("  add to values:      %s=" % k)
            for k in unused:
                print("  remove from values: %s" % k)
    if verbose and unchecked:
        print("not checked (input is not a string literal):")
        for u in unchecked:
            print("  " + u)
    return found


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="list skipped call sites"
    )
    args = parser.parse_args()
    if check(args.verbose):
        sys.exit(1)


if __name__ == "__main__":
    main()
