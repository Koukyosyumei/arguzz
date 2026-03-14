from valida_fuzzer.zkvm_repository.injection_source.executor_rs_latticevm import (
    executor_rs as executor_rs_latticevm,
)


def valida_basic_api_src_machine_basic_rs(commit_or_branch: str) -> str:
    match commit_or_branch:
        case "debuggable-v0.10.0":
            return executor_rs_latticevm()
        case _:
            raise NotImplementedError(f"unknown commit {commit_or_branch}")
