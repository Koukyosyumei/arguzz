from pico_fuzzer.zkvm_repository.injection_sources.e09f8d7 import (
    instruction_rs_e09f8d7,
    register_rs_e09f8d7,
)
from pico_fuzzer.zkvm_repository.injection_sources.latticevm import (
    instruction_rs_latticevm,
    register_rs_latticevm
)


def pico_vm_src_emulator_riscv_emulator_instruction_rs(commit_or_branch: str) -> str:
    match commit_or_branch:
        case "main":
            return instruction_rs_e09f8d7()
        case "e09f8d7c4132ac717935896fccf8a713b1fae418":
            return instruction_rs_e09f8d7()
        case "latticevm":
            return instruction_rs_latticevm()
        case _:
            raise NotImplementedError(f"unknown commit or branch {commit_or_branch}")


def pico_vm_src_compiler_riscv_register_rs(commit_or_branch: str) -> str:
    match commit_or_branch:
        case "main":
            return register_rs_e09f8d7()
        case "e09f8d7c4132ac717935896fccf8a713b1fae418":
            return register_rs_e09f8d7()
        case "latticevm":
            return register_rs_latticevm()
        case _:
            raise NotImplementedError(f"unknown commit or branch {commit_or_branch}")
