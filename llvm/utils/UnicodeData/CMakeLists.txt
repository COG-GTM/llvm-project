set(LLVM_LINK_COMPONENTS Support)

add_llvm_utility(UnicodeNameMappingGenerator
    UnicodeNameMappingGenerator.cpp
)

set(LLVM_UNICODE_DATA_DIR "" CACHE PATH
  "Directory with the UCD UnicodeData.txt and NameAliases.txt files that check-unicode-name-table verifies lib/Support/UnicodeNameToCodepointGenerated.cpp against.")

if(LLVM_UNICODE_DATA_DIR)
  add_custom_target(check-unicode-name-table
    COMMAND UnicodeNameMappingGenerator --check
            ${LLVM_UNICODE_DATA_DIR}/UnicodeData.txt
            ${LLVM_UNICODE_DATA_DIR}/NameAliases.txt
    DEPENDS UnicodeNameMappingGenerator
    COMMENT "Checking the Unicode name table against ${LLVM_UNICODE_DATA_DIR}"
    USES_TERMINAL
    )
  set_target_properties(check-unicode-name-table PROPERTIES FOLDER "LLVM/Tests")
endif()
