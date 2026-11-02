
set(LLVM_LINK_COMPONENTS
  Core
  ExecutionEngine
  IRReader
  JITLink
  Object
  ObjectYAML
  OrcDebugging
  OrcJIT
  OrcShared
  OrcTargetProcess
  Passes
  RuntimeDyld
  Support
  TargetParser
  native
  )

# Cross-check llvm::JITSymbolFlags against the ORC runtime's copy when the
# compiler-rt sources are available, even if compiler-rt is not being built.
set(ORC_RT_SOURCE_DIR ${LLVM_MAIN_SRC_DIR}/../compiler-rt/lib)
if(EXISTS ${ORC_RT_SOURCE_DIR}/orc/executor_symbol_def.h)
  set(ORC_RT_COMPAT_TESTS OrcRTJITSymbolFlagsTest.cpp)
  set_property(SOURCE OrcRTJITSymbolFlagsTest.cpp APPEND PROPERTY
    INCLUDE_DIRECTORIES ${ORC_RT_SOURCE_DIR})
else()
  set(LLVM_OPTIONAL_SOURCES OrcRTJITSymbolFlagsTest.cpp)
endif()

add_llvm_unittest(OrcJITTests
  CallableTraitsHelperTest.cpp
  CallSPSViaEPCTest.cpp
  CoreAPIsTest.cpp
  ExecutorAddressTest.cpp
  ExecutionSessionWrapperFunctionCallsTest.cpp
  EPCGenericJITLinkMemoryManagerTest.cpp
  EPCGenericMemoryAccessTest.cpp
  IndirectionUtilsTest.cpp
  JITTargetMachineBuilderTest.cpp
  LazyCallThroughAndReexportsTest.cpp
  LibraryResolverTest.cpp
  LinkGraphLinkingLayerTest.cpp
  LookupAndRecordAddrsTest.cpp
  MachOBuilderTest.cpp
  MachOPlatformTest.cpp
  MapperJITLinkMemoryManagerTest.cpp
  MemoryFlagsTest.cpp
  MemoryMapperTest.cpp
  ObjectFormatsTest.cpp
  ObjectLinkingLayerTest.cpp
  OrcCAPITest.cpp
  ${ORC_RT_COMPAT_TESTS}
  OrcTestCommon.cpp
  ResourceTrackerTest.cpp
  RTDyldObjectLinkingLayerTest.cpp
  SharedMemoryMapperTest.cpp
  SimpleExecutorMemoryManagerTest.cpp
  SimplePackedSerializationTest.cpp
  SymbolStringPoolTest.cpp
  TaskDispatchTest.cpp
  ThreadSafeModuleTest.cpp
  WaitingOnGraphTest.cpp
  WrapperFunctionUtilsTest.cpp
  JITLinkRedirectionManagerTest.cpp
  ReOptimizeLayerTest.cpp

  EXPORT_SYMBOLS
  )

target_link_libraries(OrcJITTests PRIVATE
                        LLVMTestingSupport
                        ${ORC_JIT_TEST_LIBS})
