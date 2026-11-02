.. _build_and_test:

=============================
Building and Testing the libc
=============================

Build modes
===========

The libc can be built and tested in two different modes:

#. **The overlay mode** - In this mode, one uses the static archive from LLVM's
   libc along with the system libc. See :ref:`overlay_mode` for more details
   on building and using the libc in this mode. You can only run the libc
   unittests in this mode. To run them, one simply does:

   .. code-block:: sh

     $> ninja check-libc

   Note that, unittests for only those functions which are part of the overlay
   static archive will be run with the above command.

#. **The full build mode** - In this mode, the libc is used as the only libc
   for the user's application. See :ref:`full_host_build` for more details on
   building and using the libc in this mode. Once configured for a full libc
   build, you can run three kinds of tests:

   #. Unit tests - You can run unittests by the command:

      .. code-block:: sh

        $> ninja check-libc

   #. Integration tests - You can run integration tests by the command:

      .. code-block:: sh

        $> ninja libc-integration-tests

   #. Shared tests - You can run tests for shared, standalone components (like math primitives) without needing the full libc runtime by the command:

      .. code-block:: sh

        $> ninja libc-shared-tests

Math tests and MPFR
===================

Many math unit tests compare against the
`GNU MPFR library <https://www.mpfr.org/>`_.
In overlay mode, CMake looks for MPFR (and GMP) on the default system paths, or
in ``LLVM_LIBC_MPFR_INSTALL_PATH`` if it is set. On Debian/Ubuntu:

.. code-block:: sh

  $> sudo apt-get install libmpfr-dev libgmp-dev libmpc-dev

MPFR **4.2.0 or newer** is required for full coverage. Older versions lack the
correctly rounded ``acospi``, ``asinpi``, ``atanpi``, ``cospi``, ``sinpi``,
``tanpi``, ``exp2m1``, ``exp10m1``, ``log2p1`` and ``log10p1``, so the tests for
those functions are checked against approximate reference implementations
instead. CMake reports the MPFR version it found and warns when it is older
than 4.2.0. Pass ``-DLLVM_LIBC_MPFR_STRICT_VERSION=ON`` to turn that warning
into a configuration error (the pre-commit Linux CI does this). Ubuntu 24.04
and newer ship a recent enough MPFR. On older distributions, build MPFR from
source and point ``LLVM_LIBC_MPFR_INSTALL_PATH`` at the install prefix.

Tests that need MPFR are skipped when MPFR is not found, and in full build and
GPU builds.

Building with VSCode
====================

As a quickstart to using VSCode for development, install the cmake extension
and put the following in your settings.json file:

.. code-block:: javascript

   {
     "cmake.sourceDirectory": "${workspaceFolder}/runtimes",
     "cmake.configureSettings": {
       "LLVM_ENABLE_RUNTIMES" : ["libc", "compiler-rt"],
       "LLVM_LIBC_FULL_BUILD" : true,
       "LLVM_ENABLE_SPHINX" : true,
       "LIBC_INCLUDE_DOCS" : true,
       "LLVM_LIBC_INCLUDE_SCUDO" : true,
       "COMPILER_RT_BUILD_SCUDO_STANDALONE_WITH_LLVM_LIBC": true,
       "COMPILER_RT_BUILD_GWP_ASAN" : false,
       "COMPILER_RT_SCUDO_STANDALONE_BUILD_SHARED" : false,
       "CMAKE_EXPORT_COMPILE_COMMANDS" : true,
       "LIBC_CMAKE_VERBOSE_LOGGING" : true
     }
   }

Building with Bazel
===================

#. To build with Bazel, use the following command:

  .. code-block:: sh

    $> bazel build --config=generic_clang @llvm-project//libc/...

#. To run the unit tests with bazel, use the following command:

  .. code-block:: sh

    $> bazel test --config=generic_clang @llvm-project//libc/...

#. The bazel target layout of `libc` is located at: `utils/bazel/llvm-project-overlay/libc/BUILD.bazel <https://github.com/llvm/llvm-project/tree/main/utils/bazel/llvm-project-overlay/libc/BUILD.bazel>`_.

Building in a container for a different architecture
====================================================

`Podman <https://podman.io/>`_ can be used together with
`QEMU <https://www.qemu.org/>`_ to run container images built for architectures
other than the host's. This can be used to build and test the libc on other
supported architectures for which you do not have access to hardware. It can
also be used if the hardware is slower than emulation of its architecture on a
more powerful machine under a different architecture.

As an example, to build and test in a container for 32-bit Arm:

#. To install the necessary packages on Arch Linux:

   .. code-block:: sh

     $> pacman -S podman qemu-user-static qemu-user-static-binfmt \
        qemu-system-arm

#. To run Bash interactively in an Ubuntu 22.04 container for 32-bit Arm and
   bind-mount an existing checkout of llvm-project on the host:

   .. code-block:: sh

     $> podman run -it \
        -v </host/path/to/llvm-project>:</container/path/to/llvm-project> \
        --arch arm docker.io/ubuntu:jammy bash

#. Install necessary packages, invoke CMake, build, and run tests.

Building and Testing with an Emulator
=====================================

If you are cross-compiling the libc for a different architecture, you can use an emulator
such as QEMU to run the tests directly on your host without a container. See
:ref:`full_cross_build` for detailed instructions on configuring CMake to use an emulator.
