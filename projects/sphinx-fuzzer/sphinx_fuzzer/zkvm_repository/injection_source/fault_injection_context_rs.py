# ---------------------------------------------------------------------------- #
# RV32IMFaultInjectionContext for Sphinx zkVM
#
# Dropped in as `core/src/runtime/fault_injection_context.rs`. Mirrors the
# fault-injection context that SP1's patched `executor.rs` carries, adapted to
# Sphinx's `Runtime` (in `core/src/runtime/mod.rs`).
#
# Sphinx-specific notes vs. SP1:
#   * `Instruction` is re-exported from `super::Instruction` (SP1: in scope).
#   * `ExecutorMode` does not exist in Sphinx; we drop the parameter and use a
#     simple bool to indicate constrained vs. unconstrained mode if needed.
# ---------------------------------------------------------------------------- #


def fault_injection_context_rs() -> str:
    return """use hashbrown::HashMap;
use rand::rngs::StdRng;
use rand::{Rng, SeedableRng};

use super::Instruction;

#[allow(unused_imports)]
use fuzzer_utils;

/// Context used to manage fault injections in Sphinx's RV32IM Runtime.
#[derive(Debug)]
pub struct RV32IMFaultInjectionContext {
    trace_info_enabled: bool,
    injection_enabled: bool,
    instruction_override: bool,
    injection_step: u64,
    injection_type: String,
    current_step: u64,
    rng: StdRng,
    injection_history: HashMap<u32, Instruction>,
    pc_hint: u32,
    instruction_hint: Option<Instruction>,
}

impl Default for RV32IMFaultInjectionContext {
    fn default() -> Self {
        Self::new(false, false, false, 0, String::new(), 0)
    }
}

impl RV32IMFaultInjectionContext {
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
            instruction_hint: None,
        }
    }

    pub fn step(&mut self, next_pc: u32) {
        self.current_step += 1;
        self.pc_hint = next_pc;

        if self.current_step > 1_000_000 {
            panic!("Endless loop detection step bound triggered! Bound: 1000000 steps");
        }
    }

    pub fn get_pc_hint(&self) -> u32 {
        self.pc_hint
    }

    pub fn set_instruction_hint(&mut self, instruction: &Instruction) {
        self.instruction_hint = Some(*instruction);
    }

    pub fn get_instruction_hint(&self) -> Instruction {
        self.instruction_hint.unwrap()
    }

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
                    \\"instruction\\":\\"{:?}\\", \\
                    \\"assembly\\":\\"{:?}\\", \\
                    \\"kind\\":\\"{}\\",\\
                    \\"info\\":\\"{}\\"\\
                }}</fault>",
                self.current_step,
                pc,
                instruction.opcode,
                instruction,
                injection_type,
                info,
            );
        }
    }

    pub fn is_injection_enabled(&self) -> bool {
        self.injection_enabled
    }

    pub fn is_injection(&self, injection_type: &str, pc: &u32) -> bool {
        self.injection_enabled
            && self.injection_type == injection_type
            && ((self.instruction_override && self.injection_history.contains_key(pc))
                || (self.current_step == self.injection_step))
    }

    pub fn print_trace_info(&self, pc: &u32, instruction: &Instruction, clk: u32) {
        if self.trace_info_enabled {
            println!(
                "<trace>{{\\
                    \\"step\\":{}, \\
                    \\"pc\\":{}, \\
                    \\"instruction\\":\\"{:?}\\", \\
                    \\"assembly\\":\\"{:?}\\", \\
                    \\"clk\\": \\"{}\\"\\
                }}</trace>",
                self.current_step,
                pc,
                instruction.opcode,
                instruction,
                clk,
            );
        }
    }

    pub fn random_bool(&mut self) -> bool {
        self.rng.gen::<bool>()
    }

    pub fn random_mod_of_u32(&mut self, value: u32) -> u32 {
        let r = self.rng.gen::<u32>();
        if value == 0 { r } else { r ^ value }
    }

    pub fn random_mod_of_u32_pair(&mut self, b: u32, c: u32) -> (u32, u32) {
        (self.random_mod_of_u32(b), self.random_mod_of_u32(c))
    }

    pub fn random_pc(&mut self, current_next_pc: u32) -> u32 {
        let delta = (self.rng.gen::<i32>() % 16) * 4;
        (current_next_pc as i64 + delta as i64) as u32
    }

    pub fn record_history(&mut self, pc: u32, instruction: Instruction) {
        self.injection_history.insert(pc, instruction);
    }
}

/// Build a context from the global fuzzer_utils state set up by the host.
pub fn fault_injection_context_from_globals() -> RV32IMFaultInjectionContext {
    RV32IMFaultInjectionContext::new(
        fuzzer_utils::is_trace_logging(),
        fuzzer_utils::is_injection(),
        fuzzer_utils::is_instruction_override(),
        fuzzer_utils::get_injection_step(),
        fuzzer_utils::get_injection_kind(),
        fuzzer_utils::get_seed(),
    )
}
"""
