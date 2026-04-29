import logging
from pathlib import Path

from sphinx_fuzzer.settings import (
    SPHINX_ZKVM_GIT_REPOSITORY,
)
from sphinx_fuzzer.zkvm_repository.injection import sphinx_fault_injection
from zkvm_fuzzer_utils.git import (
    git_clone_and_switch,
    git_reset_and_switch,
    is_git_repository,
)

logger = logging.getLogger("fuzzer")


def install_sphinx(
    sphinx_install_path: Path,
    commit_or_branch: str,
    *,
    enable_zkvm_modification: bool = False,
):
    if not is_git_repository(sphinx_install_path):
        logger.info(f"cloning sphinx repo to {sphinx_install_path}")
        git_clone_and_switch(sphinx_install_path, SPHINX_ZKVM_GIT_REPOSITORY, commit_or_branch)
    else:
        logger.info(f"resetting and pulling changes for sphinx repo @ {sphinx_install_path}")
        git_reset_and_switch(sphinx_install_path, commit_or_branch)

    if enable_zkvm_modification:
        logger.info(f"apply fault injection to sphinx repo @ {sphinx_install_path}")
        sphinx_fault_injection(sphinx_install_path, commit_or_branch)
