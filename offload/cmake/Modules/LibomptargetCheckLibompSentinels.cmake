# omptarget.h mirrors libomp's KMP_GTID_DNE sentinel, which is the value
# __kmpc_global_thread_num() returns when no global thread id exists. The two
# projects cannot share the macro, so fail the configure step if the copies
# drift apart. The check is skipped when the libomp sources are not available.

function(libomptarget_check_libomp_sentinels OMPTARGET_HEADER KMP_HEADER)
  if(NOT EXISTS "${KMP_HEADER}")
    message(STATUS "libomp sources not found, skipping KMP_GTID_DNE check")
    return()
  endif()

  file(STRINGS "${KMP_HEADER}" kmp_line
       REGEX "^#define[ \t]+KMP_GTID_DNE[ \t]")
  string(REGEX MATCH "\\((-?[0-9]+)\\)" _ "${kmp_line}")
  set(kmp_value "${CMAKE_MATCH_1}")

  file(STRINGS "${OMPTARGET_HEADER}" omptarget_line
       REGEX "constexpr[ \t]+int[ \t]+KMP_GTID_DNE[ \t]*=")
  string(REGEX MATCH "=[ \t]*(-?[0-9]+)" _ "${omptarget_line}")
  set(omptarget_value "${CMAKE_MATCH_1}")

  if("${kmp_value}" STREQUAL "" OR "${omptarget_value}" STREQUAL "")
    message(FATAL_ERROR
      "Could not read KMP_GTID_DNE from ${KMP_HEADER} and ${OMPTARGET_HEADER}")
  endif()
  if(NOT kmp_value EQUAL omptarget_value)
    message(FATAL_ERROR
      "KMP_GTID_DNE mismatch: ${KMP_HEADER} defines ${kmp_value} but "
      "${OMPTARGET_HEADER} defines ${omptarget_value}. Update omptarget.h.")
  endif()
endfunction()
