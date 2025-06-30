import math
from fractions import Fraction
from typing import Sequence

from setuptools.unicode_utils import decompose

from lsqecc.gates import gates
from lsqecc.gates.compress_rotation_approximations import partition_gate_sequence
from lsqecc.gates.pi_over_2_to_the_n_rz_gate_approximations import (
    get_pi_over_2_to_the_n_rz_gate,
)
from lsqecc.pauli_rotations.rotation import PauliOperator
from lsqecc.utils import is_power_of_two
import pennylane as qml
import numpy as np
from itertools import chain

def handle_sk_decompose_ops(ops:list,compress_rotations:bool,target_qubit:int) -> Sequence["gates.Gate"]:
    Tdg = 'Adjoint(T(0))'
    approx_gates = []
    for o in ops:
        if isinstance(o, qml.ops.T):
            approx_gates.append(
                gates.PauliRotations(
                    target_qubit=target_qubit, phase=Fraction(1, 4), axis=PauliOperator.Z
                )
                if compress_rotations
                else gates.T(target_qubit)
            )
        elif isinstance(o, qml.ops.H):
            approx_gates.append(gates.H(target_qubit))
        elif isinstance(o, qml.ops.S):
            approx_gates.append(
                gates.PauliRotations(
                    target_qubit=target_qubit, phase=Fraction(1, 2), axis=PauliOperator.Z
                )
                if compress_rotations
                else gates.S(target_qubit)
            )
        elif str(o) == Tdg:
            # T dagger = Z-S-T = hxh-s-t
            # approx_gates.append(gates.H(target_qubit))
            # approx_gates.append(gates.X(target_qubit))
            # approx_gates.append(gates.H(target_qubit))
            # # s
            # approx_gates.append(
            #     gates.PauliRotations(
            #         target_qubit=target_qubit, phase=Fraction(1, 2), axis=PauliOperator.Z
            #     )
            #     if compress_rotations
            #     else gates.S(target_qubit)
            # )  # t
            # approx_gates.append(
            #     gates.PauliRotations(
            #         target_qubit=target_qubit, phase=Fraction(1, 4), axis=PauliOperator.Z
            #     )
            #     if compress_rotations
            #     else gates.T(target_qubit)
            # )
           approx_gates += Tdag_to_T(target_qubit,compress_rotations)

        elif str(o) == 'GlobalPhase(array(0.), wires=[])' or isinstance(o, qml.ops.GlobalPhase):
            continue
        else:
            raise Exception(f"Cannot decompose gate: {o}")
    return approx_gates

def approximate_p_gate(p_gate:"gates.P",compress_rotations)-> Sequence["gates.Gate"]:
    #PhaseShift is  the P gate in qasm and qiskit, it  is equivalent to RZ up to a phase factor.
    op = qml.PhaseShift(p_gate.theta,wires=0)
    ops = qml.ops.sk_decomposition(op, epsilon=1e-3)
    approx_gates = handle_sk_decompose_ops(ops, compress_rotations, p_gate.target_qubit)
    return approx_gates

def approximate_u_gate(u_gate:"gates.U",compress_rotations)-> Sequence["gates.Gate"]:
    op = qml.U3(u_gate.theta,u_gate.phi,u_gate.lam, wires=0)
    ops = qml.ops.sk_decomposition(op, epsilon=1e-3)
    approx_gates = handle_sk_decompose_ops(ops, compress_rotations, u_gate.target_qubit)
    return approx_gates



def decompose_rccx_gate(u_gate:"gates.RCCX",compress_rotations=False)-> Sequence["gates.Gate"]:
    '''
    The Margolus gate can be decomposed using 3 CNOT gates
    Ry(pi/4) q[2]
    CNOT q[1],q[2]
    Ry(pi/4) q[2]
    CNOT q[0],q[2]
    Ry(-pi/4) q[2]
    CNOT q[1],q[2]
    Ry(-pi/4) q[2]
    '''
    approx_gates= []

    #Ry(-pi/4) q[2] ry=hrzh
    approx_gates.append(gates.H(u_gate.target_qubit))
    rz_gate=gates.RZ(target_qubit=u_gate.target_qubit, phase=np.pi/4)
    approx_gates+=(approximate_rz_from_no_pi(rz_gate))
    approx_gates.append(gates.H(u_gate.target_qubit))
    #CNOT q[1],q[2]
    approx_gates.append(gates.CNOT(control_qubit=u_gate.control_qubit_1, target_qubit=u_gate.target_qubit))
    #Ry(-pi/4) q[2] ry=hrzh
    approx_gates.append(gates.H(u_gate.target_qubit))
    rz_gate = gates.RZ(target_qubit=u_gate.target_qubit, phase=np.pi/4)
    approx_gates += (approximate_rz_from_no_pi(rz_gate))
    approx_gates.append(gates.H(u_gate.target_qubit))
    #CNOT q[0],q[2]
    approx_gates.append(gates.CNOT(control_qubit=u_gate.control_qubit_0, target_qubit=u_gate.target_qubit))
    #Ry(-pi/4) q[2]
    approx_gates.append(gates.H(u_gate.target_qubit))
    rz_gate = gates.RZ(target_qubit=u_gate.target_qubit, phase=-np.pi/4)
    approx_gates += (approximate_rz_from_no_pi(rz_gate))
    approx_gates.append(gates.H(u_gate.target_qubit))
    # CNOT q[1],q[2]
    approx_gates.append(gates.CNOT(control_qubit=u_gate.control_qubit_1, target_qubit=u_gate.target_qubit))
    # Ry(-pi/4) q[2]
    approx_gates.append(gates.H(u_gate.target_qubit))
    rz_gate = gates.RZ(target_qubit=u_gate.target_qubit, phase=-np.pi/4)
    approx_gates += (approximate_rz_from_no_pi(rz_gate))
    approx_gates.append(gates.H(u_gate.target_qubit))
    return  approx_gates

# approximate the gates with  phase not in pi/2^n,
def approximate_rz_from_no_pi(rz_gate: "gates.RZ",compress_rotations=False)-> Sequence["gates.Gate"]:


    #op = qml.RY(np.pi / 3, wires=0)
    op = qml.RZ(rz_gate.phase, wires=0)
    # Get the gate decomposition in ['T', 'T*', 'H']
    ops = qml.ops.sk_decomposition(op,epsilon=1e-3)
    approx_gates = handle_sk_decompose_ops(ops,compress_rotations,rz_gate.target_qubit)
    return approx_gates



def approximate_rz(rz_gate: "gates.RZ", compress_rotations: bool = False) -> Sequence["gates.Gate"]:
    """Get the Clifford+T approximation of a an rz gate.
    Currently ony supports arguments of the form pi/2^n.
    """
    if not hasattr(rz_gate.phase,"denominator") :
        return approximate_rz_from_no_pi(rz_gate,compress_rotations)

    if not (is_power_of_two(rz_gate.phase.denominator) and rz_gate.phase.numerator == 1):
        raise Exception(f"Can only approximate pi/2^n phase gates, got rz(pi*{rz_gate.phase})")

    denominator_exponent = int(math.log2(rz_gate.phase.denominator))

    approximation_gates = get_pi_over_2_to_the_n_rz_gate[denominator_exponent]
    if compress_rotations:
        approximation_gates = partition_gate_sequence(approximation_gates)
    approx_gates = []

    for gate in approximation_gates:
        if gate == "S":
            approx_gates.append(
                gates.PauliRotations(
                    target_qubit=rz_gate.target_qubit, phase=Fraction(1, 2), axis=PauliOperator.Z
                )
                if compress_rotations
                else gates.S(rz_gate.target_qubit)
            )
        elif gate == "T":
            approx_gates.append(
                gates.PauliRotations(
                    target_qubit=rz_gate.target_qubit, phase=Fraction(1, 4), axis=PauliOperator.Z
                )
                if compress_rotations
                else gates.T(rz_gate.target_qubit)
            )
        elif gate == "X":
            approx_gates.append(gates.X(rz_gate.target_qubit))
        elif gate == "H":
            approx_gates.append(gates.H(rz_gate.target_qubit))
        elif len(gate) > 1:
            approx_gates.append(from_gate_string(rz_gate.target_qubit, gate))
        else:
            raise Exception(f"Cannot decompose gate: {gate}")

    # Note that it might be possible to simplify these a little further
    return approx_gates


def count_s_and_t_to_phase(gate_string: str) -> Fraction:
    s_count = gate_string.count("S")
    t_count = gate_string.count("T")
    phase = s_count * Fraction(1, 2) + t_count * Fraction(1, 4)
    return phase


def from_gate_string(target_qubit: int, gate_string: str):
    if gate_string.startswith("H") and gate_string.endswith("H"):
        return gates.PauliRotations(
            target_qubit, phase=count_s_and_t_to_phase(gate_string), axis=PauliOperator.X
        )
    else:
        return gates.PauliRotations(
            target_qubit, phase=count_s_and_t_to_phase(gate_string), axis=PauliOperator.Z
        )



def decompose_ccx_gate(u_gate:"gates.CCX",compress_rotations=False)-> Sequence["gates.Gate"]:
    '''
    H q[2]
    CNOT q[1],q[2]
    Tdag q[2]
    CNOT q[0],q[2]
    T q[2]
    CNOT q[1],q[2]
    Tdag q[2]
    CNOT q[0],q[2]
    T q[1:2]
    CNOT q[0],q[1]
    H q[2]
    T q[0]
    Tdag q[1]
    CNOT q[0],q[1]
    '''
    target_qubit = u_gate.target_qubit
    approx_gates = list(chain(
        [
        gates.H(u_gate.target_qubit),
        gates.CNOT(control_qubit=u_gate.control_qubit_1, target_qubit=target_qubit)
        ],
        Tdag_to_T(target_qubit, compress_rotations),
        [gates.CNOT(control_qubit=u_gate.control_qubit_0, target_qubit=target_qubit)],
        #T
        [get_T(target_qubit, compress_rotations)],
        [gates.CNOT(control_qubit=u_gate.control_qubit_1, target_qubit=target_qubit)],
        Tdag_to_T(target_qubit, compress_rotations),
        [gates.CNOT(control_qubit=u_gate.control_qubit_0, target_qubit=target_qubit)],
        #T q[1:2]
        [get_T(u_gate.control_qubit_1, compress_rotations)],
        [get_T(u_gate.target_qubit, compress_rotations)],
        [gates.CNOT(control_qubit=u_gate.control_qubit_0, target_qubit=target_qubit)],
        [gates.H(u_gate.target_qubit)],
        [get_T(u_gate.control_qubit_0, compress_rotations)],
        Tdag_to_T(u_gate.control_qubit_1, compress_rotations),
        [gates.CNOT(control_qubit=u_gate.control_qubit_0, target_qubit=target_qubit)],
    ))

    return approx_gates

def Tdag_to_T(target_qubit:int,compress_rotations:bool) -> list["gates.Gate"]:
    """
    Returns the T gate that is equivalent to T dagger on the target qubit.
    """

    return [
        gates.H(target_qubit),
        gates.X(target_qubit),
        gates.H(target_qubit),
        gates.PauliRotations(
            target_qubit=target_qubit, phase=Fraction(1, 2), axis=PauliOperator.Z
        )
        if compress_rotations
        else gates.S(target_qubit),
        gates.PauliRotations(
            target_qubit=target_qubit, phase=Fraction(1, 4), axis=PauliOperator.Z
        )
        if compress_rotations
        else gates.T(target_qubit)
    ]


def get_T(target_qubit:int,compress_rotations:bool)->"gates.T":
    """
    Returns the T gate that is equivalent to T dagger on the target qubit.
    """
    return gates.PauliRotations(
            target_qubit=target_qubit, phase=Fraction(1, 4), axis=PauliOperator.Z
        ) if compress_rotations else gates.T(target_qubit)

if __name__ == '__main__':
    gate = gates.RCCX(control_qubit_0=0, control_qubit_1=1, target_qubit=2)
    ret = decompose_rccx_gate(gate,compress_rotations=False)
    print(ret)