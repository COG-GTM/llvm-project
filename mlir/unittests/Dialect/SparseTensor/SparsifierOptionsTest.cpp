//===- SparsifierOptionsTest.cpp - SparsifierOptions sync checks ----------===//
//
// Part of the LLVM Project, under the Apache License v2.0 with LLVM Exceptions.
// See https://llvm.org/LICENSE.txt for license information.
// SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
//
//===----------------------------------------------------------------------===//
//
// `SparsifierOptions` hand-copies options of passes that are defined in
// tablegen (SparseTensor/Transforms/Passes.td and Conversion/Passes.td).
// These tests fail when a copy drifts from its tablegen definition.
//
//===----------------------------------------------------------------------===//

#include "mlir/Dialect/Affine/IR/AffineOps.h"
#include "mlir/Dialect/Arith/IR/Arith.h"
#include "mlir/Dialect/Bufferization/IR/Bufferization.h"
#include "mlir/Dialect/GPU/IR/GPUDialect.h"
#include "mlir/Dialect/LLVMIR/LLVMDialect.h"
#include "mlir/Dialect/Linalg/IR/Linalg.h"
#include "mlir/Dialect/MemRef/IR/MemRef.h"
#include "mlir/Dialect/SCF/IR/SCF.h"
#include "mlir/Dialect/SparseTensor/IR/SparseTensor.h"
#include "mlir/Dialect/SparseTensor/Pipelines/Passes.h"
#include "mlir/Dialect/Vector/IR/VectorOps.h"
#include "gtest/gtest.h"

#include <string>
#include <vector>

using namespace mlir;
using namespace mlir::sparse_tensor;

namespace mlir {
#define GEN_PASS_DEF_SPARSIFICATIONPASS
#define GEN_PASS_DEF_SPARSIFICATIONANDBUFFERIZATION
#include "mlir/Dialect/SparseTensor/Transforms/Passes.h.inc"
} // namespace mlir

namespace {

/// Exposes the tablegen-generated options of the `sparsification` pass.
struct SparsificationOptionsProbe
    : public impl::SparsificationPassBase<SparsificationOptionsProbe> {
  using Base::enableRuntimeLibrary;
  using Base::parallelization;
  using Base::sparseEmitStrategy;
  void runOnOperation() override {}
};

/// Exposes the tablegen-generated options of the
/// `sparsification-and-bufferization` pass.
struct SparsificationAndBufferizationOptionsProbe
    : public impl::SparsificationAndBufferizationBase<
          SparsificationAndBufferizationOptionsProbe> {
  using Base::enableGPULibgen;
  using Base::parallelization;
  using Base::sparseEmitStrategy;
  using Base::vectorLength;
  void runOnOperation() override {}
};

/// Checks that two enum options have the same argument name, the same default
/// and the same set of literals, each mapping to the same enum value.
template <typename T, typename OptA, typename OptB>
void expectSameEnumOption(OptA &pipelineOpt, OptB &passOpt) {
  EXPECT_EQ(pipelineOpt.ArgStr, passOpt.ArgStr);
  EXPECT_EQ(static_cast<T>(pipelineOpt), static_cast<T>(passOpt))
      << "default of '" << pipelineOpt.ArgStr.str() << "' differs";

  auto &pipelineParser = pipelineOpt.getParser();
  auto &passParser = passOpt.getParser();
  auto literals = [](auto &parser) {
    std::vector<std::string> names;
    for (unsigned i = 0, e = parser.getNumOptions(); i < e; ++i)
      names.push_back(parser.getOption(i).str());
    return names;
  };
  EXPECT_EQ(literals(pipelineParser), literals(passParser))
      << "literals of '" << pipelineOpt.ArgStr.str() << "' differ";

  for (unsigned i = 0, e = pipelineParser.getNumOptions(); i < e; ++i) {
    StringRef name = pipelineParser.getOption(i);
    T pipelineValue{}, passValue{};
    ASSERT_FALSE(pipelineParser.parse(pipelineOpt, pipelineOpt.ArgStr, name,
                                      pipelineValue));
    ASSERT_FALSE(passParser.parse(passOpt, passOpt.ArgStr, name, passValue))
        << "'" << name.str() << "' is not accepted by the pass option '"
        << passOpt.ArgStr.str() << "'";
    EXPECT_EQ(pipelineValue, passValue)
        << "'" << name.str() << "' maps to different enum values";
  }
}

template <typename OptA, typename OptB>
void expectSameArgAndDefault(OptA &pipelineOpt, OptB &passOpt) {
  EXPECT_EQ(pipelineOpt.ArgStr, passOpt.ArgStr);
  EXPECT_EQ(pipelineOpt.getValue(), passOpt.getValue())
      << "default of '" << pipelineOpt.ArgStr.str() << "' differs";
}

TEST(SparsifierOptionsTest, MatchesSparsificationPass) {
  SparsifierOptions pipeline;
  SparsificationOptionsProbe pass;
  expectSameEnumOption<SparseParallelizationStrategy>(pipeline.parallelization,
                                                      pass.parallelization);
  expectSameEnumOption<SparseEmitStrategy>(pipeline.emitStrategy,
                                           pass.sparseEmitStrategy);
  expectSameArgAndDefault(pipeline.enableRuntimeLibrary,
                          pass.enableRuntimeLibrary);
}

TEST(SparsifierOptionsTest, MatchesSparsificationAndBufferizationPass) {
  SparsifierOptions pipeline;
  SparsificationAndBufferizationOptionsProbe pass;
  expectSameEnumOption<SparseParallelizationStrategy>(pipeline.parallelization,
                                                      pass.parallelization);
  expectSameEnumOption<SparseEmitStrategy>(pipeline.emitStrategy,
                                           pass.sparseEmitStrategy);
  expectSameArgAndDefault(pipeline.vectorLength, pass.vectorLength);
  expectSameArgAndDefault(pipeline.enableGPULibgen, pass.enableGPULibgen);
}

TEST(SparsifierOptionsTest, ProjectedSparsificationOptionsMatchDefaults) {
  SparsificationPassOptions tablegen;
  SparsificationOptions projected = SparsifierOptions().sparsificationOptions();
  EXPECT_EQ(projected.parallelizationStrategy, tablegen.parallelization);
  EXPECT_EQ(projected.sparseEmitStrategy, tablegen.sparseEmitStrategy);
  EXPECT_EQ(projected.enableRuntimeLibrary, tablegen.enableRuntimeLibrary);
}

TEST(SparsifierOptionsTest, MatchesCodegenAndBufferPassDefaults) {
  SparsifierOptions pipeline;
  SparseTensorCodegenOptions codegen;
  EXPECT_EQ(pipeline.enableBufferInitialization,
            codegen.enableBufferInitialization);
  EXPECT_EQ(pipeline.createSparseDeallocs, codegen.createSparseDeallocs);
  EXPECT_EQ(pipeline.enableBufferInitialization,
            SparseBufferRewriteOptions().enableBufferInitialization);

  SparseGPUCodegenOptions gpu;
  EXPECT_EQ(static_cast<int64_t>(pipeline.gpuNumThreads),
            static_cast<int64_t>(gpu.numThreads));
  EXPECT_EQ(pipeline.enableRuntimeLibrary, gpu.enableRuntimeLibrary);
}

TEST(SparsifierOptionsTest, MatchesConvertVectorToLLVMPassDefaults) {
  SparsifierOptions pipeline;
  ConvertVectorToLLVMPassOptions tablegen;
  EXPECT_EQ(pipeline.reassociateFPReductions, tablegen.reassociateFPReductions);
  EXPECT_EQ(pipeline.force32BitVectorIndices, tablegen.force32BitVectorIndices);
  EXPECT_EQ(pipeline.armNeon, tablegen.armNeon);
  EXPECT_EQ(pipeline.armSVE, tablegen.armSVE);
  EXPECT_EQ(pipeline.x86, tablegen.x86);

  ConvertVectorToLLVMPassOptions projected =
      pipeline.convertVectorToLLVMOptions();
  EXPECT_EQ(projected.reassociateFPReductions,
            tablegen.reassociateFPReductions);
  EXPECT_EQ(projected.force32BitVectorIndices,
            tablegen.force32BitVectorIndices);
  EXPECT_EQ(projected.useVectorAlignment, tablegen.useVectorAlignment);
  EXPECT_EQ(projected.armNeon, tablegen.armNeon);
  EXPECT_EQ(projected.armSVE, tablegen.armSVE);
  EXPECT_EQ(projected.armI8MM, tablegen.armI8MM);
  EXPECT_EQ(projected.armBF16, tablegen.armBF16);
  EXPECT_EQ(projected.x86, tablegen.x86);
}

} // namespace
