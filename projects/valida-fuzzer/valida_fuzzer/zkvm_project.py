import io
from pathlib import Path

from circil.ir.node import Circuit
from valida_fuzzer.settings import (
    RUST_GUEST_CORRECT_VALUE,
)
from zkvm_fuzzer_utils.file import create_file
from zkvm_fuzzer_utils.project import AbstractCircuitProjectGenerator
from zkvm_fuzzer_utils.rust.common import (
    ir_type_to_str,
    stream_circuit_output_and_compare_routine,
)
from zkvm_fuzzer_utils.rust.ir2rust import CircIL2UnsafeRustEmitter


class CircuitProjectGenerator(AbstractCircuitProjectGenerator):
    def __init__(
        self,
        root: Path,
        zkvm_path: Path,
        circuits: list[Circuit],
        fault_injection: bool,
        trace_collection: bool,
    ):
        # AbstractCircuitProjectGenerator handles basic root and path assignments
        super().__init__(root, zkvm_path, circuits, fault_injection, trace_collection)

    def create(self):
        """Orchestrates the creation of the Valida project structure."""
        self.create_guest_cargo_toml()
        self.create_guest_main_rs()
        self.create_host_cargo_toml()
        self.create_host_main_rs()

    def create_guest_cargo_toml(self):
        """Creates the Cargo.toml for the guest program (the circuit logic)."""
        create_file(
            self.root / "guest" / "Cargo.toml",
            f"""[package]
name = "valida-guest"
version = "1.0.0"
edition = "2021"

[dependencies]
# Guest logic may interact with Valida-specific intrinsics if necessary
""",
        )

    def create_guest_main_rs(self):
        """Generates the Rust guest code containing the fuzzing circuits."""
        buffer = io.StringIO()
        buffer.write("#![no_main]\n")
        buffer.write("#![no_std]\n\n")

        # Emit the generated circuit logic from CircIL
        for circuit in self.circuits:
            buffer.write(CircIL2UnsafeRustEmitter().run(circuit))
            buffer.write("\n")

        buffer.write("""
#[no_mangle]
pub extern "C" fn main() {
    // Valida uses an advice provider for inputs
""")

        # Generate code to read inputs from the advice tape
        for circuit in self.circuits:
            for parameter in circuit.inputs:
                var_name = f"{circuit.name}_{parameter.name}"
                var_type = ir_type_to_str(parameter.ty_hint)
                # Logic to read from Valida's specific input/advice channel
                buffer.write(f"    let {var_name}: {var_type} = unsafe {{ read_advice() }};\n")
        
        buffer.write("\n")

        def helper_commit_and_exit(value: int, is_end: bool) -> list[str]:
            # Valida-specific exit/output commitment logic
            if is_end:
                return [f"unsafe {{ write_output({value}_u32) }};"]
            else:
                return [f"unsafe {{ write_output({value}_u32) }};", "return;"]

        stream_circuit_output_and_compare_routine(
            buffer, self.circuits, RUST_GUEST_CORRECT_VALUE, helper_commit_and_exit
        )

        buffer.write("}")

        create_file(self.root / "guest" / "src" / "main.rs", buffer.getvalue())

    def create_host_cargo_toml(self):
        """Creates the Cargo.toml for the host (the VM executor/prover)."""
        buffer = io.StringIO()
        # The host requires Valida's internal machine crates
        buffer.write(
            f"""[package]
name = "valida-host"
version = "1.0.0"
edition = "2021"

[dependencies]
valida-machine = {{ path = "{self.zkvm_path}/machine" }}
valida-basic-api = {{ path = "{self.zkvm_path}/basic-api" }}
valida-cpu = {{ path = "{self.zkvm_path}/cpu" }}
clap = {{ version = "4.0", features = ["derive", "env"] }}
"""
        )

        if self.requires_fuzzer_utils:
            buffer.write(f'fuzzer_utils = {{ path = "{self.zkvm_path}/fuzzer_utils" }}\n')

        create_file(self.root / "host" / "Cargo.toml", buffer.getvalue())

    def create_host_main_rs(self):
        """Generates the host code that sets up Valida-VM and runs the guest ELF."""
        buffer = io.StringIO()

        if self.requires_fuzzer_utils:
            buffer.write("use fuzzer_utils;\n")

        buffer.write("""
use valida_basic_api::BasicMachine;
use valida_machine::{Machine, MachineRuntime, ValidaRuntime, StarkConfig};
use clap::Parser;
use std::time::Instant;

#[derive(Parser, Debug)]
struct Args {
""")

        if self.is_trace_collection:
            buffer.write("    #[clap(long)] trace: bool,\n")

        if self.is_fault_injection:
            buffer.write("    #[clap(long)] inject: bool,\n")
            buffer.write("    #[clap(long)] seed: Option<u64>,\n")
            buffer.write("    #[clap(long)] inject_step: Option<u64>,\n")
            buffer.write("    #[clap(long)] inject_kind: Option<String>,\n")

        # Command-line arguments for circuit inputs
        for e in self.circuit_candidate.inputs:
            buffer.write(f"    #[clap(long)] {e.name}: {ir_type_to_str(e.ty_hint)},\n")

        buffer.write("""
}

fn main() {
    let args = Args::parse();
    
    // Initialize fuzzer utils if required
""")

        if self.is_fault_injection:
            buffer.write("    fuzzer_utils::set_injection(args.inject);\n")
            # ... additional injection setup similar to Pico/Nexus ...

        buffer.write("""
    // Load the Valida guest ELF
    let elf_path = "guest/target/valida-unknown-none-elf/release/valida-guest";
    let program_data = std::fs::read(elf_path).expect("failed to read guest ELF");

    // Initialize Valida Machine and Runtime
    let mut runtime = ValidaRuntime::default();
    
    // Feed inputs into the advice provider
""")

        for e in self.circuit_candidate.inputs:
            buffer.write(f"    runtime.push_advice(Some(args.{e.name} as u8));\n")

        buffer.write("""
    let mut machine = BasicMachine::default();
    machine.init_with_program(&program_data);

    let timer = Instant::now();
    // Execute the machine using the Step/Run logic found in basic.rs
    let (instance_data, output) = machine.run(&mut runtime);
    
    println!("Execution Time: {:.2?}", timer.elapsed());
    println!("Machine Output: {:?}", output);
}
""")

        create_file(self.root / "host" / "src" / "main.rs", buffer.getvalue())