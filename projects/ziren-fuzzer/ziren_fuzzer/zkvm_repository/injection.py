import logging
import re
from pathlib import Path

from ziren_fuzzer.zkvm_repository.fuzzer_utils_crate import create_fuzzer_utils_crate
from ziren_fuzzer.zkvm_repository.injection_source import (
    ziren_crates_core_executor_src_executor_rs,
)
from zkvm_fuzzer_utils.file import prepend_file, replace_in_file

logger = logging.getLogger("fuzzer")


class ZirenManagerException(Exception):
    pass


def ziren_fault_injection(ziren_install_path: Path, commit_or_branch: str):

    # add fuzzer utils crate
    create_fuzzer_utils_crate(ziren_install_path)

    replace_in_file(
        ziren_install_path / "Cargo.toml",
        [
            (
                r"""\[workspace\]
members = \[""",
                """[workspace]
members = [
  "crates/fuzzer_utils",""",
            ),
            (
                r"\[workspace.dependencies\]",
                '[workspace.dependencies]\nfuzzer_utils = { path = "crates/fuzzer_utils" }',
            ),
        ],
    )

    executor_path = (
        ziren_install_path / "crates" / "core" / "executor" / "src" / "executor.rs"
    )

    prepend_str, replacements = ziren_crates_core_executor_src_executor_rs(commit_or_branch)

    # prepend the fault injection structs and imports
    prepend_file(executor_path, prepend_str)

    # apply targeted replacements. The patches in `executor_rs_main.py` are
    # literal Rust source, but `replace_in_file` interprets the pattern as a
    # regex, so unescaped `(`, `)`, `?`, `[`, `]` (which appear in things like
    # `(&mut self)`, `(&instruction)?`, `#[cfg(...)]`) silently fail to match.
    # Escape patterns so they're treated as literals; the replacement strings
    # have no regex backreferences (`\1`..`\9`), so they are passed through.
    escaped_replacements = [
        (re.escape(old), new.replace("\\", "\\\\")) for old, new in replacements
    ]
    replace_in_file(executor_path, escaped_replacements)

    # add rand and fuzzer_utils dependencies to executor's Cargo.toml
    replace_in_file(
        ziren_install_path / "crates" / "core" / "executor" / "Cargo.toml",
        [
            (
                r"\[dependencies\]",
                "[dependencies]\nfuzzer_utils = { workspace = true }",
            ),
        ],
    )
