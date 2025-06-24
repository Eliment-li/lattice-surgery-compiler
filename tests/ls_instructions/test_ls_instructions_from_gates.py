import re

import pytest
from qiskit import QuantumCircuit
from sympy.solvers.ode.lie_group import lie_heuristics

from lsqecc.gates.gates_circuit import GatesCircuit
from lsqecc.ls_instructions.ls_instructions_from_gates import (
    LSInstructionsFromGatesGenerator,
)


TEST = """OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
u2(2.0,-pi) q[0];
rz(pi/2) q[0];
rz(pi/4) q[0];
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
            qasmstr = TEST


        gates_circuit = GatesCircuit.from_qasm(qasmstr)
        clifford_plus_t =gates_circuit.to_clifford_plus_t()
        #print(clifford_plus_t)
        instructions: str = LSInstructionsFromGatesGenerator.text_from_gates_circuit(
                clifford_plus_t
            )

        #print('instructions=\n',instructions)
        return instructions
        # instructions: str = repr(
        #     LSInstructionsFromGatesGenerator.text_from_gates_circuit(
        #         GatesCircuit.from_qasm(QFT_CIRCUIT).to_clifford_plus_t()
        #     )
        # )
        #save_string_to_file('d:/ls.txt', instructions, mode='w', encoding='utf-8')
        # snapshot.assert_match(instructions, "circuit.txt")

    def test_text_from_gates_circuit_fail_non_clifford_plus_t(self):
        circuit = GatesCircuit.from_qasm(TEST)
        # with pytest.raises(Exception):
        output = LSInstructionsFromGatesGenerator.text_from_gates_circuit(circuit)
        print(output)

    def test_to_instructions(self,qasmstr=None):
        clifford_plus_t = GatesCircuit.from_qasm(qasmstr).to_clifford_plus_t()
        instructions: str = LSInstructionsFromGatesGenerator.text_from_gates_circuit(
                clifford_plus_t
            )

        print('instructions=\n',instructions)
        return instructions

    def test_convert_all_file(self):
        input_directory = 'd:/sync/mqtbench/ori'
        output_directory = 'd:/sync/mqtbench/ls_inst'
        for filename in os.listdir(input_directory):
            input_file_path = os.path.join(input_directory, filename)
            content = ''
            if os.path.isfile(input_file_path):
                with open(input_file_path, 'r') as infile:

                    lines = infile.readlines()  # Read all lines from the file
                    #print(lines)
                    prefixes = ('creg',r'//', 'barrier', 'measure','p')

                    #pre process
                    for i in range(5,len( lines)):
                        line = lines[i]
                        #if line.startswith('creg') or line.startswith(r'//') or line.startswith('barrier') or line.startswith('measure'):
                        if line.startswith(prefixes):
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
                        if line.startswith('ry'):
                            match1 = re.match(r'ry\(([^)]+)\) q\[(\d+)\];', line)
                            phase = match1.group(1)
                            q = match1.group(2)
                            line = f'h q[{q}];\nrz({phase}) q[{q}];\nh q[{q}];'
                        if len(line)>0:
                            content += line

                print(content)
                content = self.test_to_instructions(qasmstr=content)
                # Write the processed lines to a new file in the output directory
                output_file_path = os.path.join(output_directory, f"LSI_{filename[:-4]}lsi")
                with open(output_file_path, 'w') as outfile:
                    outfile.writelines(content)
