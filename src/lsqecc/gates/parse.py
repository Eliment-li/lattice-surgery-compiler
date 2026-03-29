"""
Helper methods to parse qasm circuits.
"""

from fractions import Fraction
from typing import List, Sequence, Tuple
from lsqecc.gates import gates
from lsqecc.utils import QasmParseException


def test_get_index_arg():
    str= "cx q[1] q[2]"
    print(get_index_arg(str))

def get_index_arg(qreg_arg: str) -> int:
    return int(qreg_arg.split("[")[1].split("]")[0])


def split_instruciton_and_args(line: str) -> Tuple[str, List[str]]:
    line = line.strip()
    if not line:
        return line, []
    paren_depth = 0
    split_index = -1
    for index, char in enumerate(line):
        if char == "(":
            paren_depth += 1
        elif char == ")":
            paren_depth = max(0, paren_depth - 1)
        elif char.isspace() and paren_depth == 0:
            split_index = index
            break

    if split_index == -1:
        return line, []

    instruction = line[:split_index]
    args = line[split_index + 1 :].strip()
    return instruction, [arg.strip() for arg in args.split(",")]


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

    # qregs = list(filter(lambda line: line[0] == "qreg", instructions))
    # if len(qregs) != 1:
    #     raise QasmParseException(f"Need exactly one qreg, got {len(qregs)}")
    
    #没有实际作用，只是确认至少有一条分配量子寄存器的指令
    qregs = list(filter(lambda line: line[0] == "qreg", instructions))
    if len(qregs) == 1:
        qreg_name, qreg_args = qregs[0]
        num_qubits = get_index_arg(qreg_args[0])
    elif len(qregs) == 0:
        qubit_decls = list(filter(lambda line: line[0].startswith("qubit["), instructions))
        if len(qubit_decls) != 1:
            raise QasmParseException(
                f"Need exactly one qubit declaration, got {len(qubit_decls)}"
            )
        qubit_decl, _ = qubit_decls[0]
        num_qubits = get_index_arg(qubit_decl)
    else:
        raise QasmParseException(f"Need exactly one qreg, got {len(qregs)}")
        
    instructions = list(
        filter(
            lambda line: line[0] not in {"OPENQASM", "include", "barrier", "qreg","meas"}
            and not line[0].startswith("qubit[")
            and not line[0].startswith("meas[")
            and not line[0].startswith("bit["),

            instructions,
        )
    )

    ret_gates: List[gates.Gate] = []

    for instruction, args in instructions:
        if instruction and instruction in "hxzst":
            ret_gates.append(parse_trivial_gate(instruction, args))
        elif instruction[0:2] == "rz":
            if instruction[2:6] != "(pi/":
                ##TODO check the  theta phi and  lam
                lam = parse_phrase(instruction)
                ret_gates.append(gates.U(theta = 0, phi=0,lam=lam,target_qubit=get_index_arg(args[0])))
                # raise QasmParseException(
                #     f"Can only parse pi/n for n power of 2 angles as rz args, " f"got {instruction}"
                # )
            else:
                phase_pi_frac_den = int(instruction[6:].split(")")[0])
                ret_gates.append(gates.RZ(get_index_arg(args[0]), Fraction(1, phase_pi_frac_den)))
        #support u3 instruction
        elif instruction.startswith("u3"):
            theta, phi, lam = parse_u3_instruction(instruction)
            ret_gates.append(
                gates.U(type='u3', theta=theta, phi=phi, lam=lam, target_qubit=get_index_arg(args[0]))
            )
        #support u2 instruction
        elif instruction.startswith("u2"):
            phi,lam = parse_u2_instruction(instruction)
            ret_gates.append(
                ##TODO check the  theta phi and  lam
                gates.U(type='u2',theta=np.pi/2, phi=phi, lam=lam, target_qubit=get_index_arg(args[0]))
            )
        #support u1 instruction
        elif instruction.startswith("u1"):
            theta = parse_u1_instruction(instruction)
            ret_gates.append(
                ##TODO check the  theta phi and  lam
                gates.U(type='u2',theta=theta, phi=0, lam=0, target_qubit=get_index_arg(args[0]))
            )
        #support p instruction
        elif instruction.startswith("p"):
            theta = parse_p_instruction(instruction)
            ret_gates.append(
                gates.P(theta=theta, target_qubit=get_index_arg(args[0]))
            )
        elif instruction.startswith('rccx'):
            c0 = get_index_arg(args[0])
            c1 = get_index_arg(args[1])
            t2 = get_index_arg(args[2])
            ret_gates.append(
                gates.RCCX(control_qubit_0=c0, control_qubit_1=c1,target_qubit=t2)
            )
        elif instruction[0:3] == "crz":
            if instruction[3:7] != "(pi/":
                #-pi/n
                lam = parse_phrase(instruction)
                ret_gates.append(gates.U(theta=0, phi=0, lam=lam))

                # raise QasmParseException(
                #     f"Can only parse pi/n for n power of 2 angles as rz args in crz, " f"got {instruction}"
                # )

        elif instruction.startswith('ccx'):
            ret_gates.append(
                gates.CCX(
                    control_qubit_0=get_index_arg(args[0]),
                    control_qubit_1=get_index_arg(args[1]),
                    target_qubit=get_index_arg(args[2]),
                )
            )
        elif instruction.startswith('rx'):
            theta =  parse_phrase(instruction)
            ret_gates.append(gates.U(theta =theta,phi=-np.pi/2, lam=np.pi/2, target_qubit=get_index_arg(args[0]), type='rx'))
        elif instruction.startswith('cx'):
            if len(args) != 2:
                raise QasmParseException(f"CNOT instruction requires exactly 2 args, got {len(args)}")
            ret_gates.append(
                gates.CNOT(control_qubit=get_index_arg(args[0]), target_qubit=get_index_arg(args[1]))
            )
        elif instruction.startswith('cz'):
            if len(args) != 2:
                raise QasmParseException(f"CZ instruction requires exactly 2 args, got {len(args)}")
            ret_gates.append(
                gates.CZ(control_qubit=get_index_arg(args[0]), target_qubit=get_index_arg(args[1]))
            )
        elif not instruction and not args:
            pass
        else:
            print(instruction, args)
            raise QasmParseException(f"Instruction {instruction} with args {args} not implemented")

    return ret_gates

import re
import numpy as np

def test_parse_phrase():
    test_cases = [
        "str1(pi)",
        "str1(-pi)",
        "str1(pi/2)",
        "str1(pi/3)",
        "str1(5)",
        "u(-3.14)",
        "p(pi/8)"
    ]
    for test in test_cases:
            result = parse_phrase(test)
            print(result)

def parse_phrase(instruction):
    # 使用正则表达式匹配括号内的内容
    match = re.search(r'\((.*?)\)', instruction)
    if not match:
        raise ValueError("输入字符串中没有找到括号")

    return parse_angle_expression(match.group(1))


def parse_angle_expression(expression: str):
    expr = expression.replace(' ', '')

    # 处理 pi 的表达式
    pi_pattern = re.compile(r'^([+-]?[\d\.]*)\*?pi(?:/([+-]?[\d\.]+))?$')
    m = pi_pattern.match(expr)
    if m:
        m_coeff = m.group(1)
        n_denom = m.group(2)
        # 处理 m
        if m_coeff == '' or m_coeff == '+':
            m_val = 1.0
        elif m_coeff == '-':
            m_val = -1.0
        else:
            m_val = float(m_coeff)
        # 处理 n
        if n_denom:
            n_val = float(n_denom)
            return m_val * np.pi / n_val
        else:
            return m_val * np.pi

    # 纯数字
    try:
        return float(expr)
    except ValueError:
        raise ValueError(f"invalid expr: {expr}")


def parse_p_instruction(instruction):
    pattern = r'p\(([^,]+)\)'
    match = re.fullmatch(pattern, instruction)
    assert match is not None, f"指令格式不正确: {instruction}"
    return parse_angle_expression(match.group(1))


def parse_u1_instruction(instruction):
    pattern = r'u1\(([^)]+)\)'
    match = re.fullmatch(pattern, instruction)
    if match:
        return parse_angle_expression(match.group(1))
    raise ValueError(f"指令格式不正确: {instruction}")

def parse_u2_instruction(instruction):
    # 匹配括号中的内容
    pattern = r'u2\(([^,]+),([^,]+)\)'
    match = re.fullmatch(pattern, instruction)

    if match:
        return parse_angle_expression(match.group(1)), parse_angle_expression(match.group(2))
    else:
        raise ValueError(f"指令格式不正确{instruction}")


def parse_u3_instruction(instruction):
    pattern = r'u3\(([^,]+),([^,]+),([^,]+)\)'
    match = re.fullmatch(pattern, instruction)

    if match:
        return (
            parse_angle_expression(match.group(1)),
            parse_angle_expression(match.group(2)),
            parse_angle_expression(match.group(3)),
        )
    raise ValueError(f"指令格式不正确: {instruction}")


