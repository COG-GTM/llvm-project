## Getting Started

This directory contains `libsycl` tests distributed in subdirectories based on
testing scope. `libsycl` uses LIT to configure and run its tests.

Please see the [Lit Command Guide](https://llvm.org/docs/CommandGuide/lit.html)
for more information about LIT.

## Prerequisites

* Compiler & libsycl. Can be built following these
  [instructions](/libsycl/docs/index.rst). This also builds the `sycl-ls`
  tool, which the test configuration requires: `llvm-lit` stops with
  "can't find `sycl-ls`" if it is not in the compiler's `bin` directory or the
  LLVM tools directory.
* Target runtime(s) to execute tests on devices. libsycl runs on top of
  liboffload (`offload` in `LLVM_ENABLE_RUNTIMES`), and the only device
  currently supported for testing is a **Level Zero GPU** (`level_zero:gpu` in
  `sycl-ls` output). This requires:
  * liboffload built with the Level Zero plugin
    (`-DLIBOMPTARGET_PLUGINS_TO_BUILD=level_zero`, see
    `offload/cmake/Modules/LibomptargetGetDependencies.cmake`);
  * the Level Zero loader and GPU driver installed on the host;
  * the runtime libraries being discoverable when tests run. `LD_LIBRARY_PATH`
    from the host environment is propagated to tests; extra locations can be
    added with the `extra_environment` / `extra_system_environment` parameters
    (see [llvm-lit parameters](#llvm-lit-parameters)).

  Running `sycl-ls` from the build directory is a quick way to check the
  setup: it should list at least one `[level_zero:gpu]` device.

### Running without a supported device

Once `sycl-ls` is found, device detection never fails the test run:

* If `sycl-ls` exits with an error (for example because liboffload or one of
  its plugins cannot be loaded), `llvm-lit` prints a warning with the error
  output and continues as if no device were available.
* Devices other than `level_zero:gpu` (e.g. `opencl`, `cuda`, `hip` or CPU
  devices) are reported with a warning and ignored.

In both cases tests marked `REQUIRES: any-device` (or another device feature)
are reported as `UNSUPPORTED`, while tests that do not need a device still run.

## Run the tests

`libsycl` is integrated via `LLVM_ENABLE_RUNTIMES` and is not visible as a top
level target. The same is applicable to tests. To run `check-sycl` tests you need
to prepend `<build>/runtimes/runtimes-bins/` to the paths of all tests.
For example, to run all the `libsycl` tests you can do:
```bash
<build>/bin/llvm-lit <build>/runtimes/runtimes-bins/libsycl/test
```

To run an individual test, use the path to it instead.

If you are using `ninja` as your build system, you can run all the tests in the
`libsycl` testsuite as:

```bash
 ninja -C <build>/runtimes/runtimes-bins check-sycl
 ```

## CMake parameters

These parameters can be used to configure tests:

`LIBSYCL_CXX_COMPILER` - path to compiler to use it for building tests.

`LIBSYCL_TEST_COMPILER_OPTIONS` - flags to be passed to `LIBSYCL_CXX_COMPILER` when
    building libsycl tests.

`LLVM_LIT` - path to llvm-lit tool.

## Creating or modifying tests

### LIT feature checks

Following features can be passed to LIT via `REQUIRES`, `UNSUPPORTED`, etc.
filters to limit test execution to the specific environment.

#### Auto-detected features

The following features are automatically detected by `llvm-lit` by scanning the
environment:

* `any-device` - presence of at least 1 supported device;
* `any-device-is-gpu` - device type to be available;
* `any-device-is-level_zero` - backend to be available;

Devices are detected by running `sycl-ls` once when the test configuration is
loaded. Only supported devices (currently `level_zero:gpu`) contribute these
features; see [Running without a supported device](#running-without-a-supported-device).

Note: the `sycl-ls` tool doesn't have an assigned feature since it is essential for
test configuration and is always available.

### llvm-lit parameters

The following options can be passed to the `llvm-lit` tool with `--param`
option to configure test execution:

* `libsycl_compiler` - full path to compiler to use.
* `extra_environment` - comma-separated list of variables with values to be
  added to the test environment. Can be also set by the `LIT_EXTRA_ENVIRONMENT`
  variable in CMake.
* `extra_system_environment` - comma-separated list of variables to be
  propagated from the host environment to the test environment. Can be also set
  by `LIT_EXTRA_SYSTEM_ENVIRONMENT` variable in CMake.

Example:

```bash
<build>/bin/llvm-lit  --param libsycl_compiler=path/to/clang++ \
        <build>/runtimes/runtimes-bins/libsycl/test
```