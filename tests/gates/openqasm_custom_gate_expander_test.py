import pytest

from lsqecc.gates.openqasm_custom_gate_expander import expand_custom_gates


def test_expand_simple_custom_gate():
    qasm = """OPENQASM 3.0;
include \"stdgates.inc\";
gate MAJ a, b, c {
  cx a, b;
  cx a, c;
  ccx c, b, a;
}
qubit[3] q;
MAJ q[0], q[1], q[2];
"""

    expanded = expand_custom_gates(qasm)

    assert "gate MAJ" not in expanded
    assert "MAJ q[0], q[1], q[2];" not in expanded
    assert "cx q[0], q[1];" in expanded
    assert "cx q[0], q[2];" in expanded
    assert "ccx q[2], q[1], q[0];" in expanded


def test_expand_parameterized_custom_gate():
    qasm = """OPENQASM 3.0;
include \"stdgates.inc\";
gate phase_turn(theta) target {
  p(theta) target;
  rz(theta) target;
}
qubit[1] q;
phase_turn(pi/8) q[0];
"""

    expanded = expand_custom_gates(qasm)

    assert "phase_turn(pi/8) q[0];" not in expanded
    assert "p(pi/8) q[0];" in expanded
    assert "rz(pi/8) q[0];" in expanded


def test_expand_nested_parameterized_custom_gates():
    qasm = """OPENQASM 3.0;
include \"stdgates.inc\";
gate inner(theta) control, target {
  crz(theta) control, target;
}
gate outer(theta) control, target {
  h target;
  inner(theta) control, target;
}
qubit[2] q;
outer(pi/16) q[0], q[1];
"""

    expanded = expand_custom_gates(qasm)

    assert "gate inner" not in expanded
    assert "gate outer" not in expanded
    assert "outer(pi/16) q[0], q[1];" not in expanded
    assert "inner(pi/16) q[0], q[1];" not in expanded
    assert "h q[1];" in expanded
    assert "crz(pi/16) q[0], q[1];" in expanded


def test_expand_custom_gates_rejects_wrong_argument_count():
    qasm = """OPENQASM 3.0;
include \"stdgates.inc\";
gate pair(a, b) control, target {
  cx control, target;
}
qubit[2] q;
pair(pi/4) q[0], q[1];
"""

    with pytest.raises(ValueError, match="expects 2 expression arguments but got 1"):
        expand_custom_gates(qasm)