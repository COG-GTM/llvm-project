The libraries in this directory are mirrored from external projects.

Patches to them should first be contributed upstream and then return to Polly
as normal (re)imports of these updated libraries.

We currently have the following external libraries.

# isl
License: MIT-STYLE
Details: isl/LICENSE

# imath
License: MIT-STYLE
Details: isl/imath/LICENSE
Notes: isl/imath/doc.md is generated from doc.md.in and the imath headers by
       isl/imath/tools/mkdoc.py (Python 3). Polly's CMake build does not
       regenerate it; after an update, run 'make check-doc' (or 'make doc.md')
       in isl/imath to confirm it still matches the headers.

To update these libraries run 'autoreconf -i && ./configure && make dist' in
the isl git directory and move the resulting files into lib/External/isl.
Alternatively, run the update-isl.sh script.
