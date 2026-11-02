; Dropping a reducible flag must lower the complexity score, otherwise
; llvm-reduce stops iterating after a round whose only progress was dropping
; that flag.
;
; Here %gated can only be removed once samesign is gone. In the first round the
; instructions pass cannot remove %gated and the instruction-flags pass then
; drops samesign. %gated is only removed if that counts as progress and a
; second round runs.
;
; RUN: llvm-reduce --abort-on-invalid-reduction --delta-passes=instructions,instruction-flags --test %python --test-arg %p/Inputs/samesign-gates-instruction.py %s -o %t
; RUN: FileCheck --implicit-check-not=gated %s < %t

; CHECK-LABEL: define i1 @samesign_gates_instruction(
; CHECK-NEXT: %cmp = icmp ult i32 %a, 10
; CHECK-NEXT: ret i1 %cmp
define i1 @samesign_gates_instruction(i32 %a) {
  %gated = add i32 %a, 1
  %cmp = icmp samesign ult i32 %a, 10
  ret i1 %cmp
}
