import re

import pytest
from qiskit import QuantumCircuit
from sympy.solvers.ode.lie_group import lie_heuristics

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
qreg q[2];
cx q[0],q[1];
"""

TEST = """OPENQASM 2.0;
include "qelib1.inc";
qreg q[10];
creg c[10];
creg meas[10];
h q[9];
cp(pi/2) q[9],q[8];
h q[8];
cp(pi/4) q[9],q[7];
cp(pi/2) q[8],q[7];
h q[7];
cp(pi/8) q[9],q[6];
cp(pi/4) q[8],q[6];
cp(pi/2) q[7],q[6];
h q[6];
cp(pi/16) q[9],q[5];
cp(pi/8) q[8],q[5];
cp(pi/4) q[7],q[5];
cp(pi/2) q[6],q[5];
h q[5];
cp(pi/32) q[9],q[4];
cp(pi/16) q[8],q[4];
cp(pi/8) q[7],q[4];
cp(pi/4) q[6],q[4];
cp(pi/2) q[5],q[4];
h q[4];
cp(pi/64) q[9],q[3];
cp(pi/32) q[8],q[3];
cp(pi/16) q[7],q[3];
cp(pi/8) q[6],q[3];
cp(pi/4) q[5],q[3];
cp(pi/2) q[4],q[3];
h q[3];
cp(pi/128) q[9],q[2];
cp(pi/64) q[8],q[2];
cp(pi/32) q[7],q[2];
cp(pi/16) q[6],q[2];
cp(pi/8) q[5],q[2];
cp(pi/4) q[4],q[2];
cp(pi/2) q[3],q[2];
h q[2];
cp(pi/256) q[9],q[1];
cp(pi/128) q[8],q[1];
cp(pi/64) q[7],q[1];
cp(pi/32) q[6],q[1];
cp(pi/16) q[5],q[1];
cp(pi/8) q[4],q[1];
cp(pi/4) q[3],q[1];
cp(pi/2) q[2],q[1];
h q[1];
cp(pi/512) q[9],q[0];
cp(pi/256) q[8],q[0];
cp(pi/128) q[7],q[0];
cp(pi/64) q[6],q[0];
cp(pi/32) q[5],q[0];
cp(pi/16) q[4],q[0];
cp(pi/8) q[3],q[0];
cp(pi/4) q[2],q[0];
cp(pi/2) q[1],q[0];
h q[0];
swap q[0],q[9];
swap q[1],q[8];
swap q[2],q[7];
swap q[3],q[6];
swap q[4],q[5];
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
    def test_text_from_gates_circuit(self,qasmstr=None):
        if not qasmstr:
            qasmstr = TEST2

        clifford_plus_t = GatesCircuit.from_qasm(qasmstr).to_clifford_plus_t()
        #print(clifford_plus_t)
        instructions: str = LSInstructionsFromGatesGenerator.text_from_gates_circuit(
                clifford_plus_t
            )

        print('instructions=\n',instructions)
        return instructions
        # instructions: str = repr(
        #     LSInstructionsFromGatesGenerator.text_from_gates_circuit(
        #         GatesCircuit.from_qasm(QFT_CIRCUIT).to_clifford_plus_t()
        #     )
        # )
        #save_string_to_file('d:/ls.txt', instructions, mode='w', encoding='utf-8')
        # snapshot.assert_match(instructions, "circuit.txt")

    def test_text_from_gates_circuit_fail_non_clifford_plus_t(self):
        circuit = GatesCircuit.from_qasm(QFT_CIRCUIT)
        # with pytest.raises(Exception):
        output = LSInstructionsFromGatesGenerator.text_from_gates_circuit(circuit)
        print(output)

    def to_instructions(self,qasmstr=None):
        if not qasmstr:
            qasmstr = TEST2

        clifford_plus_t = GatesCircuit.from_qasm(qasmstr).to_clifford_plus_t()
        #print(clifford_plus_t)
        instructions: str = LSInstructionsFromGatesGenerator.text_from_gates_circuit(
                clifford_plus_t
            )

        #print('instructions=\n',instructions)
        return instructions


    def test_convert_all_file(self):
        input_directory = 'd:/sync/mqtbench/ori'
        output_directory = 'd:/sync/mqtbench/out'
        for filename in os.listdir(input_directory):
            input_file_path = os.path.join(input_directory, filename)
            content = ''
            if os.path.isfile(input_file_path):
                with open(input_file_path, 'r') as infile:
                    lines = infile.readlines()  # Read all lines from the file
                    #print(lines)
                    for line in lines:
                        if line.startswith('creg') or line.startswith(r'//') or line.startswith('barrier') or line.startswith('measure'):
                            continue
                        #  'cp' to 'crz'
                        line = line.strip().replace('cp', 'crz')+'\n'
                        line = line.strip().replace('cnot', 'cx')+'\n'

                        #SWAP(A,B)=CNOT(A,B)→CNOT(B,A)→CNOT(A,B)
                        if line.startswith('swap'):
                            match1 =re.match(r'swap q\[(\d+)\],q\[(\d+)\];', line)
                            qa = match1.group(1)
                            qb = match1.group(2)
                            line = f'cx q[{qa}],q[{qb}]\ncx [{qb}],[{qa}]\ncx [{qa}],[{qb}];\n'
                        if len(line)>0:
                            content += line
                #print(content)
                content = self.to_instructions(qasmstr=content)
                # Write the processed lines to a new file in the output directory
                output_file_path = os.path.join(output_directory, f"processed_{filename}")
                with open(output_file_path, 'w') as outfile:
                    outfile.writelines(content)



    # def test_convert_to_basic_gates(self,qasm:str=''):
    #     qasm =TEST
    #     basic_gates = ['s','x','cx','rz','crz','t','h']
    #     new_circuit = QuantumCircuit.from_qasm_str(qasm)
    #     c = new_circuit.decompose(gates_to_decompose = basic_gates)
    #     print(c)
    #     #convert circuit to qasm file
    #     qasm = c.qasm()
    #     print(qasm)

