"""Publish deterministic qualifier checks, not results from an LLM benchmark."""

import json
from dataclasses import asdict
from pathlib import Path

from websemantic.registry import load_descriptor
from websemantic.session import Session


def main():
    root = Path(__file__).resolve().parents[1]
    descriptor = load_descriptor(root, "tls")
    traces = []
    for group in ("inputs", "experiment"):
        for name, spec in descriptor[group].items():
            for level, definition in spec.get("qualitative_scale", {}).get("levels", {}).items():
                for phrase in definition["aliases"]:
                    state = Session(descriptor)
                    # A synthetic extraction exercises the reviewed local resolver.
                    parsed = {"task": state.scenario.task, "message": "", "updates": [
                        {"field": f"{group}.{name}", "value": level, "unit": "", "evidence": phrase}]}
                    state.apply(phrase, parsed)
                    record = getattr(state.scenario, group)[name]
                    expected = definition.get("value") if "value" in definition else (
                        spec["qualitative_scale"]["reference_upper"] * definition["fraction"])
                    assert record.value == expected
                    assert record.unit == spec["unit"]
                    assert record.origin == "assumption" and not record.accepted
                    before = asdict(record)
                    state.propose_profile()
                    state.accept_profile()
                    assert state.result().decision == "execute"
                    traces.append({"field": f"{group}.{name}", "phrase": phrase,
                                   "level": level, "proposal": before,
                                   "after_acceptance": asdict(getattr(state.scenario, group)[name]),
                                   "passed": True})
    report = {"kind": "deterministic_development_check", "llm_calls": 0,
              "backend_execution": False,
              "scope": "Declared TLS aliases and acceptance only; not held-out agent performance",
              "traces": traces}
    target = root / "evaluation" / "qualifier-checks.json"
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{len(traces)} deterministic qualifier checks passed.")


if __name__ == "__main__":
    main()
