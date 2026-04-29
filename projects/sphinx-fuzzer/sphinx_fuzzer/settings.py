from sphinx_fuzzer.kinds import InjectionKind, InstrKind

#
# ZKVM Specific Versions and URLs
#

SPHINX_AVAILABLE_COMMITS_OR_BRANCHES = [
    "8a39b951e3ea520e295b693ad38bff6b43a2630c",
]
SPHINX_ZKVM_GIT_REPOSITORY = "https://github.com/argumentcomputer/sphinx"

# Sphinx pins its toolchain via rust-toolchain.toml in the cloned repo, so the
# guest builds against whatever channel the upstream repo declares. The host
# project we generate uses a stable channel that can drive sphinx-helper.
RUST_TOOLCHAIN_VERSION = "stable"

#
# Rust Magic Values
#

RUST_GUEST_RETURN_TYPE = "u32"
RUST_GUEST_CORRECT_VALUE = 0xDEADBEEF

#
# Flag to decide if division and modulo of 0 should be transformed
#

APPLY_SAFE_REM_DIV_TRANSFORMATION = True

#
# Special Timeout handling
#

TIMEOUT_PER_RUN = 60 * 4   # 4 min, in seconds
TIMEOUT_PER_BUILD = 60 * 30  # 30 min, in seconds

#
# Injection Specifics
#

ENABLED_INJECTION_KINDS: list[InjectionKind] = [
    InjectionKind.POST_EXEC_PRE_COMMIT_PC_MOD,
    InjectionKind.POST_EXEC_POST_COMMIT_PC_MOD,
    InjectionKind.INSTR_WORD_MOD,
    InjectionKind.ALU_RESULT_MOD,
    InjectionKind.ALU_RESULT_LOC_MOD,
    InjectionKind.ALU_PARSED_OPERAND_MOD,
    InjectionKind.EXECUTE_INSTRUCTION_AGAIN,
    InjectionKind.ALU_LOAD_OPERAND_MOD,
    InjectionKind.SYS_CALL_MOD_ECALL_ID,
]

# NOTE: empty list disables preferences
PREFERRED_INSTRUCTIONS: list[InstrKind] = []
