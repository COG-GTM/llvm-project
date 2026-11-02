# omptarget.h mirrors libomp's KMP_GTID_DNE sentinel, which is the value
# __kmpc_global_thread_num() returns when no global thread id exists. The two
# projects cannot share the macro, so fail the configure step if the copies
# drift apart. The check is skipped when the libomp sources are not available.

# Reads the single line of HEADER defining KMP_GTID_DNE, requires it to match
# LINE_REGEX, and stores the captured integer literal in OUT_VAR. file(STRINGS)
# escapes ';' as '\;' in the returned line.
function(libomptarget_read_sentinel HEADER LINE_REGEX OUT_VAR)
  file(STRINGS "${HEADER}" lines REGEX "KMP_GTID_DNE[ \t]*[=(]")
  list(LENGTH lines num_lines)
  if(NOT num_lines EQUAL 1 OR NOT lines MATCHES "${LINE_REGEX}")
    message(FATAL_ERROR
      "Expected exactly one integer-literal definition of KMP_GTID_DNE in "
      "${HEADER}, found: ${lines}")
  endif()
  set(${OUT_VAR} "${CMAKE_MATCH_1}" PARENT_SCOPE)
endfunction()

function(libomptarget_check_libomp_sentinels OMPTARGET_HEADER KMP_HEADER)
  if(NOT EXISTS "${KMP_HEADER}")
    message(STATUS "libomp sources not found, skipping KMP_GTID_DNE check")
    return()
  endif()

  # Re-run the check when either header changes.
  set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS
               "${KMP_HEADER}" "${OMPTARGET_HEADER}")

  libomptarget_read_sentinel("${KMP_HEADER}"
    "^#define[ \t]+KMP_GTID_DNE[ \t]+\\((-?[0-9]+)\\)[ \t]*(/\\*.*\\*/)?[ \t]*$"
    kmp_value)
  libomptarget_read_sentinel("${OMPTARGET_HEADER}"
    "^[ \t]*static[ \t]+constexpr[ \t]+int[ \t]+KMP_GTID_DNE[ \t]*=[ \t]*(-?[0-9]+)[ \t]*\\\\?;[ \t]*$"
    omptarget_value)

  if(NOT kmp_value EQUAL omptarget_value)
    message(FATAL_ERROR
      "KMP_GTID_DNE mismatch: ${KMP_HEADER} defines ${kmp_value} but "
      "${OMPTARGET_HEADER} defines ${omptarget_value}. Update omptarget.h.")
  endif()
endfunction()
