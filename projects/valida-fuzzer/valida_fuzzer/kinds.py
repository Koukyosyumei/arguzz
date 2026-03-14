from strenum import StrEnum


class InstrKind(StrEnum):
    # Core/Memory Instructions
    LOAD32 = "load32"
    LOADU8 = "loadu8"
    LOADS8 = "loads8"
    STORE32 = "store32"
    STOREU8 = "storeu8"
    JAL = "jal"
    JALV = "jalv"
    BEQ = "beq"
    BNE = "bne"
    IMM32 = "imm32"
    STOP = "stop"
    FAIL = "fail"
    LOADFP = "loadfp"
    MEMCPY = "memcpy"

    # ALU 32-bit Instructions
    ADD32 = "add32"
    SUB32 = "sub32"
    MUL32 = "mul32"
    MULHS32 = "mulhs32"
    MULHU32 = "mulhu32"
    DIV32 = "div32"
    SDIV32 = "sdiv32"
    SHL32 = "shl32"
    SHR32 = "shr32"
    SRA32 = "sra32"
    LT32 = "lt32"
    LTE32 = "lte32"
    SLT32 = "slt32"
    SLE32 = "sle32"
    AND32 = "and32"
    OR32 = "or32"
    XOR32 = "xor32"
    NE32 = "ne32"
    EQ32 = "eq32"

    # I/O and Extensions
    READ_ADVICE = "read"
    WRITE = "write"
    KECCAKF = "keccakf"
    COMB_SECP256K1 = "comb_secp256k1"
    MULS_SECP256K1 = "muls_secp256k1"
    SINV_SECP256K1 = "sinv_secp256k1"
    SMUL_SECP256K1 = "smul_secp256k1"

    @classmethod
    def alus(cls) -> list["InstrKind"]:
        return [
            cls.ADD32, cls.SUB32, cls.MUL32, cls.MULHS32, cls.MULHU32,
            cls.DIV32, cls.SDIV32, cls.SHL32, cls.SHR32, cls.SRA32,
            cls.LT32, cls.LTE32, cls.SLT32, cls.SLE32,
            cls.AND32, cls.OR32, cls.XOR32, cls.NE32, cls.EQ32,
        ]

    @classmethod
    def loads(cls) -> list["InstrKind"]:
        return [cls.LOAD32, cls.LOADU8, cls.LOADS8, cls.LOADFP]

    @classmethod
    def stores(cls) -> list["InstrKind"]:
        return [cls.STORE32, cls.STOREU8]

    @classmethod
    def branches(cls) -> list["InstrKind"]:
        return [cls.BEQ, cls.BNE, cls.JAL, cls.JALV]

    def is_alu(self) -> bool:
        return self in InstrKind.alus()

    def has_modifiable_output(self) -> bool:
        # Most ALU and memory load operations have outputs written to memory
        return self.is_alu() or self in InstrKind.loads() or self == InstrKind.READ_ADVICE


class InjectionKind(StrEnum):
    # Modifies the PC at the end of the step function but before the next pc is committed.
    # Results in skipping or going back one or multiple instructions.
    POST_EXEC_PRE_COMMIT_PC_MOD = "POST_EXEC_PRE_COMMIT_PC_MOD"

    # Modifies the PC at the end of the step function but before the next pc is committed.
    # Results in skipping or going back one or multiple instructions.
    POST_EXEC_POST_COMMIT_PC_MOD = "POST_EXEC_POST_COMMIT_PC_MOD"

    # Modifies the loaded word from the program memory.
    INSTR_WORD_MOD = "INSTR_WORD_MOD"

    # Modifies the computed result of an ALU instruction.
    ALU_RESULT_MOD = "ALU_RESULT_MOD"

    # Modifies the operands BEFORE the alu instruction is executed, but after
    # the instruction is read and returns the modified operands.
    ALU_PARSED_OPERAND_MOD = "ALU_PARSED_OPERAND_MOD"

    # Modifies the operand parsing of an alu instruction.
    ALU_LOAD_OPERAND_MOD = "ALU_LOAD_OPERAND_MOD"

    # Modifies the output location / register of an alu instruction.
    ALU_RESULT_LOC_MOD = "ALU_RESULT_LOC_MOD"

    # Executes the same instruction again
    EXECUTE_INSTRUCTION_AGAIN = "EXECUTE_INSTRUCTION_AGAIN"

    # Changes the ecall id of a system call
    SYS_CALL_MOD_ECALL_ID = "SYS_CALL_MOD_ECALL_ID"

    @classmethod
    def retrieve_injection_types(
        cls, kind: InstrKind, enabled_injection_kinds: list["InjectionKind"] | None
    ) -> list["InjectionKind"]:

        # following types are always valid
        result = {
            cls.POST_EXEC_PRE_COMMIT_PC_MOD,
            cls.POST_EXEC_POST_COMMIT_PC_MOD,
            cls.INSTR_WORD_MOD,
            cls.EXECUTE_INSTRUCTION_AGAIN,
        }

        # instruction with a simple output and no side effects
        if kind.is_alu():
            result.add(cls.ALU_RESULT_MOD)
            result.add(cls.ALU_PARSED_OPERAND_MOD)
            result.add(cls.ALU_RESULT_LOC_MOD)
            result.add(cls.ALU_LOAD_OPERAND_MOD)

        # ecall instruction
        #if kind.is_ecall():
        #    result.add(cls.SYS_CALL_MOD_ECALL_ID)

        if enabled_injection_kinds:
            return sorted(list(result.intersection(enabled_injection_kinds)))
        else:
            return sorted(result)