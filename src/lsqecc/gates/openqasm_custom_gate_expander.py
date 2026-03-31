from dataclasses import dataclass
import re
from typing import Dict, List, Sequence


@dataclass(frozen=True)
class GateDefinition:
    expression_parameters: Sequence[str]
    qubit_parameters: Sequence[str]
    body_lines: Sequence[str]


_GATE_DEFINITION_RE = re.compile(
    r"^\s*gate\s+(\w+)(?:\(([^)]*)\))?\s+([^{}]+)\{\s*$"
)
_GATE_INVOCATION_RE = re.compile(r"^(\w+)(?:\(([^)]*)\))?\s+(.+);$")


def expand_custom_gates(input_code: str) -> str:
    gate_definitions, output_lines = _extract_gate_definitions(input_code)
    expanded_output: List[str] = []

    for line in output_lines:
        expanded_output.extend(_expand_operation(line, gate_definitions, []))

    return "".join(expanded_output)


def _extract_gate_definitions(input_code: str):
    gate_definitions: Dict[str, GateDefinition] = {}
    output_lines: List[str] = []
    current_gate_name = None
    current_gate_expression_params: List[str] = []
    current_gate_qubit_params: List[str] = []
    current_gate_body: List[str] = []

    for line in input_code.splitlines(keepends=True):
        if current_gate_name is not None:
            if line.strip() == "}":
                gate_definitions[current_gate_name] = GateDefinition(
                    expression_parameters=tuple(current_gate_expression_params),
                    qubit_parameters=tuple(current_gate_qubit_params),
                    body_lines=tuple(current_gate_body),
                )
                current_gate_name = None
                current_gate_expression_params = []
                current_gate_qubit_params = []
                current_gate_body = []
                continue

            current_gate_body.append(line.strip())
            continue

        gate_match = _GATE_DEFINITION_RE.match(line)
        if gate_match:
            current_gate_name = gate_match.group(1)
            current_gate_expression_params = _split_csv(gate_match.group(2) or "")
            current_gate_qubit_params = _split_csv(gate_match.group(3))
            current_gate_body = []
            continue

        output_lines.append(line)

    if current_gate_name is not None:
        raise ValueError(f"Gate {current_gate_name} is missing a closing brace")

    return gate_definitions, output_lines


def _expand_operation(
    line: str, gate_definitions: Dict[str, GateDefinition], expansion_stack: List[str]
) -> List[str]:
    stripped_line = line.strip()
    if not stripped_line:
        return []

    invocation_match = _GATE_INVOCATION_RE.match(stripped_line)
    if not invocation_match:
        return [stripped_line + "\n"]

    gate_name = invocation_match.group(1)
    if gate_name not in gate_definitions:
        return [stripped_line + "\n"]

    if gate_name in expansion_stack:
        raise ValueError(
            f"Recursive custom gate expansion detected: {' -> '.join(expansion_stack + [gate_name])}"
        )

    gate_definition = gate_definitions[gate_name]
    expression_arguments = _split_csv(invocation_match.group(2) or "")
    qubit_arguments = _split_csv(invocation_match.group(3))

    if len(gate_definition.expression_parameters) != len(expression_arguments):
        raise ValueError(
            f"Gate {gate_name} expects {len(gate_definition.expression_parameters)} expression arguments but got {len(expression_arguments)}"
        )

    if len(gate_definition.qubit_parameters) != len(qubit_arguments):
        raise ValueError(
            f"Gate {gate_name} expects {len(gate_definition.qubit_parameters)} qubit arguments but got {len(qubit_arguments)}"
        )

    parameter_mapping = {
        **dict(zip(gate_definition.expression_parameters, expression_arguments)),
        **dict(zip(gate_definition.qubit_parameters, qubit_arguments)),
    }
    expanded_lines: List[str] = []

    for body_line in gate_definition.body_lines:
        replaced_line = body_line
        for parameter, argument in parameter_mapping.items():
            replaced_line = re.sub(rf"\b{re.escape(parameter)}\b", argument, replaced_line)
        expanded_lines.extend(
            _expand_operation(replaced_line, gate_definitions, expansion_stack + [gate_name])
        )

    return expanded_lines


def _split_csv(raw_values: str) -> List[str]:
    return [value.strip() for value in raw_values.split(",") if value.strip()]