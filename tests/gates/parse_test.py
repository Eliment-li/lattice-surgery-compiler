from lsqecc.gates import gates, parse


def test_parse_gates_circuit_parses_p_with_fractional_pi_angle():
    qasm = (
        'OPENQASM 3.0;\n'
        'include "stdgates.inc";\n'
        'qubit[20] q;\n'
        'p(pi/8) q[19];\n'
    )

    assert parse.parse_gates_circuit(qasm) == [
        gates.P(target_qubit=19, theta=parse.np.pi / 8),
    ]


def test_parse_gates_circuit_parses_u1_with_negative_fractional_pi_angle():
    qasm = (
        'OPENQASM 3.0;\n'
        'include "stdgates.inc";\n'
        'qubit[5] q;\n'
        'u1(-pi/8) q[3];\n'
    )

    assert parse.parse_gates_circuit(qasm) == [
        gates.U(type='u2', theta=-parse.np.pi / 8, phi=0, lam=0, target_qubit=3),
    ]


def test_parse_gates_circuit_parses_u2_with_fractional_pi_angles():
    qasm = (
        'OPENQASM 3.0;\n'
        'include "stdgates.inc";\n'
        'qubit[5] q;\n'
        'u2(-pi/8, pi/8) q[4];\n'
    )

    assert parse.parse_gates_circuit(qasm) == [
        gates.U(type='u2', theta=parse.np.pi / 2, phi=-parse.np.pi / 8, lam=parse.np.pi / 8, target_qubit=4),
    ]


def test_parse_gates_circuit_parses_u2_with_spaces_inside_parameter_list():
    qasm = (
        'OPENQASM 3.0;\n'
        'include "stdgates.inc";\n'
        'qubit[10] q;\n'
        'u2(pi/8, -pi) q[9];\n'
    )

    assert parse.parse_gates_circuit(qasm) == [
        gates.U(type='u2', theta=parse.np.pi / 2, phi=parse.np.pi / 8, lam=-parse.np.pi, target_qubit=9),
    ]


def test_parse_gates_circuit_parses_u3_with_fractional_pi_angles():
    qasm = (
        'OPENQASM 3.0;\n'
        'include "stdgates.inc";\n'
        'qubit[28] q;\n'
        'u3(pi, -pi, -pi/8) q[27];\n'
    )

    assert parse.parse_gates_circuit(qasm) == [
        gates.U(type='u3', theta=parse.np.pi, phi=-parse.np.pi, lam=-parse.np.pi / 8, target_qubit=27),
    ]


def test_split_instruction_and_args_handles_spaces_after_commas():
    instruction, args = parse.split_instruciton_and_args("cx q[1], q[2]")

    assert instruction == "cx"
    assert args == ["q[1]", "q[2]"]


def test_parse_gates_circuit_ignores_qasm3_declarations():
    qasm = (
        'OPENQASM 3.0;\n'
        'include "stdgates.inc";\n'
        'bit[29] meas;\n'
        'qubit[29] q;\n'
        'cx q[1], q[2];\n'
    )

    assert parse.parse_gates_circuit(qasm) == [
        gates.CNOT(control_qubit=1, target_qubit=2),
    ]