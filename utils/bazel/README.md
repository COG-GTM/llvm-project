# Introduction

*Warning* The Bazel build is experimental and best-effort, supported in line
with the policy for
[LLVM's peripheral support tier](https://llvm.org/docs/SupportPolicy.html).
LLVM's official build system is CMake. If in doubt use that. If you make changes
to LLVM, you're expected to update the CMake build but you don't need to update
Bazel build files. Reviewers should not ask authors to update Bazel build files
unless the author has opted in to support Bazel. Keeping the Bazel build files
up-to-date is on the people who use the Bazel build.

[Bazel](https://bazel.build/) is a multi-language build system focused on
reproducible builds to enable dependency analysis and caching for fast
incremental builds.

The main motivation behind the existence of an LLVM Bazel build is that a number
of projects that depend on LLVM use Bazel, and Bazel works best when it knows
about the whole source tree (as opposed to installing artifacts coming from
another build system). Community members are also welcome to use Bazel for their
own development as long as they continue to maintain the official CMake build
system. See also, the
[proposal](https://github.com/llvm/llvm-www/blob/main/proposals/LP0002-BazelBuildConfiguration.md)
for adding this configuration.

# Quick Start

1. `git clone https://github.com/llvm/llvm-project.git; cd llvm-project` if
   you don't have a checkout yet.
2. Install Bazel at the version indicated by [.bazelversion](./.bazelversion),
   following the official instructions, if you don't have it installed yet:
   https://docs.bazel.build/versions/main/install.html.
   * You can also install and use
     [bazelisk](https://github.com/bazelbuild/bazelisk) which automates
     downloading the proper bazel version
3. `cd utils/bazel`
4. The `bazel build` command depends on the local compiler you want to use.
   * For **clang**, go to step 5.
   * For **gcc** or **MSVC**, go to step 6
5. If you are using **clang**, it is expected that lld is also available.
   The `--config=generic_clang` flag by default sets the compiler to be `clang`
   binary on the `PATH`.
   ```
   bazel build --config=generic_clang @llvm-project//...
   ```
   To provide a specific path to your `clang`, use the `--repo_env` Bazel flag.
   For example:
   ```
   bazel build --config=generic_clang --repo_env=CC=/usr/bin/clang --repo_env=CXX=/usr/bin/clang++  @llvm-project//...
   ```
6. If you are using **gcc** or **MSVC**, instead of `--config=generic_clang`
   , pass `--config=generic_gcc` or `--config=generic_msvc`, which sets the
   compiler to be `gcc` binary on the `PATH`.
   ```
   bazel build --config=generic_gcc @llvm-project//...
   ```
   To provide a specific path to your `gcc`, use the `--repo_env` Bazel flag.
   For example:
   ```
   bazel build --config=generic_gcc --repo_env=CC=/usr/bin/gcc --repo_env=CXX=/usr/bin/g++  @llvm-project//...
   ```

# Configuration

The repository `.bazelrc` will import user-specific settings from a
`user.bazelrc` file (in addition to the standard locations). Adding your typical
config setting is recommended.

```.bazelrc
build --config=generic_clang
```

You can enable
[disk caching](https://docs.bazel.build/versions/main/remote-caching.html#disk-cache),
which will cache build results

```.bazelrc
build --disk_cache=~/.cache/bazel-disk-cache
```

You can instruct Bazel to use a ramdisk for its sandboxing operations via
[--sandbox_base](https://docs.bazel.build/versions/main/command-line-reference.html#flag--sandbox_base),
which can help avoid IO bottlenecks for the symlink strategy used for
sandboxing. This is especially important with many inputs and many cores (see
https://github.com/bazelbuild/bazel/issues/11868):

```.bazelrc
build --sandbox_base=/dev/shm
```

Bear in mind that this requires that your ramdisk is of sufficient size to hold
any temporary files. Anecdotally, 1GB should be sufficient.

# Coverage

The LLVM, MLIR, and Clang subprojects have configurations for Linux (Clang and
GCC), Mac (Clang and GCC), and Windows (MSVC). Configuration options that are
platform-specific are selected for in defines. Many are also hardcoded to the
values currently used by all supported configurations. If there is a
configuration you'd like to use that isn't supported, please send a patch.

# Continuous Testing

A [Buildkite pipeline](https://buildkite.com/llvm-project/upstream-bazel)
runs the full Bazel build on every commit to the main branch. Notifications of
failures are sent to the
[llvm-bazel-alerts google group](https://groups.google.com/g/llvm-bazel-alerts),
which anyone is free to join. Currently, the behavior is just to send an email
on each failure using Buildkite's built-in notification system, so if you
subscribe, it is highly recommended that you set up email filters or some other
mechanism to not flood your inbox. More sophisticated notifications, e.g. only
on status change or routed based on blamelist are TODO (contributions welcome).

# Premerge CI

Pull requests and pushes to `main` that touch `utils/bazel/**` or
[bazel-checks.yml](../../.github/workflows/bazel-checks.yml) run two GitHub
Actions jobs (only in `llvm/llvm-project`, not in forks):

* **Buildifier** (`ubuntu-24.04`): checks the formatting of every `BUILD`,
  `*.bazel` and `*.bzl` file under `utils/bazel` with buildifier v8.2.1. To
  reproduce locally, from the repository root:
  ```
  buildifier --mode=check $(find ./utils/bazel -name '*BUILD*' -o -name '*bzl' -o -name '*.bazel')
  ```
  Use `--mode=fix` instead of `--mode=check` to apply the fixes.
* **Bazel Build/Test**: builds and tests `@llvm-project//... //...` with
  `--config=ci`. See the `ci` section of [.bazelrc](./.bazelrc) for what it
  sets: `-O1`, `--config=generic_clang` (so `clang` and `lld` are needed),
  the system `mpfr` and `pfm` libraries, skipping targets tagged
  `nobuildkite`, and `--keep_going`.

To reproduce the Bazel Build/Test job locally on Debian/Ubuntu, install the
system packages the job installs, plus clang and lld:
```
sudo apt-get install -y libmpfr-dev libpfm4-dev m4 libedit-dev clang lld
```
Install [bazelisk](https://github.com/bazelbuild/bazelisk) (CI uses v1.27.0),
then run the job's command without the remote cache flags:
```
cd utils/bazel
bazelisk test --config=ci @llvm-project//... //...
```
`--config=ci` puts the sandbox on `/dev/shm`. If your ramdisk is too small, add
`--sandbox_base=""` (as CI does) to use the default location. Building every
target takes a long time. To debug one failure, replace
`@llvm-project//... //...` with the failing target.

The job runs on the self-hosted `llvm-premerge-cluster-us-central` runner group
(`llvm-premerge-linux-runners` label). It runs only on US Central workers
because the cache buckets are per cluster. It reads from and writes to a Google
Cloud Storage remote cache (`--remote_cache=https://storage.googleapis.com/$CACHE_GCS_BUCKET-bazel`
with `--google_default_credentials`). `CACHE_GCS_BUCKET` is set in the runner
environment by the premerge cluster. It is not a repository secret or variable,
so contributors cannot use it, and the build does not need it to produce the
same results.

# Usage in Downstream Projects

To use in dependent projects using Bazel, you can import LLVM and then use the
provided configuration rule. See example usage in the `examples/` directory.
