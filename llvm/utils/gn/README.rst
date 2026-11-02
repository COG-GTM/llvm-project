=====================
Building LLVM with GN
=====================

.. contents::
   :local:

.. _Introduction:

Introduction
============

*Warning* The GN build is experimental and best-effort. It might not work,
and if you use it you're expected to feel comfortable to unbreak it if
necessary. LLVM's official build system is CMake, if in doubt use that.
If you add files, you're expected to update the CMake build but you don't need
to update GN build files. Reviewers should not ask authors to update GN build
files. Keeping the GN build files up-to-date is on the people who use the GN
build.

`GN <https://gn.googlesource.com/gn/>`_ is a metabuild system. It always
creates ninja files, but it can create some IDE projects (MSVC, Xcode, ...)
which then shell out to ninja for the actual build.

The main motivation behind the GN build is that some people find it more
convenient for day-to-day hacking on LLVM than CMake. Distribution, building
just parts of LLVM, and embedding the LLVM GN build from other builds are
non-goals for the GN build.

This is a `good overview of GN <https://docs.google.com/presentation/d/15Zwb53JcncHfEwHpnG_PoIbbzQ3GQi_cpujYwbpcbZo/edit#slide=id.g119d702868_0_12>`_.

.. _Quick start:

Quick start
===========

#. ``git clone https://github.com/llvm/llvm-project.git; cd llvm-project`` if
   you don't have a checkout yet.

#. ``llvm/utils/gn/get.py`` to download a prebuilt gn binary if you're on a
   64-bit X86 system running Linux, macOS, or Windows. `Build gn yourself
   <https://gn.googlesource.com/gn/#getting-started>`_ if you're on a different
   platform or don't want to trust prebuilt binaries.

#. ``llvm/utils/gn/gn.py gen out/gn`` to run GN and create build files.
   ``out/gn`` is the build directory, it can have any name, and you can have as
   many as you want, each with different build settings.  (The ``gn.py`` script
   adds ``--dotfile=llvm/utils/gn/.gn --root=.`` and just runs regular ``gn``;
   you can manually pass these parameters and not use the wrapper if you
   prefer.)

#. ``echo out >> .git/info/exclude`` to tell git to ignore files below ``out``.

#. ``ninja -C out/gn check-lld`` to build all prerequisites for and run the LLD
   tests.

By default, you get a release build with assertions enabled that targets
the host arch. You can set build options by editing ``out/gn/args.gn``, for
example putting ``is_debug = true`` in there gives you a debug build. Run
``llvm/utils/gn/gn.py args --list out/gn`` to see a list of all possible
options. After touching ``out/gn/args.gn`` just run ninja: it will re-invoke gn
before starting the build.

GN has extensive built-in help; try e.g. ``llvm/utils/gn/gn.py help gen`` to see
the help for the ``gen`` command. The full GN reference is also `available
online <https://gn.googlesource.com/gn/+/refs/heads/main/docs/reference.md>`_.

GN has an autoformatter:
``git ls-files '*.gn' '*.gni' | xargs llvm/utils/gn/gn.py format``
after making GN build changes is your friend.

To not put ``BUILD.gn`` files into the main tree, they are all below
``utils/gn/secondary``.  For example, the build file for ``llvm/lib/Support``
is in ``utils/gn/secondary/llvm/lib/Support``.

.. _Syncing GN files from CMake files:

Syncing GN files from CMake files
=================================

Sometimes after pulling in the latest changes, the GN build doesn't work.
Most of the time this is due to someone adding a file to CMakeLists.txt file.
Run ``llvm/utils/gn/build/sync_source_lists_from_cmake.py`` to print a report
of which files need to be added to or removed from ``BUILD.gn`` files to
match the corresponding ``CMakeLists.txt``. You have to manually read the output
of the script and implement its suggestions.

If new ``CMakeLists.txt`` files have been added, you have to manually create
a new corresponding ``BUILD.gn`` file below ``llvm/utils/gn/secondary/``.

If the dependencies in a ``CMakeLists.txt`` file have been changed, you have to
manually analyze and fix.

The script also compares ``LLVM_ALL_TARGETS`` and
``LLVM_ALL_EXPERIMENTAL_TARGETS`` in ``llvm/CMakeLists.txt`` with the target
lists in ``llvm/utils/gn/secondary/llvm/lib/Target/targets.gni``. It also
checks the ``targets_with_*.gni`` capability lists against the backends in
``llvm/lib/Target/``. If a target is added, removed, or promoted in CMake, it
reports what to change. See `Adding a target`_.

.. _Adding a target:

Adding a target
===============

``targets.gni`` puts each CMake target in exactly one list.
``llvm_all_stable_targets`` and ``llvm_all_experimental_targets`` hold targets
that GN can build. ``llvm_unported_stable_targets`` and
``llvm_unported_experimental_targets`` hold targets that exist in CMake but are
not ported to GN yet. ``llvm_targets_to_build = "all"`` builds only the ported
stable targets, so it can be a subset of CMake's ``all``. Asking for an unported
target stops ``gn gen`` with an error.

When CMake gets a new target, add it to the matching ``llvm_unported_*`` list
at least. To port a target ``T``:

- In ``llvm/utils/gn/secondary/llvm/lib/Target/targets.gni``, move ``T`` from
  ``llvm_unported_*_targets`` to ``llvm_all_*_targets``. Then add a
  ``target == "T"`` branch to the validation chain. Use the "Nothing to do"
  branch, or add an ``llvm_build_T`` variable if a ``BUILD.gn`` file needs to
  know whether ``T`` is built (for example, for conditional unittests).
- If ``T`` has no ``AsmParser/`` or ``Disassembler/``, list it in
  ``targets_with_asm_parsers.gni`` or ``targets_with_disassemblers.gni``. If
  it supports llvm-exegesis (``llvm/tools/llvm-exegesis/lib/T/``) or
  llvm-mca (``llvm/lib/Target/T/MCA/``), list it in
  ``targets_with_exegesis.gni`` or ``targets_with_mcas.gni``.
- Create ``BUILD.gn`` files for ``llvm/lib/Target/T/`` and its subdirectories
  below ``llvm/utils/gn/secondary/``. Copy the layout of an existing target,
  including the ``tablegen`` targets that match its CMakeLists.txt.
- Add ``BUILD.gn`` files for ``llvm/unittests/Target/T/`` and the other
  target-specific directories (``llvm/tools/llvm-exegesis/lib/T``,
  ``llvm/unittests/tools/llvm-exegesis/T``, ...). Add them to the dependency
  lists that are guarded by ``llvm_build_T``.
- Run ``sync_source_lists_from_cmake.py``. It should report nothing.

.. _Philosophy:

Philosophy
==========

GN believes in using GN arguments to configure the build explicitly, instead
of implicitly figuring out what to do based on what's available on the current
system.

configure is used for three classes of feature checks:

- compiler checks. In GN, these could use exec_script to identify the host
  compiler at GN time. For now the build has explicit toggles for compiler
  features. (Maybe there could be a script that writes args.gn based on the
  host compiler).  It's possible we'll use exec_script() for this going forward,
  but we'd have one exec_script call to identify compiler id and version,
  and then base GN arg default values of compiler id and version instead of
  doing one exec_script per feature check.
  (In theory, the config approach means a new os / compiler just needs to tweak
  the checks and not the code, but in practice a) new os's / compilers are rare
  b) they will require code changes anyhow, so the configure tradeoff seems
  not worth it.)

- library checks. For e.g. like zlib, GN thinks it's better to say "we require
  zlib, else we error at build time" than silently omitting features. People
  who really don't want to install zlib can explicitly set the GN arg to turn
  off zlib.

- header checks (does system header X exist). These are generally not needed
  (just keying this off the host OS works fine), but if they should become
  necessary in the future, they should be done at build time and the few
  targets that need to know if header X exists then depend on that build-time
  check while everything else can build parallel with it.

- LLVM-specific build toggles (assertions on/off, debug on/off, targets to
  build, ...). These map cleanly to GN args (which then get copied into
  config.h in a build step).

For the last two points, it would be nice if LLVM didn't have a single
``config.h`` header, but one header per toggle. That way, when e.g.
``llvm_enable_zlib`` is toggled, only the 3 files caring about that setting
would need to be rebuilt, instead of everything including ``config.h``.

GN doesn't believe in users setting arbitrary cflags from an environment
variable, it wants the build to be controlled by .gn files.
