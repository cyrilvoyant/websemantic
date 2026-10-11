"""WebSemantic MCP server (Hugging Face Space, free CPU).

A language-model agent reads a code's contract, writes a scenario, has it checked, and only the pinned original code
computes it. No language model runs here and no key is needed: the calling agent reads the words, this server checks
and computes. Codes: TLS (road-tunnel electricity demand) and LQL-Equiv (radiotherapy dose equivalence; fictitious
scenarios for research and teaching, not a medical device). Same descriptors, validator, SHACL shapes and pinned codes
as the web app (bundle.zip, built by tools/build_webapp.py).
"""

import dataclasses
import functools
import hashlib
import json
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

import gradio as gr

HERE = Path(__file__).resolve().parent
WS = HERE / "ws"
BUNDLE_SHA256 = hashlib.sha256((HERE / "bundle.zip").read_bytes()).hexdigest()
if not (WS / "src").exists():
    with zipfile.ZipFile(HERE / "bundle.zip") as archive:
        archive.extractall(WS)
sys.path.insert(0, str(WS / "src"))

from websemantic.core.validation import validate  # noqa: E402
from websemantic.registry import execute, load_descriptor  # noqa: E402
from websemantic.replay import load_scenario  # noqa: E402
from websemantic.scenario_check import check_lql  # noqa: E402

CODES = ("tls", "lql")
DESC = {code: load_descriptor(WS, code) for code in CODES}
MAX_DAYS, MAX_RUNS, MAX_POINTS = 366, 10, 366 * 96 * 10  # same limits as the web app
FULL_FILE = 50_000  # characters: larger outputs are returned truncated, with their size


def _json(obj):  # strict JSON for agents (not a Python repr)
    return json.dumps(obj, ensure_ascii=False, allow_nan=False, default=str)


def _safe(tool):  # a malformed request is refused with its reason, never computed
    @functools.wraps(tool)
    def wrapper(*args, **kwargs):
        try:
            return tool(*args, **kwargs)
        except (ValueError, TypeError, KeyError, OSError) as error:
            return _json({"computed": False, "decision": "refuse", "error": str(error)})
    return wrapper


def _code(code):
    code = str(code).strip().lower()
    if code not in CODES:
        raise ValueError(f"Unknown code {code!r}: use 'tls' or 'lql'.")
    return code


def _scenario(scenario_json):
    document = json.loads(scenario_json) if isinstance(scenario_json, str) else scenario_json
    return document, load_scenario(document)


def _value(group, name):
    record = group.get(name)
    return getattr(record, "value", None) if record is not None else None


def _shacl(scenario):
    """The ontology's SHACL shapes on an LQL-Equiv scenario (one course)."""
    inp = scenario.inputs
    course = {k: _value(inp, k) for k in ("dose_per_fraction", "n_fractions", "gap_days")}
    organ, ref = _value(inp, "organ"), _value(inp, "reference_dose")
    return check_lql(WS, [{k: v for k, v in course.items() if v is not None}], _value(inp, "tumour_site"),
                     [organ] if organ else [], None if ref is None else float(ref))


def _over_limit(scenario):
    exp = scenario.experiment
    days, runs = _value(exp, "n_days") or 0, _value(exp, "n_runs") or 0
    step = _value(exp, "freq_minutes") or 15
    return days > MAX_DAYS or runs > MAX_RUNS or days * 1440 / max(step, 1) * runs > MAX_POINTS


@_safe
def get_contract(code: str) -> str:
    """Read this first. Returns the reading contract of a code: its tasks, its parameters (field, unit, label,
    categories), the rules for reading a request (units, defaults, qualitative conventions, origins, acceptance) and a
    complete example scenario in the exact JSON format expected by check_scenario and run_scenario.

    Args:
        code: "tls" for road-tunnel electricity demand (Tunnel Load Simulator), or "lql" for radiotherapy dose equivalence with LQL-Equiv (EQD2, BED, TCP, NTCP; fictitious scenarios only, not a medical device).
    """
    code = _code(code)
    llm = json.loads((HERE / "llm" / f"{code}.json").read_text(encoding="utf-8"))
    example = json.loads((WS / "examples" / f"{'tls' if code == 'tls' else 'lql'}-complete.json").read_text(encoding="utf-8"))
    return _json({"code": code, "tasks": DESC[code]["tasks"]["supported"], "parameters": llm["params"],
            "contract": llm["contract"], "example_scenario": example,
            "how_to": "Write a scenario like example_scenario: every parameter has value, unit (canonical), origin "
                      "(provided only if the user stated it; assumption or default otherwise), source and accepted. "
                      "Ask the user before accepting any default or convention. Then call check_scenario; compute "
                      "with run_scenario only when the decision is execute."})


@_safe
def check_scenario(code: str, scenario_json: str) -> str:
    """Checks a scenario without computing anything. Returns the decision (execute, clarify or refuse) with every issue
    (missing value, default not yet accepted, unit, bounds, origin...). For LQL-Equiv the ontology's SHACL shapes also
    check the scenario (types, declared bounds, complete groups). Ask the user about each issue before going on.

    Args:
        code: "tls" or "lql".
        scenario_json: the scenario as a JSON string, in the format of get_contract's example_scenario.
    """
    return _json(_check(_code(code), scenario_json))


def _check(code, scenario_json):
    _, scenario = _scenario(scenario_json)
    gate = validate(scenario, DESC[code])
    out = {"code": code, **dataclasses.asdict(gate)}
    if code == "lql":
        out["shacl"] = _shacl(scenario)
        if out["shacl"]["status"] == "violation" and out["decision"] == "execute":
            out["decision"] = "clarify"
    if code == "tls" and _over_limit(scenario):
        out["decision"], out["limit"] = "clarify", f"at most {MAX_DAYS} days, {MAX_RUNS} runs, {MAX_POINTS} points"
    return out


@_safe
def run_scenario(code: str, scenario_json: str) -> str:
    """Computes a checked scenario with the pinned original code (TLS v1.0.1 commit 748e053, LQL-Equiv v3.0.0 commit
    dfc9a33) and returns its indicators, the manifest (versions, commits, SHA-256 of inputs and outputs) and the output
    files. Nothing is computed if check_scenario does not return execute: the check result is returned instead.

    Args:
        code: "tls" or "lql".
        scenario_json: the accepted scenario as a JSON string (format of get_contract's example_scenario).
    """
    code = _code(code)
    checked = _check(code, scenario_json)
    if checked["decision"] != "execute":
        return _json({"computed": False, **checked})
    _, scenario = _scenario(scenario_json)
    out_root = Path(tempfile.mkdtemp(prefix="ws-"))
    try:
        target, indicators = execute(scenario, DESC[code], WS, out_root)
        target = Path(target)
        files = {}
        for path in sorted(p for p in target.rglob("*") if p.is_file()):
            text = path.read_text(encoding="utf-8", errors="replace")
            name = str(path.relative_to(target)).replace("\\", "/")
            files[name] = text if len(text) <= FULL_FILE else {"truncated": True, "characters": len(text),
                                                                "start": text[:FULL_FILE]}
        manifest = json.loads((target / "manifest.json").read_text(encoding="utf-8")) if (target / "manifest.json").exists() else None
        return _json({"computed": True, "code": code, "indicators": indicators, "manifest": manifest,
                "shacl": checked.get("shacl"), "bundle_sha256": BUNDLE_SHA256, "files": files,
                "notice": "Simulation by the pinned original code. Fictitious scenarios for research and teaching; "
                          "LQL-Equiv is not a medical device and the practitioner decides."})
    finally:
        shutil.rmtree(out_root, ignore_errors=True)


ABOUT = f"""# WebSemantic — MCP server

Tools for language-model agents: **get_contract** (read first), **check_scenario**, **run_scenario**.
The agent reads the user's words; this server checks the scenario and only the pinned original codes compute.
No language model and no key here. Codes: TLS (road-tunnel electricity demand) and LQL-Equiv (radiotherapy dose
equivalence, fictitious scenarios only, not a medical device).

MCP endpoint: this Space's address followed by `/gradio_api/mcp/`. Web app for humans:
https://cyrilvoyant-websemantic.static.hf.space · Source: https://github.com/cyrilvoyant/websemantic · bundle sha256
`{BUNDLE_SHA256[:12]}`
"""

with gr.Blocks(title="WebSemantic MCP") as demo:
    gr.Markdown(ABOUT)
    with gr.Tab("get_contract"):
        c1 = gr.Dropdown(list(CODES), value="lql", label="code")
        gr.Button("Read").click(get_contract, c1, gr.Code(language="json", label="result"), api_name="get_contract")
    with gr.Tab("check_scenario"):
        c2, s2 = gr.Dropdown(list(CODES), value="lql", label="code"), gr.Code(language="json", label="scenario_json")
        gr.Button("Check").click(check_scenario, [c2, s2], gr.Code(language="json", label="result"), api_name="check_scenario")
    with gr.Tab("run_scenario"):
        c3, s3 = gr.Dropdown(list(CODES), value="lql", label="code"), gr.Code(language="json", label="scenario_json")
        gr.Button("Run").click(run_scenario, [c3, s3], gr.Code(language="json", label="result"), api_name="run_scenario")

if __name__ == "__main__":
    demo.launch(mcp_server=True)
