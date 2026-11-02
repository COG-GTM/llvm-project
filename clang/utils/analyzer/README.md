# Static Analyzer regression testing scripts

`SATest.py` is the driver for the Clang Static Analyzer regression tests. It
analyzes the open source projects listed in `projects/projects.json` and
compares the results with the reference results stored next to them. Run
`./SATest.py --help` or `./SATest.py <subcommand> --help` for the full list of
options.

## Running the tests in Docker

The `docker` subcommand runs the tests in a container that has every
dependency of the test projects installed. The container image is defined by
`Dockerfile`, and its entry point is `entrypoint.py`.

1. Build the image (tagged `satest-image`):

   ```
   ./SATest.py docker --build-image
   ```

2. Build LLVM inside the container and then run the tests:

   ```
   ./SATest.py docker --build-dir <build-dir> --clang-dir <install-dir> \
       -- --build-llvm [-D<VAR>=<VALUE> ...] [build options]
   ```

   Everything after `--` is forwarded to `entrypoint.py`, which understands:

   - `--build-llvm`: configure (only if `<build-dir>` has no `build.ninja`
     yet), build and install LLVM, then run the tests.
   - `--build-llvm-only`: configure, build and install LLVM without running
     the tests.
   - `-D<VAR>=<VALUE>`: an extra CMake option, may be repeated. These are only
     used when CMake is run, so delete `<build-dir>` to apply new options to an
     existing build.
   - Any other argument is passed to `SATest.py` inside the container, so
     name the subcommand to run there, for example
     `build -j4 --projects box2d`.

   Without `--build-llvm` or `--build-llvm-only`, the tests use the clang
   already installed in `<install-dir>`.

3. To debug inside the container, start a shell instead:

   ```
   ./SATest.py docker --build-dir <build-dir> --clang-dir <install-dir> --shell
   ```

`SATest.py docker` mounts these host directories in the container:

| Container path  | Host path                                                     |
| --------------- | ------------------------------------------------------------- |
| `/llvm-project` | `--llvm-project-dir` (defaults to this checkout)              |
| `/build`        | `--build-dir`                                                 |
| `/analyzer`     | `--clang-dir`, the LLVM install prefix                        |
| `/scripts`      | this directory                                                |
| `/projects`     | `projects/`                                                   |

### Default CMake configuration

With `--build-llvm` or `--build-llvm-only`, `entrypoint.py` configures LLVM
in `/build` with the following command:

```
cmake -G Ninja \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_INSTALL_PREFIX=/analyzer \
    -DLLVM_TARGETS_TO_BUILD=X86 \
    -DLLVM_ENABLE_PROJECTS=clang \
    -DLLVM_ENABLE_RUNTIMES=openmp \
    -DLLVM_BUILD_RUNTIME=OFF \
    -DCLANG_ENABLE_STATIC_ANALYZER=ON \
    [-D<VAR>=<VALUE> ...] \
    /llvm-project/llvm
```

and then runs `ninja install`. The `-D` options from the command line come
after the defaults, so they can also override them. For example, this builds
an assertions-enabled clang and runs the box2d project:

```
./SATest.py docker --build-dir ~/satest-build --clang-dir ~/satest-install \
    -- --build-llvm -DLLVM_ENABLE_ASSERTIONS=ON build --projects box2d
```

To build the same configuration outside Docker, run the command above with
`CMAKE_INSTALL_PREFIX` and the source path changed to local directories.
