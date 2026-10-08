"""Freeze the ToolRosella tool lists used by the T/TC conditions (evaluation/PREREG-toolrosella-and-human.md).

Input: the private result folder of hpc/run_toolrosella.sh (logs, tools/, tools-dynamic/, workspace/*/mcp_output).
Output (private): benchmark-reserve/toolrosella/<run>/
  - status.json: conversion success per code (ToolRosella's own criterion) and the failure reason;
  - primary/<domain>.json: tools/list as an MCP client sees it (dynamic export); empty when the conversion failed,
    as preregistered;
  - exploratory/<domain>.json: for failed conversions, the generated tools rebuilt from mcp_service.py (AST only, the
    generated code is never executed) into the input schema FastMCP derives from a signature; declared exploratory.
Usage: python build_toolrosella_lists.py <result_folder>
"""

import ast
import json
import sys
from pathlib import Path

RESERVE = Path(__file__).resolve().parents[3] / "benchmark-reserve"
REPOS = {"tls": "tunnel-load-simulator", "lqlequiv": "LQL-Equiv-web", "pyrcel": "pyrcel"}
JSON_TYPES = {"str": "string", "int": "integer", "float": "number", "bool": "boolean", "dict": "object", "list": "array"}


def succeeded(log):
    text = log.read_text(encoding="utf-8", errors="replace")
    return "Code execution successful, review passed" in text and "completed for 0/1" not in text


def failure_reason(run_log):
    if not run_log.exists():
        return None
    err = json.loads(run_log.read_text(encoding="utf-8")).get("run_result", {}).get("stderr", "")
    lines = [ln.strip() for ln in err.splitlines() if ln.strip()]
    return lines[-1][:200] if lines else None


def schema_from_ast(service):
    """Input schema as FastMCP derives it from a signature (types from annotations, required = no default)."""
    tree = ast.parse(service.read_text(encoding="utf-8"))
    tools = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        dec = next((d for d in node.decorator_list if isinstance(d, ast.Call) and ast.unparse(d.func).endswith("tool")), None)
        if dec is None:
            continue
        kw = {k.arg: k.value.value for k in dec.keywords if isinstance(k.value, ast.Constant)}
        args = node.args.args
        n_req = len(args) - len(node.args.defaults)
        props = {}
        for a in args:
            t = JSON_TYPES.get(ast.unparse(a.annotation) if a.annotation else "", None)
            props[a.arg] = ({"type": t, "additionalProperties": True} if t == "object" else {"type": t}) if t else {}
        schema = {"type": "object", "additionalProperties": bool(node.args.vararg or node.args.kwarg), "properties": props}
        if n_req:
            schema["required"] = [a.arg for a in args[:n_req]]
        tools.append({"name": kw.get("name", node.name), "description": kw.get("description") or ast.get_docstring(node) or "",
                      "inputSchema": schema})
    return tools


def main(folder):
    folder = Path(folder)
    out = RESERVE / "toolrosella" / folder.name
    (out / "primary").mkdir(parents=True, exist_ok=True)
    (out / "exploratory").mkdir(parents=True, exist_ok=True)
    status = {"run": folder.name, "commit": (folder / "toolrosella-commit.txt").read_text().strip(), "codes": {}}
    for domain, repo in REPOS.items():
        ok = succeeded(folder / f"toolrosella-{repo}.log")
        mcp = folder / "workspace" / repo / "mcp_output"
        generated = schema_from_ast(mcp / "mcp_plugin" / "mcp_service.py")
        if ok:
            dyn = json.loads((folder / "tools-dynamic" / f"{repo}.json").read_text(encoding="utf-8"))
            if dyn.get("mode") != "dynamic":
                raise SystemExit(f"{repo}: conversion succeeded but no dynamic export")
            primary = dyn["tools"]
        else:
            primary = []
        status["codes"][domain] = {"repository": repo, "conversion": "success" if ok else "failure",
                                   "reason": None if ok else failure_reason(mcp / "mcp_logs" / "run_log.json"),
                                   "generated_tools": len(generated), "primary_tools": len(primary)}
        (out / "primary" / f"{domain}.json").write_text(json.dumps(primary, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        (out / "exploratory" / f"{domain}.json").write_text(
            json.dumps(primary if ok else generated, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    (out / "status.json").write_text(json.dumps(status, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(status, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv[1])
