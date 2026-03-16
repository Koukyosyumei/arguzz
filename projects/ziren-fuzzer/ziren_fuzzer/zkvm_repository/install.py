import logging
from pathlib import Path

from ziren_fuzzer.settings import (
    ZIREN_ZKVM_GIT_REPOSITORY,
)
from ziren_fuzzer.zkvm_repository.injection import ziren_fault_injection
from zkvm_fuzzer_utils.git import (
    git_clone_and_switch,
    git_reset_and_switch,
    is_git_repository,
)

logger = logging.getLogger("fuzzer")


def install_ziren(
    ziren_install_path: Path,
    commit_or_branch: str,
    *,
    enable_zkvm_modification: bool = False,
):
    # check if we already have the repository
    if not is_git_repository(ziren_install_path):
        # pull the repository from the official Ziren github page
        logger.info(f"cloning Ziren repo to {ziren_install_path}")
        git_clone_and_switch(ziren_install_path, ZIREN_ZKVM_GIT_REPOSITORY, commit_or_branch)
    else:
        # reset all current changes and pull the newest version
        logger.info(f"resetting and pulling changes for Ziren repo @ {ziren_install_path}")
        git_reset_and_switch(ziren_install_path, commit_or_branch)

    # if fault injection is enabled, replace files
    if enable_zkvm_modification:
        logger.info(f"apply fault injection to Ziren repo @ {ziren_install_path}")
        ziren_fault_injection(ziren_install_path, commit_or_branch)
