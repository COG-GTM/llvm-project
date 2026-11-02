Github action workflows should be stored in this directory.

Pushing an `llvmorg-X.Y.Z[-rcN]` tag runs `release-tasks.yml`, which creates the
GitHub release, publishes `lit` to PyPI and builds and uploads documentation,
doxygen and release binaries. Its jobs, the secrets and environments it needs
(`RELEASE_TASKS_USER_TOKEN`, `pypi`, `release`) and the release manager
permission check are documented in the
[Automated Release Tasks](https://llvm.org/docs/HowToReleaseLLVM.html#automated-release-tasks)
section of `llvm/docs/HowToReleaseLLVM.rst`.
