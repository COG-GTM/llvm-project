===========================
SYCL runtime implementation
===========================

.. contents::
   :local:

.. _index:

Current Status
==============

The implementation is in the very early stages of upstreaming. The first
milestone is to get
support for a simple SYCL application with device code using Unified Shared
Memory:

.. code-block:: c++

   #include <sycl/sycl.hpp>
   
   class TestKernel;
   
   int main() {
     sycl::queue q;
   
     const size_t dataSize = 32;
     int *dataPtr = sycl::malloc_shared<int>(32, q);
     for (int i = 0; i < dataSize; ++i)
       dataPtr[i] = 0;
   
     q.submit([&](sycl::handler &cgh) {
       cgh.parallel_for<TestKernel>(
           sycl::range<1>(dataSize),
           [=](sycl::id<1> idx) { dataPtr[idx] = idx[0]; });
     });
     q.wait();
   
     bool error = false;
     for (int i = 0; i < dataSize; ++i)
       if (dataPtr[i] != i) error = true;
   
     free(dataPtr, q);
   
     return error;
   }

This requires at least partial support of the following functionality on the
libsycl side:

* ``sycl::platform`` class
* ``sycl::device`` class
* ``sycl::context`` class
* ``sycl::queue`` class
* ``sycl::handler`` class
* ``sycl::id`` and ``sycl::range`` classes
* Unified shared memory allocation/deallocation
* Program manager, an internal component for retrieving and using device images
  from the multi-architectural binaries

Build steps
===========

To build LLVM with libsycl runtime enabled the following script can be used.

.. code-block:: console

  #!/bin/sh

  build_llvm=`pwd`/build-llvm
  installprefix=`pwd`/install
  llvm=`pwd`
  mkdir -p $build_llvm
  mkdir -p $installprefix

  # LIBOMPTARGET_PLUGINS_TO_BUILD: build the liboffload level_zero plugin,
  # which requires Level Zero to be installed, see
  # offload/cmake/Modules/LibomptargetGetDependencies.cmake
  cmake -G Ninja -S $llvm/llvm -B $build_llvm \
        -DLLVM_ENABLE_PROJECTS="clang" \
        -DLLVM_INSTALL_UTILS=ON \
        -DCMAKE_INSTALL_PREFIX=$installprefix \
        -DLLVM_ENABLE_RUNTIMES="offload;openmp;libsycl" \
        -DCMAKE_BUILD_TYPE=Release \
        -DLIBOMPTARGET_PLUGINS_TO_BUILD=level_zero

  ninja -C $build_llvm install

Running the tests
=================

The libsycl tests are a lit test suite exposed as the ``check-sycl`` target.
It is not part of ``check-all``. The premerge ``Test SYCL`` check
(``.github/workflows/sycl-tests.yml``) runs on pull requests that touch
``libsycl/**`` and uses the following configuration:

.. code-block:: console

  cmake -G Ninja -S llvm -B build \
        -DCMAKE_BUILD_TYPE=Release \
        -DLLVM_ENABLE_ASSERTIONS=ON \
        -DLLVM_ENABLE_PROJECTS=clang \
        -DLLVM_ENABLE_RUNTIMES="offload;openmp;libsycl" \
        -DLLVM_TARGETS_TO_BUILD="host;SPIRV" \
        -DLLVM_INCLUDE_SPIRV_TOOLS_TESTS=ON

  ninja -C build check-sycl

Notes:

* ``offload`` and ``openmp`` must be enabled together with ``libsycl``.
* ``LLVM_INCLUDE_SPIRV_TOOLS_TESTS`` is an advanced option. It adds a
  ``SPIRVTools`` target that clones and builds SPIRV-Tools from GitHub for the
  LLVM/Clang SPIR-V tests; ``check-sycl`` itself does not build it. Existing
  ``spirv-as``, ``spirv-dis``, ``spirv-val`` and ``spirv-link`` binaries can be
  used instead of cloning by passing ``SPIRV_AS``, ``SPIRV_DIS``,
  ``SPIRV_VAL`` and ``SPIRV_LINK``.
* CI runs in the ``ghcr.io/llvm/ci-ubuntu-24.04:latest`` container with
  sccache as ``CMAKE_C_COMPILER_LAUNCHER``/``CMAKE_CXX_COMPILER_LAUNCHER``.
  Use the same image to reproduce a CI failure locally:

  .. code-block:: console

    docker run --rm -it -v "$PWD":/llvm-project -w /llvm-project \
           ghcr.io/llvm/ci-ubuntu-24.04:latest

* Tests that execute SYCL code are marked ``REQUIRES: any-device``. Without a
  device that the test suite recognizes (currently Level Zero GPUs) they are
  reported as ``UNSUPPORTED``.

See ``libsycl/test/README.md`` for running single tests with ``llvm-lit`` and
for the available lit parameters.


Limitations
===========

Libsycl is not currently supported on Windows because it depends on liboffload
which doesn't currently support Windows.

TODO for added SYCL classes
===========================

* ``exception``: methods with context are not implemented, to add once context is ready
* ``platform``: deprecated info descriptor is not implemented (info::platform::extensions), to implement on RT level with ``device::get_info<info::device::aspects>()``
* ``device``:

  * ``get_info``: to find an efficient way to map descriptors to liboffload types, add other descriptors, add cache of info data
  * ``has(aspect)``: same as get_info
  * ``create_sub_devices``: partitioning is not supported by liboffload now, blocked
  * ``has_extension``: deprecated API, to implement on RT level with ``device::has``

* device selection: to add compatibility with old SYCL 1.2.1 device selectors, still part of SYCL 2020 specification
* ``context``: to implement get_info, properties & public constructors once context support is added to liboffload
* ``queue``:

  * to implement USM methods
  * to implement synchronization methods
  * to implement submit & copy with accessors (low priority)
  * get_info & properties
  * ctors that accepts context (blocked by lack of liboffload support)

* ``property_list``: to fully implement and integrate with existing SYCL runtime classes supporting it
* usm allocations:

  * add aligned functions (blocked by liboffload support)
  * forward templated funcs to alignment methods (rewrite current impl)
  * handle sub devices once they are implemented (blocked by liboffload support)

* ``event``: get_wait_list, get_info, get_profiling_info, wait_and_throw & default ctor are not implemented
* general opens:

  * define a way to report errors from object dtors.