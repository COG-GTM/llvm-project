=================================
How To Release LLVM To The Public
=================================

Introduction
============

This document contains information about successfully releasing LLVM ---
including sub-projects: e.g., ``clang`` and ``compiler-rt`` --- to the public.
It is the Release Manager's responsibility to ensure that a high quality build
of LLVM is released.

If you're looking for the document on how to test the release candidates and
create the binary packages, please refer to the :doc:`ReleaseProcess` instead.

.. _timeline:

Release Timeline
================

LLVM is released on a time-based schedule --- with major releases roughly
every 6 months.  In between major releases there may be dot releases.
The release manager will determine if and when to make a dot release based
on feedback from the community.  Typically, dot releases should be made if
there are a large number of bug fixes in the stable branch or a critical bug
has been discovered that affects a large number of users.

Unless otherwise stated, dot releases will follow the same procedure as
major releases.

Annual Release Schedule
-----------------------

Here is the annual release schedule for LLVM.  This is meant to be a
guide, and release managers are not required to follow this exactly.
Releases should be tagged on Tuesdays.

=============================== =========================
Release                         Approx. Date
=============================== =========================
*release branch: even releases* *2nd Tue in January*
*release branch: odd releases*  *2nd Tue in July*
X.1.0-rc1                       3 days after branch.
X.1.0-rc2                       2 weeks after branch.
X.1.0-rc3                       4 weeks after branch
**X.1.0-final**                 **6 weeks after branch**
**X.1.1**                       **8 weeks after branch**
**X.1.2**                       **10 weeks after branch**
**X.1.3**                       **12 weeks after branch**
**X.1.4**                       **14 weeks after branch**
**X.1.5**                       **16 weeks after branch**
**X.1.6**                       **18 weeks after branch**
**X.1.7**                       **20 weeks after branch**
**X.1.8**                       **22 weeks after branch**
**X.1.9** (If necessary)        **24 weeks after branch**
**Next release branches**       **~25 weeks after branch**
=============================== =========================

Release Process Summary
-----------------------

* Announce release schedule to the LLVM community and update the website.  Do
  this at least 3 weeks before the -rc1 release.

* Create release branch and begin release process.

* Send out release candidate sources for first round of testing.  Testing lasts
  6 weeks.  During the first round of testing, any regressions found should be
  fixed.  Patches are merged from mainline into the release branch.  Also, all
  features need to be completed during this time.  Any features not completed at
  the end of the first round of testing will be removed or disabled for the
  release.

* Generate and send out the second release candidate sources.  Only *critical*
  bugs found during this testing phase will be fixed.  Any bugs introduced by
  merged patches will be fixed.  If so, a third round of testing is needed.

* The release notes are updated.

* Finally, release!

* Announce bug fix release schedule to the LLVM community and update the website.

* Do bug-fix releases every two weeks until X.1.5 or X.1.6 (if necessary).

Release Process
===============

.. contents::
   :local:

Release Administrative Tasks
----------------------------

This section describes a few administrative tasks that need to be done for the
release process to begin.  Specifically, it involves:

* Updating version numbers,

* Creating the release branch, and

* Tagging release candidates for the release team to begin testing.

Create Release Branch and Update LLVM Version
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Branch the Git trunk using the following procedure:

#. Verify the current git trunk is in decent shape by examining the status
   checks on the `most recent commits <https://github.com/llvm/llvm-project/commits/main>`_

#. Bump the version in trunk to ``N.0.0git`` and clear the release notes: ::

    $ llvm/utils/release/bump-version.py --git N.0.0
    $ llvm/utils/release/clear-release-notes.py
    $ git commit -am "Bump version to N.0.0git"
    $ git push origin main

   If the push fails, rebase if necessary and try again.

#. Tag the commit bumping the version on trunk with ``llvmorg-N-init``. If
   ``X`` is the version to be released, then ``N`` is ``X + 1``. ::

    $ GPG_TTY=$(tty) git tag -sa llvmorg-N-init -m "llvmorg-N-init"
    $ git push origin llvmorg-N-init

#. Create the release branch from the last known good revision before the
   version bump. The branch name is ``release/X.x`` where ``X`` is the major
   version number and ``x`` is just the letter ``x``. Assuming the revision
   before the version bump is ok, this would be: ::

    $ git checkout -b release/X.x llvmorg-N-init^

#. On the newly-created release branch, immediately bump the version to
   ``X.1.0git`` (where ``X`` is the major version number): ::

    $ llvm/utils/release/bump-version.py --git X.1.0
    $ git commit -am "Bump version to X.1.0git"

#. Push release branch: ::

    $ git push -u origin release/X.x

#. And finally, create the release branch in ``llvm-test-suite`` repo: ::

    $ cd <llvm-test-suite>
    $ git checkout main
    $ git pull
    $ git checkout -b release/X.x
    $ git push -u origin release/X.x

Tagging the LLVM Release Candidates
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Tag release candidates:

::

  $ git tag -sa llvmorg-X.Y.Z-rcN

The pre-packaged source tarballs will be automatically generated via the
`Release Sources
<https://github.com/llvm/llvm-project/actions/workflows/release-sources.yml>`_
workflow on GitHub.  This workflow will create an artifact containing all the
release tarballs and the artifact attestation.  The Release Manager should
download the artifact, verify the tarballs, sign them, and then upload them to
the release page.

::

  $ unzip artifact.zip
  $ gh auth login
  $ for f in *.xz; do gh attestation verify --owner llvm $f && gpg -b $f; done

Tarballs, release binaries,  or any other release artifacts must be uploaded to
GitHub.  This can be done using the ``github-upload-release.py`` script in ``utils/release``.

::

  $ github-upload-release.py upload --token <github-token> --release X.Y.Z-rcN --files <release_files>


Build The Binary Distribution
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The official release binaries for Linux, macOS and Windows are built and
uploaded by GitHub Actions, as described in
:ref:`automated-release-binaries` below.  Release managers do not need to build
these binaries by hand.

Release testers and community members who build binaries for other platforms,
or who want to validate a release candidate locally, use the manual
``test-release.sh`` process described :doc:`here <ReleaseProcess>`.  That
process is *not* how the binaries published by the GitHub workflows are made,
so its output will not match them exactly.

``test-release.sh`` performs both Release+Asserts and Release builds but only
packs the Release build for upload. You should use the Release+Asserts sysroot,
normally under ``final/Phase3/Release+Asserts/llvmCore-3.8.1-RCn.install/``,
for test-suite and run-time benchmarks, to ensure nothing serious has
passed through the net. For compile-time benchmarks, use the Release version.

The minimum required version of the tools you'll need are :doc:`here <GettingStarted>`

.. _automated-release-binaries:

Automated Release Binaries
^^^^^^^^^^^^^^^^^^^^^^^^^^

Workflow chain
""""""""""""""

Pushing a release tag starts the following chain of GitHub workflows:

::

  git push origin llvmorg-X.Y.Z[-rcN]
    -> .github/workflows/release-tasks.yml         (validate tag, create release)
      -> .github/workflows/release-binaries-all.yml  (one job per platform)
        -> .github/workflows/release-binaries.yml      (prepare, build, upload)

* `release-tasks.yml
  <https://github.com/llvm/llvm-project/actions/workflows/release-tasks.yml>`_
  runs on ``llvmorg-*`` tag pushes in ``llvm/llvm-project`` only.  It checks
  that the tag matches ``llvmorg-X.Y.Z`` or ``llvmorg-X.Y.Z-rcN``, creates the
  GitHub release, and then calls ``release-binaries-all.yml`` with
  ``upload: true``.  It also builds the documentation, doxygen, source
  tarballs and the ``lit`` package.  When the binaries are done, it uncomments
  the download links in the release notes.
* `release-binaries-all.yml
  <https://github.com/llvm/llvm-project/actions/workflows/release-binaries-all.yml>`_
  calls ``release-binaries.yml`` once for each of these runners:
  ``ubuntu-22.04``, ``ubuntu-22.04-arm``, ``macos-14``, ``windows-2022`` and
  ``windows-11-arm`` (``fail-fast`` is off).  It also runs every Saturday on a
  schedule, and on pull requests that change the release workflows or
  ``clang/cmake/caches/Release.cmake``.  Scheduled and pull request runs never
  upload anything.
* `release-binaries.yml
  <https://github.com/llvm/llvm-project/actions/workflows/release-binaries.yml>`_
  has three jobs:

  #. ``prepare`` checks permissions (see :ref:`release-binaries-permissions`),
     works out the release version, file name, CMake flags and runners for the
     platform.
  #. ``build-release-package`` builds the package, saves it as a workflow
     artifact together with its sha256 digest, and then runs the tests.
  #. ``upload-release-binaries`` (skipped for pull requests) downloads the
     artifact, checks the digest, generates a build provenance attestation and,
     if ``upload`` is true, checks permissions again and uploads the package
     and ``<file>.jsonl`` attestation to the GitHub release.

All jobs in ``release-binaries.yml`` require
``github.repository_owner == 'llvm'``, so the workflow does nothing in forks.

Running the workflows manually
""""""""""""""""""""""""""""""

If a build fails or needs to be redone, a release manager can start it again
from the Actions tab with ``workflow_dispatch``:

* *Release Binaries All* builds all platforms.  Inputs: ``release-version``
  (e.g. ``X.Y.Z-rcN``, required) and ``upload``.
* *Release Binaries* builds one platform.  Inputs: ``release-version``,
  ``upload`` and ``runs-on``.  Only ``ubuntu-22.04``, ``ubuntu-22.04-arm`` and
  ``macos-14`` can be picked here; to rebuild Windows, use
  *Release Binaries All*.

When ``release-version`` is set, the workflow builds the ``llvmorg-<version>``
tag.  The GitHub release for that version must already exist before
``upload`` is turned on.  For example, with the GitHub CLI:

::

  $ gh workflow run release-binaries-all.yml --repo llvm/llvm-project \
      -f release-version=X.Y.Z-rcN -f upload=true

The workflow artifacts (package and attestation) can be downloaded from the run
page and checked with ``gh attestation verify --owner llvm <file>``.

.. _release-binaries-permissions:

Secrets and permissions
"""""""""""""""""""""""

The workflows use one repository secret, ``RELEASE_TASKS_USER_TOKEN``.  It is a
GitHub token that can read the members of the ``llvm`` organization's teams.
It is passed to ``llvm/utils/release/github-upload-release.py`` as
``--user-token`` together with ``--user $GITHUB_ACTOR``.  The script then
checks that the user who started the workflow is a member of the
``llvm-release-managers`` team, and fails otherwise.  The workflow's own
``GITHUB_TOKEN`` (``contents: write``, ``id-token: write`` and
``attestations: write`` on the upload job) does the actual release creation,
attestation and upload.

This check runs:

* in ``release-tasks.yml`` before the release is created (the ``create``
  command) and before ``lit`` is published,
* in the ``prepare`` job of ``release-binaries.yml`` for every event except
  ``pull_request`` (so scheduled and manual runs also need the secret and a
  release manager), and
* in ``upload-release-artifact`` right before the upload, when ``upload`` is
  true.

The secret is not available to pull request runs, which skip these checks and
never upload.  If the token expires or can no longer read the team
membership, every release workflow (except pull request runs) fails at the
permission check, so the secret must be rotated in the repository settings.

Build recipe
""""""""""""

On Linux and macOS, the package is built with the ``Release.cmake`` cache and
the ``stage2-package`` target.  To reproduce a published binary locally, run
the same commands from the root of a checkout of the release tag:

::

  $ cmake -G Ninja -S llvm -B build <platform flags> \
      -C clang/cmake/caches/Release.cmake
  $ ninja -C build stage2-package
  $ ninja -C build stage2-check-all   # optional, see below

The package ends up in the ``stage2-bins`` directory under the build
directory and is named ``LLVM-<version>-<OS>-<arch>.tar.xz`` (for example
``LLVM-X.Y.Z-Linux-X64.tar.xz``).  ``<platform flags>`` are the extra flags
listed in the next section.  They must come before ``-C``, because
``Release.cmake`` only sets its ``LLVM_RELEASE_*`` options if they are not
already in the cache.

``Release.cmake`` defaults to a multi-stage build with PGO
(``LLVM_RELEASE_ENABLE_PGO=ON``) and ThinLTO (``LLVM_RELEASE_ENABLE_LTO=THIN``).
With PGO on, the final stage is configured through ``BOOTSTRAP_BOOTSTRAP_*``
variables; with PGO off, through ``BOOTSTRAP_*``.  See the comments at the top
of ``clang/cmake/caches/Release.cmake`` for the projects and runtimes it
enables on each platform.

On Windows, the workflow runs
``llvm/utils/release/build_llvm_release.bat --x64|--arm64 --version <version>
--local-python --skip-checkout`` instead, which produces both the
``clang+llvm-<version>-<arch>-pc-windows-msvc.tar.xz`` tarball and the
``.exe`` installer.  It does not use ``Release.cmake`` or the flags computed in
``prepare``.

Platform differences
""""""""""""""""""""

The ``prepare`` job changes the runner and the CMake flags depending on the
platform and on the event that started the workflow.  The binaries are
therefore not all built with the same configuration:

.. list-table::
   :header-rows: 1

   * - Matrix entry
     - Build runner (tag push or manual run)
     - Build runner (pull request)
     - Extra flags / configuration
   * - ``ubuntu-22.04``, ``ubuntu-22.04-arm``
     - ``depot-ubuntu-22.04-16``, ``depot-ubuntu-22.04-arm-16``
     - same as tag push
     - None.  PGO + ThinLTO.  Ubuntu 22.04 is used, rather than the latest
       version, so the binaries work with older glibc versions.
   * - ``macos-14``
     - ``depot-macos-14``
     - ``macos-14`` (GitHub-hosted)
     - Always ``-DBOOTSTRAP_BOOTSTRAP_COMPILER_RT_ENABLE_IOS=OFF`` and
       ``-DBOOTSTRAP_BOOTSTRAP_DARWIN_osx_ARCHS=arm64``
       ``-DBOOTSTRAP_BOOTSTRAP_DARWIN_osx_BUILTIN_ARCHS=arm64`` (no iOS
       compiler-rt, arm64 only, see `#99767
       <https://github.com/llvm/llvm-project/issues/99767>`_).  On the
       GitHub-hosted runner, also ``-DLLVM_RELEASE_ENABLE_LTO=OFF
       -DLLVM_RELEASE_ENABLE_PGO=OFF`` so the build fits in the 6 hour job
       limit.  flang is not built on macOS.
   * - ``windows-2022``
     - ``depot-windows-2022-16``
     - same as tag push
     - ``build_llvm_release.bat --x64``: PGO, no LTO.
   * - ``windows-11-arm``
     - ``windows-11-arm-16core``
     - ``windows-11-arm`` (also used by scheduled runs)
     - ``build_llvm_release.bat --arm64``: PGO, no LTO.

On all platforms, the build sets ``CPACK_PACKAGE_FILE_NAME`` for the final
stage to the release file name.  ``prepare`` also adds
``-DLLVM_RELEASE_ENABLE_LTO=OFF`` for Windows because the build used to time
out, but this flag is only used by the ``Release.cmake`` path, so it has no
effect on the Windows build script.

Because pull request runs on macOS use a different runner and configuration
than tag pushes, a green pull request build does not prove that the full
PGO + LTO release configuration builds on macOS.

Tests do not block the release
""""""""""""""""""""""""""""""

On Linux and macOS, ``ninja stage2-check-all`` runs *after* the package has
been saved as an artifact, and the step has ``continue-on-error: true``.  Test
failures are shown in the job log but never stop the upload.  Release managers
should look at the *Run Tests* step of each ``build-release-package`` job
before announcing a release.

On Windows, there is no separate test step.  ``build_llvm_release.bat`` runs a
subset of ``check-*`` targets itself while building, and those do stop the
build when they fail.

Release Qualification Criteria
------------------------------

There are no official release qualification criteria.
The release manager determines when a release is ready.  The release manager
should pay attention to the results of community testing, the number of outstanding
bugs, and the number of regressions when determining whether or not to make a
release.

The community values time based releases, so releases should not be delayed for
too long unless critical issues remain.  In most cases, the only
kind of bugs that are critical enough to block a release would be a major regression
from a previous release.

Official Testing
----------------

A few developers in the community have dedicated time to validate the release
candidates and volunteered to be the official release testers for each
architecture.

These will be the ones testing, generating, and uploading the official binaries
to the server, and will be the minimum tests *necessary* for the release to
proceed.

This will obviously not cover all OSs and distributions, so additional community
validation is important. However, if community input is not received before the
release, all reported bugs will be deferred to the next stable release.

The official release managers are:

* Even releases: Tom Stellard (tstellar@redhat.com)
* Odd releases: Tobias Hieta (tobias@hieta.se)

The official release testers are volunteers from the community who have
consistently validated and released binaries for their targets/OSs. To contact
them, you should post on the `Discourse forums (Project
Infrastructure - Release Testers). <https://discourse.llvm.org/c/infrastructure/release-testers/66>`_

The official testers list is in the file ``RELEASE_TESTERS.TXT``
<https://github.com/llvm/llvm-project/blob/main/llvm/RELEASE_TESTERS.TXT>`_, in
the LLVM repository.

Community Testing
-----------------

Once all testing is complete and appropriate bugs are filed, the release
candidate tarballs are put on the website, and the LLVM community is notified.

We ask that all LLVM developers test the release in any the following ways:

#. Download ``llvm-X.Y``, ``llvm-test-X.Y``, and the appropriate ``clang``
   binary.  Build LLVM.  Run ``make check`` and the full LLVM test suite (``make
   TEST=nightly report``).

#. Download ``llvm-X.Y``, ``llvm-test-X.Y``, and the ``clang`` sources.  Compile
   everything.  Run ``make check`` and the full LLVM test suite (``make
   TEST=nightly report``).

#. Download ``llvm-X.Y``, ``llvm-test-X.Y``, and the appropriate ``clang``
   binary. Build whole programs with it (ex. Chromium, Firefox, Apache) for
   your platform.

#. Download ``llvm-X.Y``, ``llvm-test-X.Y``, and the appropriate ``clang``
   binary. Build *your* programs with it and check for conformance and
   performance regressions.

#. Run the :doc:`release process <ReleaseProcess>`, if your platform is
   *different* than that which is officially supported, and report back errors
   only if they were not reported by the official release tester for that
   architecture.

We also ask that the OS distribution release managers test their packages with
the first candidate of every release and report any *new* errors in GitHub.
If the bug can be reproduced with an unpatched upstream version of the release
candidate (as opposed to the distribution's own build), the priority should be
release blocker.

During the first round of testing, all regressions must be fixed before the
second release candidate is tagged.

In the subsequent stages, the testing is only to ensure that bug
fixes previously merged in have not created new major problems. *This is not
the time to solve additional and unrelated bugs!* If no patches are merged in,
the release is determined to be ready and the release manager may move onto the
next stage.

Reporting Regressions
---------------------

Every regression found during the tests (as per the criteria above)
should be filled in a bug in GitHub and added to the release milestone.

If a bug can't be reproduced or stops being a blocker, it should be removed
from the Milestone. Debugging can continue, but on trunk.

Backport Requests
-----------------

Instructions for requesting a backport to a stable branch can be found
:ref:`here <backporting>`.

Triaging Bug Reports for Releases
---------------------------------

This section describes how to triage bug reports:

#. Search for bugs with a Release Milestone that have not been added to the
   "Release Status" github project:

   https://github.com/llvm/llvm-project/issues?q=is%3Aissue+milestone%3A%22LLVM+14.0.5+Release%22+no%3Aproject+

   Replace 14.0.5 in this query with the version from the Release Milestone being
   targeted.

   Add these bugs to the "Release Status" project.

#. Navigate to the `Release Status project <https://github.com/orgs/llvm/projects/3>`_
   to see the list of bugs that are being considered for the release.

#. Review each bug and first check if it has been fixed in main.  If it has, update
   its status to "Needs Pull Request" and create a pull request for the fix
   using the ``/cherry-pick`` or ``/branch`` comments if this has not been done already.

#. If a bug has been fixed and has a pull request created for backporting it,
   then update its status to "Needs Review" and notify a knowledgeable
   reviewer.  Usually you will want to notify the person who approved the
   patch, but you may use your best judgement on who a good reviewer would be.
   Once you have identified the reviewer(s), assign the issue to them and
   mention them (i.e., ``@username``) in a comment and ask them if the patch is safe
   to backport.  You should also review the bug yourself to ensure that it
   meets the requirements for committing to the release branch.

#. Once a bug has been reviewed, update the status to "Needs Merge". Check the
   pull request associated with the issue. If all the tests pass, then the pull
   request can be merged. If not, then add a comment on the issue asking
   someone to take a look at the failures.


Release Patch Rules
-------------------

Below are the rules regarding patching the release branch:

#. Patches applied to the release branch may only be applied by the release
   manager, the official release testers, or the maintainers with approval from
   the release manager.

#. Release managers are encouraged, but not required, to get approval from a
   maintainer before approving patches.  If there are no reachable maintainers,
   then release managers can ask approval from patch reviewers or other
   developers active in that area.

#. *Before RC1* Patches should be limited to bug fixes, important optimization
   improvements, or completion of features that were started before the branch
   was created.  As with all phases, release managers and maintainers can reject
   patches that are deemed too invasive.

#. *Before RC2/RC3* Patches should be limited to bug fixes or backend-specific
   improvements that are determined to be very safe.

#. *Before Final Major Release* Patches should be limited to critical
   bugs or regressions.

#. *Bug fix releases* Patches should be limited to bug fixes or very safe
   and critical performance improvements.  Patches must maintain both API and
   ABI compatibility with the X.1.0 release.

Release Final Tasks
-------------------

The final stages of the release process involve tagging the "final" release
branch, updating documentation that refers to the release, and updating the
demo page.

Update Documentation
^^^^^^^^^^^^^^^^^^^^

Review the documentation in the release branch and ensure that it is up
to date.  The "Release Notes" must be updated to reflect new features, bug
fixes, new known issues, and changes in the list of supported platforms.
The :doc:`GettingStarted` page should be updated to reflect the new release
version number tag and changes in basic system requirements.

.. _tag:

Tag the LLVM Final Release
^^^^^^^^^^^^^^^^^^^^^^^^^^

Tag the final release sources:

::

  $ git tag -sa llvmorg-X.Y.Z
  $ git push https://github.com/llvm/llvm-project.git llvmorg-X.Y.Z

Update the LLVM Website
^^^^^^^^^^^^^^^^^^^^^^^

The website must be updated before the release announcement is sent out.  Here
is what to do:

#. Check out the `www-releases <https://github.com/llvm/www-releases>`_ repo
   from GitHub.

#. Create a new sub-directory ``X.Y.Z`` in the releases directory.

#. Copy and commit the ``llvm/docs`` and ``LICENSE.txt`` files into this new
   directory.

#. Update the ``releases/download.html`` file with links to the release
   binaries on GitHub.

#. Update the ``releases/index.html`` with the new release and link to release
   documentation.

#. After you push the changes to the ``www-releases`` repo, someone with admin
   access must log in to ``prereleases-origin.llvm.org`` and manually pull the new
   changes into ``/data/www-releases/``. This is where the website is served from.

#. Finally, check out the ``llvm-www`` repo and update the main page
   (``index.html`` and sidebar) to point to the new release and release
   announcement.

Announce the Release
^^^^^^^^^^^^^^^^^^^^

Create a new post in the `Announce Category <https://discourse.llvm.org/c/announce>`_
once all the release tasks are complete.  For X.1.0 releases, make sure to include a
link to the release notes in the post.  For X.1.1+ releases, generate a changelog
using this command and add it to the post.

::

  $ git log --format="- %aN: [%s (%h)](https://github.com/llvm/llvm-project/commit/%H)" llvmorg-X.1.N-1..llvmorg-X.1.N

Once the release has been announced, add a link to the announcement on the llvm
homepage (from the ``llvm-www`` repo) in the "Release Emails" section.
