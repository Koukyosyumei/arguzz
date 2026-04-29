"""
Sphinx zkVM fault-injection patches.

Layout differences vs. SP1's `sp1_fuzzer.zkvm_repository.injection`:

  * SP1's executor lives in `crates/core/executor/src/executor.rs` and is
    overwritten wholesale with a pre-patched copy. Sphinx's executor lives in
    `core/src/runtime/mod.rs` and is patched **incrementally** here via
    `prepend_file` / `replace_in_file`, so the patch survives small upstream
    drift better.

  * Sphinx's `Register::from_u32` panics on out-of-range values (SP1's
    equivalent is `from_u8`); the OOB-hotfix is adapted accordingly.

  * Sphinx's memory is a `HashMap<u32, MemoryRecord>` in `state.rs`, so the
    paged-memory hotfix from SP1's `memory.rs` does not apply.
"""
import logging
from pathlib import Path

from sphinx_fuzzer.zkvm_repository.fuzzer_utils_crate import create_fuzzer_utils_crate
from sphinx_fuzzer.zkvm_repository.injection_source import fault_injection_context_rs
from zkvm_fuzzer_utils.file import create_file, prepend_file, replace_in_file

logger = logging.getLogger("fuzzer")


class SphinxManagerException(Exception):
    pass


def _patch_workspace_cargo_toml(sphinx_install_path: Path) -> None:
    """Add the locally-generated ``fuzzer_utils`` crate to the Sphinx workspace."""
    replace_in_file(
        sphinx_install_path / "Cargo.toml",
        [
            (
                r"""\[workspace\]
members = \[""",
                """[workspace]
members = [
  "fuzzer_utils",""",
            ),
            (
                r"\[workspace\.dependencies\]",
                '[workspace.dependencies]\nfuzzer_utils = { path = "fuzzer_utils" }',
            ),
        ],
    )


def _drop_in_fault_injection_module(sphinx_install_path: Path) -> None:
    """Write `core/src/runtime/fault_injection_context.rs` and wire it into mod.rs."""
    create_file(
        sphinx_install_path / "core" / "src" / "runtime" / "fault_injection_context.rs",
        fault_injection_context_rs(),
    )
    # declare the module + re-export the context, alongside the existing modules.
    replace_in_file(
        sphinx_install_path / "core" / "src" / "runtime" / "mod.rs",
        [
            (
                r"mod context;",
                "mod context;\nmod fault_injection_context;",
            ),
            (
                r"pub use context::\*;",
                "pub use context::*;\npub use fault_injection_context::*;",
            ),
        ],
    )


def _add_field_to_runtime(sphinx_install_path: Path) -> None:
    """Add `fault_injection_context` to the `Runtime` struct + initializer."""
    replace_in_file(
        sphinx_install_path / "core" / "src" / "runtime" / "mod.rs",
        [
            # Add the field at the very end of the Runtime struct definition.
            (
                r"""    /// The maximum number of cpu cycles to use for execution\.
    pub max_cycles: Option<u64>,
\}""",
                """    /// The maximum number of cpu cycles to use for execution.
    pub max_cycles: Option<u64>,

    /// Context for fault injection (added by arguzz / sphinx-fuzzer).
    pub fault_injection_context: RV32IMFaultInjectionContext,
}""",
            ),
            # Initialize the field in `with_context`.
            (
                r"""            max_cycles: context\.max_cycles,
        \}
    \}""",
                """            max_cycles: context.max_cycles,
            fault_injection_context: fault_injection_context_from_globals(),
        }
    }""",
            ),
        ],
    )


def _wrap_pc_commit(sphinx_install_path: Path) -> None:
    """Wrap `self.state.pc = next_pc;` with PRE/POST commit-PC injections."""
    replace_in_file(
        sphinx_install_path / "core" / "src" / "runtime" / "mod.rs",
        [
            (
                r"""        // Update the program counter\.
        self\.state\.pc = next_pc;""",
                """        // -- arguzz: POST_EXEC_PRE_COMMIT_PC_MOD ---------------------------------
        if self.fault_injection_context.is_injection(
            "POST_EXEC_PRE_COMMIT_PC_MOD",
            &self.fault_injection_context.get_pc_hint(),
        ) {
            let new_next_pc = self.fault_injection_context.random_pc(next_pc);
            self.fault_injection_context.print_injection_info(
                &self.fault_injection_context.get_pc_hint(),
                &self.fault_injection_context.get_instruction_hint(),
                "POST_EXEC_PRE_COMMIT_PC_MOD",
                &format!("next_pc {} -> {}", next_pc, new_next_pc),
            );
            next_pc = new_next_pc;
        }

        // Update the program counter.
        self.state.pc = next_pc;

        // -- arguzz: POST_EXEC_POST_COMMIT_PC_MOD --------------------------------
        if self.fault_injection_context.is_injection(
            "POST_EXEC_POST_COMMIT_PC_MOD",
            &self.fault_injection_context.get_pc_hint(),
        ) {
            let new_pc = self.fault_injection_context.random_pc(self.state.pc);
            self.fault_injection_context.print_injection_info(
                &self.fault_injection_context.get_pc_hint(),
                &self.fault_injection_context.get_instruction_hint(),
                "POST_EXEC_POST_COMMIT_PC_MOD",
                &format!("pc {} -> {}", self.state.pc, new_pc),
            );
            self.state.pc = new_pc;
        }""",
            )
        ],
    )


def _hook_execute_instruction_entry(sphinx_install_path: Path) -> None:
    """At entry to `execute_instruction`, record the current instruction and emit trace info."""
    replace_in_file(
        sphinx_install_path / "core" / "src" / "runtime" / "mod.rs",
        [
            (
                r"""    fn execute_instruction\(&mut self, instruction: Instruction\) -> Result<\(\), ExecutionError> \{
        let mut pc = self\.state\.pc;
        let mut clk = self\.state\.clk;
        let mut exit_code = 0u32;

        let mut next_pc = self\.state\.pc\.wrapping_add\(4\);""",
                """    fn execute_instruction(&mut self, instruction: Instruction) -> Result<(), ExecutionError> {
        // -- arguzz: per-step bookkeeping -------------------------------------
        self.fault_injection_context.set_instruction_hint(&instruction);
        self.fault_injection_context.print_trace_info(
            &self.state.pc,
            &instruction,
            self.state.clk,
        );

        let mut pc = self.state.pc;
        let mut clk = self.state.clk;
        let mut exit_code = 0u32;

        let mut next_pc = self.state.pc.wrapping_add(4);""",
            )
        ],
    )


def _step_after_instruction(sphinx_install_path: Path) -> None:
    """Call `fault_injection_context.step(next_pc)` after the cycle finishes."""
    replace_in_file(
        sphinx_install_path / "core" / "src" / "runtime" / "mod.rs",
        [
            (
                r"""        \};
        Ok\(\)
    \}

    /// Executes one cycle of the program, returning whether the program has finished\.""",
                """        };

        // -- arguzz: advance fault-injection step counter ---------------------
        self.fault_injection_context.step(next_pc);

        Ok(())
    }

    /// Executes one cycle of the program, returning whether the program has finished.""",
            )
        ],
    )


def _patch_alu_rr(sphinx_install_path: Path) -> None:
    """Wire ALU_PARSED_OPERAND_MOD and ALU_LOAD_OPERAND_MOD into `alu_rr`."""
    replace_in_file(
        sphinx_install_path / "core" / "src" / "runtime" / "mod.rs",
        [
            (
                r"""    fn alu_rr\(&mut self, instruction: Instruction\) -> \(Register, u32, u32\) \{
        if !instruction\.imm_c \{
            let \(rd, rs1, rs2\) = instruction\.r_type\(\);
            let c = self\.rr\(rs2, MemoryAccessPosition::C\);
            let b = self\.rr\(rs1, MemoryAccessPosition::B\);
            \(rd, b, c\)
        \} else if !instruction\.imm_b && instruction\.imm_c \{
            let \(rd, rs1, imm\) = instruction\.i_type\(\);
            let \(rd, b, c\) = \(rd, self\.rr\(rs1, MemoryAccessPosition::B\), imm\);
            \(rd, b, c\)
        \} else \{
            assert!\(instruction\.imm_b && instruction\.imm_c\);
            let \(rd, b, c\) = \(
                Register::from_u32\(instruction\.op_a\),
                instruction\.op_b,
                instruction\.op_c,
            \);
            \(rd, b, c\)
        \}
    \}""",
                """    fn alu_rr(&mut self, instruction: Instruction) -> (Register, u32, u32) {
        let (rd, mut b, mut c): (Register, u32, u32) = if !instruction.imm_c {
            let (rd, rs1, rs2) = instruction.r_type();
            let mut c = self.rr(rs2, MemoryAccessPosition::C);
            let mut b = self.rr(rs1, MemoryAccessPosition::B);
            // -- arguzz: ALU_LOAD_OPERAND_MOD ---------------------------------
            if self.fault_injection_context.is_injection(
                "ALU_LOAD_OPERAND_MOD",
                &self.fault_injection_context.get_pc_hint(),
            ) {
                let (nb, nc) = self.fault_injection_context.random_mod_of_u32_pair(b, c);
                self.fault_injection_context.print_injection_info(
                    &self.fault_injection_context.get_pc_hint(),
                    &instruction,
                    "ALU_LOAD_OPERAND_MOD",
                    &format!("(b,c) ({},{}) -> ({},{})", b, c, nb, nc),
                );
                b = nb;
                c = nc;
            }
            (rd, b, c)
        } else if !instruction.imm_b && instruction.imm_c {
            let (rd, rs1, imm) = instruction.i_type();
            (rd, self.rr(rs1, MemoryAccessPosition::B), imm)
        } else {
            assert!(instruction.imm_b && instruction.imm_c);
            (
                Register::from_u32(instruction.op_a),
                instruction.op_b,
                instruction.op_c,
            )
        };

        // -- arguzz: ALU_PARSED_OPERAND_MOD -------------------------------
        if self.fault_injection_context.is_injection(
            "ALU_PARSED_OPERAND_MOD",
            &self.fault_injection_context.get_pc_hint(),
        ) {
            let (nb, nc) = self.fault_injection_context.random_mod_of_u32_pair(b, c);
            self.fault_injection_context.print_injection_info(
                &self.fault_injection_context.get_pc_hint(),
                &instruction,
                "ALU_PARSED_OPERAND_MOD",
                &format!("(b,c) ({},{}) -> ({},{})", b, c, nb, nc),
            );
            b = nb;
            c = nc;
        }

        (rd, b, c)
    }""",
            )
        ],
    )


def _patch_alu_rw(sphinx_install_path: Path) -> None:
    """Wire ALU_RESULT_MOD and ALU_RESULT_LOC_MOD into `alu_rw`."""
    replace_in_file(
        sphinx_install_path / "core" / "src" / "runtime" / "mod.rs",
        [
            (
                r"""    /// Set the destination register with the result and emit an ALU event\.
    fn alu_rw\(
        &mut self,
        instruction: Instruction,
        rd: Register,
        a: u32,
        b: u32,
        c: u32,
        lookup_id: usize,
    \) \{
        self\.rw\(rd, a\);
        if self\.emit_events \{
            self\.emit_alu\(self\.state\.clk, instruction\.opcode, a, b, c, lookup_id\);
        \}""",
                """    /// Set the destination register with the result and emit an ALU event.
    fn alu_rw(
        &mut self,
        instruction: Instruction,
        rd: Register,
        a: u32,
        b: u32,
        c: u32,
        lookup_id: usize,
    ) {
        let mut rd = rd;
        let mut a = a;
        // -- arguzz: ALU_RESULT_MOD ---------------------------------------
        if self.fault_injection_context.is_injection(
            "ALU_RESULT_MOD",
            &self.fault_injection_context.get_pc_hint(),
        ) {
            let na = self.fault_injection_context.random_mod_of_u32(a);
            self.fault_injection_context.print_injection_info(
                &self.fault_injection_context.get_pc_hint(),
                &instruction,
                "ALU_RESULT_MOD",
                &format!("a {} -> {}", a, na),
            );
            a = na;
        }
        // -- arguzz: ALU_RESULT_LOC_MOD -----------------------------------
        if self.fault_injection_context.is_injection(
            "ALU_RESULT_LOC_MOD",
            &self.fault_injection_context.get_pc_hint(),
        ) {
            let new_idx =
                ((rd as u32).wrapping_add(self.fault_injection_context.random_mod_of_u32(1))) % 32;
            let new_rd = Register::from_u32(new_idx);
            self.fault_injection_context.print_injection_info(
                &self.fault_injection_context.get_pc_hint(),
                &instruction,
                "ALU_RESULT_LOC_MOD",
                &format!("rd {:?} -> {:?}", rd, new_rd),
            );
            rd = new_rd;
        }
        self.rw(rd, a);
        if self.emit_events {
            self.emit_alu(self.state.clk, instruction.opcode, a, b, c, lookup_id);
        }""",
            )
        ],
    )


def _patch_ecall_syscall_id(sphinx_install_path: Path) -> None:
    """Wire SYS_CALL_MOD_ECALL_ID into the ECALL arm."""
    replace_in_file(
        sphinx_install_path / "core" / "src" / "runtime" / "mod.rs",
        [
            (
                r"""            Opcode::ECALL => \{
                // We peek at register x5 to get the syscall id\. The reason we don't `self\.rr` this
                // register is that we write to it later\.
                let t0 = Register::X5;
                let syscall_id = self\.register\(t0\);""",
                """            Opcode::ECALL => {
                // We peek at register x5 to get the syscall id. The reason we don't `self.rr` this
                // register is that we write to it later.
                let t0 = Register::X5;
                let mut syscall_id = self.register(t0);
                // -- arguzz: SYS_CALL_MOD_ECALL_ID ----------------------------
                if self.fault_injection_context.is_injection(
                    "SYS_CALL_MOD_ECALL_ID",
                    &self.fault_injection_context.get_pc_hint(),
                ) {
                    let new_id = self.fault_injection_context.random_mod_of_u32(syscall_id);
                    self.fault_injection_context.print_injection_info(
                        &self.fault_injection_context.get_pc_hint(),
                        &instruction,
                        "SYS_CALL_MOD_ECALL_ID",
                        &format!("syscall_id {} -> {}", syscall_id, new_id),
                    );
                    syscall_id = new_id;
                }""",
            )
        ],
    )


def _patch_execute_cycle(sphinx_install_path: Path) -> None:
    """Wire INSTR_WORD_MOD and EXECUTE_INSTRUCTION_AGAIN into execute_cycle."""
    replace_in_file(
        sphinx_install_path / "core" / "src" / "runtime" / "mod.rs",
        [
            (
                r"""    fn execute_cycle\(&mut self\) -> Result<bool, ExecutionError> \{
        // Fetch the instruction at the current program counter\.
        let instruction = self\.fetch\(\);

        // Log the current state of the runtime\.
        self\.log\(&instruction\);

        // Execute the instruction\.
        self\.execute_instruction\(instruction\)\?;""",
                """    fn execute_cycle(&mut self) -> Result<bool, ExecutionError> {
        // Fetch the instruction at the current program counter.
        let mut instruction = self.fetch();

        // -- arguzz: INSTR_WORD_MOD --------------------------------------
        if self.fault_injection_context.is_injection("INSTR_WORD_MOD", &self.state.pc) {
            let original = instruction;
            let nb = self.fault_injection_context.random_mod_of_u32(instruction.op_b);
            let nc = self.fault_injection_context.random_mod_of_u32(instruction.op_c);
            instruction.op_b = nb;
            instruction.op_c = nc;
            self.fault_injection_context
                .record_history(self.state.pc, original);
            self.fault_injection_context.print_injection_info(
                &self.state.pc,
                &original,
                "INSTR_WORD_MOD",
                &format!("(op_b,op_c) ({},{}) -> ({},{})", original.op_b, original.op_c, nb, nc),
            );
        }

        // Log the current state of the runtime.
        self.log(&instruction);

        // Execute the instruction.
        self.execute_instruction(instruction)?;

        // -- arguzz: EXECUTE_INSTRUCTION_AGAIN ----------------------------
        if self.fault_injection_context.is_injection(
            "EXECUTE_INSTRUCTION_AGAIN",
            &self.fault_injection_context.get_pc_hint(),
        ) {
            self.fault_injection_context.print_injection_info(
                &self.fault_injection_context.get_pc_hint(),
                &instruction,
                "EXECUTE_INSTRUCTION_AGAIN",
                &"replaying instruction".to_string(),
            );
            self.execute_instruction(instruction)?;
        }""",
            )
        ],
    )


def _patch_register_oob_hotfix(sphinx_install_path: Path) -> None:
    """Clamp out-of-range register indices when fault injection is active."""
    prepend_file(
        sphinx_install_path / "core" / "src" / "runtime" / "register.rs",
        "#[allow(unused_imports)]\nuse fuzzer_utils;\n",
    )
    replace_in_file(
        sphinx_install_path / "core" / "src" / "runtime" / "register.rs",
        [
            (
                r"""    pub fn from_u32\(value: u32\) -> Self \{
        match value \{""",
                """    pub fn from_u32(value: u32) -> Self {
        let value = if value >= 32 && fuzzer_utils::is_injection() {
            println!("WARNING: Hotfix for register access out-of-bounds!");
            value % 32
        } else {
            value
        };
        match value {""",
            )
        ],
    )


def _wrap_asserts_in_core(sphinx_install_path: Path) -> None:
    """Recursively replace `assert!` / `assert_eq!` in `core/` with fuzzer_utils macros.

    Some files use ``assert!`` inside ``const fn`` constructors or pass non-Copy
    values into the assert (where re-evaluating would move twice). Our wrapper
    macro is non-const and re-evaluates its arguments, so we exclude those
    files and let the original ``assert!`` stand.
    """
    excluded_elems: list[Path] = [
        # const fn constructors with `assert!`.
        (sphinx_install_path / "core" / "src" / "runtime" / "memory.rs").absolute(),
        # passes non-Copy values into assert_eq! (would be moved twice).
        (sphinx_install_path / "core" / "src" / "stark" / "debug.rs").absolute(),
        (
            sphinx_install_path
            / "core"
            / "src"
            / "operations"
            / "field"
            / "field_inner_product.rs"
        ).absolute(),
    ]
    working_dirs = [sphinx_install_path / "core"]
    while working_dirs:
        working_dir = working_dirs.pop()
        for elem in working_dir.iterdir():
            elem = elem.absolute()
            if elem in excluded_elems:
                continue
            if elem.is_dir():
                working_dirs.append(elem)
                continue
            if elem.is_file() and elem.name == "Cargo.toml":
                replace_in_file(
                    elem,
                    [
                        (
                            r"\[dependencies\]",
                            "[dependencies]\nfuzzer_utils.workspace = true",
                        )
                    ],
                )
            if elem.is_file() and elem.suffix == ".rs":
                is_updated = replace_in_file(
                    elem,
                    [
                        (r"\bassert_eq!", "fuzzer_utils::fuzzer_assert_eq!"),
                        (r"\bassert!", "fuzzer_utils::fuzzer_assert!"),
                    ],
                )
                # mod.rs already gets `use fuzzer_utils;` indirectly via the
                # inserted `mod fault_injection_context;` chain — skip the
                # double-import.
                if is_updated and elem.name not in {"mod.rs"}:
                    prepend_file(
                        elem,
                        "#[allow(unused_imports)]\nuse fuzzer_utils;\n",
                    )


def sphinx_fault_injection(sphinx_install_path: Path, commit_or_branch: str) -> None:
    """Apply all fault-injection patches to the cloned Sphinx repository."""
    del commit_or_branch  # only one upstream layout is currently supported

    create_fuzzer_utils_crate(sphinx_install_path)
    _patch_workspace_cargo_toml(sphinx_install_path)
    _drop_in_fault_injection_module(sphinx_install_path)
    _add_field_to_runtime(sphinx_install_path)
    _hook_execute_instruction_entry(sphinx_install_path)
    _wrap_pc_commit(sphinx_install_path)
    _step_after_instruction(sphinx_install_path)
    _patch_alu_rr(sphinx_install_path)
    _patch_alu_rw(sphinx_install_path)
    _patch_ecall_syscall_id(sphinx_install_path)
    _patch_execute_cycle(sphinx_install_path)
    _patch_register_oob_hotfix(sphinx_install_path)
    _wrap_asserts_in_core(sphinx_install_path)
