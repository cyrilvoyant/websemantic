"""First deterministic gate. Canonical values only; no LLM or unit conversion.

Evidence presence is checked, not its semantic truth. SHACL and relational
task-suitability rules are intentionally not implemented by this first slice.
"""

from dataclasses import dataclass, field
from datetime import date
from math import isfinite
from operator import ge, gt, le, lt
from typing import Any


@dataclass(frozen=True)
class Parameter:
    value: Any = None
    unit: str | None = None
    origin: str = "missing"
    evidence: str | None = None
    source: str | None = None
    accepted: bool = False
    conflicts: tuple[Any, ...] = ()


@dataclass(frozen=True)
class Scenario:
    request: str
    task: str
    inputs: dict[str, Parameter] = field(default_factory=dict)
    experiment: dict[str, Parameter] = field(default_factory=dict)


@dataclass(frozen=True)
class Issue:
    field: str
    code: str
    message: str


@dataclass(frozen=True)
class ValidationResult:
    decision: str
    issues: tuple[Issue, ...]


def validate(scenario: Scenario, descriptor: dict) -> ValidationResult:
    """Return execute/clarify/refuse, never fill a missing field.

    Tasks must match a descriptor task exactly in this initial implementation.
    Unknown descriptor types fail closed. Descriptor review is still required.
    """
    tasks = descriptor.get("tasks", {})
    if scenario.task not in tasks.get("supported", []):
        return ValidationResult(
            "refuse",
            (Issue("task", "unsupported_task", "Task is not declared as supported."),),
        )
    issues = []
    for group in ("inputs", "experiment"):
        supplied = getattr(scenario, group)
        specs = descriptor.get(group, {})
        for name in sorted(supplied.keys() - specs.keys()):
            issues.append(
                Issue(
                    f"{group}.{name}",
                    "unknown_field",
                    "Field is not declared in the descriptor.",
                )
            )
        for name, spec in specs.items():
            path = f"{group}.{name}"
            record = supplied.get(name, Parameter())
            value = record.value
            if type(record.accepted) is not bool:
                issues.append(Issue(path, "acceptance_type", "Acceptance must be a JSON boolean."))
                continue
            if record.conflicts:
                issues.append(Issue(path, "conflict", "Resolve conflicting values."))
            if value is None:
                issues.append(
                    Issue(
                        path,
                        "missing",
                        "An explicit value or accepted assumption is required.",
                    )
                )
                continue
            if record.origin == "provided":
                if not record.evidence or record.evidence not in scenario.request:
                    issues.append(
                        Issue(
                            path,
                            "evidence",
                            "Provide an exact evidence span from the request.",
                        )
                    )
            elif record.origin in ("default", "assumption"):
                if not record.accepted or not record.source:
                    issues.append(
                        Issue(
                            path,
                            "unaccepted_assumption",
                            "Assumptions need a source and explicit acceptance.",
                        )
                    )
            else:
                issues.append(
                    Issue(
                        path,
                        "unsupported_origin",
                        "Origin is unsupported by this initial gate.",
                    )
                )
            if spec.get("unit") != record.unit:
                issues.append(
                    Issue(
                        path,
                        "unit",
                        "Use the canonical descriptor unit; no conversion is performed.",
                    )
                )
            kind = spec.get("type")
            valid_type = False
            if kind == "int":
                valid_type = type(value) is int
            elif kind == "float":
                valid_type = type(value) in (int, float)
            elif kind == "category":
                valid_type = isinstance(value, str)
            elif kind == "date":
                valid_type = isinstance(value, str)
                if valid_type:
                    try:
                        valid_type = date.fromisoformat(value).isoformat() == value
                    except ValueError:
                        valid_type = False
            if not valid_type:
                issues.append(
                    Issue(path, "type", f"Invalid value for descriptor type {kind!r}.")
                )
                continue
            if kind in ("int", "float"):
                try:
                    finite = isfinite(value)
                except OverflowError:
                    finite = False
                if not finite:
                    issues.append(
                        Issue(path, "finite", "Numeric values must be finite.")
                    )
                    continue
                bounds = spec.get("bounds", {})
                checks = {
                    "min": ge,
                    "max": le,
                    "min_exclusive": gt,
                    "max_exclusive": lt,
                }
                for key, check in checks.items():
                    if key in bounds and not check(value, bounds[key]):
                        issues.append(
                            Issue(
                                path,
                                "bounds",
                                f"Violates {key}={bounds[key]} ({bounds.get('authority', 'unspecified')}).",
                            )
                        )
            elif kind == "category" and value not in spec.get("values", []):
                issues.append(
                    Issue(path, "category", "Value is not an allowed category.")
                )
    return ValidationResult("clarify" if issues else "execute", tuple(issues))
