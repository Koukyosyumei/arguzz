import logging
from pathlib import Path

from valida_fuzzer.settings import (
    VALIDA_ZKVM_GIT_REPOSITORY,
)
from valida_fuzzer.zkvm_repository.injection import valida_fault_injection
from zkvm_fuzzer_utils.git import (
    git_clone_and_switch,
    git_reset_and_switch,
    is_git_repository,
)

logger = logging.getLogger("fuzzer")


def install_valida(
    valida_install_path: Path,
    commit_or_branch: str,
    *,
    enable_zkvm_modification: bool = False,
):
    # check if we already have the repository
    if not is_git_repository(valida_install_path):
        # pull the repository from the official sp1 github page
        logger.info(f"cloning valida repo to {valida_install_path}")
        git_clone_and_switch(valida_install_path, VALIDA_ZKVM_GIT_REPOSITORY, commit_or_branch)
    else:
        # reset all current changes and pull the newest version
        logger.info(f"resetting and pulling changes for sp1 repo @ {valida_install_path}")
        git_reset_and_switch(valida_install_path, commit_or_branch)

    # if fault injection is enabled, replace files
    if enable_zkvm_modification:
        logger.info(f"apply fault injection to sp1 repo @ {valida_install_path}")
        valida_fault_injection(valida_install_path, commit_or_branch)
