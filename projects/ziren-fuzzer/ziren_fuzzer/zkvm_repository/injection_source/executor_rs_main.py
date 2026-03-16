# ---------------------------------------------------------------------------- #
#                    Fault injection additions for Ziren executor              #
# ---------------------------------------------------------------------------- #
#
# Returns a tuple of (prepend_content, replacements) where:
#   prepend_content: str to prepend to executor.rs
#   replacements: list of (old_str, new_str) for replace_in_file
#


def ziren_fault_injection_context_struct() -> str:
    return """
// <----------------------- START OF FAULT INJECTION ----------------------->

use rand::rngs::StdRng;
use rand::{Rng, SeedableRng};
use fuzzer_utils;

/// Context used to manage fault injections for the MIPS zkVM
#[derive(Debug)]
pub struct MIPSFaultInjectionContext {
    trace_info_enabled: bool,
    injection_enabled: bool,
    instruction_override: bool,
    injection_step: u64,
    injection_type: String,
    current_step: u64,
    rng: StdRng,
    injection_history: HashMap<u32, Instruction>,
    pc_hint: u32,
}

impl MIPSFaultInjectionContext {

    /// construct the MIPS fault injection context
    pub fn new(
        trace_info_enabled: bool,
        injection_enabled: bool,
        instruction_override: bool,
        injection_step: u64,
        injection_type: String,
        injection_seed: u64,
    ) -> Self {
        Self {
            trace_info_enabled,
            injection_enabled,
            instruction_override,
            injection_step,
            injection_type,
            current_step: 0,
            rng: StdRng::seed_from_u64(injection_seed),
            injection_history: HashMap::new(),
            pc_hint: 0,
        }
    }

    /// advances the context one step
    pub fn step(&mut self, next_pc: u32) {
        self.current_step += 1;
        self.pc_hint = next_pc;

        if self.current_step > 1000000 {
            panic!("Endless loop detection step bound triggered! Bound: 1000000 steps");
        }
    }

    /// get a guess what the current pc might be
    pub fn get_pc_hint(&self) -> u32 {
        self.pc_hint
    }

    /// prints the injection info in parsable format
    pub fn print_injection_info(
        &self,
        pc: &u32,
        instruction: &Instruction,
        injection_type: &str,
        info: &String,
    ) {
        if self.trace_info_enabled {
            println!(
                "<fault>{{\\
                    \\"step\\":{}, \\
                    \\"pc\\":{}, \\
                    \\"instruction\\":\\"{}\\", \\
                    \\"assembly\\":\\"{:?}\\", \\
                    \\"kind\\":\\"{}\\",\\
                    \\"info\\":\\"{}\\"\\
                }}</fault>",
                self.current_step,
                pc,
                instruction.opcode.mnemonic(),
                instruction,
                injection_type,
                info,
            );
        }
    }

    /// checks if injections are enabled
    pub fn is_injection_enabled(&self) -> bool {
        self.injection_enabled
    }

    /// predicate to indicate if an injection should take place now
    pub fn is_injection(
        &self,
        injection_type: &str,
        pc: &u32,
        _executor_mode: ExecutorMode,
    ) -> bool {
        self.injection_enabled &&
        self.injection_type == injection_type && (
            (
                self.instruction_override
                && self.injection_history.contains_key(pc)
            ) || (
                self.current_step == self.injection_step
            )
        )
    }

    /// prints trace information on the current step
    pub fn print_trace_info(
        &self,
        pc: &u32,
        instruction: &Instruction,
        executor_mode: ExecutorMode,
        clk: u32,
    ) {
        if self.trace_info_enabled {
            println!(
                "<trace>{{\\
                    \\"step\\":{}, \\
                    \\"pc\\":{}, \\
                    \\"instruction\\":\\"{}\\", \\
                    \\"assembly\\":\\"{:?}\\", \\
                    \\"executor_mode\\":\\"{:?}\\", \\
                    \\"clk\\": \\"{}\\"\\
                }}</trace>",
                self.current_step,
                pc,
                instruction.opcode.mnemonic(),
                instruction,
                executor_mode,
                clk,
            );
        }
    }

    /// randomly modify a given instruction
    pub fn random_modify_instruction(&mut self, instruction: &Instruction) -> Instruction {
        loop {
            let new_op = if self.rng.gen::<bool>() {
                match self.rng.gen_range(0..=25) {
                    0  => Opcode::ADD,
                    1  => Opcode::SUB,
                    2  => Opcode::MUL,
                    3  => Opcode::SLL,
                    4  => Opcode::SRL,
                    5  => Opcode::SRA,
                    6  => Opcode::SLT,
                    7  => Opcode::SLTU,
                    8  => Opcode::AND,
                    9  => Opcode::OR,
                    10 => Opcode::XOR,
                    11 => Opcode::NOR,
                    12 => Opcode::DIV,
                    13 => Opcode::DIVU,
                    14 => Opcode::MOD,
                    15 => Opcode::MODU,
                    16 => Opcode::LB,
                    17 => Opcode::LH,
                    18 => Opcode::LW,
                    19 => Opcode::LBU,
                    20 => Opcode::LHU,
                    21 => Opcode::SB,
                    22 => Opcode::SH,
                    23 => Opcode::SW,
                    24 => Opcode::BEQ,
                    25 => Opcode::BNE,
                    _  => unreachable!(),
                }
            } else {
                instruction.opcode.clone()
            };

            let op_change_mask = self.rng.gen_range(0..=7) as u32;
            let new_op_a = if op_change_mask & 1 == 1 {
                self.rng.gen_range(0..=31)
            } else {
                instruction.op_a
            };

            let random_instruction = match self.rng.gen_range(0..=2) {
                // reg, reg, reg
                0 => {
                    let new_op_b = if op_change_mask & 2 == 2 || instruction.imm_b {
                        self.rng.gen_range(0..=31) as u32
                    } else {
                        instruction.op_b
                    };
                    let new_op_c = if op_change_mask & 4 == 4 || instruction.imm_c {
                        self.rng.gen_range(0..=31) as u32
                    } else {
                        instruction.op_c
                    };
                    Instruction::new(
                        new_op,
                        new_op_a,
                        new_op_b,
                        new_op_c,
                        false, /* imm b */
                        false, /* imm c */
                    )
                },
                // reg, reg, imm
                1 => {
                    let new_op_b = if op_change_mask & 2 == 2 || instruction.imm_b {
                        self.rng.gen_range(0..=31) as u32
                    } else {
                        instruction.op_b
                    };
                    let new_op_c = if op_change_mask & 4 == 4 {
                        self.rng.gen::<u32>()
                    } else {
                        instruction.op_c
                    };
                    Instruction::new(
                        new_op,
                        new_op_a,
                        new_op_b,
                        new_op_c,
                        false, /* imm b */
                        true,  /* imm c */
                    )
                },
                // reg, imm, imm
                2 => {
                    let new_op_b = if op_change_mask & 2 == 2 {
                        self.rng.gen::<u32>()
                    } else {
                        instruction.op_b
                    };
                    let new_op_c = if op_change_mask & 4 == 4 {
                        self.rng.gen::<u32>()
                    } else {
                        instruction.op_c
                    };
                    Instruction::new(
                        new_op,
                        new_op_a,
                        new_op_b,
                        new_op_c,
                        true, /* imm b */
                        true, /* imm c */
                    )
                },
                _ => unreachable!(),
            };

            // NOTE: Instruction does not always derive "PartialEq" so we use the fmt impl
            if format!("{:?}", instruction) != format!("{:?}", random_instruction) {
                return random_instruction;
            }
        }
    }

    /// returns a cached or a new instruction based on the setting and the provided parameters
    pub fn get_or_create_instruction(&mut self, instruction: &Instruction, pc: u32) -> Instruction {
        if self.instruction_override {
            if let Some(prev_instruction) = self.injection_history.get(&pc) {
                return prev_instruction.clone();
            }
        }
        let new_instruction = self.random_modify_instruction(instruction);
        self.injection_history.insert(pc, new_instruction);
        new_instruction
    }

    /// given a pc, this function returns a new pc within a distance of 1 up to 1000 steps
    pub fn random_pc(&mut self, pc: u32) -> u32 {
        let steps: u32 = match self.rng.gen_range(0..=2) {
            0 => { 1 },
            1 => { self.rng.gen_range(2..=10) },
            2 => { self.rng.gen_range(11..=1000) },
            _ => unreachable!(),
        };

        if self.rng.gen::<bool>() {
            pc.wrapping_add(steps * 4_u32)
        } else {
            pc.saturating_sub(steps * 4_u32)
        }
    }

    /// randomly modifies a given value
    pub fn random_mod_of_u32(&mut self, value: u32) -> u32 {
        let mut new_value = value;
        while new_value == value {
            let selector: u32 = self.rng.gen_range(0..=7);
            new_value = match selector {
                0 => { 0 },
                1 => { 1 },
                2 => { 0xffffffff },
                3 => { 0xfffffffe },
                4 => {
                    let n = self.rng.gen_range(1..=31);
                    let bits_to_flip = rand::seq::index::sample(&mut self.rng, 31, n).into_vec();
                    let mut flipped_value = value;
                    for bit_to_flip in bits_to_flip {
                        flipped_value ^= 1 << bit_to_flip;
                    }
                    flipped_value
                },
                5 => { value.saturating_add(1) },
                6 => { value.saturating_sub(1) },
                7 => { self.rng.gen::<u32>() },
                _ => unreachable!(),
            };
        }
        new_value
    }

    /// returns a random syscall code for MIPS
    pub fn random_syscall(&mut self) -> u32 {
        let selector: u32 = self.rng.gen_range(0..=7);
        match selector {
            0 => { 0x00_00_00_00 }, // HALT
            1 => { 0x00_00_00_02 }, // WRITE
            2 => { 0x00_00_00_03 }, // ENTER_UNCONSTRAINED
            3 => { 0x00_00_00_04 }, // EXIT_UNCONSTRAINED
            4 => { 0x00_00_00_10 }, // COMMIT
            5 => { 0x00_00_00_F0 }, // HINT_LEN
            6 => { 0x00_00_00_F1 }, // HINT_READ
            7 => { self.rng.gen::<u32>() },
            _ => unreachable!(),
        }
    }

    /// returns a random syscall different from the given one
    pub fn random_mod_syscall(&mut self, old_syscall: u32) -> u32 {
        let mut new_syscall: u32 = old_syscall;
        while new_syscall == old_syscall {
            new_syscall = self.random_syscall();
        }
        new_syscall
    }

    /// returns a random boolean
    pub fn random_bool(&mut self) -> bool {
        self.rng.gen::<bool>()
    }
}

/// Default implementation for `MIPSFaultInjectionContext`
impl Default for MIPSFaultInjectionContext {
    fn default() -> Self {
        Self::new(
            fuzzer_utils::is_trace_logging(),
            fuzzer_utils::is_injection(),
            fuzzer_utils::is_instruction_override(),
            fuzzer_utils::get_injection_step(),
            fuzzer_utils::get_injection_kind(),
            fuzzer_utils::get_seed(),
        )
    }
}

// <-----------------------  END OF FAULT INJECTION  ----------------------->

"""


def ziren_crates_core_executor_src_executor_rs(commit_or_branch: str) -> tuple[str, list[tuple[str, str]]]:
    """
    Returns (prepend_str, list_of_replacements) for modifying executor.rs.

    prepend_str is prepended to the file.
    list_of_replacements is a list of (old, new) string pairs for replace_in_file.
    """
    prepend_str = ziren_fault_injection_context_struct()

    replacements = [
        # 1. Add fault_injection_context field to the Executor struct (after lde_size_threshold)
        (
            "    /// The maximum LDE size to allow.\n    pub lde_size_threshold: u64,\n}",
            "    /// The maximum LDE size to allow.\n    pub lde_size_threshold: u64,\n\n"
            "    // <----------------------- START OF FAULT INJECTION ----------------------->\n\n"
            "    /// context for fault injection\n"
            "    pub fault_injection_context: MIPSFaultInjectionContext,\n\n"
            "    // <------------------------ END OF FAULT INJECTION ------------------------>\n}",
        ),
        # 2. Initialize fault_injection_context in with_context (after lde_size_threshold: 0,)
        (
            "            lde_size_check: false,\n            lde_size_threshold: 0,\n        }",
            "            lde_size_check: false,\n            lde_size_threshold: 0,\n"
            "            fault_injection_context: MIPSFaultInjectionContext::default(),\n        }",
        ),
        # 3. Modify execute_cycle to add fault injection
        (
            "    fn execute_cycle(&mut self) -> Result<bool, ExecutionError> {\n"
            "        // Fetch the instruction at the current program counter.\n"
            "        let instruction = self.fetch();\n"
            "\n"
            "        // Log the current state of the runtime.\n"
            "        #[cfg(debug_assertions)]\n"
            "        self.log(&instruction);\n"
            "\n"
            "        // Execute the instruction.\n"
            "        self.execute_operation(&instruction)?;\n",
            "    fn execute_cycle(&mut self) -> Result<bool, ExecutionError> {\n"
            "        // Fetch the instruction at the current program counter.\n"
            "        let mut instruction = self.fetch();\n"
            "\n"
            "        // -- FAULT INJECTION: INSTR_WORD_MOD --\n"
            "        if self.fault_injection_context.is_injection(\"INSTR_WORD_MOD\", &self.state.pc, self.executor_mode) {\n"
            "            let new_instruction = self.fault_injection_context.get_or_create_instruction(&instruction, self.state.pc);\n"
            "            self.fault_injection_context.print_injection_info(&self.state.pc, &instruction, \"INSTR_WORD_MOD\", &format!(\"{:?}\", new_instruction));\n"
            "            instruction = new_instruction;\n"
            "        }\n"
            "        self.fault_injection_context.print_trace_info(&self.state.pc, &instruction, self.executor_mode, self.state.clk);\n"
            "        // -- END FAULT INJECTION --\n"
            "\n"
            "        // Log the current state of the runtime.\n"
            "        #[cfg(debug_assertions)]\n"
            "        self.log(&instruction);\n"
            "\n"
            "        // Save PC for potential EXECUTE_INSTRUCTION_AGAIN injection\n"
            "        let _fi_saved_pc = self.state.pc;\n"
            "\n"
            "        // Execute the instruction.\n"
            "        self.execute_operation(&instruction)?;\n"
            "\n"
            "        // -- POST EXECUTION FAULT INJECTION --\n"
            "        let _fi_cur_pc = self.state.pc;\n"
            "        if self.fault_injection_context.is_injection(\"POST_EXEC_PRE_COMMIT_PC_MOD\", &_fi_cur_pc, self.executor_mode) {\n"
            "            let new_pc = self.fault_injection_context.random_pc(_fi_cur_pc);\n"
            "            self.fault_injection_context.print_injection_info(&_fi_cur_pc, &instruction, \"POST_EXEC_PRE_COMMIT_PC_MOD\", &new_pc.to_string());\n"
            "            self.state.pc = new_pc;\n"
            "            self.state.next_pc = new_pc.wrapping_add(4);\n"
            "        }\n"
            "        if self.fault_injection_context.is_injection(\"EXECUTE_INSTRUCTION_AGAIN\", &_fi_saved_pc, self.executor_mode) {\n"
            "            self.fault_injection_context.print_injection_info(&_fi_saved_pc, &instruction, \"EXECUTE_INSTRUCTION_AGAIN\", &String::from(\"re-executing instruction\"));\n"
            "            self.state.pc = _fi_saved_pc;\n"
            "            self.state.next_pc = _fi_saved_pc;\n"
            "        }\n"
            "        self.fault_injection_context.step(self.state.pc);\n"
            "        if self.fault_injection_context.is_injection(\"POST_EXEC_POST_COMMIT_PC_MOD\", &self.state.pc, self.executor_mode) {\n"
            "            let new_pc = self.fault_injection_context.random_pc(self.state.pc);\n"
            "            self.fault_injection_context.print_injection_info(&self.state.pc, &instruction, \"POST_EXEC_POST_COMMIT_PC_MOD\", &new_pc.to_string());\n"
            "            self.state.pc = new_pc;\n"
            "            self.state.next_pc = new_pc.wrapping_add(4);\n"
            "        }\n"
            "        // -- END POST EXECUTION FAULT INJECTION --\n"
            "\n",
        ),
    ]

    return prepend_str, replacements
