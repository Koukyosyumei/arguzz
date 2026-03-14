import io
from pathlib import Path

from circil.ir.node import Circuit
from circil.ir.type import IRType
from valida_fuzzer.assembly import CircIL2ValidaAssemblyEmitter
from valida_fuzzer.settings import RUST_GUEST_CORRECT_VALUE
from zkvm_fuzzer_utils.file import create_file
from zkvm_fuzzer_utils.project import AbstractCircuitProjectGenerator
from zkvm_fuzzer_utils.rust.common import ir_type_to_str

# Git coordinates for Plonky3 that the Valida workspace uses.
_P3_GIT_URL = "https://github.com/Koukyosyumei/lita-xyz-Plonky3.git"
_P3_GIT_BRANCH = "debuggable"


class CircuitProjectGenerator(AbstractCircuitProjectGenerator):
    def __init__(
        self,
        root: Path,
        zkvm_path: Path,
        circuits: list[Circuit],
        fault_injection: bool,
        trace_collection: bool,
    ):
        super().__init__(root, zkvm_path, circuits, fault_injection, trace_collection)

    def create(self):
        """Orchestrates the creation of the flat Valida runner project."""
        self.create_guest_val()
        self.create_cargo_toml()
        self.create_main_rs()

    # ------------------------------------------------------------------ #

    def create_guest_val(self):
        """Generates the Valida assembly file from the circuits."""
        asm = CircIL2ValidaAssemblyEmitter(
            self.circuits, RUST_GUEST_CORRECT_VALUE
        ).run()
        create_file(self.root / "guest.val", asm)

    # ------------------------------------------------------------------ #

    def create_cargo_toml(self):
        """Creates Cargo.toml for the flat single-package Valida runner."""
        buf = io.StringIO()
        buf.write(f"""\
[package]
name = "valida-runner"
version = "0.1.0"
edition = "2021"

[dependencies]
valida-basic-api = {{ path = "{self.zkvm_path}/basic-api" }}
valida-assembler  = {{ path = "{self.zkvm_path}/assembler" }}
valida-machine    = {{ path = "{self.zkvm_path}/machine" }}
valida-cpu        = {{ path = "{self.zkvm_path}/cpu" }}
valida-program    = {{ path = "{self.zkvm_path}/program" }}
p3-baby-bear = {{ git = "{_P3_GIT_URL}", branch = "{_P3_GIT_BRANCH}" }}
clap = {{ version = "4.0", features = ["derive"] }}
""")
        if self.requires_fuzzer_utils:
            buf.write(
                f'fuzzer_utils = {{ path = "{self.zkvm_path}/fuzzer_utils" }}\n'
            )
        create_file(self.root / "Cargo.toml", buf.getvalue())

    # ------------------------------------------------------------------ #

    def create_main_rs(self):
        """Generates the host Rust code that assembles and runs the Valida program."""
        buf = io.StringIO()

        if self.requires_fuzzer_utils:
            buf.write("use fuzzer_utils;\n")

        buf.write("""\
use clap::Parser;
use std::time::Instant;
use p3_baby_bear::BabyBear;
use valida_assembler::assemble;
use valida_basic_api::commands::common::prepare_runtime;
use valida_basic_api::{BasicMachine, BasicMachineMetrics};
use valida_cpu::MachineWithRegisters;
use valida_machine::{
    get_fixed_advice_provider, AdviceProviderWithDefault, Machine, ProgramROM,
    WriteCallbackWithDefault,
};
use valida_program::MachineWithProgramROM;

#[derive(Parser, Debug)]
#[clap(author, version, about)]
struct Args {
""")

        if self.is_trace_collection:
            buf.write("    #[clap(long)]\n")
            buf.write("    trace: bool,\n\n")

        if self.is_fault_injection:
            buf.write(
                '    #[arg(long, requires_all=["inject_step", "inject_kind", "seed"])]\n'
            )
            buf.write("    #[clap(long)]\n")
            buf.write("    inject: bool,\n\n")
            buf.write("    #[clap(long)]\n")
            buf.write("    seed: Option<u64>,\n\n")
            buf.write("    #[clap(long)]\n")
            buf.write("    inject_step: Option<u64>,\n\n")
            buf.write("    #[clap(long)]\n")
            buf.write("    inject_kind: Option<String>,\n\n")

        for e in self.circuit_candidate.inputs:
            buf.write("    #[clap(long)]\n")
            buf.write(f"    {e.name}: {ir_type_to_str(e.ty_hint)},\n\n")

        buf.write("}\n\nfn main() {\n")
        buf.write("    let args = Args::parse();\n\n")

        if self.is_trace_collection:
            buf.write("    fuzzer_utils::set_trace_logging(args.trace);\n")

        if self.is_fault_injection:
            buf.write("    fuzzer_utils::set_injection(args.inject);\n")
            buf.write("    if args.inject {\n")
            buf.write("        fuzzer_utils::set_seed(args.seed.unwrap());\n")
            buf.write(
                "        fuzzer_utils::set_injection_step(args.inject_step.unwrap());\n"
            )
            buf.write(
                "        fuzzer_utils::set_injection_kind(args.inject_kind.unwrap());\n"
            )
            buf.write("        fuzzer_utils::disable_assertions();\n")
            buf.write("    } else {\n")
            buf.write("        fuzzer_utils::enable_assertions();\n")
            buf.write("    }\n\n")

        # Build advice bytes from CLI inputs (matches what the assembly reads).
        buf.write("    // Build advice bytes from CLI inputs (LE encoding).\n")
        buf.write("    let mut advice_bytes: Vec<u8> = Vec::new();\n")
        for e in self.circuit_candidate.inputs:
            if e.ty_hint == IRType.Field:
                buf.write(
                    f"    advice_bytes.extend_from_slice(&args.{e.name}.to_le_bytes());\n"
                )
            else:  # Bool
                buf.write(
                    f"    advice_bytes.push(if args.{e.name} {{ 1u8 }} else {{ 0u8 }});\n"
                )

        # Machine setup and execution.
        buf.write(r"""
    // Assemble the guest Valida program (embedded at compile time).
    let asm = include_str!("../guest.val");
    let machine_code = assemble(asm).expect("assembly failed");

    // Set up the Valida machine.
    let mut machine = BasicMachine::<BabyBear>::default();
    machine.set_segment_number(0);
    machine.set_max_trace_height(65536);
    let rom = ProgramROM::from_machine_code(&machine_code);
    machine.set_program_rom(rom, valida_program::ProgramTableType::Public);
    let fp_init: u32 = 16777216; // default stack base
    machine.set_initial_register_values(valida_cpu::Registers { pc: 0, fp: fp_init });

    // Set up the advice provider and runtime.
    let advice = get_fixed_advice_provider(advice_bytes);
    let mut runtime = prepare_runtime(
        AdviceProviderWithDefault(advice),
        WriteCallbackWithDefault::default(),
    )
    .expect("runtime init failed");

    // Run the machine and measure time.
    let timer = Instant::now();
    let mut state = machine.start(&mut runtime);
    let mut metrics = BasicMachineMetrics::initialize();
    let (_instance_data, output) = BasicMachine::run(&mut state, &mut metrics);
    let elapsed = timer.elapsed();

    // Parse the 4-byte LE output as a u32.
    let result_bytes: [u8; 4] = output[0..4].try_into().expect("output too short");
    let result = u32::from_le_bytes(result_bytes);

    println!(
        "<record>{{\"context\":\"Execution\", \"status\":\"success\", \"output\":\"{}\", \"time\":\"{:.2?}\"}}</record>",
        result,
        elapsed
    );
}
""")

        create_file(self.root / "src" / "main.rs", buf.getvalue())
