# LLVM Testing Utilities

This folder contains the setup for the `llvm-testing-tools` python package
(`name = "llvm_testing_tools"` in `pyproject.toml`; `pip` normalizes it to
`llvm-testing-tools`, which is how `libcxx/test/requirements.txt` pins it).
The package ships prebuilt `FileCheck` and `split-file` binaries, plus console
script wrappers, through PyPI. The goal is to cover the testing needs of
runtimes builds without a bootstrapping build.

## How a release is built

The package version is the `version` field in `pyproject.toml`. It follows the
LLVM major version (e.g. `23.0.0`) and has to be bumped by hand.

`.github/workflows/release-llvm-testing-tools.yml` builds the package. It does
not publish it:

* It runs only on `pull_request` events that touch this directory or the
  workflow file, and only in `llvm/llvm-project`.
* It builds `FileCheck` and `split-file` (`CMAKE_BUILD_TYPE=Release`) on an
  `ubuntu-24.04` runner and copies them into `src/llvm_testing_tools/binaries/`.
  It then runs `python3 -m build` and uploads `dist/*` (sdist and wheel) as a
  workflow artifact named `packages`.
* It uses no secrets and has no `id-token` permission, so it cannot upload to
  PyPI.

To build the same artifacts locally from the monorepo root:

```
cmake -S llvm -B build -GNinja -DCMAKE_BUILD_TYPE=Release
ninja -C build split-file FileCheck
cd llvm/utils/llvm-testing-tools
mkdir -p src/llvm_testing_tools/binaries
cp ../../../build/bin/FileCheck ../../../build/bin/split-file src/llvm_testing_tools/binaries/
python3 -m build
```

## How a release is published

No workflow in this repository publishes `llvm-testing-tools` to PyPI.
`release-tasks.yml` publishes `lit` on `llvmorg-*` tags using PyPI trusted
publishing (the `pypi` environment). It does not build or upload this package.

Any version on PyPI was therefore uploaded by hand by a maintainer of the PyPI
project, outside this repository's CI. The repository does not record who holds
those PyPI credentials or which build produced the uploaded binaries. To
release by hand:

1. Check out the matching `llvmorg-X.Y.Z` tag and confirm that `version` in
   `pyproject.toml` matches it.
2. Build the artifacts as shown above, on an `ubuntu-24.04` x86_64 machine, or
   download the `packages` artifact from a run of the workflow on that tag's
   sources.
3. Run `twine check dist/*`, then upload to test.pypi.org and after that to
   pypi.org with an account that maintains the `llvm-testing-tools` project.

## Supported platforms

The binaries are native x86_64 Linux executables built on the workflow's
`ubuntu-24.04` runner. They are dynamically linked against glibc, libstdc++,
libm and libgcc_s. They need a glibc and libstdc++ at least as new as the
newest `GLIBC_*`/`GLIBCXX_*` symbol versions they reference. That is at most
what Ubuntu 24.04 ships (glibc 2.39). Nothing pins or checks this floor, so
updating the runner image can raise it. For example, a local build on Ubuntu
22.04 references up to `GLIBC_2.34` and `GLIBCXX_3.4.29`; you can check with
`objdump -T`. The package therefore supports only x86_64 Linux with a
sufficiently recent glibc and libstdc++.

The wheel is still tagged `py3-none-any`, because setuptools treats the
binaries as plain package data. `pip` will install it on any platform,
including macOS, Windows, AArch64 and older glibc systems. There, the
`FileCheck` and `split-file` wrappers fail when they run, so libc++'s
`has-filecheck`/`has-split-file` features stay off. The wheel is not
`manylinux`-tagged and `auditwheel` is not run on it. The sdist also contains
the same prebuilt binaries, because `binaries/*` is listed as package data.

## Automating publication

Fix the wheel's platform tag (and build one wheel per supported platform)
before automating uploads. Then add a job to `release-tasks.yml` modeled on
`release-lit`. PyPI trusted publishing does not support called workflows, so
the job has to live in `release-tasks.yml` itself and needs
`id-token: write`, the `pypi` environment, and a trusted publisher registered
on the `llvm-testing-tools` PyPI project.
