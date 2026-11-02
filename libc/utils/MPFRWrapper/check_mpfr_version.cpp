#include <mpfr.h>

// The version string is embedded in the binary so that CMake can read it back
// without running the executable (which also works when cross compiling).
static const char mpfr_version_info[] =
    "INFO:mpfr_version[" MPFR_VERSION_STRING "]";

int main(int argc, char **) { return mpfr_version_info[argc]; }
