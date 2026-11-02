Github action workflows should be stored in this directory.

## HLSL tests (`hlsl-matrix.yaml`, `hlsl-test-all.yaml`)

`hlsl-matrix.yaml` runs on pull requests that touch DirectX/HLSL code (and on
`workflow_dispatch`) and calls the reusable `hlsl-test-all.yaml` workflow once
per runner SKU.

`hlsl-test-all.yaml` inputs:

| Input                | Default      | Used for                                                   |
| -------------------- | ------------ | ---------------------------------------------------------- |
| `SKU`                | (required)   | `runs-on` label of the runner.                             |
| `LLVM-ref`           | `main`       | `ref` of the llvm-project checkout.                        |
| `OffloadTest-branch` | `main`       | `ref` of the llvm/offload-test-suite checkout.             |
| `TestTarget`         | `check-hlsl` | Extra ninja target run after the LLVM/Clang/HLSL checks.   |

`hlsl-matrix.yaml` passes `LLVM-ref: ${{ github.ref }}`, so pull requests test
their own merge ref. Pass a different `LLVM-ref` or `OffloadTest-branch` to test
a release branch or an offload-test-suite change.

External dependencies (not pinned; the job tests whatever these point to at run
time):

* `Microsoft/DirectXShaderCompiler` at `main` (with submodules): builds `dxv`
  and `llvm-dis` used for DXIL validation and disassembly.
* `llvm/offload-test-suite` at `OffloadTest-branch`: built as the
  `OffloadTest` external LLVM project; also provides the
  `cmake/caches/sccache.cmake` cache file used by both builds.
* `llvm/offload-golden-images` at `main`: reference images (`GOLDENIMAGE_DIR`).

Runner requirements: `hlsl-macos` is a self-hosted runner label (macOS with
Metal, for `check-hlsl-clang-mtl`) that needs CMake, Ninja, a host C/C++
toolchain, and sccache (used by `sccache.cmake`). Repositories without a runner
registered under that label (GitHub-hosted runners, forks) leave the job queued.

To reproduce locally on a suitable machine, check out the four repositories
side by side at the refs above and run the `Build DXC`, `Build LLVM` and
`Run HLSL Tests` steps from `hlsl-test-all.yaml`, replacing
`${{ github.workspace }}` with the parent directory.
