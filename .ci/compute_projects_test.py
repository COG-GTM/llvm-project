# Part of the LLVM Project, under the Apache License v2.0 with LLVM Exceptions.
# See https://llvm.org/LICENSE.txt for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
"""Tests for compute_projects.py"""

import pathlib
import re
import unittest

import compute_projects

GITHUB_DOCS = pathlib.Path(__file__).parent.parent / "llvm" / "docs" / "GitHub.rst"


def _parse_documented_exclusions() -> dict[str, set[str]]:
    """Parses the "Projects not tested by pre-merge CI" list in GitHub.rst."""
    lines = GITHUB_DOCS.read_text().splitlines()
    start = lines.index("Projects not tested by pre-merge CI")
    platform_prefixes = [
        ("Linux", "Linux"),
        ("Windows, only when a dependency changed", "Windows dependents"),
        ("Windows", "Windows"),
        ("macOS", "Darwin"),
    ]
    exclusions = {}
    current_platform = None
    current_bullet = None
    for line in lines[start + 2 :]:
        if re.fullmatch(r"[=\-^~]+", line):
            break
        for prefix, platform_name in platform_prefixes:
            if line.startswith(prefix):
                current_platform = platform_name
                exclusions[current_platform] = set()
                break
        if line.startswith("* "):
            current_bullet = line[2:]
        elif current_bullet is not None and line.startswith("  "):
            current_bullet += " " + line.strip()
        else:
            current_bullet = None
        if current_bullet is not None and ": " in current_bullet:
            names = current_bullet.split(": ", 1)[0]
            exclusions[current_platform].update(re.findall(r"``([^`]+)``", names))
    return exclusions


class TestComputeProjects(unittest.TestCase):
    def test_llvm(self):
        env_variables = compute_projects.get_env_variables(
            ["llvm/CMakeLists.txt"], "Linux"
        )
        self.assertEqual(
            env_variables["projects_to_build"],
            "bolt;clang;clang-tools-extra;flang;lld;lldb;llvm;mlir;polly",
        )
        self.assertEqual(
            env_variables["project_check_targets"],
            "check-bolt check-clang check-clang-tools check-flang check-lld check-lldb check-llvm check-mlir check-polly",
        )
        self.assertEqual(
            env_variables["runtimes_to_build"], "libcxx;libcxxabi;libunwind"
        )
        self.assertEqual(
            env_variables["runtimes_check_targets"],
            "",
        )
        self.assertEqual(
            env_variables["runtimes_check_targets_needs_reconfig"],
            "check-cxx check-cxxabi check-unwind",
        )

    def test_llvm_windows(self):
        env_variables = compute_projects.get_env_variables(
            ["llvm/CMakeLists.txt"], "Windows"
        )
        self.assertEqual(
            env_variables["projects_to_build"],
            "clang;clang-tools-extra;lld;llvm;mlir;polly",
        )
        self.assertEqual(
            env_variables["project_check_targets"],
            "check-clang check-clang-tools check-lld check-llvm check-mlir check-polly",
        )
        self.assertEqual(env_variables["runtimes_to_build"], "")
        self.assertEqual(
            env_variables["runtimes_check_targets"],
            "",
        )
        self.assertEqual(
            env_variables["runtimes_check_targets_needs_reconfig"],
            "",
        )

    def test_llvm_mac(self):
        env_variables = compute_projects.get_env_variables(
            ["llvm/CMakeLists.txt"], "Darwin"
        )
        self.assertEqual(
            env_variables["projects_to_build"],
            "clang;clang-tools-extra;lld;llvm;mlir",
        )
        self.assertEqual(
            env_variables["project_check_targets"],
            "check-clang check-clang-tools check-lld check-llvm check-mlir",
        )
        self.assertEqual(env_variables["runtimes_to_build"], "")
        self.assertEqual(
            env_variables["runtimes_check_targets"],
            "",
        )
        self.assertEqual(
            env_variables["runtimes_check_targets_needs_reconfig"],
            "",
        )

    def test_clang(self):
        env_variables = compute_projects.get_env_variables(
            ["clang/CMakeLists.txt"], "Linux"
        )
        self.assertEqual(
            env_variables["projects_to_build"],
            "clang;clang-tools-extra;lld;lldb;llvm",
        )
        self.assertEqual(
            env_variables["project_check_targets"],
            "check-clang check-clang-tools check-lldb",
        )
        self.assertEqual(
            env_variables["runtimes_to_build"], "compiler-rt;libcxx;libcxxabi;libunwind"
        )
        self.assertEqual(
            env_variables["runtimes_check_targets"],
            "check-compiler-rt",
        )
        self.assertEqual(
            env_variables["runtimes_check_targets_needs_reconfig"],
            "check-cxx check-cxxabi check-unwind",
        )
        self.assertEqual(
            env_variables["enable_cir"],
            "OFF",
        )

    def test_clang_windows(self):
        env_variables = compute_projects.get_env_variables(
            ["clang/CMakeLists.txt"], "Windows"
        )
        self.assertEqual(
            env_variables["projects_to_build"], "clang;clang-tools-extra;lld;llvm"
        )
        self.assertEqual(
            env_variables["project_check_targets"], "check-clang check-clang-tools"
        )
        self.assertEqual(env_variables["runtimes_to_build"], "compiler-rt")
        self.assertEqual(
            env_variables["runtimes_check_targets"],
            "check-compiler-rt",
        )
        self.assertEqual(
            env_variables["runtimes_check_targets_needs_reconfig"],
            "",
        )
        self.assertEqual(env_variables["enable_cir"], "OFF")

    def test_compiler_rt(self):
        env_variables = compute_projects.get_env_variables(
            ["compiler-rt/lib/asan/asan_allocator.cpp"], "Linux"
        )
        self.assertEqual(
            env_variables["projects_to_build"],
            "clang;lld",
        )
        self.assertEqual(
            env_variables["project_check_targets"],
            "",
        )
        self.assertEqual(env_variables["runtimes_to_build"], "compiler-rt")
        self.assertEqual(
            env_variables["runtimes_check_targets"],
            "check-compiler-rt",
        )
        self.assertEqual(
            env_variables["runtimes_check_targets_needs_reconfig"],
            "",
        )
        self.assertEqual(
            env_variables["enable_cir"],
            "OFF",
        )

    def test_cir(self):
        env_variables = compute_projects.get_env_variables(
            ["clang/lib/CIR/CMakeLists.txt"], "Linux"
        )
        self.assertEqual(
            env_variables["projects_to_build"],
            "clang;clang-tools-extra;lld;lldb;llvm;mlir",
        )
        self.assertEqual(
            env_variables["project_check_targets"],
            "check-clang check-clang-cir check-clang-tools check-lldb",
        )
        self.assertEqual(
            env_variables["runtimes_to_build"], "compiler-rt;libcxx;libcxxabi;libunwind"
        )
        self.assertEqual(
            env_variables["runtimes_check_targets"],
            "check-compiler-rt",
        )
        self.assertEqual(
            env_variables["runtimes_check_targets_needs_reconfig"],
            "check-cxx check-cxxabi check-unwind",
        )
        self.assertEqual(env_variables["enable_cir"], "ON")

    def test_bolt(self):
        env_variables = compute_projects.get_env_variables(
            ["bolt/CMakeLists.txt"], "Linux"
        )
        self.assertEqual(env_variables["projects_to_build"], "bolt;clang;lld;llvm")
        self.assertEqual(env_variables["project_check_targets"], "check-bolt")
        self.assertEqual(env_variables["runtimes_to_build"], "")
        self.assertEqual(env_variables["runtimes_check_targets"], "")
        self.assertEqual(env_variables["runtimes_check_targets_needs_reconfig"], "")

    def test_lldb(self):
        env_variables = compute_projects.get_env_variables(
            ["lldb/CMakeLists.txt"], "Linux"
        )
        self.assertEqual(env_variables["projects_to_build"], "clang;lldb;llvm")
        self.assertEqual(env_variables["project_check_targets"], "check-lldb")
        self.assertEqual(env_variables["runtimes_to_build"], "")
        self.assertEqual(env_variables["runtimes_check_targets"], "")
        self.assertEqual(env_variables["runtimes_check_targets_needs_reconfig"], "")

    def test_mlir(self):
        env_variables = compute_projects.get_env_variables(
            ["mlir/CMakeLists.txt"], "Linux"
        )
        self.assertEqual(env_variables["projects_to_build"], "clang;flang;llvm;mlir")
        self.assertEqual(
            env_variables["project_check_targets"], "check-flang check-mlir"
        )
        self.assertEqual(env_variables["runtimes_to_build"], "")
        self.assertEqual(env_variables["runtimes_check_targets"], "")
        self.assertEqual(env_variables["runtimes_check_targets_needs_reconfig"], "")
        self.assertEqual(env_variables["enable_cir"], "OFF")

    def test_flang(self):
        env_variables = compute_projects.get_env_variables(
            ["flang/CMakeLists.txt"], "Linux"
        )
        self.assertEqual(env_variables["projects_to_build"], "clang;flang;llvm")
        self.assertEqual(env_variables["project_check_targets"], "check-flang")
        self.assertEqual(env_variables["runtimes_to_build"], "flang-rt")
        self.assertEqual(env_variables["runtimes_check_targets"], "check-flang-rt")
        self.assertEqual(env_variables["runtimes_check_targets_needs_reconfig"], "")
        self.assertEqual(env_variables["enable_cir"], "OFF")

    def test_invalid_subproject(self):
        env_variables = compute_projects.get_env_variables(
            ["llvm-libgcc/CMakeLists.txt"], "Linux"
        )
        self.assertEqual(env_variables["projects_to_build"], "")
        self.assertEqual(env_variables["project_check_targets"], "")
        self.assertEqual(env_variables["runtimes_to_build"], "")
        self.assertEqual(env_variables["runtimes_check_targets"], "")
        self.assertEqual(env_variables["runtimes_check_targets_needs_reconfig"], "")

    def test_top_level_file(self):
        env_variables = compute_projects.get_env_variables(["README.md"], "Linux")
        self.assertEqual(env_variables["projects_to_build"], "")
        self.assertEqual(env_variables["project_check_targets"], "")
        self.assertEqual(env_variables["runtimes_to_build"], "")
        self.assertEqual(env_variables["runtimes_check_targets"], "")
        self.assertEqual(env_variables["runtimes_check_targets_needs_reconfig"], "")

    def test_exclude_libcxx_in_projects(self):
        env_variables = compute_projects.get_env_variables(
            ["libcxx/CMakeLists.txt"], "Linux"
        )
        self.assertEqual(env_variables["projects_to_build"], "")
        self.assertEqual(env_variables["project_check_targets"], "")
        self.assertEqual(env_variables["runtimes_to_build"], "")
        self.assertEqual(env_variables["runtimes_check_targets"], "")
        self.assertEqual(env_variables["runtimes_check_targets_needs_reconfig"], "")

    def test_include_libc_in_runtimes(self):
        env_variables = compute_projects.get_env_variables(
            ["libc/CMakeLists.txt"], "Linux"
        )
        self.assertEqual(env_variables["projects_to_build"], "clang;lld")
        self.assertEqual(env_variables["project_check_targets"], "")
        self.assertEqual(env_variables["runtimes_to_build"], "libc")
        self.assertEqual(env_variables["runtimes_check_targets"], "check-libc")
        self.assertEqual(env_variables["runtimes_check_targets_needs_reconfig"], "")

    def test_include_libclc_in_runtimes(self):
        env_variables = compute_projects.get_env_variables(
            ["libclc/CMakeLists.txt"], "Linux"
        )
        self.assertEqual(env_variables["projects_to_build"], "clang;llvm")
        self.assertEqual(env_variables["project_check_targets"], "")
        self.assertEqual(env_variables["runtimes_to_build"], "")
        self.assertEqual(
            env_variables["runtimes_check_targets"],
            "check-libclc",
        )
        self.assertEqual(env_variables["runtimes_check_targets_needs_reconfig"], "")

    def test_exclude_docs(self):
        env_variables = compute_projects.get_env_variables(
            ["llvm/docs/CIBestPractices.rst"], "Linux"
        )
        self.assertEqual(env_variables["projects_to_build"], "")
        self.assertEqual(env_variables["project_check_targets"], "")
        self.assertEqual(env_variables["runtimes_to_build"], "")
        self.assertEqual(env_variables["runtimes_check_targets"], "")
        self.assertEqual(env_variables["runtimes_check_targets_needs_reconfig"], "")

    def test_exclude_gn(self):
        env_variables = compute_projects.get_env_variables(
            ["llvm/utils/gn/build/BUILD.gn"], "Linux"
        )
        self.assertEqual(env_variables["projects_to_build"], "")
        self.assertEqual(env_variables["project_check_targets"], "")
        self.assertEqual(env_variables["runtimes_to_build"], "")
        self.assertEqual(env_variables["runtimes_check_targets"], "")
        self.assertEqual(env_variables["runtimes_check_targets_needs_reconfig"], "")

    def test_ci(self):
        env_variables = compute_projects.get_env_variables(
            [".ci/compute_projects.py"], "Linux"
        )
        self.assertEqual(
            env_variables["projects_to_build"],
            "bolt;clang;clang-tools-extra;flang;lld;lldb;llvm;mlir;polly",
        )
        self.assertEqual(
            env_variables["project_check_targets"],
            "check-bolt check-clang check-clang-cir check-clang-tools check-flang check-lld check-lldb check-llvm check-mlir check-polly",
        )
        self.assertEqual(
            env_variables["runtimes_to_build"],
            "compiler-rt;flang-rt;libc;libcxx;libcxxabi;libunwind",
        )
        self.assertEqual(
            env_variables["runtimes_check_targets"],
            "check-compiler-rt check-flang-rt check-libc check-libclc",
        )
        self.assertEqual(
            env_variables["runtimes_check_targets_needs_reconfig"],
            "check-cxx check-cxxabi check-unwind",
        )

    def test_windows_ci(self):
        env_variables = compute_projects.get_env_variables(
            [".ci/compute_projects.py"], "Windows"
        )
        self.assertEqual(
            env_variables["projects_to_build"],
            "clang;clang-tools-extra;lld;llvm;mlir;polly",
        )
        self.assertEqual(
            env_variables["project_check_targets"],
            "check-clang check-clang-cir check-clang-tools check-lld check-llvm check-mlir check-polly",
        )
        self.assertEqual(
            env_variables["runtimes_to_build"],
            "compiler-rt",
        )
        self.assertEqual(
            env_variables["runtimes_check_targets"],
            "check-compiler-rt check-libclc",
        )
        self.assertEqual(
            env_variables["runtimes_check_targets_needs_reconfig"],
            "",
        )

    def test_lldb(self):
        env_variables = compute_projects.get_env_variables(
            ["lldb/CMakeLists.txt"], "Linux"
        )
        self.assertEqual(env_variables["projects_to_build"], "clang;lld;lldb;llvm")
        self.assertEqual(env_variables["project_check_targets"], "check-lldb")
        self.assertEqual(
            env_variables["runtimes_to_build"], "compiler-rt;libcxx;libcxxabi;libunwind"
        )
        self.assertEqual(env_variables["runtimes_check_targets"], "")
        self.assertEqual(env_variables["runtimes_check_targets_needs_reconfig"], "")

    def test_clang_tools_extra(self):
        env_variables = compute_projects.get_env_variables(
            ["clang-tools-extra/CMakeLists.txt"], "Linux"
        )
        self.assertEqual(
            env_variables["projects_to_build"], "clang;clang-tools-extra;lld;llvm"
        )
        self.assertEqual(env_variables["project_check_targets"], "check-clang-tools")
        self.assertEqual(env_variables["runtimes_to_build"], "libc")
        self.assertEqual(env_variables["runtimes_check_targets"], "check-libc")
        self.assertEqual(env_variables["runtimes_check_targets_needs_reconfig"], "")

    def test_premerge_workflow(self):
        env_variables = compute_projects.get_env_variables(
            [".github/workflows/premerge.yaml"], "Linux"
        )
        self.assertEqual(
            env_variables["projects_to_build"],
            "bolt;clang;clang-tools-extra;flang;lld;lldb;llvm;mlir;polly",
        )
        self.assertEqual(
            env_variables["project_check_targets"],
            "check-bolt check-clang check-clang-cir check-clang-tools check-flang check-lld check-lldb check-llvm check-mlir check-polly",
        )
        self.assertEqual(
            env_variables["runtimes_to_build"],
            "compiler-rt;flang-rt;libc;libcxx;libcxxabi;libunwind",
        )
        self.assertEqual(
            env_variables["runtimes_check_targets"],
            "check-compiler-rt check-flang-rt check-libc check-libclc",
        )
        self.assertEqual(
            env_variables["runtimes_check_targets_needs_reconfig"],
            "check-cxx check-cxxabi check-unwind",
        )

    def test_other_github_workflow(self):
        env_variables = compute_projects.get_env_variables(
            [".github/workflows/docs.yml"], "Linux"
        )
        self.assertEqual(env_variables["projects_to_build"], "")
        self.assertEqual(env_variables["project_check_targets"], "")
        self.assertEqual(env_variables["runtimes_to_build"], "")
        self.assertEqual(env_variables["runtimes_check_targets"], "")
        self.assertEqual(env_variables["runtimes_check_targets_needs_reconfig"], "")

    def test_third_party_benchmark(self):
        env_variables = compute_projects.get_env_variables(
            ["third-party/benchmark/CMakeLists.txt"], "Linux"
        )
        self.assertEqual(
            env_variables["projects_to_build"],
            "bolt;clang;clang-tools-extra;flang;lld;lldb;llvm;mlir;polly",
        )
        self.assertEqual(
            env_variables["project_check_targets"],
            "check-bolt check-clang check-clang-cir check-clang-tools check-flang check-lld check-lldb check-llvm check-mlir check-polly",
        )
        self.assertEqual(
            env_variables["runtimes_to_build"],
            "compiler-rt;flang-rt;libc;libcxx;libcxxabi;libunwind",
        )
        self.assertEqual(
            env_variables["runtimes_check_targets"],
            "check-compiler-rt check-flang-rt check-libc check-libclc",
        )
        self.assertEqual(
            env_variables["runtimes_check_targets_needs_reconfig"],
            "check-cxx check-cxxabi check-unwind",
        )

    def test_lit(self):
        env_variables = compute_projects.get_env_variables(
            ["llvm/utils/lit/CMakeLists.txt"], "Linux"
        )
        self.assertEqual(
            env_variables["projects_to_build"],
            "bolt;clang;clang-tools-extra;flang;lld;lldb;llvm;mlir;polly",
        )
        self.assertEqual(
            env_variables["project_check_targets"],
            "check-bolt check-clang check-clang-tools check-flang check-lit check-lld check-lldb check-llvm check-mlir check-polly",
        )
        self.assertEqual(
            env_variables["runtimes_to_build"], "libcxx;libcxxabi;libunwind"
        )
        self.assertEqual(
            env_variables["runtimes_check_targets"],
            "",
        )
        self.assertEqual(
            env_variables["runtimes_check_targets_needs_reconfig"],
            "check-cxx check-cxxabi check-unwind",
        )

    def test_excluded_projects_reported_linux(self):
        env_variables = compute_projects.get_env_variables(
            ["openmp/runtime/src/kmp.h", "cross-project-tests/CMakeLists.txt"],
            "Linux",
        )
        self.assertEqual(env_variables["projects_to_build"], "")
        self.assertEqual(env_variables["project_check_targets"], "")
        self.assertEqual(
            env_variables["excluded_projects"], "cross-project-tests openmp"
        )

    def test_excluded_dependents_reported_linux(self):
        env_variables = compute_projects.get_env_variables(
            ["clang/CMakeLists.txt"], "Linux"
        )
        self.assertNotIn("check-cross-project", env_variables["project_check_targets"])
        self.assertEqual(env_variables["excluded_projects"], "cross-project-tests")

    def test_excluded_projects_ci_linux(self):
        env_variables = compute_projects.get_env_variables(
            [".ci/compute_projects.py"], "Linux"
        )
        self.assertEqual(env_variables["excluded_projects"], "openmp")

    def test_no_excluded_projects_llvm_linux(self):
        env_variables = compute_projects.get_env_variables(
            ["llvm/CMakeLists.txt"], "Linux"
        )
        self.assertEqual(env_variables["excluded_projects"], "")

    def test_excluded_projects_llvm_windows(self):
        env_variables = compute_projects.get_env_variables(
            ["llvm/CMakeLists.txt"], "Windows"
        )
        self.assertEqual(
            env_variables["excluded_projects"],
            "bolt flang libcxx libcxxabi libunwind lldb",
        )

    def test_excluded_projects_flang_windows(self):
        env_variables = compute_projects.get_env_variables(
            ["flang/CMakeLists.txt"], "Windows"
        )
        self.assertIn("check-flang", env_variables["project_check_targets"])
        self.assertEqual(env_variables["excluded_projects"], "flang-rt")

    def test_excluded_projects_clang_mac(self):
        env_variables = compute_projects.get_env_variables(
            ["clang/CMakeLists.txt"], "Darwin"
        )
        self.assertEqual(
            env_variables["excluded_projects"],
            "compiler-rt cross-project-tests libcxx libcxxabi libunwind lldb",
        )

    def test_exclusions_documented(self):
        self.assertEqual(
            _parse_documented_exclusions(),
            {
                "Linux": set(compute_projects.EXCLUDE_LINUX),
                "Windows": set(compute_projects.EXCLUDE_WINDOWS),
                "Windows dependents": set(compute_projects.EXCLUDE_DEPENDENTS_WINDOWS),
                "Darwin": set(compute_projects.EXCLUDE_MAC),
            },
        )


if __name__ == "__main__":
    unittest.main()
