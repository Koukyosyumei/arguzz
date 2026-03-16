from strenum import StrEnum


class InstrKind(StrEnum):
    # ALU
    ADD = "add"
    SUB = "sub"
    MUL = "mul"
    MULT = "mult"
    MULTU = "multu"
    DIV = "div"
    DIVU = "divu"
    MOD = "mod"
    MODU = "modu"
    SLL = "sll"
    SRL = "srl"
    SRA = "sra"
    ROR = "ror"
    SLT = "slt"
    SLTU = "sltu"
    AND = "and"
    OR = "or"
    XOR = "xor"
    NOR = "nor"
    CLZ = "clz"
    CLO = "clo"
    # Branch
    BEQ = "beq"
    BNE = "bne"
    BGEZ = "bgez"
    BGTZ = "bgtz"
    BLEZ = "blez"
    BLTZ = "bltz"
    # Jump
    JUMP = "jump"
    JUMPI = "jumpi"
    JUMP_DIRECT = "jump_direct"
    # Memory loads
    LB = "lb"
    LBU = "lbu"
    LH = "lh"
    LHU = "lhu"
    LW = "lw"
    LWL = "lwl"
    LWR = "lwr"
    LL = "ll"
    # Memory stores
    SB = "sb"
    SH = "sh"
    SW = "sw"
    SWL = "swl"
    SWR = "swr"
    SC = "sc"
    # Misc
    INS = "ins"
    MADDU = "maddu"
    MSUBU = "msubu"
    MADD = "madd"
    MSUB = "msub"
    MEQ = "meq"
    MNE = "mne"
    WSBH = "wsbh"
    EXT = "ext"
    TEQ = "teq"
    SEXT = "seb"
    SYSCALL = "syscall"
    UNIMPL = "unimpl"

    @classmethod
    def loads(cls) -> list["InstrKind"]:
        return [cls.LB, cls.LBU, cls.LH, cls.LHU, cls.LW, cls.LWL, cls.LWR, cls.LL]

    @classmethod
    def stores(cls) -> list["InstrKind"]:
        return [cls.SB, cls.SH, cls.SW, cls.SWL, cls.SWR, cls.SC]

    @classmethod
    def alus(cls) -> list["InstrKind"]:
        return [
            cls.ADD,
            cls.SUB,
            cls.MUL,
            cls.MULT,
            cls.MULTU,
            cls.DIV,
            cls.DIVU,
            cls.MOD,
            cls.MODU,
            cls.SLL,
            cls.SRL,
            cls.SRA,
            cls.ROR,
            cls.SLT,
            cls.SLTU,
            cls.AND,
            cls.OR,
            cls.XOR,
            cls.NOR,
            cls.CLZ,
            cls.CLO,
        ]

    @classmethod
    def branches(cls) -> list["InstrKind"]:
        return [cls.BEQ, cls.BNE, cls.BGEZ, cls.BGTZ, cls.BLEZ, cls.BLTZ]

    def is_load(self) -> bool:
        return self in InstrKind.loads()

    def is_store(self) -> bool:
        return self in InstrKind.stores()

    def is_alu(self) -> bool:
        return self in InstrKind.alus()

    def is_branch(self) -> bool:
        return self in InstrKind.branches()

    def is_syscall(self) -> bool:
        return self == InstrKind.SYSCALL


class InjectionKind(StrEnum):
    # Modifies the PC after execution but before the next pc is committed.
    POST_EXEC_PRE_COMMIT_PC_MOD = "POST_EXEC_PRE_COMMIT_PC_MOD"

    # Modifies the PC after execution and after the next pc is committed.
    POST_EXEC_POST_COMMIT_PC_MOD = "POST_EXEC_POST_COMMIT_PC_MOD"

    # Modifies the loaded instruction word.
    INSTR_WORD_MOD = "INSTR_WORD_MOD"

    # Executes the same instruction again.
    EXECUTE_INSTRUCTION_AGAIN = "EXECUTE_INSTRUCTION_AGAIN"

    # Modifies the computed result of an ALU instruction.
    ALU_RESULT_MOD = "ALU_RESULT_MOD"

    # Modifies the operands before an ALU instruction is executed.
    ALU_PARSED_OPERAND_MOD = "ALU_PARSED_OPERAND_MOD"

    # Modifies the output location / register of an ALU instruction.
    ALU_RESULT_LOC_MOD = "ALU_RESULT_LOC_MOD"

    # Modifies the syscall code.
    SYS_CALL_MOD_SYSCALL_ID = "SYS_CALL_MOD_SYSCALL_ID"

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

        # syscall instruction
        if kind.is_syscall():
            result.add(cls.SYS_CALL_MOD_SYSCALL_ID)

        if enabled_injection_kinds:
            return sorted(list(result.intersection(enabled_injection_kinds)))
        else:
            return sorted(result)
