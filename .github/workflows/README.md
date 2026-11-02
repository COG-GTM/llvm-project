Github action workflows should be stored in this directory.

## Release Binaries pre-merge build

`release-binaries-all.yml` runs a test build of the release binaries on pull
requests that change any of these paths (keep this list in sync with its
`pull_request.paths` filter):

* `.github/workflows/release-binaries-all.yml`
* `.github/workflows/release-binaries.yml`
* `.github/workflows/get-llvm-version/**`
* `.github/workflows/upload-release-artifact/**`
* `clang/cmake/caches/Release.cmake`
* `llvm/utils/release/build_llvm_release.bat`
* `llvm/utils/release/github-upload-release.py`

On pull requests the binaries are built but not uploaded: the permission check
and the `upload-release-binaries` job (which uses `upload-release-artifact` and
`github-upload-release.py`) are skipped, so those inputs only trigger the build.
The workflow also runs weekly on a schedule and from `release-tasks.yml`.
