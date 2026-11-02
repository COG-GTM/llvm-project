# GitHub Actions workflows

GitHub Actions workflows should be stored in this directory.

This file is an index of the workflows in this directory: what triggers
them, where they run, which container images they build or use, which
secrets and environments they need, and how to reproduce them locally.
Policy for writing workflows (fork guards, hash pinning, permissions, etc.)
is in [CI Best Practices](../../llvm/docs/CIBestPractices.rst). The
contributor-facing description of pre-merge CI is in the "Pre-merge
Continuous Integration (CI)" section of [GitHub.rst](../../llvm/docs/GitHub.rst).

**Keep this file up to date.** When you add a workflow, or change its
triggers, runner, container, secrets or environment, update the matching
row below in the same PR.

## Fork behaviour

Most jobs have a guard such as `if: github.repository_owner == 'llvm'` or
`if: github.repository == 'llvm/llvm-project'`. In a fork these jobs are
skipped, so the workflow shows as run but does nothing. The "Guard" column
below shows which guard each workflow uses (`owner` = `repository_owner ==
'llvm'`, `repo` = `repository == 'llvm/llvm-project'`, `-` = no guard).

## Runners

| Runner label | Kind | Where it is used |
|---|---|---|
| `ubuntu-24.04`, `ubuntu-24.04-arm`, `ubuntu-22.04`, `ubuntu-22.04-arm`, `windows-2022`, `windows-2025`, `windows-11-arm`, `macos-14`, `macos-15` | GitHub-hosted | Most workflows |
| `windows-11-arm-16core` | GitHub-hosted larger runner | `release-binaries.yml` (Windows on Arm release builds) |
| `depot-ubuntu-24.04-16`, `depot-ubuntu-24.04-arm-16` | Third-party [Depot](https://depot.dev) runners (16 vCPU VMs, Linux x86-64 / AArch64) | `build-ci-container.yml`, `premerge.yaml` (AArch64 Linux job) |
| `depot-ubuntu-22.04-16`, `depot-ubuntu-22.04-arm-16`, `depot-windows-2022-16`, `depot-macos-14` | Depot runners | `release-binaries.yml` build stage (derived from the `runs-on` input) |
| `llvm-premerge-linux-runners`, `llvm-premerge-windows-2022-runners` | Self-hosted, LLVM premerge cluster on GCP (`bazel-checks.yml` pins runner group `llvm-premerge-cluster-us-central`) | `premerge.yaml`, `bazel-checks.yml` |
| `llvm-premerge-libcxx-runners`, `llvm-premerge-libcxx-next-runners` | Self-hosted libc++ runner sets | `libcxx-build-and-test.yaml`, `libcxx-run-benchmarks.yml` |
| `hlsl-macos` | Self-hosted HLSL runner | `hlsl-matrix.yaml` via `hlsl-test-all.yaml` |

The self-hosted runners and the Depot account are set up and paid for by
the LLVM Foundation outside this repository. Jobs that use them only run in
`llvm/llvm-project`. The premerge runners get their sccache bucket from the
`CACHE_GCS_BUCKET` variable that the runner pod sets, and the Depot runners
get it from `SCCACHE_WEBDAV_ENDPOINT` / `SCCACHE_WEBDAV_TOKEN`. Neither is a
repository secret.

## Container images

All images are published to `ghcr.io/llvm/` (see
<https://github.com/orgs/llvm/packages>). Container builds run on every PR
that touches their inputs, but **images are only pushed on `push` to
`main`**.

`.github/actions/build-container` tags an image as
`ghcr.io/<owner>/<arch>/<name>:<12-char commit sha>`, where `<arch>` is
`amd64` or `arm64v8`. `.github/actions/push-container` also pushes `:latest`,
and for `amd64` it pushes an extra alias with no arch component. So
`ghcr.io/llvm/ci-ubuntu-24.04:latest` is the x86-64 image and
`ghcr.io/llvm/arm64v8/ci-ubuntu-24.04:latest` is the AArch64 image.

| Image | Built by | Source | Consumed by |
|---|---|---|---|
| `ci-ubuntu-24.04` (amd64 + arm64v8) | `build-ci-container.yml` | `containers/github-action-ci/Dockerfile`, target `ci-container` | `premerge.yaml` (AArch64 job), `ci-post-commit-analyzer.yml`, `spirv-tests.yml`, `mlir-spirv-tests.yml`, `sycl-tests.yml` |
| `ci-ubuntu-24.04-agent` (amd64 + arm64v8) | `build-ci-container.yml` | same Dockerfile, target `ci-container-agent` | Self-hosted runner image (`ci-container` plus the Actions runner); the runner deployment lives outside this repo |
| `ci-ubuntu-24.04-format` | `build-ci-container-tooling.yml` | `containers/github-action-ci-tooling/Dockerfile`, target `ci-container-code-format` | `pr-code-format.yml` |
| `ci-ubuntu-24.04-lint` | `build-ci-container-tooling.yml` | same, target `ci-container-code-lint` | `pr-code-lint.yml` |
| `ci-ubuntu-24.04-abi-tests` | `build-ci-container-tooling.yml` | same, target `ci-container-abi-tests` | `llvm-abi-tests.yml`, `libclang-abi-tests.yml` (pinned by digest) |
| `ci-windows-2022` | `build-ci-container-windows.yml` | `containers/github-action-ci-windows/Dockerfile` | Self-hosted Windows runner image; the runner deployment lives outside this repo |
| `libc-ubuntu-24.04` (amd64 + arm64v8) | `build-libc-container.yml` | `containers/libc/Dockerfile` | `libc-fullbuild-tests.yml` |
| `metrics` | `build-metrics-container.yml` | `.ci/metrics/` | CI metrics collection (deployed outside this repo) |
| `libcxx-linux-builder-base`, `libcxx-linux-builder`, `libcxx-android-builder` | `libcxx-build-containers.yml` | `libcxx/utils/ci/docker/docker-compose.yml` | libc++ CI, see `libcxx/utils/ci/docker/` |

How changes flow through the chain:

```
PR edits .github/workflows/containers/github-action-ci/**
  -> build-ci-container.yml builds and smoke-tests on depot-ubuntu-24.04-16 / -arm-16 (no push)
  -> merge to main: push-ci-container (ubuntu-24.04) pushes :<sha> and :latest to ghcr.io/llvm
  -> later runs of premerge.yaml, spirv-tests.yml, ... pull the new :latest
```

So a Dockerfile change is only exercised by the consuming workflows after it
lands on `main`.

## Secrets and environments

`GITHUB_TOKEN` is the token GitHub creates for each run. Its scope comes
from each job's `permissions:` block. All other secrets are only set on
`llvm/llvm-project`.

| Secret | Purpose | Used by |
|---|---|---|
| `ISSUE_SUBSCRIBER_TOKEN` | Bot PAT for labelling and @-mentioning teams on issues/PRs, and for filing audit issues | `issue-subscriber.yml`, `pr-subscriber.yml`, `new-issues.yml`, `new-prs.yml`, `release-asset-audit.yml` |
| `LLVM_TOKEN_GENERATOR_CLIENT_ID`, `LLVM_TOKEN_GENERATOR_PRIVATE_KEY` | GitHub App credentials, exchanged for a short-lived token | `commit-access-review.yml` |
| `RELEASE_WORKFLOW_PR_CREATE`, `RELEASE_WORKFLOW_PUSH_SECRET` | Open backport PRs and push backport branches for `/cherry-pick` comments | `issue-release-workflow.yml` |
| `RELEASE_TASKS_USER_TOKEN` | Upload release assets and check release-manager membership | `release-tasks.yml`, `release-binaries-all.yml`, `release-binaries.yml`, `release-doxygen.yml` |
| `LLVMBOT_WWW_RELEASES_PUSH`, `WWW_RELEASES_TOKEN` | Publish release docs to the `llvm/www-releases` repo | `release-documentation.yml` |
| `LLVM_BUGS_KEY` | Mailgun API key for the llvm-bugs mailing list | `llvm-bugs.yml` |

| Environment | Purpose | Used by |
|---|---|---|
| `main-branch-only` | Keeps secrets for jobs that must only run from `main` | `commit-access-review.yml`, `issue-release-workflow.yml` |
| `release` | Release documentation publishing | `release-documentation.yml` |
| `pypi` | PyPI trusted publishing of release Python packages | `release-tasks.yml` |

## Workflow index

Path filters are shortened. The YAML file has the full list, and nearly
every workflow also triggers on edits to its own file. "PR" means
`pull_request`. "PR-target" means `pull_request_target`, which runs with
base-branch code and secrets.

### Pre-merge build and test

| Workflow | Trigger | Runner | Container | Secrets / env | Guard | Local equivalent |
|---|---|---|---|---|---|---|
| `premerge.yaml` (CI Checks) | PR (all paths, incl. `closed` to cancel in-flight runs); push `release/**` | `llvm-premerge-linux-runners`, `depot-ubuntu-24.04-arm-16`, `llvm-premerge-windows-2022-runners`; `macos-14` for release branches only | `ghcr.io/llvm/arm64v8/ci-ubuntu-24.04` on Depot; runner pod image elsewhere | - | owner | See [Reproducing pre-merge CI](#reproducing-pre-merge-ci-locally) |
| `bazel-checks.yml` | PR / push `main`: `utils/bazel/**` | `ubuntu-24.04` (buildifier); `llvm-premerge-linux-runners` (build) | - | - | repo | `cd utils/bazel && bazelisk test --config=ci @llvm-project//... //...` |
| `check-ci.yml` | PR / push `main`: `.ci/**` | `ubuntu-24.04` | - | - | repo | `pip install -r .ci/all_requirements.txt -r .ci/metrics/requirements.lock.txt pytest && (cd .ci && pytest)` |
| `docs.yml` | PR / push `main`: `*/docs/**`, doc `.td` files | `ubuntu-24.04` | - | - | repo | `pip install -r llvm/docs/requirements-hashed.txt`, then `cmake -B build -GNinja -DLLVM_ENABLE_SPHINX=ON [-DLLVM_ENABLE_PROJECTS=...] llvm && ninja -C build docs-<project>-html` |
| `pr-code-format.yml` | PR to `main` / `users/**` (all paths) | `ubuntu-24.04` | `ghcr.io/llvm/ci-ubuntu-24.04-format` | `GITHUB_TOKEN` | repo | `git clang-format origin/main` (C/C++) and `darker --check --diff -r origin/main...HEAD <files>` (Python); the CI driver is `llvm/utils/git/code-format-helper.py` |
| `pr-code-lint.yml` | PR to `main` / `users/**`: `clang-tools-extra/clang-tidy/**` | `ubuntu-24.04` | `ghcr.io/llvm/ci-ubuntu-24.04-lint` | `GITHUB_TOKEN` | owner | `llvm/utils/git/code-lint-helper.py` after a build that produces `compile_commands.json` |
| `email-check.yaml` | PR opened | `ubuntu-24.04` | - | - | repo | Warns (via comment) when the commit author email ends in `noreply.github.com`; check `git log --format=%ae` |
| `version-check.yml` | PR / push `release/**` | `ubuntu-24.04` | - | - | owner | `.github/workflows/version-check.py <version from cmake/Modules/LLVMVersion.cmake>` |

### Project-specific tests

| Workflow | Trigger | Runner | Container | Secrets / env | Guard | Local equivalent |
|---|---|---|---|---|---|---|
| `libcxx-build-and-test.yaml` | PR: `libcxx/**`, `libcxxabi/**`, `libunwind/**`, `runtimes/**`, `cmake/**`; daily cron | `llvm-premerge-libcxx-runners`, `macos-15`, `windows-2022`, `windows-11-arm` | - (Linux jobs use the self-hosted runner image) | - | owner | `libcxx/utils/ci/run-buildbot <config>` (e.g. `generic-cxx26`) |
| `libcxx-check-generated-files.yml` | PR: `libcxx/**` | `ubuntu-24.04` | - | - | repo | `libcxx/utils/ci/run-buildbot check-generated-output` |
| `libcxx-run-benchmarks.yml` | Issue comment on a PR (`/libcxx-bot benchmark ...`) | `llvm-premerge-libcxx-next-runners` | - | - | - | `libcxx/utils/test-at-commit` + `libcxx/utils/compare-benchmarks` |
| `libc-fullbuild-tests.yml` | PR to `main`: `libc/**` | `ubuntu-24.04`, `ubuntu-24.04-arm` | `ghcr.io/llvm/[arm64v8/]libc-ubuntu-24.04` | - | - | Full-build libc with `-DLLVM_LIBC_FULL_BUILD=ON` (see `libc/docs/full_host_build.rst`) |
| `libc-overlay-tests.yml` | PR to `main`: `libc/**` | `ubuntu-24.04[-arm]`, `windows-2022`, `windows-2025`, `macos-15` | - | - | - | `cmake -S runtimes -B build -GNinja -DLLVM_ENABLE_RUNTIMES=libc && cmake --build build --target check-libc` |
| `libc-shared-tests.yml` | PR: `libc/**` | `windows-2022`, `windows-11-arm`, `ubuntu-24.04` | - | - | - | `cmake -S runtimes -B build -GNinja ...` (see workflow), then `cmake --build build --target libc-shared-tests` |
| `libclang-python-tests.yml` | PR / push `main`: `clang/bindings/python/**`, `clang/tools/libclang/**` | `ubuntu-24.04` | - | - | repo | `cmake -GNinja -B build -DLLVM_ENABLE_PROJECTS=clang llvm && ninja -C build check-clang-python` |
| `lldb-pylint-action.yml` | PR: `lldb/test/API/**.py` | `ubuntu-24.04` | - | - | owner | `pip install --require-hashes -r llvm/utils/git/requirements_pylint.txt && pylint --disable=all --enable=E0102 <files>` |
| `spirv-tests.yml` | PR: `llvm/lib/Target/SPIRV/**`, `llvm/test/CodeGen/SPIRV/**` | `ubuntu-24.04` | `ghcr.io/llvm/ci-ubuntu-24.04:latest` | - | owner | `cmake -GNinja -S llvm -B build -DLLVM_TARGETS_TO_BUILD=SPIRV -DLLVM_INCLUDE_SPIRV_TOOLS_TESTS=ON && ninja -C build check-llvm-codegen-spirv` |
| `mlir-spirv-tests.yml` | PR: MLIR SPIR-V dialect/target paths; manual | `ubuntu-24.04` | `ghcr.io/llvm/ci-ubuntu-24.04:latest` | - | owner | `ninja -C build check-mlir` |
| `sycl-tests.yml` | PR: `libsycl/**` | `ubuntu-24.04` | `ghcr.io/llvm/ci-ubuntu-24.04:latest` | - | owner | `ninja -C build check-sycl` |
| `hlsl-matrix.yaml` -> `hlsl-test-all.yaml` | PR to `main`: DirectX / HLSL paths; manual | `hlsl-macos` | - | - | - | See `hlsl-test-all.yaml` (builds DXC and llvm/offload-test-suite) |
| `ci-post-commit-analyzer.yml` | Daily cron; push `release/**` (`clang/**`, `llvm/**`); PR editing the workflow | `ubuntu-24.04` | `ghcr.io/llvm/ci-ubuntu-24.04:latest` | - | owner | `ninja -C build libLLVM.so libclang.so && python3 .github/workflows/ci-post-commit-analyzer-run.py build/compile_commands.json` |
| `llvm-abi-tests.yml` | PR / push `release/**`: `llvm/**`; manual | `ubuntu-24.04` | `ghcr.io/llvm/ci-ubuntu-24.04-abi-tests` (digest-pinned) | - | owner | abi-dumper / abi-compliance-checker against the previous release |
| `libclang-abi-tests.yml` | PR / push `release/**`: `clang/**`; manual | `ubuntu-24.04` | `ghcr.io/llvm/ci-ubuntu-24.04-abi-tests` (digest-pinned) | - | owner | as above, for `libclang.so` |
| `ids-check.yml` | Manual only | `ubuntu-24.04` | - | `GITHUB_TOKEN` | owner | Builds [compnerd/ids](https://github.com/compnerd/ids) and checks `LLVM_ABI` annotations in public headers |

### CI container builds

| Workflow | Trigger | Runner | Produces | Secrets / env | Guard |
|---|---|---|---|---|---|
| `build-ci-container.yml` | PR / push `main`: `containers/github-action-ci/**`, `.github/actions/{build,push}-container/**` | Build: `depot-ubuntu-24.04-16`, `depot-ubuntu-24.04-arm-16`. Push: `ubuntu-24.04` | `ci-ubuntu-24.04`, `ci-ubuntu-24.04-agent` | `GITHUB_TOKEN` (`packages: write`, push job only) | owner |
| `build-ci-container-tooling.yml` | PR / push `main`: `containers/github-action-ci-tooling/**`, `llvm/utils/git/requirements_{formatting,linting}.txt` | `ubuntu-24.04` | `ci-ubuntu-24.04-{format,lint,abi-tests}` | `GITHUB_TOKEN` | owner |
| `build-ci-container-windows.yml` | PR / push `main`: `containers/github-action-ci-windows/**` | Build: `windows-2022`. Push: `ubuntu-24.04` (skopeo) | `ci-windows-2022` | `GITHUB_TOKEN` | owner |
| `build-libc-container.yml` | PR / push `main`: `containers/libc/**` | `ubuntu-24.04`, `ubuntu-24.04-arm` | `libc-ubuntu-24.04` | `GITHUB_TOKEN` | owner |
| `build-metrics-container.yml` | PR / push `main`: `.ci/metrics/**` | `ubuntu-24.04` | `metrics` | `GITHUB_TOKEN` | owner |
| `libcxx-build-containers.yml` | PR / push `main`: `libcxx/utils/ci/docker/**` | `ubuntu-24.04` | `libcxx-*-builder*` | `GITHUB_TOKEN` | owner |

Build a container image locally the same way CI does (podman or docker):

```bash
podman build --target ci-container \
  -f .github/workflows/containers/github-action-ci/Dockerfile \
  -t ci-ubuntu-24.04 .github/workflows/containers/github-action-ci/
```

### Issue and PR automation

| Workflow | Trigger | Runner | Secrets / env | Guard |
|---|---|---|---|---|
| `new-prs.yml` | PR-target opened/reopened/ready/synchronize | `ubuntu-24.04` | `GITHUB_TOKEN`, `ISSUE_SUBSCRIBER_TOKEN` | repo |
| `new-issues.yml` | Issue opened | `ubuntu-24.04` | `ISSUE_SUBSCRIBER_TOKEN` | repo |
| `issue-subscriber.yml` | Issue labeled | `ubuntu-24.04` | `ISSUE_SUBSCRIBER_TOKEN` | repo |
| `pr-subscriber.yml` | PR-target labeled | `ubuntu-24.04` | `ISSUE_SUBSCRIBER_TOKEN` | repo |
| `issue-write.yml` | `workflow_run` completed for: Check code formatting, Check for private emails used in PRs, PR Request Release Note, Code lint, CI Checks, Test Issue Write, Check LLVM ABI annotations | `ubuntu-24.04` | `GITHUB_TOKEN` (`pull-requests: write`) | - |
| `merged-prs.yml` | PR-target closed | `ubuntu-24.04` | `GITHUB_TOKEN` | repo |
| `commit-access-greeter.yml` | Issue labeled | `ubuntu-24.04` | - | owner |
| `commit-access-review.yml` | Monthly cron; manual | `ubuntu-24.04` | `LLVM_TOKEN_GENERATOR_*`; env `main-branch-only` | owner |
| `llvm-bugs.yml` | Issue opened | `ubuntu-24.04` | `LLVM_BUGS_KEY` | repo |
| `issue-release-workflow.yml` | Issue comment (`/cherry-pick`, `/branch`); issue opened | `ubuntu-24.04` | `RELEASE_WORKFLOW_PR_CREATE`, `RELEASE_WORKFLOW_PUSH_SECRET`; env `main-branch-only` | repo |

Labels and team mentions come from `.github/new-prs-labeler.yml` and
`.github/new-issues-labeler.yml`. Most helpers are in
`llvm/utils/git/github-automation.py`.

### Release

| Workflow | Trigger | Runner | Secrets / env | Guard |
|---|---|---|---|---|
| `release-tasks.yml` | Push tag `llvmorg-*` | `ubuntu-24.04` (calls the workflows below) | `RELEASE_TASKS_USER_TOKEN`; env `pypi` | repo |
| `release-binaries-all.yml` | Weekly cron; manual; called by `release-tasks.yml`; PR editing release build files | Matrix: `ubuntu-22.04[-arm]`, `macos-14`, `windows-2022`, `windows-11-arm` | `RELEASE_TASKS_USER_TOKEN` | - |
| `release-binaries.yml` | Manual; called | Prepare/upload: GitHub-hosted. Build: `ubuntu-22.04*`/`windows-2022` -> `depot-<input>-16`; `macos-14` -> `depot-macos-14` (not on PRs); `windows-11-arm` -> `windows-11-arm-16core` (not on PRs/cron) | `RELEASE_TASKS_USER_TOKEN` | owner |
| `release-sources.yml` | Manual; called; PR editing `llvm/utils/release/export.sh` | `ubuntu-24.04` | - | owner |
| `release-documentation.yml` | Manual; called | `ubuntu-24.04` | `LLVMBOT_WWW_RELEASES_PUSH`, `WWW_RELEASES_TOKEN`; env `release` | - |
| `release-doxygen.yml` | Manual; called | `ubuntu-24.04` | `RELEASE_TASKS_USER_TOKEN` | - |
| `release-asset-audit.yml` | Hourly cron; release event; manual; PR editing the audit script | `ubuntu-24.04` | `ISSUE_SUBSCRIBER_TOKEN` | repo |
| `release-llvm-testing-tools.yml` | PR: `llvm/utils/llvm-testing-tools/**` | `ubuntu-24.04` | - | repo |

The release process itself is in `llvm/docs/HowToReleaseLLVM.rst`. Locally,
`llvm/utils/release/export.sh` builds the source tarballs and
`clang/cmake/caches/Release.cmake` is the binary build configuration.

### Repository hygiene and security

| Workflow | Trigger | Runner | Secrets / env | Guard |
|---|---|---|---|---|
| `zizmor.yml` | PR / push `main`: `.github/**` | `ubuntu-24.04` | - | owner |
| `gha-codeql.yml` | PR to `main`: `.github/**`; daily cron | `ubuntu-24.04` | - | - |
| `scorecard.yml` | Branch protection rule change; daily cron | `ubuntu-24.04` | - | repo |
| `prune-branches.yml` | Daily cron; PR editing the prune script | `ubuntu-24.04` | `GITHUB_TOKEN` | owner |
| `test-unprivileged-download-artifact.yml` | PR / push `main`: `unprivileged-download-artifact/**` | `ubuntu-24.04` | - | owner |

`zizmor.yml` uses `zizmorcore/zizmor-action`; run `zizmor .github/workflows` locally before sending a workflow change.

## Reusable actions and helper scripts

| Path | Kind | Used by |
|---|---|---|
| `.github/actions/build-container` | Composite action: podman build + artifact + smoke test | Container build workflows |
| `.github/actions/push-container` | Composite action: push `:<sha>`, `:latest` and amd64 alias to ghcr.io | Container build workflows |
| `get-llvm-version/` | Composite action: read the LLVM version from CMake | ABI tests, `release-binaries.yml` |
| `unprivileged-download-artifact/` | Composite action: download artifacts from another run without write permissions | `issue-write.yml` |
| `upload-release-artifact/` | Composite action: attest and upload release assets | `release-binaries.yml`, `release-sources.yml` |
| `hlsl-test-all.yaml` | Reusable workflow (`workflow_call`) | `hlsl-matrix.yaml` |
| `*.py`, `*.sh` in this directory | Helper scripts for the workflow with the matching name | - |
| `.ci/` | Pre-merge driver scripts (`compute_projects.py`, `monolithic-*.sh`, report generators) and metrics | `premerge.yaml`, `check-ci.yml` |

## Reproducing pre-merge CI locally

`premerge.yaml` works out what to build from the files changed by the last
commit. It then runs the monolithic build script in the same image the CI
runners use:

```bash
# From the monorepo root, with the change committed as HEAD.
podman run --rm -it -v "$PWD:/src" -w /src ghcr.io/llvm/ci-ubuntu-24.04:latest bash

# Inside the container:
git config --global --add safe.directory '*'
source <(git diff --name-only HEAD~1...HEAD | python3 .ci/compute_projects.py)
echo "$projects_to_build | $project_check_targets | $runtimes_to_build"
export CC=/opt/llvm/bin/clang CXX=/opt/llvm/bin/clang++
sccache --start-server
./.ci/monolithic-linux.sh "${projects_to_build}" "${project_check_targets}" \
  "${runtimes_to_build}" "${runtimes_check_targets}" \
  "${runtimes_check_targets_needs_reconfig}" "${enable_cir}"
```

Notes:

* `.ci/utils.sh` deletes `${BUILD_DIR}` (default: `<repo>/build`) before it
  configures. Set `BUILD_DIR` if you have a build tree you want to keep.
* Use `ghcr.io/llvm/arm64v8/ci-ubuntu-24.04:latest` to match the AArch64 job.
* Windows uses `.ci/monolithic-windows.sh` from a VS developer prompt. macOS
  (release branches only) runs plain `cmake`/`ninja`, see the
  `premerge-check-macos` job.
