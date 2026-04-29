from valida_fuzzer.zkvm_repository.injection_source.executor_rs_latticevm import (
    executor_rs as executor_rs_latticevm,
)


def valida_basic_api_src_machine_basic_rs(commit_or_branch: str) -> str:
    match commit_or_branch:
        case "a13377060607ed3463cc17a7c8d005a9fe492b03":
            return executor_rs_latticevm()
        case _:
            raise NotImplementedError(f"unknown commit {commit_or_branch}")
