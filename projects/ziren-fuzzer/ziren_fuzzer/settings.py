from ziren_fuzzer.kinds import InjectionKind, InstrKind

#
# ZKVM Specific Versions and URLs
#

ZIREN_AVAILABLE_COMMITS_OR_BRANCHES = [
    "1054a6fd9e4e982772533789b3bdad8240514815",
    "latticevm",
]
ZIREN_ZKVM_GIT_REPOSITORY = "https://github.com/ProjectZKM/Ziren"
RUST_TOOLCHAIN_VERSION = "nightly-2025-10-30"

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
TIMEOUT_PER_BUILD = 60 * 60  # 60 min, in seconds

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
    InjectionKind.SYS_CALL_MOD_SYSCALL_ID,
]

# NOTE: empty list disables preferences
PREFERRED_INSTRUCTIONS: list[InstrKind] = []
