import re

import pytest
from qiskit import QuantumCircuit
from sympy.solvers.ode.lie_group import lie_heuristics

from lsqecc.gates.gates_circuit import GatesCircuit
from lsqecc.gates.openqasm_custom_gate_expander import expand_custom_gates
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
#get qubit number and bit number from qasmstr

def extract_register_declaration(input_code, register_kind):
    '''
    OpenQASM 2.0 使用 qreg/creg，例如 qreg q[2];、creg meas[2];
    OpenQASM 3.0 使用 qubit/bit，例如 qubit[29] q;、bit[29] meas;
    当检测到 OPENQASM 3.0; 时，会从 qubit 和 bit 声明中提取寄存器大小，
    '''
    is_openqasm3 = "OPENQASM 3.0;" in input_code
    version_label = "OpenQASM 3.0" if is_openqasm3 else "OpenQASM 2.0"
    register_specs = {
        True: {
            "quantum": {
                "pattern": r"^\s*qubit\[(\d+)\]\s+(\w+)\s*;\s*$",
                "size_first": True,
                "keyword": "qubit",
                "declaration": lambda total: f"qubit[{total}] q;\n",
            },
            "classical": {
                "pattern": r"^\s*bit\[(\d+)\]\s+(\w+)\s*;\s*$",
                "size_first": True,
                "keyword": "bit",
                "declaration": lambda total: f"bit[{total}] meas;\n",
            },
        },
        False: {
            "quantum": {
                "pattern": r"^\s*qreg\s+(\w+)\[(\d+)\]\s*;\s*$",
                "size_first": False,
                "keyword": "qreg",
                "declaration": lambda total: f"qreg q[{total}];\n",
            },
            "classical": {
                "pattern": r"^\s*creg\s+(\w+)\[(\d+)\]\s*;\s*$",
                "size_first": False,
                "keyword": "creg",
                "declaration": lambda total: f"creg meas[{total}];\n",
            },
        },
    }

    if register_kind not in {"quantum", "classical"}:
        raise ValueError(f"Unsupported register kind: {register_kind}")

    register_spec = register_specs[is_openqasm3][register_kind]
    declaration_pattern = re.compile(register_spec["pattern"], re.MULTILINE)

    if register_spec["size_first"]:
        matches = [
            (name, int(size))
            for size, name in declaration_pattern.findall(input_code)
        ]
    else:
        matches = [
            (name, int(size))
            for name, size in declaration_pattern.findall(input_code)
        ]

    if not matches:
        preview = "\n".join(input_code.splitlines()[:20])
        raise ValueError(
            f"{version_label} input is missing {register_spec['keyword']} declarations,\n{preview}"
        )

    return declaration_pattern, matches, register_spec["declaration"]



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

    def merge_qreg_file(self,file_path):
        """兼容 OpenQASM 2.0/3.0 的寄存器合并。

        OpenQASM 2.0 使用 qreg/creg，例如 qreg q[2];、creg meas[2];
        OpenQASM 3.0 使用 qubit/bit，例如 qubit[29] q;、bit[29] meas;
        当检测到 OPENQASM 3.0; 时，会从 qubit 和 bit 声明中提取寄存器大小，
        分别合并为单个 q 和 meas，并同步重映射后续索引访问。
        """
        with open(file_path, 'r', encoding='utf-8') as file:
            input_code = file.read()

        quantum_decl_pattern, quantum_matches, quantum_decl = extract_register_declaration(
            input_code, "quantum"
        )
        classical_decl_pattern, classical_matches, classical_decl =extract_register_declaration(
            input_code, "classical"
        )

        if len(quantum_matches) <= 1 and len(classical_matches) <= 1:
            print("only got one register no need to merge。")
            return

        def build_register_mapping(matches, merged_name):
            total_size = 0
            register_mapping = {}

            for name, size in matches:
                register_mapping[name] = (merged_name, total_size, size)
                total_size += size

            return register_mapping, total_size

        quantum_mapping, total_qubits = build_register_mapping(quantum_matches, "q")
        classical_mapping, total_bits = build_register_mapping(classical_matches, "meas")
        register_mapping = {**quantum_mapping, **classical_mapping}

        def replace_indices(match):
            var_name = match.group(1)
            index = int(match.group(2))
            mapped_register = register_mapping.get(var_name)

            if mapped_register is None:
                return match.group(0)

            merged_name, start_idx, register_size = mapped_register
            if index >= register_size:
                return match.group(0)

            return f"{merged_name}[{start_idx + index}]"

        updated_lines = []
        quantum_decl_written = False
        classical_decl_written = False

        for line in input_code.splitlines(keepends=True):
            if quantum_decl_pattern.match(line):
                if not quantum_decl_written and total_qubits > 0:
                    updated_lines.append(quantum_decl(total_qubits))
                    quantum_decl_written = True
                continue

            if classical_decl_pattern.match(line):
                if not classical_decl_written and total_bits > 0:
                    updated_lines.append(classical_decl(total_bits))
                    classical_decl_written = True
                continue

            updated_lines.append(re.sub(r"\b(\w+)\[(\d+)\]", replace_indices, line))

        updated_code = "".join(updated_lines)
        updated_code = re.sub(r"\n\s*\n", "\n", updated_code)

        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(updated_code)

    ## Main function ##
    def test_convert_all_file(self):
        input_directory = 'd:/mqtbench/ori1'
        output_directory = 'd:/mqtbench/ls_inst'

        for filename in os.listdir(input_directory):
            print(f"Processing file: {filename}")
            input_file_path = os.path.join(input_directory, filename)
            self.merge_qreg_file(input_file_path)
            content = ''
            if os.path.isfile(input_file_path):
                with open(input_file_path, 'r') as infile:

                    expanded_code = expand_custom_gates(infile.read())
                    lines = expanded_code.splitlines(keepends=True)
                    #print(lines)
                    prefixes = ('OPENQASM', 'include', r'//', 'barrier', 'measure')

                    #pre process
                    for i in range(len(lines)):
                        line = lines[i]
                        #if line.startswith('creg') or line.startswith(r'//') or line.startswith('barrier') or line.startswith('measure'):
                        if not line.strip() or line.startswith(prefixes):
                            continue
                        #  'cp' to 'crz'
                        line = line.strip().replace('cp', 'crz')+'\n'
                        line = line.strip().replace('cnot', 'cx')+'\n'
                        #see https://openqasm.com/language/standard_library.html
                        line = line.strip().replace('tdg', 'p(-pi/4)')+'\n'

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
                            line = f'h q[{q}];\nrz({phase}) q[{q}];\nh q[{q}];\n'
                        if len(line)>0:
                            content += line

                #print(content)
                content = self.test_to_instructions(qasmstr=content)
                # Write the processed lines to a new file in the output directory
                output_file_path = os.path.join(output_directory, f"LSI_{filename[:-4]}lsi")
                with open(output_file_path, 'w') as outfile:
                    outfile.writelines(content)
                    
if __name__ == "__main__":
    test_instance = TestLSInstructionsFromGatesGenerator()
    test_instance.test_convert_all_file()
