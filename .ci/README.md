# Pre-merge CI (`.ci/`)

This directory holds the scripts behind the main pre-merge check, the
**CI Checks** workflow in
[`.github/workflows/premerge.yaml`](../.github/workflows/premerge.yaml). It runs
on every pull request (opened, synchronized, reopened) and on every push to a
`release/**` branch. Its jobs only run when the repository owner is `llvm`,
so they are skipped on forks.

The policy side (checks are not mandatory, do not land clear test failures) is
described in the "Pre-merge Continuous Integration (CI)" section of
[`llvm/docs/GitHub.rst`](../llvm/docs/GitHub.rst). This file describes what
the workflow does and how to reproduce it locally.

## Overview

Each job does the same three things:

1. Check out the PR merge commit with `fetch-depth: 2`, so `HEAD~1` is the tip
   of the target branch and `HEAD~1...HEAD` is the diff of the PR.
2. Pipe the changed file names into `compute_projects.py`, which prints shell
   variables saying what to build and test.
3. Pass those variables to the platform build script.

| Job (check name) | Runner | Runs on | Build script |
| --- | --- | --- | --- |
| Build and Test Linux | `llvm-premerge-linux-runners` (x86_64, GCP-hosted, already running inside the CI container) | every PR, `release/**` pushes | `monolithic-linux.sh` |
| Build and Test Linux AArch64 | `depot-ubuntu-24.04-arm-16` (Depot VM; the job runs in `ghcr.io/llvm/arm64v8/ci-ubuntu-24.04`) | every PR, `release/**` pushes | `monolithic-linux.sh` |
| Build and Test Windows | `llvm-premerge-windows-2022-runners` (GCP-hosted) | every PR, `release/**` pushes | `monolithic-windows.sh`, run from `VsDevCmd.bat -arch=amd64 -host_arch=amd64` |
| MacOS Premerge Checks | `macos-14` (GitHub-hosted) | **only** pushes to `release/**` and PRs targeting `release/**` | none, the CMake/Ninja commands live in `premerge.yaml` |

The Linux job has a 120 minute timeout and the Windows build step has a 180
minute timeout. Build logs, `sccache` statistics, lit XML results and any
Clang crash reproducers are uploaded as the "Premerge Artifacts" workflow
artifact, kept for 5 days.

## How `compute_projects.py` picks projects

`compute_projects.py` reads one changed path per line on stdin. It takes the
platform from `platform.system()` (`Linux`, `Windows` or `Darwin`), or from its
first argument if one is given. It prints:

| Variable | Meaning |
| --- | --- |
| `projects_to_build` | `;`-separated list for `LLVM_ENABLE_PROJECTS` |
| `project_check_targets` | space-separated `check-*` targets passed to `ninja` |
| `runtimes_to_build` | `;`-separated list for `LLVM_ENABLE_RUNTIMES` |
| `runtimes_check_targets` | runtime `check-*` targets |
| `runtimes_check_targets_needs_reconfig` | runtime targets re-run with `std=c++26` and with Clang modules (Linux only) |
| `enable_cir` | value for `CLANG_ENABLE_CIR` (`ON` when a CIR path changed) |

The selection is driven by the tables at the top of the script:

- The first path component of each file is the modified project
  (`clang/lib/Sema/Sema.cpp` -> `clang`). `META_PROJECTS` overrides this for
  some paths: `clang/{lib,test,include/clang}/CIR` -> `CIR`,
  `llvm/utils/lit` -> `lit`, `.github/workflows/premerge.yaml` and
  `third-party/` -> `.ci`. Changes under any `*/docs` directory or
  `llvm/utils/gn` select nothing.
- `DEPENDENTS_TO_TEST` adds projects to test when a project changes (for
  example, an `llvm` change also tests clang, clang-tools-extra, lld, lldb,
  mlir, polly, bolt and flang). Changes to `.ci/` test almost everything.
- `DEPENDENT_RUNTIMES_TO_TEST`, `DEPENDENT_RUNTIMES_TO_TEST_NEEDS_RECONFIG`
  and `DEPENDENT_RUNTIMES_TO_BUILD` add runtimes (a `clang` change tests
  compiler-rt and re-runs libc++/libc++abi/libunwind with the new compiler).
- `PROJECT_DEPENDENCIES` adds the projects needed to build the selected ones.
  These are built but their tests are not run.
- `EXCLUDE_LINUX`, `EXCLUDE_WINDOWS`, `EXCLUDE_DEPENDENTS_WINDOWS` and
  `EXCLUDE_MAC` drop projects that are not tested on a platform.
- Changes only to runtimes that have their own workflows (for example
  `libcxx/`, see `libcxx-build-and-test.yaml`) select nothing here.

To see what CI will pick for your change, run this from the root of the
checkout:

```bash
# Diff of the PR against the branch it targets (CI uses HEAD~1...HEAD on the
# merge commit, which is the same set of files).
git diff --name-only origin/main...HEAD | python3 .ci/compute_projects.py

# The same for the other platforms.
git diff --name-only origin/main...HEAD | python3 .ci/compute_projects.py Windows
git diff --name-only origin/main...HEAD | python3 .ci/compute_projects.py Darwin

# A single file.
echo clang/lib/Sema/Sema.cpp | python3 .ci/compute_projects.py Linux
```

The last command prints:

```
projects_to_build='clang;clang-tools-extra;lld;lldb;llvm'
project_check_targets='check-clang check-clang-tools check-lldb'
runtimes_to_build='compiler-rt;libcxx;libcxxabi;libunwind'
runtimes_check_targets='check-compiler-rt'
runtimes_check_targets_needs_reconfig='check-cxx check-cxxabi check-unwind'
enable_cir='OFF'
```

The CI log also prints these values at the start of the "Build and Test"
step ("Building projects: ...", "Running project checks targets: ...").

When changing the selection logic, run the unit tests:

```bash
python3 .ci/compute_projects_test.py
```

## Reproducing the Linux job

`monolithic-linux.sh` takes the `compute_projects.py` outputs as positional
arguments:

```
.ci/monolithic-linux.sh <projects> <project_check_targets> <runtimes> \
    <runtimes_check_targets> <runtimes_check_targets_needs_reconfig> <enable_cir>
```

It sources `utils.sh`, which:

- uses `MONOREPO_ROOT` (default: `git rev-parse --show-toplevel`) and
  `BUILD_DIR` (default: `$MONOREPO_ROOT/build`), and **deletes `BUILD_DIR`**
  before configuring;
- needs `sccache` on `PATH` and installs the Python packages from
  `.ci/all_requirements.txt` with `pip` (`PIP_BREAK_SYSTEM_PACKAGES=1`);
- writes logs and results to `artifacts/` in the current directory.

The script then configures a Release build with assertions, examples,
`-Werror`, LLD, `-gmlt`, the MLIR Python bindings and LLDB Python support (see
the `cmake` command in `monolithic-linux.sh` for the full list), runs
`ninja -k 0` on the project check targets, then the runtime check targets,
and finally reconfigures twice to re-run the libc++/libc++abi/libunwind
targets with `std=c++26` and with `enable_modules=clang`.

The closest match to CI is the container image the jobs use. It contains the
pinned Clang (`/opt/llvm/bin/clang`), CMake, Ninja, `sccache` and the other
tools the script expects. It is built from
[`.github/workflows/containers/github-action-ci/Dockerfile`](../.github/workflows/containers/github-action-ci/Dockerfile)
by `build-ci-container.yml` and published as `ghcr.io/llvm/ci-ubuntu-24.04`
(x86_64) and `ghcr.io/llvm/arm64v8/ci-ubuntu-24.04` (AArch64).

```bash
cd llvm-project
docker run --rm -it --privileged \
  -v "$PWD":/home/gha/llvm-project -w /home/gha/llvm-project \
  ghcr.io/llvm/ci-ubuntu-24.04:latest bash

# Inside the container:
git config --global --add safe.directory '*'
source <(git diff --name-only origin/main...HEAD | python3 .ci/compute_projects.py)
export CC=/opt/llvm/bin/clang CXX=/opt/llvm/bin/clang++
export SCCACHE_IDLE_TIMEOUT=0
sccache --start-server
./.ci/monolithic-linux.sh "${projects_to_build}" "${project_check_targets}" \
  "${runtimes_to_build}" "${runtimes_check_targets}" \
  "${runtimes_check_targets_needs_reconfig}" "${enable_cir}"
```

Notes:

- `--privileged` matches CI and is needed by the LLDB tests that disable ASLR.
- The image runs as user `gha` (uid 1001). If your host uid differs, add
  `--user "$(id -u):$(id -g)"` or make the checkout writable for uid 1001.
- Without the remote cache variables below, `sccache` only uses a local disk
  cache, so the first build is a full build.
- To re-run a single failing target after the script finishes, use the build
  directory it left behind, for example
  `ninja -C build check-clang` or
  `build/bin/llvm-lit -v clang/test/Sema/some-test.c`.
- When the script exits with a failure outside GitHub Actions, `utils.sh`
  calls `premerge_advisor_upload.py`, which tries to post the failure to the
  premerge advisor. That step needs network access and does not change the
  build result.

### CI-only environment

These are set by the runners or the workflow and are not needed locally:

| Variable | Where it comes from | Purpose |
| --- | --- | --- |
| `CACHE_GCS_BUCKET` | runner pod definition on the GCP clusters (differs per cluster) | copied to `SCCACHE_GCS_BUCKET`, with `SCCACHE_GCS_RW_MODE=READ_WRITE`, on `llvm-premerge-linux-runners` and the Windows runners |
| `SCCACHE_WEBDAV_ENDPOINT`, `SCCACHE_WEBDAV_TOKEN` | Depot runner host, passed into the container with `--env` | `sccache` cache on the AArch64 Depot runners |
| `SCCACHE_IDLE_TIMEOUT=0` | workflow | keep the `sccache` server alive for the whole job so statistics are not lost |
| `GITHUB_TOKEN`, `GITHUB_PR_NUMBER` | workflow | used by `premerge_advisor_explain.py` to comment on the PR |
| `GITHUB_ACTIONS`, `RUNNER_ARCH` | GitHub Actions | enable the step summary (`generate_test_report_github.py`), the premerge advisor and the lit timing cache download (`cache_lit_timing_files.py`, x86_64 only) |

## Reproducing the Windows job

The Windows job runs `compute_projects.py` with the Windows exclusions (no
libc, lldb, bolt, openmp, libc++ or flang-rt; flang is only tested when flang
itself changes) and then, from a Visual Studio developer prompt, runs:

```
.ci/monolithic-windows.sh <projects> <project_check_targets> <runtimes> <runtimes_check_targets>
```

The script uses `clang-cl` from `C:/clang/clang-msvc/bin/clang-cl.exe`,
`link.exe`, `sccache`, and disables the linker manifest (`/MANIFEST:NO`, see
https://github.com/llvm/llvm-project/pull/82393). To reproduce it, open a
"x64 Native Tools" prompt (or run
`VsDevCmd.bat -arch=amd64 -host_arch=amd64`), start Git Bash from it, and run:

```bash
source <(git diff --name-only origin/main...HEAD | python .ci/compute_projects.py Windows)
sccache --start-server
.ci/monolithic-windows.sh "${projects_to_build}" "${project_check_targets}" \
  "${runtimes_to_build}" "${runtimes_check_targets}"
```

Edit the `CC`/`CXX` paths in the script if `clang-cl` is installed elsewhere.
The CI environment is described by
[`.github/workflows/containers/github-action-ci-windows/Dockerfile`](../.github/workflows/containers/github-action-ci-windows/Dockerfile).

## The macOS job (release branches only)

`premerge-check-macos` runs only for pushes to `release/**` and for PRs whose
base branch is `release/**`. It is not run for PRs against `main`.

It uses the macOS exclusions in `compute_projects.py` (no bolt, compiler-rt,
flang, libc, lldb, openmp, polly or runtimes) and builds directly from the
workflow, without a `.ci` script. Compared to the Linux job it:

- builds only `projects_to_build` and runs only `project_check_targets`; no
  runtimes are built or tested, because the libc++ tests fail there;
- passes `-DLLVM_DISABLE_ASSEMBLY_FILES=ON`
  (https://github.com/llvm/llvm-project/issues/81967) and
  `-DLLDB_INCLUDE_TESTS=OFF`;
- uses the default Apple toolchain with `ccache` instead of `sccache`, and no
  `-Werror`, LLD, examples or Python bindings.

To reproduce it on a Mac with Ninja and `ccache` installed:

```bash
source <(git diff --name-only origin/release/<N>.x...HEAD | python3 .ci/compute_projects.py Darwin)
cmake -G Ninja -B build -S llvm \
  -DLLVM_ENABLE_PROJECTS="${projects_to_build}" \
  -DLLVM_DISABLE_ASSEMBLY_FILES=ON \
  -DCMAKE_BUILD_TYPE=Release \
  -DLLDB_INCLUDE_TESTS=OFF \
  -DLLVM_ENABLE_ASSERTIONS=ON \
  -DCMAKE_C_COMPILER_LAUNCHER=ccache \
  -DCMAKE_CXX_COMPILER_LAUNCHER=ccache
ninja -C build ${project_check_targets}
```

Replace `release/<N>.x` with the release branch your PR targets. If you change
the flags in `premerge.yaml`, update this section too.

## Other files in this directory

- `generate_test_report_github.py`, `generate_test_report_lib.py`: turn the
  lit XML results and Ninja logs into the job summary and PR comment.
- `premerge_advisor_explain.py`, `premerge_advisor_upload.py`: send failures
  to the premerge advisor service and post a PR comment with any explanations
  it returns.
- `cache_lit_timing_files.py`: download/upload lit test timing data so lit can
  schedule slow tests first.
- `buildbot/`, `green-dragon/`, `metrics/`: post-commit buildbot
  configuration, Green Dragon (macOS) jobs and CI metrics collection.
