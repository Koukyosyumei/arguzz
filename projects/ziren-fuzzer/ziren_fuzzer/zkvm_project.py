import io
from pathlib import Path

from circil.ir.node import Circuit
from ziren_fuzzer.settings import (
    RUST_GUEST_CORRECT_VALUE,
    RUST_GUEST_RETURN_TYPE,
    RUST_TOOLCHAIN_VERSION,
)
from zkvm_fuzzer_utils.file import create_file
from zkvm_fuzzer_utils.project import AbstractCircuitProjectGenerator
from zkvm_fuzzer_utils.rust.common import (
    ir_type_to_str,
    stream_circuit_output_and_compare_routine,
    stream_list_of_names,
    stream_list_of_typed_identifiers,
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
        super().__init__(root, zkvm_path, circuits, fault_injection, trace_collection)

    def create(self):
        self.create_root_cargo_toml()
        self.create_root_rust_toolchain()
        self.create_host_build_rs()
        self.create_host_cargo_toml()
        self.create_host_main_rs()
        self.create_guest_cargo_toml()
        self.create_guest_main_rs()

    def create_root_cargo_toml(self):
        create_file(
            self.root / "Cargo.toml",
            """[workspace]
members = [
    "host",
    "guest",
]
default-members = [ "host" ]

resolver = "2"
""",
        )

    def create_root_rust_toolchain(self):
        create_file(
            self.root / "rust-toolchain.toml",
            f"""[toolchain]
channel = "{RUST_TOOLCHAIN_VERSION}"
components = ["rustfmt", "clippy"]
""",
        )

    def create_host_build_rs(self):
        create_file(
            self.root / "host" / "build.rs",
            """fn main() {
    zkm_build::build_program("../guest");
}
""",
        )

    def create_host_cargo_toml(self):
        buffer = io.StringIO()
        buffer.write(
            f"""[package]
version = "0.1.0"
name = "ziren-host"
edition = "2021"
default-run = "ziren-host"

[[bin]]
name = "ziren-host"
path = "src/main.rs"

[dependencies]
zkm-sdk = {{ path = "{self.zkvm_path}/crates/sdk" }}
"""
        )

        if self.requires_fuzzer_utils:
            buffer.write(f'fuzzer_utils = {{ path = "{self.zkvm_path}/crates/fuzzer_utils" }}\n')

        buffer.write(
            f"""clap = {{ version = "4.0", features = ["derive", "env"] }}

[build-dependencies]
zkm-build = {{ path = "{self.zkvm_path}/crates/build" }}
camino = "=1.2.1"
"""
        )
        create_file(
            self.root / "host" / "Cargo.toml",
            buffer.getvalue(),
        )

    def create_host_main_rs(self):
        buffer = io.StringIO()

        if self.requires_fuzzer_utils:
            buffer.write("use fuzzer_utils;")

        buffer.write(
            """use clap::Parser;
use std::time::Instant;
use zkm_sdk::{include_elf, utils, ProverClient, ZKMStdin};

pub const ZIREN_GUEST_ELF: &[u8] = include_elf!("ziren-guest");

#[derive(Parser, Debug)]
#[clap(author, version, about, long_about = None)]
struct Args {
        """
        )

        if self.is_trace_collection:
            buffer.write("    #[clap(long)]\n")
            buffer.write("    trace: bool,\n")
            buffer.write("\n")

        if self.is_fault_injection:
            buffer.write('    #[arg(long, requires_all=["inject_step", "inject_kind", "seed"])]\n')
            buffer.write("    #[clap(long)]\n")
            buffer.write("    inject: bool,\n\n")

            buffer.write("    #[clap(long)]\n")
            buffer.write("    seed: Option<u64>,\n\n")

            buffer.write("    #[clap(long)]\n")
            buffer.write("    inject_step: Option<u64>,\n\n")

            buffer.write("    #[clap(long)]\n")
            buffer.write("    inject_kind: Option<String>,\n\n")

        for e in self.circuit_candidate.inputs:
            buffer.write("\n")
            buffer.write("    #[clap(long)]\n")
            buffer.write(f"    {e.name}: {ir_type_to_str(e.ty_hint)},\n")

        buffer.write(
            """}

fn create_ziren_stdin"""
        )
        stream_list_of_typed_identifiers(
            buffer, self.circuit_candidate.inputs, always_bracketed=True
        )
        buffer.write(
            """ -> ZKMStdin {
    let mut stdin = ZKMStdin::new();
"""
        )

        for circuit in self.circuits:
            buffer.write(f"    // -- {circuit.name} --\n")
            for e in self.circuit_candidate.inputs:
                buffer.write("    stdin.write(&")
                buffer.write(e.name)
                buffer.write(");\n")
            buffer.write("\n")

        buffer.write(
            """    return stdin;
}

fn main() {
    utils::setup_logger();
    let args = Args::parse();
"""
        )

        if self.is_trace_collection:
            buffer.write("    fuzzer_utils::set_trace_logging(args.trace);\n")

        if self.is_fault_injection:
            buffer.write("    fuzzer_utils::set_injection(args.inject);\n")
            buffer.write("    if args.inject {\n")
            buffer.write("        fuzzer_utils::set_seed(args.seed.unwrap());\n")
            buffer.write("        fuzzer_utils::set_injection_step(args.inject_step.unwrap());\n")
            buffer.write("        fuzzer_utils::set_injection_kind(args.inject_kind.unwrap());\n")
            buffer.write("        fuzzer_utils::disable_assertions();\n")
            buffer.write("    } else {\n")
            buffer.write("        fuzzer_utils::enable_assertions();\n")
            buffer.write("    }\n\n")

        for e in self.circuit_candidate.inputs:
            buffer.write(f"    let {e.name} = args.{e.name};\n")

        buffer.write(
            """
    // == Ziren Proof Setup ==

    println!(
        "<record>{{\\
            \\"context\\":\\"Setup\\", \\
            \\"status\\":\\"start\\"\\
        }}</record>"
    );
    let timer = Instant::now();
    let client = ProverClient::cpu();
    let stdin = create_ziren_stdin"""
        )

        stream_list_of_names(buffer, self.circuit_candidate.inputs, always_bracketed=True)

        buffer.write(
            f""";
    let (pk, vk) = client.setup(ZIREN_GUEST_ELF);
    println!(
        "<record>{{{{\\
            \\"context\\":\\"Setup\\", \\
            \\"status\\":\\"success\\", \\
            \\"time\\":\\"{{:.2?}}\\"\\
        }}}}</record>",
        timer.elapsed()
    );

    // == Ziren Proof Generation ==

    println!(
        "<record>{{{{\\
            \\"context\\":\\"Prover\\", \\
            \\"status\\":\\"start\\"\\
        }}}}</record>"
    );
    let timer = Instant::now();
    let proof = match client.prove(&pk, stdin).run() {{
        Ok(mut proof) => {{
            let output = proof.public_values.read::<{RUST_GUEST_RETURN_TYPE}>();
            println!(
                "<record>{{{{\\
                    \\"context\\":\\"Prover\\", \\
                    \\"status\\":\\"success\\", \\
                    \\"time\\":\\"{{:.2?}}\\", \\
                    \\"output\\":\\"{{}}\\"\\
                }}}}</record>",
                timer.elapsed(),
                output,
            );
            proof
        }},
        Err(error) => {{
            println!(
                "<record>{{{{\\
                    \\"context\\":\\"Prover\\", \\
                    \\"status\\":\\"error\\", \\
                    \\"time\\":\\"{{:.2?}}\\"\\
                }}}}</record>",
                timer.elapsed()
            );
            panic!("{{}}", error);
        }}
    }};

    // == Ziren Verification ==
"""
        )

        if self.is_fault_injection:
            buffer.write("    if args.inject { fuzzer_utils::enable_assertions(); }\n")

        buffer.write(
            """
    println!(
        "<record>{{\\
            \\"context\\":\\"Verifier\\", \\
            \\"status\\":\\"start\\"\\
        }}</record>"
    );
    let timer = Instant::now();
    match client.verify(&proof, &vk) {
        Ok(_) => {
            println!(
                "<record>{{\\
                    \\"context\\":\\"Verifier\\", \\
                    \\"status\\":\\"success\\", \\
                    \\"time\\":\\"{:.2?}\\"\\
                }}</record>",
                timer.elapsed()
            );
        },
        Err(error) => {
            println!(
                "<record>{{\\
                    \\"context\\":\\"Verifier\\", \\
                    \\"status\\":\\"error\\", \\
                    \\"time\\":\\"{:.2?}\\"\\
                }}</record>",
                timer.elapsed()
            );
            panic!("{}", error);
        }
    }
}
"""
        )

        create_file(self.root / "host" / "src" / "main.rs", buffer.getvalue())

    def create_guest_cargo_toml(self):
        create_file(
            self.root / "guest" / "Cargo.toml",
            f"""[package]
version = "0.1.0"
name = "ziren-guest"
edition = "2021"

[dependencies]
zkm-zkvm = {{ path = "{self.zkvm_path}/crates/zkvm/entrypoint" }}
""",
        )

    def create_guest_main_rs(self):
        buffer = io.StringIO()

        buffer.write("#![no_std]\n")
        buffer.write("#![no_main]\n")
        buffer.write("#![allow(unconditional_panic)]\n")
        buffer.write("#![allow(unused_variables)]\n")
        buffer.write("#![allow(arithmetic_overflow)]\n\n")
        buffer.write("#![feature(asm_experimental_arch)]\n\n")

        buffer.write("zkm_zkvm::entrypoint!(main);\n")

        for circuit in self.circuits:
            buffer.write(CircIL2UnsafeRustEmitter().run(circuit))
            buffer.write("\n")

        buffer.write("pub fn main() {\n")

        for circuit in self.circuits:
            for parameter in circuit.inputs:
                var_name = f"{circuit.name}_{parameter.name}"
                var_type = ir_type_to_str(parameter.ty_hint)
                buffer.write(
                    f"    let {var_name}: {var_type} = zkm_zkvm::io::read::<{var_type}>();\n"
                )
        buffer.write("\n")

        def helper_commit_and_exit(value: int, is_end: bool) -> list[str]:
            if is_end:
                return [f"zkm_zkvm::io::commit::<{RUST_GUEST_RETURN_TYPE}>(&{value}_u32);"]
            else:
                return [
                    f"zkm_zkvm::io::commit::<{RUST_GUEST_RETURN_TYPE}>(&{value}_u32);",
                    "return; // abort",
                ]

        stream_circuit_output_and_compare_routine(
            buffer, self.circuits, RUST_GUEST_CORRECT_VALUE, helper_commit_and_exit
        )

        buffer.write("}\n")

        create_file(self.root / "guest" / "src" / "main.rs", buffer.getvalue())
