"""
Helper methods to parse qasm circuits.
"""

from fractions import Fraction
from typing import List, Sequence, Tuple

from lsqecc.gates import gates
from lsqecc.utils import QasmParseException


def get_index_arg(qreg_arg: str) -> int:
    return int(qreg_arg.split("[")[1].split("]")[0])


def split_instruciton_and_args(line: str) -> Tuple[str, List[str]]:
    if " " not in line:
        return line, []
    return line.split(" ")[0], line.split(" ")[1].split(",")


def parse_trivial_gate(instruction: str, args: List[str]) -> gates.Gate:
    if instruction == "h":
        return gates.H(get_index_arg(args[0]))
    elif instruction == "x":
        return gates.X(get_index_arg(args[0]))
    elif instruction == "s":
        return gates.S(get_index_arg(args[0]))
    elif instruction == "t":
        return gates.T(get_index_arg(args[0]))
    else:
        raise QasmParseException(f"Not a trivial gate: {instruction}")


def parse_gates_circuit(qasm: str) -> Sequence[gates.Gate]:

    instructions: List[Tuple[str, List[str]]] = list(
        map(split_instruciton_and_args, qasm.split(";\n"))
    )

    qregs = list(filter(lambda line: line[0] == "qreg", instructions))
    if len(qregs) != 1:
        raise QasmParseException(f"Need exactly one qreg, got {len(qregs)}")

    instructions = list(
        filter(lambda line: line[0] not in {"OPENQASM", "include", "barrier", "qreg"}, instructions)
    )

    ret_gates: List[gates.Gate] = []

    for instruction, args in instructions:
        if instruction and instruction in "hxzst":
            ret_gates.append(parse_trivial_gate(instruction, args))
        elif instruction[0:2] == "rz":
            if instruction[2:6] != "(pi/":
                ##TODO check the  theta phi and  lam
                lam = re.search(r"rz\((\d+\.\d+)\)", instruction).group(1)
                lam = float(lam)
                ret_gates.append(gates.U(theta = 0, phi=0,lam=lam))
                # raise QasmParseException(
                #     f"Can only parse pi/n for n power of 2 angles as rz args, " f"got {instruction}"
                # )
            else:
                phase_pi_frac_den = int(instruction[6:].split(")")[0])
                ret_gates.append(gates.RZ(get_index_arg(args[0]), Fraction(1, phase_pi_frac_den)))
        #support u2 instruction
        elif instruction.startswith("u2"):
            phi,lam = parse_u2_instruction(instruction)
            ret_gates.append(
                ##TODO check the  theta phi and  lam
                gates.U(type='u2',theta=np.pi/2, phi=phi, lam=lam, target_qubit=get_index_arg(args[0]))
            )
        #support p instruction
        elif instruction.startswith("p"):
            theta = parse_p_instruction(instruction)
            ret_gates.append(
                gates.P(theta=theta, target_qubit=get_index_arg(args[0]))
            )

        elif instruction[0:3] == "crz":
            if instruction[3:7] != "(pi/":
                raise QasmParseException(
                    f"Can only parse pi/n for n power of 2 angles as rz args in crz, " f"got {instruction}"
                )
            phase_pi_frac_den = int(instruction[7:].split(")")[0])
            ret_gates.append(
                gates.CRZ(
                    control_qubit=get_index_arg(args[0]),
                    target_qubit=get_index_arg(args[1]),
                    phase=Fraction(1, phase_pi_frac_den),
                )
            )
        elif instruction.startswith('cx'):
            if len(args) != 2:
                raise QasmParseException(f"CNOT instruction requires exactly 2 args, got {len(args)}")
            ret_gates.append(
                gates.CNOT(control_qubit=get_index_arg(args[0]), target_qubit=get_index_arg(args[1]))
            )
        elif not instruction and not args:
            pass
        else:
            raise QasmParseException(f"Instruction {instruction} with args {args} not implemented")

    return ret_gates

import re
import numpy as np

def parse_p_instruction(instruction):
    pattern = r'p\(([^,]+)\)'
    match = re.fullmatch(pattern, instruction)
    assert match is not None, f"指令格式不正确: {instruction}"
    value = match.group(1)
    if value == 'pi':
        value = np.pi
    elif value =='-pi':
        value  = -np.pi
    else:
        value = float(value)
    return value

def parse_u2_instruction(instruction):

    # 匹配括号中的内容
    pattern = r'u2\(([^,]+),([^,]+)\)'
    match = re.search(pattern, instruction)

    if match:
        # 提取括号中的两个值
        value1 = match.group(1).strip()
        value2 = match.group(2).strip()

        # 处理可能的 'pi' 替换为 np.pi
        if value1 == 'pi':
            value1 = np.pi
        else:
            value1 = float(value1)

        if value2 == 'pi':
            value2 = np.pi
        elif value2 == '-pi':
            value2 = -np.pi
        else:
            value2 = float(value2)

        return value1, value2
    else:
        raise ValueError("指令格式不正确")


if __name__ == '__main__':
    test_cases = [
        "p(123)",  # 纯数字
        "p(45.6)",  # 浮点数，前后有字符
        "p(789)",  # 数字后跟字符
        "p(0)",  # 0
        "p(3.14159)",  # 浮点数
        "p(pi)",  # 非数字
        "p(-pi)",  # 非数字
    ]

    for cmd in test_cases:
        result = parse_p_instruction(cmd)
        print(f"命令: '{cmd}' -> 提取结果: {result}")