import pytest

from lsqecc.gates.gates_circuit import GatesCircuit
from lsqecc.ls_instructions.ls_instructions_from_gates import (
    LSInstructionsFromGatesGenerator,
)

QFT_CIRCUIT = """OPENQASM 2.0;
include "qelib1.inc";
qreg q0[4];
h q0[3];
barrier q0[0],q0[1],q0[2],q0[3];
crz(pi/2) q0[2],q0[3];
h q0[2];
barrier q0[0],q0[1],q0[2],q0[3];
crz(pi/4) q0[1],q0[3];
crz(pi/2) q0[1],q0[2];
h q0[1];
barrier q0[0],q0[1],q0[2],q0[3];
crz(pi/8) q0[0],q0[3];
crz(pi/4) q0[0],q0[2];
crz(pi/2) q0[0],q0[1];
h q0[0];
barrier q0[0],q0[1],q0[2],q0[3];
"""

TEST2 = """OPENQASM 2.0;
include "qelib1.inc";
qreg q[3];
h q[0];
crz(pi/2) q[1],q[0];
crz(pi/4) q[2],q[0];
h q[1];
crz(pi/2) q[2],q[1];
h q[2];
"""

TEST = """OPENQASM 2.0;
include "qelib1.inc";
qreg q[3];
h q[0];
crz(pi/2) q[1],q[0];
crz(pi/4) q[2],q[0];
h q[1];
crz(pi/2) q[2],q[1];
h q[2];
"""

import os
def save_string_to_file(filename, content, mode='w', encoding='utf-8', line_ending=None):
    if line_ending == 'windows':
        content = content.replace('\n', '\r\n')
    elif line_ending == 'unix':
        content = content.replace('\r\n', '\n')

    try:
        with open(filename, mode, encoding=encoding, newline='') as file:
            file.write(content)
        print(f"内容已成功保存到文件: {filename}")
    except IOError as e:
        print(f"保存文件时出错: {e}")


class TestLSInstructionsFromGatesGenerator:
    def test_text_from_gates_circuit(self):
        instructions: str = LSInstructionsFromGatesGenerator.text_from_gates_circuit(
                GatesCircuit.from_qasm(TEST).to_clifford_plus_t()
            )
        print('instructions=\n',instructions)
        # instructions: str = repr(
        #     LSInstructionsFromGatesGenerator.text_from_gates_circuit(
        #         GatesCircuit.from_qasm(QFT_CIRCUIT).to_clifford_plus_t()
        #     )
        # )
        save_string_to_file('d:/ls.txt', instructions, mode='w', encoding='utf-8')
        # snapshot.assert_match(instructions, "circuit.txt")

    def test_text_from_gates_circuit_fail_non_clifford_plus_t(self):
        circuit = GatesCircuit.from_qasm(QFT_CIRCUIT)
        with pytest.raises(Exception):
            LSInstructionsFromGatesGenerator.text_from_gates_circuit(circuit)

