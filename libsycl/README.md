## SYCL runtime library

The libsycl subproject is an implementation of the SYCL runtime library as defined by the
[SYCL 2020 specification](https://registry.khronos.org/SYCL/specs/sycl-2020/html/sycl-2020.html).

Subproject documentation is available at: [Libsycl documentation](./docs).

libsycl runtime library and headers require C++17 support or higher.

### How to use libsycl with Clang

libsycl is in the early stages of upstreaming (see
[Current Status](./docs/index.rst#current-status)). The libsycl test suite
currently builds programs with the Clang from the same build tree, with the
libsycl headers on the include path and `libsycl` on the link line:

```bash
<build>/bin/clang++ app.cpp -o app \
    -isystem <build>/include -isystem <build>/include/sycl \
    -L<build>/lib/x86_64-unknown-linux-gnu -lsycl
LD_LIBRARY_PATH=<build>/lib/x86_64-unknown-linux-gnu ./app
```

The library directory is `lib/<target triple>` because
`LLVM_ENABLE_PER_TARGET_RUNTIME_DIR` is on by default on Linux. Running SYCL
kernels needs a device and driver that liboffload supports; the libsycl test
suite currently only recognizes Level Zero GPUs.

#### How to build

libsycl is built as an LLVM runtime and depends on the `offload` and `openmp`
runtimes, which must be enabled in the same build. This is the configuration
the premerge `Test SYCL` check runs in
[sycl-tests.yml](../.github/workflows/sycl-tests.yml):

```bash
cmake -G Ninja -S llvm -B build \
    -DCMAKE_BUILD_TYPE=Release \
    -DLLVM_ENABLE_ASSERTIONS=ON \
    -DLLVM_ENABLE_PROJECTS=clang \
    -DLLVM_ENABLE_RUNTIMES="offload;openmp;libsycl" \
    -DLLVM_TARGETS_TO_BUILD="host;SPIRV" \
    -DLLVM_INCLUDE_SPIRV_TOOLS_TESTS=ON
ninja -C build check-sycl
```

`check-sycl` builds Clang, the runtimes and the libsycl tests, and then runs the
tests with `llvm-lit`. `LLVM_INCLUDE_SPIRV_TOOLS_TESTS` is an advanced option
that adds a `SPIRVTools` target which clones and builds SPIRV-Tools
(`spirv-as`, `spirv-dis`, `spirv-val`, `spirv-link`) from GitHub for the
LLVM/Clang SPIR-V tests. `check-sycl` itself does not build it, so it is only
needed to match the CI configuration exactly. To use existing binaries instead
of cloning, pass their paths with `-DSPIRV_AS=...`, `-DSPIRV_DIS=...`,
`-DSPIRV_VAL=...` and `-DSPIRV_LINK=...`.

CI runs this inside the `ghcr.io/llvm/ci-ubuntu-24.04:latest` container (with
sccache as the compiler launcher). To reproduce a CI failure in the same
environment:

```bash
docker run --rm -it -v "$PWD":/llvm-project -w /llvm-project \
    ghcr.io/llvm/ci-ubuntu-24.04:latest
```

and run the commands above inside the container. See the
[libsycl documentation](./docs/index.rst#build-steps) for installing libsycl
and [test/README.md](./test/README.md) for running individual tests and the
lit parameters.

# License

See [LICENSE](./LICENSE.txt) for details.
