"""
Valida assembly emitter for CircIL circuits.

Translates SSA-transformed CircIL circuits into a single Valida assembly
`main:` function that runs all circuits and compares their outputs.
"""

import io

from circil.ir.node import (
    Assignment,
    BinaryExpression,
    Boolean,
    CallExpression,
    Circuit,
    Identifier,
    Integer,
    TernaryExpression,
    UnaryExpression,
)
from circil.ir.operator import Operator
from circil.ir.type import IRType
from zkvm_fuzzer_utils.circil import SSATransformer


class CircIL2ValidaAssemblyEmitter:
    """
    Emits a single Valida assembly `main:` function that:
      1. Reads all circuit inputs from the advice tape.
      2. Executes each circuit's SSA statements sequentially.
      3. Compares pairwise circuit outputs (XOR == 0 check).
      4. Writes the correct output value on success, or an error ID on mismatch.
    """

    def __init__(self, circuits: list[Circuit], correct_output: int):
        self._circuits = circuits
        self._correct_output = correct_output
        self._slot_counter: int = 0
        self._var_to_slot: dict[str, int] = {}
        self._label_counter: int = 0
        self._buf = io.StringIO()

    # ---- Slot Management ----

    def _alloc(self, key: str) -> int:
        if key not in self._var_to_slot:
            idx = self._slot_counter
            self._slot_counter += 1
            self._var_to_slot[key] = idx
        return self._var_to_slot[key]

    def _off(self, key: str) -> int:
        """fp-relative integer offset for a slot key (always negative multiples of 4)."""
        return -(self._var_to_slot[key] + 1) * 4

    def _fp(self, key: str) -> str:
        """fp-relative offset string suitable for use in assembly operands."""
        return f"{self._off(key)}(fp)"

    def _alloc_tmp(self, hint: str = "") -> str:
        key = f"__tmp_{self._slot_counter}_{hint}"
        self._alloc(key)
        return key

    # ---- Emit Helpers ----

    def _emit(self, line: str):
        self._buf.write(f"\t{line}\n")

    def _emit_label(self, label: str):
        self._buf.write(f"{label}:\n")

    def _new_label(self) -> str:
        lbl = f".L_{self._label_counter}"
        self._label_counter += 1
        return lbl

    def _emit_imm32(self, key: str, value: int):
        """Emit imm32 instruction to store a 32-bit integer in slot `key`."""
        v = value & 0xFFFFFFFF
        b = [v & 0xFF, (v >> 8) & 0xFF, (v >> 16) & 0xFF, (v >> 24) & 0xFF]
        self._emit(f"imm32\t{self._fp(key)}, {b[0]}, {b[1]}, {b[2]}, {b[3]}")

    def _emit_copy(self, dst_key: str, src_key: str):
        """Emit addi dst, src, 0  (copy src slot to dst slot)."""
        self._emit(f"addi\t{self._fp(dst_key)}, {self._fp(src_key)}, 0")

    def _emit_write_u32(self, key: str):
        """
        Write the u32 value stored at `key` to the output tape as 4 LE bytes.
        Uses a temporary slot to avoid clobbering the source.
        """
        tmp = self._alloc_tmp("wr")
        self._emit_copy(tmp, key)
        off = self._off(tmp)
        self._emit(f"write\t0, {off}, 0, 0, 1")
        self._emit(f"divi\t{off}, {off}, 256")
        self._emit(f"write\t0, {off}, 0, 0, 1")
        self._emit(f"divi\t{off}, {off}, 256")
        self._emit(f"write\t0, {off}, 0, 0, 1")
        self._emit(f"divi\t{off}, {off}, 256")
        self._emit(f"write\t0, {off}, 0, 0, 1")

    def _emit_write_const_and_stop(self, value: int):
        """Emit a constant value as 4-byte output and then stop."""
        const_key = self._alloc_tmp(f"cv{value & 0xFFFF}")
        self._emit_imm32(const_key, value)
        self._emit_write_u32(const_key)
        self._emit("stop")

    # ---- Input Reading from Advice Tape ----

    def _emit_read_input_from_advice(self, inp_key: str, ty: IRType):
        """
        Emit instructions to read one input value from the advice tape.

        Bool inputs: 1 byte → stored directly (0 or 1) into inp_key.
        Field inputs: 4 bytes LE → read into 4 temp slots, then combined into inp_key.
        """
        if ty == IRType.Bool:
            # advread stores one byte as Word([byte, 0, 0, 0]) = integer value = byte
            self._emit(f"advread\t{self._off(inp_key)}")
        else:
            # Read 4 LE bytes individually then combine: val = b0 + b1*256 + b2*65536 + b3*16M
            b0 = self._alloc_tmp("b0")
            b1 = self._alloc_tmp("b1")
            b2 = self._alloc_tmp("b2")
            b3 = self._alloc_tmp("b3")

            self._emit(f"advread\t{self._off(b0)}")  # byte 0 (LSB)
            self._emit(f"advread\t{self._off(b1)}")  # byte 1
            self._emit(f"advread\t{self._off(b2)}")  # byte 2
            self._emit(f"advread\t{self._off(b3)}")  # byte 3 (MSB)

            # Combine bytes: inp = b0 + b1*256 + b2*65536 + b3*16777216
            t1 = self._alloc_tmp("sh1")  # b1 * 256
            t2 = self._alloc_tmp("ab01")  # b0 + b1*256
            t3 = self._alloc_tmp("sh2")  # b2 * 65536
            t4 = self._alloc_tmp("ab012")  # b0 + b1*256 + b2*65536
            t5 = self._alloc_tmp("sh3")  # b3 * 16777216

            self._emit(f"muli\t{self._fp(t1)}, {self._fp(b1)}, 256")
            self._emit(f"add\t{self._fp(t2)}, {self._fp(b0)}, {self._fp(t1)}")
            self._emit(f"muli\t{self._fp(t3)}, {self._fp(b2)}, 65536")
            self._emit(f"add\t{self._fp(t4)}, {self._fp(t2)}, {self._fp(t3)}")
            self._emit(f"muli\t{self._fp(t5)}, {self._fp(b3)}, 16777216")
            self._emit(f"add\t{self._fp(inp_key)}, {self._fp(t4)}, {self._fp(t5)}")

    # ---- Circuit Variable Key ----

    def _ckey(self, circuit_name: str, var_name: str) -> str:
        """Construct the slot key for a variable in a circuit's scope."""
        return f"{circuit_name}__{var_name}"

    # ---- Expression Materialization ----

    def _expr_to_fp(self, cn: str, expr) -> str:
        """
        Return the fp-relative address string for a simple expression.
        For Identifier: returns its allocated slot's fp string.
        For Integer/Boolean: allocates a fresh temp slot, emits imm32, returns the fp string.
        """
        if isinstance(expr, Identifier):
            key = self._ckey(cn, expr.name)
            return self._fp(key)
        elif isinstance(expr, Integer):
            tmp = self._alloc_tmp(f"ic{expr.value & 0xFFFF}")
            self._emit_imm32(tmp, expr.value)
            return self._fp(tmp)
        elif isinstance(expr, Boolean):
            tmp = self._alloc_tmp(f"bc{1 if expr.value else 0}")
            self._emit_imm32(tmp, 1 if expr.value else 0)
            return self._fp(tmp)
        else:
            raise NotImplementedError(f"_expr_to_fp: unsupported type {type(expr)}")

    def _as_imm(self, expr) -> int | None:
        """If expr is a constant, return its integer value; otherwise None."""
        if isinstance(expr, Integer):
            return expr.value
        elif isinstance(expr, Boolean):
            return 1 if expr.value else 0
        return None

    # ---- Statement Emission ----

    def _emit_binary(self, cn: str, dst_key: str, op: Operator, lhs, rhs):
        dst = self._fp(dst_key)
        rhs_imm = self._as_imm(rhs)
        lhs_imm = self._as_imm(lhs)

        def lhs_fp():
            return self._expr_to_fp(cn, lhs)

        def rhs_fp():
            return self._expr_to_fp(cn, rhs)

        match op:
            case Operator.ADD:
                if rhs_imm is not None:
                    self._emit(f"addi\t{dst}, {lhs_fp()}, {rhs_imm}")
                elif lhs_imm is not None:
                    self._emit(f"addi\t{dst}, {rhs_fp()}, {lhs_imm}")
                else:
                    self._emit(f"add\t{dst}, {lhs_fp()}, {rhs_fp()}")

            case Operator.SUB:
                if rhs_imm is not None:
                    self._emit(f"subi\t{dst}, {lhs_fp()}, {rhs_imm}")
                else:
                    self._emit(f"sub\t{dst}, {lhs_fp()}, {rhs_fp()}")

            case Operator.MUL:
                if rhs_imm is not None:
                    self._emit(f"muli\t{dst}, {lhs_fp()}, {rhs_imm}")
                elif lhs_imm is not None:
                    self._emit(f"muli\t{dst}, {rhs_fp()}, {lhs_imm}")
                else:
                    self._emit(f"mul\t{dst}, {lhs_fp()}, {rhs_fp()}")

            case Operator.DIV:
                if rhs_imm is not None and rhs_imm != 0:
                    self._emit(f"divi\t{dst}, {lhs_fp()}, {rhs_imm}")
                else:
                    self._emit(f"div\t{dst}, {lhs_fp()}, {rhs_fp()}")

            case Operator.REM:
                # rem(a, b) = a - (a / b) * b  (unsigned)
                q = self._alloc_tmp("rq")
                p = self._alloc_tmp("rp")
                if rhs_imm is not None and rhs_imm != 0:
                    self._emit(f"divi\t{self._fp(q)}, {lhs_fp()}, {rhs_imm}")
                    self._emit(f"muli\t{self._fp(p)}, {self._fp(q)}, {rhs_imm}")
                else:
                    rhs_slot = rhs_fp()
                    lhs_slot = lhs_fp()
                    self._emit(f"div\t{self._fp(q)}, {lhs_slot}, {rhs_slot}")
                    self._emit(f"mul\t{self._fp(p)}, {self._fp(q)}, {rhs_slot}")
                    dst = self._fp(dst_key)  # refresh in case lhs_fp/rhs_fp alloc'd tmps
                    self._emit(f"sub\t{dst}, {lhs_slot}, {self._fp(p)}")
                    return
                dst = self._fp(dst_key)
                self._emit(f"sub\t{dst}, {lhs_fp()}, {self._fp(p)}")

            case Operator.POW:
                # After rewrite rules pow2_to_mul / pow3_to_mul, POW should be rare.
                # Fallback: treat as mul (only exact for exponent 1).
                if rhs_imm is not None:
                    self._emit(f"muli\t{dst}, {lhs_fp()}, {rhs_imm}")
                else:
                    self._emit(f"mul\t{dst}, {lhs_fp()}, {rhs_fp()}")

            case Operator.AND | Operator.LAND:
                if rhs_imm is not None:
                    self._emit(f"andi\t{dst}, {lhs_fp()}, {rhs_imm}")
                elif lhs_imm is not None:
                    self._emit(f"andi\t{dst}, {rhs_fp()}, {lhs_imm}")
                else:
                    self._emit(f"and\t{dst}, {lhs_fp()}, {rhs_fp()}")

            case Operator.OR | Operator.LOR:
                if rhs_imm is not None:
                    self._emit(f"ori\t{dst}, {lhs_fp()}, {rhs_imm}")
                elif lhs_imm is not None:
                    self._emit(f"ori\t{dst}, {rhs_fp()}, {lhs_imm}")
                else:
                    self._emit(f"or\t{dst}, {lhs_fp()}, {rhs_fp()}")

            case Operator.XOR | Operator.LXOR:
                if rhs_imm is not None:
                    self._emit(f"xori\t{dst}, {lhs_fp()}, {rhs_imm}")
                elif lhs_imm is not None:
                    self._emit(f"xori\t{dst}, {rhs_fp()}, {lhs_imm}")
                else:
                    self._emit(f"xor\t{dst}, {lhs_fp()}, {rhs_fp()}")

            case Operator.EQU:
                if rhs_imm is not None:
                    self._emit(f"eqi\t{dst}, {lhs_fp()}, {rhs_imm}")
                elif lhs_imm is not None:
                    self._emit(f"eqi\t{dst}, {rhs_fp()}, {lhs_imm}")
                else:
                    self._emit(f"eq\t{dst}, {lhs_fp()}, {rhs_fp()}")

            case Operator.NEQ:
                if rhs_imm is not None:
                    self._emit(f"nei\t{dst}, {lhs_fp()}, {rhs_imm}")
                elif lhs_imm is not None:
                    self._emit(f"nei\t{dst}, {rhs_fp()}, {lhs_imm}")
                else:
                    self._emit(f"ne\t{dst}, {lhs_fp()}, {rhs_fp()}")

            case Operator.LTH:
                if rhs_imm is not None:
                    self._emit(f"lti\t{dst}, {lhs_fp()}, {rhs_imm}")
                else:
                    self._emit(f"lt\t{dst}, {lhs_fp()}, {rhs_fp()}")

            case Operator.LEQ:
                if rhs_imm is not None:
                    self._emit(f"ltei\t{dst}, {lhs_fp()}, {rhs_imm}")
                else:
                    self._emit(f"lte\t{dst}, {lhs_fp()}, {rhs_fp()}")

            case Operator.GTH:
                # a > b  <=>  b < a
                if lhs_imm is not None:
                    self._emit(f"lti\t{dst}, {rhs_fp()}, {lhs_imm}")
                else:
                    self._emit(f"lt\t{dst}, {rhs_fp()}, {lhs_fp()}")

            case Operator.GEQ:
                # a >= b  <=>  b <= a
                if lhs_imm is not None:
                    self._emit(f"ltei\t{dst}, {rhs_fp()}, {lhs_imm}")
                else:
                    self._emit(f"lte\t{dst}, {rhs_fp()}, {lhs_fp()}")

            case _:
                # Unknown operator – fall back to copying lhs into dst
                self._emit(f"addi\t{dst}, {lhs_fp()}, 0")

    def _emit_unary(self, cn: str, dst_key: str, op: Operator, val):
        dst = self._fp(dst_key)
        match op:
            case Operator.NOT:
                # Logical NOT: dst = (val == 0)
                if isinstance(val, (Integer, Boolean)):
                    v = (1 if val.value else 0) if isinstance(val, Boolean) else val.value
                    self._emit_imm32(dst_key, 1 if v == 0 else 0)
                else:
                    src = self._expr_to_fp(cn, val)
                    self._emit(f"eqi\t{dst}, {src}, 0")
            case Operator.COMP:
                # Bitwise complement: XOR with 0xFFFFFFFF  (= -1 as i32)
                src = self._expr_to_fp(cn, val)
                self._emit(f"xori\t{dst}, {src}, -1")
            case Operator.SUB:
                # Unary negation: dst = 0 - val  (using pre-allocated zero slot)
                zero_key = "__zero__"
                src = self._expr_to_fp(cn, val)
                self._emit(f"sub\t{dst}, {self._fp(zero_key)}, {src}")
            case _:
                src = self._expr_to_fp(cn, val)
                self._emit(f"addi\t{dst}, {src}, 0")

    def _emit_ternary(self, cn: str, dst_key: str, cond, if_expr, else_expr):
        """Emit: dst = cond ? if_expr : else_expr using Valida branch instructions."""
        dst = self._fp(dst_key)

        true_lbl = self._new_label()
        end_lbl = self._new_label()

        # Materialize cond into a slot (fixed string, no re-evaluation)
        cond_fp = self._expr_to_fp(cn, cond)

        # Jump to true_lbl if cond != 0
        self._emit(f"bnei\t{true_lbl}, {cond_fp}, 0")

        # False branch: dst = else_expr
        else_fp = self._expr_to_fp(cn, else_expr)
        self._emit(f"addi\t{dst}, {else_fp}, 0")

        # Unconditional jump to end (self-compare: fp[x] == fp[x] is always true)
        self._emit(f"beq\t{end_lbl}, {cond_fp}, {cond_fp}")

        # True branch: dst = if_expr
        self._emit_label(true_lbl)
        if_fp = self._expr_to_fp(cn, if_expr)
        self._emit(f"addi\t{dst}, {if_fp}, 0")

        self._emit_label(end_lbl)

    def _emit_call(self, cn: str, dst_key: str, func_name: str, args: list):
        """Emit a RISC-V extension call expression mapped to Valida instructions."""
        dst = self._fp(dst_key)

        def arg_fp(i: int) -> str:
            return self._expr_to_fp(cn, args[i])

        def arg_imm(i: int) -> int | None:
            return self._as_imm(args[i]) if i < len(args) else None

        match func_name:
            case "add":
                self._emit(f"add\t{dst}, {arg_fp(0)}, {arg_fp(1)}")
            case "addi":
                imm = arg_imm(1) if len(args) > 1 else 0
                self._emit(f"addi\t{dst}, {arg_fp(0)}, {imm}")
            case "sub":
                self._emit(f"sub\t{dst}, {arg_fp(0)}, {arg_fp(1)}")
            case "lui":
                imm = arg_imm(0) if args else 0
                self._emit_imm32(dst_key, ((imm or 0) & 0xFFFFF) << 12)
            case "xor":
                self._emit(f"xor\t{dst}, {arg_fp(0)}, {arg_fp(1)}")
            case "xori":
                imm = arg_imm(1) if len(args) > 1 else 0
                self._emit(f"xori\t{dst}, {arg_fp(0)}, {imm}")
            case "or":
                self._emit(f"or\t{dst}, {arg_fp(0)}, {arg_fp(1)}")
            case "ori":
                imm = arg_imm(1) if len(args) > 1 else 0
                self._emit(f"ori\t{dst}, {arg_fp(0)}, {imm}")
            case "and":
                self._emit(f"and\t{dst}, {arg_fp(0)}, {arg_fp(1)}")
            case "andi":
                imm = arg_imm(1) if len(args) > 1 else 0
                self._emit(f"andi\t{dst}, {arg_fp(0)}, {imm}")
            case "sll":
                self._emit(f"shl\t{dst}, {arg_fp(0)}, {arg_fp(1)}")
            case "slli":
                imm = arg_imm(1) if len(args) > 1 else 0
                self._emit(f"shli\t{dst}, {arg_fp(0)}, {imm}")
            case "srl":
                self._emit(f"shr\t{dst}, {arg_fp(0)}, {arg_fp(1)}")
            case "srli":
                imm = arg_imm(1) if len(args) > 1 else 0
                self._emit(f"shri\t{dst}, {arg_fp(0)}, {imm}")
            case "sra":
                self._emit(f"sra\t{dst}, {arg_fp(0)}, {arg_fp(1)}")
            case "srai":
                imm = arg_imm(1) if len(args) > 1 else 0
                self._emit(f"srai\t{dst}, {arg_fp(0)}, {imm}")
            case "slt":
                self._emit(f"slt\t{dst}, {arg_fp(0)}, {arg_fp(1)}")
            case "slti":
                imm = arg_imm(1) if len(args) > 1 else 0
                self._emit(f"slti\t{dst}, {arg_fp(0)}, {imm}")
            case "sltu":
                self._emit(f"lt\t{dst}, {arg_fp(0)}, {arg_fp(1)}")
            case "sltiu":
                imm = arg_imm(1) if len(args) > 1 else 0
                self._emit(f"lti\t{dst}, {arg_fp(0)}, {imm}")
            case "beq":
                self._emit(f"eq\t{dst}, {arg_fp(0)}, {arg_fp(1)}")
            case "bne":
                self._emit(f"ne\t{dst}, {arg_fp(0)}, {arg_fp(1)}")
            case "blt":
                self._emit(f"slt\t{dst}, {arg_fp(0)}, {arg_fp(1)}")
            case "bge":
                self._emit(f"sle\t{dst}, {arg_fp(1)}, {arg_fp(0)}")
            case "bltu":
                self._emit(f"lt\t{dst}, {arg_fp(0)}, {arg_fp(1)}")
            case "bgeu":
                self._emit(f"lte\t{dst}, {arg_fp(1)}, {arg_fp(0)}")
            case "jal":
                # jal always returns 1 (jumps forward, skips nothing observable)
                self._emit_imm32(dst_key, 1)
            case "mul":
                self._emit(f"mul\t{dst}, {arg_fp(0)}, {arg_fp(1)}")
            case "mulh":
                self._emit(f"mulhs\t{dst}, {arg_fp(0)}, {arg_fp(1)}")
            case "mulhsu":
                # Approximate as signed mul-high (mulhs)
                self._emit(f"mulhs\t{dst}, {arg_fp(0)}, {arg_fp(1)}")
            case "mulhu":
                self._emit(f"mulhu\t{dst}, {arg_fp(0)}, {arg_fp(1)}")
            case "div":
                # RISC-V signed division
                self._emit(f"sdiv\t{dst}, {arg_fp(0)}, {arg_fp(1)}")
            case "divu":
                # RISC-V unsigned division
                self._emit(f"div\t{dst}, {arg_fp(0)}, {arg_fp(1)}")
            case "rem" | "remu":
                # rem(a, b) = a - (a/b)*b
                q = self._alloc_tmp("cq")
                p = self._alloc_tmp("cp")
                a_fp = arg_fp(0)
                b_fp = arg_fp(1)
                div_op = "sdiv" if func_name == "rem" else "div"
                self._emit(f"{div_op}\t{self._fp(q)}, {a_fp}, {b_fp}")
                self._emit(f"mul\t{self._fp(p)}, {self._fp(q)}, {b_fp}")
                self._emit(f"sub\t{dst}, {a_fp}, {self._fp(p)}")
            case "sb_lb" | "sh_lh" | "sw_lw" | "sb_lbu" | "sh_lhu":
                # Memory store+load – approximate as identity of the value argument.
                # This is not exact but consistent across circuits for fuzzing.
                if len(args) > 1:
                    self._emit(f"addi\t{dst}, {arg_fp(1)}, 0")
                else:
                    self._emit_imm32(dst_key, 0)
            case _:
                # Unknown function – fall back to 0
                self._emit_imm32(dst_key, 0)

    def _emit_assignment(self, cn: str, stmt: Assignment):
        """Emit assembly for one SSA assignment statement."""
        lhs_key = self._ckey(cn, stmt.lhs.name)
        self._alloc(lhs_key)

        rhs = stmt.rhs

        if isinstance(rhs, Identifier):
            src_key = self._ckey(cn, rhs.name)
            self._emit_copy(lhs_key, src_key)

        elif isinstance(rhs, Integer):
            self._emit_imm32(lhs_key, rhs.value)

        elif isinstance(rhs, Boolean):
            self._emit_imm32(lhs_key, 1 if rhs.value else 0)

        elif isinstance(rhs, UnaryExpression):
            self._emit_unary(cn, lhs_key, rhs.op, rhs.value)

        elif isinstance(rhs, BinaryExpression):
            self._emit_binary(cn, lhs_key, rhs.op, rhs.lhs, rhs.rhs)

        elif isinstance(rhs, TernaryExpression):
            self._emit_ternary(cn, lhs_key, rhs.cond, rhs.if_expr, rhs.else_expr)

        elif isinstance(rhs, CallExpression):
            self._emit_call(cn, lhs_key, rhs.function.name, rhs.arguments)

        else:
            # Unknown node type – fall back to 0
            self._emit_imm32(lhs_key, 0)

    def _emit_circuit(self, circuit_ssa: Circuit):
        """Emit all SSA assignment statements for one circuit."""
        cn = circuit_ssa.name
        # Pre-allocate output slots so they are available for comparison.
        for out in circuit_ssa.outputs:
            self._alloc(self._ckey(cn, out.name))
        for stmt in circuit_ssa.statements:
            if isinstance(stmt, Assignment):
                self._emit_assignment(cn, stmt)
            # Assertions (if any) are skipped – not representable in Valida assembly.

    def run(self) -> str:
        """
        Generate and return the complete Valida assembly as a string.
        Can be called multiple times (resets state each time).
        """
        self._buf.truncate(0)
        self._buf.seek(0)
        self._slot_counter = 0
        self._var_to_slot = {}
        self._label_counter = 0

        self._buf.write("main:\n")

        # Allocate and initialize the permanent ZERO slot (used by unary negation).
        zero_key = "__zero__"
        self._alloc(zero_key)
        self._emit_imm32(zero_key, 0)

        first_circuit = self._circuits[0]

        # Read all inputs from the advice tape (only for the first circuit).
        for inp in first_circuit.inputs:
            inp_key = self._ckey(first_circuit.name, inp.name)
            self._alloc(inp_key)
            self._emit_read_input_from_advice(inp_key, inp.ty_hint)

        # Subsequent circuits share the same input slots (alias, no re-read needed).
        for circuit in self._circuits[1:]:
            for i, inp in enumerate(circuit.inputs):
                dst_key = self._ckey(circuit.name, inp.name)
                src_key = self._ckey(first_circuit.name, first_circuit.inputs[i].name)
                # Alias: point dst_key to the exact same slot index as src_key.
                self._var_to_slot[dst_key] = self._var_to_slot[src_key]

        # Apply SSA transformation and emit each circuit's statements.
        ssa_circuits = [SSATransformer().transform(c) for c in self._circuits]
        for circuit_ssa in ssa_circuits:
            self._emit_circuit(circuit_ssa)

        # Compare pairwise output slots.
        for c_idx, (c0, c1) in enumerate(zip(ssa_circuits[:-1], ssa_circuits[1:])):
            for o_idx, (c0_out, c1_out) in enumerate(zip(c0.outputs, c1.outputs)):
                error_id = c_idx * 1000 + o_idx

                c0_out_key = self._ckey(c0.name, c0_out.name)
                c1_out_key = self._ckey(c1.name, c1_out.name)

                diff_key = self._alloc_tmp("diff")
                self._emit(
                    f"xor\t{self._fp(diff_key)}, "
                    f"{self._fp(c0_out_key)}, {self._fp(c1_out_key)}"
                )

                ok_lbl = self._new_label()
                self._emit(f"beqi\t{ok_lbl}, {self._fp(diff_key)}, 0")

                # Outputs differ → write error_id and stop.
                self._emit_write_const_and_stop(error_id)

                self._emit_label(ok_lbl)

        # All outputs matched → write the correct value and stop.
        self._emit_write_const_and_stop(self._correct_output)

        return self._buf.getvalue()
