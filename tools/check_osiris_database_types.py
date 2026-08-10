#!/usr/bin/env python3

"""Check Osiris database column types without starting Baldur's Gate 3."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path


CALL_PATTERN = re.compile(r"^(?:NOT\s+)?([A-Za-z_][A-Za-z0-9_]*)\((.*)\);?$")
CAST_PATTERN = re.compile(r"^\(([A-Z][A-Z0-9_]*)\)(_[A-Za-z][A-Za-z0-9_]*)$")
VARIABLE_PATTERN = re.compile(r"^_[A-Za-z][A-Za-z0-9_]*$")
HEADER_FUNCTION_PATTERN = re.compile(
    r"^(?:query|call|event)\s+([A-Za-z_][A-Za-z0-9_]*)\((.*)\)\s+\([0-9,]+\)$"
)
HEADER_PARAMETER_PATTERN = re.compile(r"(?:\[(?:in|out)\])?\(([A-Z][A-Z0-9_]*)\)")
ALIAS_PATTERN = re.compile(r"^alias_type\s+\{([A-Z][A-Z0-9_]*),\s*([0-9]+),\s*([0-9]+)\}$")
ENUM_PATTERN = re.compile(r"^enum_type\s+\{([A-Z][A-Z0-9_]*),\s*([0-9]+),")


@dataclass(frozen=True)
class Call:
    path: Path
    line: int
    rule: int
    name: str
    arguments: tuple[str, ...]


@dataclass(frozen=True)
class Diagnostic:
    path: Path
    line: int
    message: str


@dataclass
class SignatureData:
    types: dict[str, str]
    functions: dict[tuple[str, int], tuple[str, ...]]


def split_arguments(arguments: str) -> tuple[str, ...]:
    result: list[str] = []
    start = 0
    depth = 0
    quoted = False

    for index, character in enumerate(arguments):
        if character == '"' and (index == 0 or arguments[index - 1] != "\\"):
            quoted = not quoted
        elif not quoted:
            if character == "(":
                depth += 1
            elif character == ")":
                depth -= 1
            elif character == "," and depth == 0:
                result.append(arguments[start:index].strip())
                start = index + 1

    result.append(arguments[start:].strip())
    return tuple(result)


def load_signature_snapshot(path: Path) -> SignatureData:
    document = json.loads(path.read_text(encoding="utf-8"))
    types = document["types"]
    functions = {
        (entry["name"], len(entry["parameters"])): tuple(entry["parameters"])
        for entry in document["functions"]
    }
    return SignatureData(types=types, functions=functions)


def parse_story_header(path: Path) -> SignatureData:
    intrinsic_names = {
        1: "INTEGER",
        2: "INTEGER64",
        3: "REAL",
        4: "STRING",
        5: "GUIDSTRING",
    }
    type_names = dict(intrinsic_names)
    types = {name: name for name in intrinsic_names.values()}
    functions: dict[tuple[str, int], tuple[str, ...]] = {}

    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        alias = ALIAS_PATTERN.match(line)
        if alias:
            name, type_id_text, base_id_text = alias.groups()
            base_id = int(base_id_text)
            if base_id not in type_names:
                raise ValueError(f"{path}: alias {name} refers to unknown type ID {base_id}")
            type_names[int(type_id_text)] = name
            types[name] = types[type_names[base_id]]
            continue

        enum = ENUM_PATTERN.match(line)
        if enum:
            name, type_id_text = enum.groups()
            type_names[int(type_id_text)] = name
            types[name] = "INTEGER"
            continue

        function = HEADER_FUNCTION_PATTERN.match(line)
        if function:
            name, parameters_text = function.groups()
            parameters = tuple(HEADER_PARAMETER_PATTERN.findall(parameters_text))
            functions[(name, len(parameters))] = parameters

    if not functions:
        raise ValueError(f"{path}: no Osiris function signatures found")
    return SignatureData(types=types, functions=functions)


def parse_goal(path: Path) -> tuple[list[Call], list[Diagnostic]]:
    calls: list[Call] = []
    diagnostics: list[Diagnostic] = []
    in_kb_section = False
    rule = 0

    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        line = raw_line.strip()
        if line == "KBSECTION":
            in_kb_section = True
            continue
        if line == "EXITSECTION":
            in_kb_section = False
            continue
        if not in_kb_section or not line or line.startswith("//"):
            continue
        if line in {"IF", "PROC", "QRY"}:
            rule += 1
            continue
        if line in {"AND", "THEN"} or any(operator in line for operator in (" < ", " <= ", " > ", " >= ", " == ", " != ")):
            continue

        call = CALL_PATTERN.match(line)
        if call:
            name, arguments_text = call.groups()
            calls.append(
                Call(
                    path=path,
                    line=line_number,
                    rule=rule,
                    name=name,
                    arguments=split_arguments(arguments_text),
                )
            )
        elif "(" in line or ")" in line:
            diagnostics.append(Diagnostic(path, line_number, "cannot parse Osiris call"))

    return calls, diagnostics


def literal_type(argument: str) -> str | None:
    if argument.startswith('"') and argument.endswith('"'):
        return "STRING"
    if re.fullmatch(r"-?[0-9]+", argument):
        return "INTEGER"
    if re.fullmatch(r"-?(?:[0-9]+\.[0-9]*|[0-9]*\.[0-9]+)", argument):
        return "REAL"
    return None


def validate(paths: list[Path], signatures: SignatureData) -> list[Diagnostic]:
    calls: list[Call] = []
    diagnostics: list[Diagnostic] = []
    for path in paths:
        parsed_calls, parse_diagnostics = parse_goal(path)
        calls.extend(parsed_calls)
        diagnostics.extend(parse_diagnostics)

    database_types: dict[tuple[str, int], tuple[str, ...]] = {}
    variables: dict[str, str] = {}
    active_rule: tuple[Path, int] | None = None

    def intrinsic(type_name: str) -> str:
        if type_name not in signatures.types:
            raise ValueError(f"unknown Osiris type {type_name}")
        return signatures.types[type_name]

    def compatible(expected: str, actual: str) -> bool:
        if expected == actual:
            return True
        if intrinsic(expected) != intrinsic(actual):
            return False
        return expected == intrinsic(expected)

    def resolve(argument: str, expected: str | None) -> str | None:
        cast = CAST_PATTERN.match(argument)
        if cast:
            type_name, variable = cast.groups()
            intrinsic(type_name)
            variables[variable] = type_name
            return type_name

        if VARIABLE_PATTERN.match(argument):
            if argument in variables:
                return variables[argument]
            if expected is not None:
                variables[argument] = expected
                return expected
            return None

        if argument == "_":
            return expected
        return literal_type(argument)

    for call in calls:
        rule_key = (call.path, call.rule)
        if rule_key != active_rule:
            variables = {}
            active_rule = rule_key

        key = (call.name, len(call.arguments))
        expected_types = database_types.get(key) if call.name.startswith("DB_") else signatures.functions.get(key)
        if expected_types is None and not call.name.startswith("DB_"):
            diagnostics.append(
                Diagnostic(call.path, call.line, f"unknown Osiris function {call.name}/{len(call.arguments)}")
            )
            continue

        actual_types = tuple(
            resolve(argument, expected_types[index] if expected_types is not None else None)
            for index, argument in enumerate(call.arguments)
        )

        if expected_types is None:
            if any(type_name is None for type_name in actual_types):
                diagnostics.append(
                    Diagnostic(call.path, call.line, f"cannot infer all columns of {call.name}/{len(call.arguments)}")
                )
            else:
                database_types[key] = tuple(type_name for type_name in actual_types if type_name is not None)
            continue

        for index, (expected, actual) in enumerate(zip(expected_types, actual_types), 1):
            if actual is None:
                diagnostics.append(
                    Diagnostic(call.path, call.line, f"cannot infer argument {index} of {call.name}/{len(call.arguments)}")
                )
            elif not compatible(expected, actual):
                diagnostics.append(
                    Diagnostic(
                        call.path,
                        call.line,
                        f"argument {index} of {call.name}/{len(call.arguments)} expects {expected}; {actual} specified",
                    )
                )

    return diagnostics


def collect_goal_paths(arguments: list[Path], repository_root: Path) -> list[Path]:
    candidates = arguments or [repository_root / "Mods"]
    paths: set[Path] = set()
    for candidate in candidates:
        if candidate.is_dir():
            paths.update(candidate.glob("**/Story/RawFiles/Goals/*.txt"))
            paths.update(candidate.glob("*.txt"))
        elif candidate.is_file():
            paths.add(candidate)
        else:
            raise FileNotFoundError(candidate)
    if not paths:
        raise ValueError("no Osiris goal files found")
    return sorted(paths)


def main(argv: list[str] | None = None) -> int:
    script_directory = Path(__file__).resolve().parent
    repository_root = script_directory.parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", type=Path, help="Goal files or directories; defaults to Mods")
    parser.add_argument(
        "--signatures",
        type=Path,
        default=script_directory / "osiris-signatures.json",
        help="Checked-in signature snapshot",
    )
    parser.add_argument("--story-header", type=Path, help="Use signatures from an installed story_header.div")
    args = parser.parse_args(argv)

    try:
        signatures = parse_story_header(args.story_header) if args.story_header else load_signature_snapshot(args.signatures)
        paths = collect_goal_paths(args.paths, repository_root)
        diagnostics = validate(paths, signatures)
    except (FileNotFoundError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    for diagnostic in diagnostics:
        print(f"{diagnostic.path}:{diagnostic.line}: error: {diagnostic.message}", file=sys.stderr)
    if diagnostics:
        return 1

    print(f"Checked {len(paths)} Osiris goal file(s); no database type errors found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
