import logging
from pathlib import Path

from valida_fuzzer.zkvm_repository.fuzzer_utils_crate import create_fuzzer_utils_crate
from valida_fuzzer.zkvm_repository.injection_source import (
    valida_basic_api_src_machine_basic_rs,
)
from zkvm_fuzzer_utils.file import overwrite_file, prepend_file, replace_in_file

logger = logging.getLogger("fuzzer")

class ValidaManagerException(Exception):
    pass

def valida_fault_injection(valida_install_path: Path, commit_or_branch: str):
    # 1. Create fuzzer_utils crate at the root of the Valida repository
    create_fuzzer_utils_crate(valida_install_path)

    # 2. Update root Cargo.toml to include the new crate in the workspace
    replace_in_file(
        valida_install_path / "Cargo.toml",
        [
            (
                r"members = \[", 
                'members = [\n  "fuzzer_utils",'
            ),
            (
                r"\[workspace.dependencies\]",
                '[workspace.dependencies]\nfuzzer_utils = { path = "fuzzer_utils" }',
            ),
        ],
    )

    # 3. Inject Executor Hooks into basic-api
    # This replaces the main execution loop/step logic with instrumented code.
    overwrite_file(
        valida_install_path / "basic-api" / "src" / "machine" / "basic.rs",
        valida_basic_api_src_machine_basic_rs(commit_or_branch),
    )

    """
    # 3b. Add rand to basic-api so the injected fault-injection code compiles.
    # (fuzzer_utils is added to all core crates uniformly in step 5 below.)
    replace_in_file(
        valida_install_path / "basic-api" / "Cargo.toml",
        [
            (
                r"\[dependencies\]",
                "[dependencies]\nrand = { version = \"0.8\", features = [\"std_rng\"] }",
            )
        ],
    )
    """

    # 4. Handle Memory/Register OOB (Out-Of-Bounds) Fixes
    # Valida uses a memory-based addressing system. OOB protection should be added to 
    # the memory backend if necessary.
    memory_lib_rs = valida_install_path / "memory" / "src" / "lib.rs"
    if memory_lib_rs.exists():
        prepend_file(memory_lib_rs, "#[allow(unused_imports)]\nuse fuzzer_utils;\n")
        # Logic to handle OOB would go here, similar to the register logic in the example.

    # 5. Update sub-crate dependencies and replace standard assertions
    # Valida's core logic is split across multiple top-level crates.
    core_crates = ["alu_u32", "basic-api", "cpu", "machine", "memory", "program"]
    
    # Files that should not have fuzzer_utils prepended due to compilation order/issues
    excluded_files = [
        (valida_install_path / "machine" / "src" / "operations" / "field" / "field_inner_product.rs").absolute()
    ]

    for crate_name in core_crates:
        crate_path = valida_install_path / crate_name
        if not crate_path.exists():
            continue

        # Add fuzzer_utils as a workspace dependency in each crate's Cargo.toml
        replace_in_file(
            crate_path / "Cargo.toml",
            [
                (
                    r"\[dependencies\]",
                    """[dependencies]\nfuzzer_utils.workspace = true""",
                )
            ],
        )

        # Iterate through all Rust source files in the crate
        for rs_file in (crate_path / "src").rglob("*.rs"):
            rs_file_abs = rs_file.absolute()
            if rs_file_abs in excluded_files:
                continue

            # Replace standard asserts with fuzzer-specific ones for better error reporting
            is_updated = replace_in_file(
                rs_file,
                [
                    (r"\bassert_eq!", "fuzzer_utils::fuzzer_assert_eq!"),
                    (r"\bassert!", "fuzzer_utils::fuzzer_assert!"),
                ],
            )

            # Prepend the import if we modified the file and it's not the executor hook itself
            if is_updated and rs_file.name != "basic.rs":
                prepend_file(
                    rs_file,
                    "#[allow(unused_imports)]\nuse fuzzer_utils;\n",
                )

    logger.info("Successfully injected Valida-VM fault injection hooks.")