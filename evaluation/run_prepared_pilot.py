"""Collect the reserved development pilot through the unchanged public CLI.

Instrumentation records calls, states and outputs; no fabricated model replies.
Corpus and transcripts stay outside public evaluation exports.
"""

# ruff: noqa: B023 -- callbacks run synchronously inside each patched CLI invocation.

import argparse
import builtins
import contextlib
import hashlib
import importlib.util
import io
import json
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from websemantic import cli
from websemantic.session import Session


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--llm", default="gemini-3.5-flash-lite")
    parser.add_argument("--domains", nargs="+", default=["tls", "lqlequiv", "pyrcel"])
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    args.output.mkdir(parents=True, exist_ok=False)
    router = module(args.corpus / "tools/continuation_router.py", "pilot_router")
    lexicon = module(args.corpus / "tools/topic_lexicon.py", "pilot_lexicon")
    original_extract, original_run = cli.extract, cli.run_if_ready
    last_call = 0.0
    results = []
    stop = False

    for domain in args.domains:
        corpus_path = args.corpus / domain / "pilot.jsonl"
        corpus_hash = hashlib.sha256(corpus_path.read_bytes()).hexdigest()
        for line in corpus_path.read_text(encoding="utf-8").splitlines():
            if stop:
                break
            case = json.loads(line)
            target = args.output / case["id"]
            target.mkdir()
            transcript = io.StringIO()
            trial = {"id": case["id"], "domain": domain, "family": case["family"],
                     "group": case["group"], "model_requested": args.llm,
                     "started": datetime.now(timezone.utc).isoformat(),
                     "corpus_sha256": corpus_hash, "messages": [], "calls": [],
                     "states": [], "runs": [], "routing": []}
            sessions = []
            queue = iter(case["turns"])
            done = set()
            cursor = 0
            turn_count = 0

            class ObservedSession(Session):
                def __init__(self, descriptor):
                    super().__init__(descriptor)
                    sessions.append(self)

            def extract(*a, **kw):
                nonlocal last_call, stop
                # Respect a conservative request rate; no retry on quota failure.
                delay = 5.0 - (time.monotonic() - last_call)
                if delay > 0:
                    time.sleep(delay)
                last_call = time.monotonic()
                call = {"request": a[0], "started": datetime.now(timezone.utc).isoformat()}
                trial["calls"].append(call)
                try:
                    parsed, usage = original_extract(*a, **kw)
                    call.update(response=parsed, usage=usage)
                    return parsed, usage
                except Exception as exc:
                    call["error"] = str(exc)
                    if any(code in str(exc) for code in ("HTTP 429", "HTTP 403", "HTTP 401")):
                        stop = True
                    raise
                finally:
                    call["elapsed_s"] = time.monotonic() - last_call

            def observed_run(session, *a, **kw):
                trial["states"].append({"after_message": len(trial["messages"]),
                                        "gate": asdict(session.result()),
                                        "scenario": asdict(session.scenario),
                                        "comparison": {k: asdict(v.scenario) for k, v in session.scenarios.items()},
                                        "pending": session.pending_clarification,
                                        "run_requested": session.run_requested})
                result = original_run(session, *a, **kw)
                if result:
                    trial["runs"].append({"after_message": len(trial["messages"]),
                                          "path": str(result[0]), "summary": result[1]})
                return result

            def next_input(prompt=""):
                nonlocal cursor, turn_count, stop
                observed = transcript.getvalue()[cursor:]
                cursor = len(transcript.getvalue())
                if any(code in observed for code in ("HTTP 429", "HTTP 403", "HTTP 401")):
                    stop = True
                if stop or turn_count >= 10:
                    return "/quit"
                try:
                    request = next(queue)
                    source = "prepared turn"
                except StopIteration:
                    steps = case.get("continuation", {}).get("steps", [])
                    topics = lexicon.topics_asked(observed, domain)
                    request, newly_done = router.route(steps, done, topics)
                    trial["routing"].append({"system_message": observed, "topics": sorted(topics),
                                              "matched_steps": sorted(newly_done)})
                    if request is None:
                        return "/quit"
                    done.update(newly_done)
                    source = "scripted continuation"
                turn_count += 1
                trial["messages"].append({"request": request, "source": source})
                transcript.write(prompt + request + "\n")
                cursor = len(transcript.getvalue())
                return request

            with contextlib.redirect_stdout(transcript), patch.object(builtins, "input", next_input), \
                 patch.object(cli, "extract", extract), patch.object(cli, "run_if_ready", observed_run), \
                 patch.object(cli, "Session", ObservedSession):
                try:
                    trial["exit_code"] = cli.main(["chat", "--direct", "--model",
                        "lql" if domain == "lqlequiv" else domain, "--workspace", str(root),
                        "--output-dir", str(target / "runs"), "--llm", args.llm, "--max-calls", "8"])
                except (OSError, ValueError, TypeError, RuntimeError, KeyError) as exc:
                    trial["unhandled_error"] = f"{type(exc).__name__}: {exc}"
            if sessions:
                session = sessions[0]
                trial["final_gate"] = asdict(session.result())
                trial["final_scenario"] = asdict(session.scenario)
                trial["final_comparison"] = {k: asdict(v.scenario) for k, v in session.scenarios.items()}
                trial["pending"] = session.pending_clarification
            trial["finished"] = datetime.now(timezone.utc).isoformat()
            trial["continuation_steps_done"] = sorted(done)
            trial["expected"] = case
            dump(target / "trial.json", trial)
            (target / "transcript.txt").write_text(transcript.getvalue(), encoding="utf-8")
            results.append({"id": case["id"], "domain": domain, "calls": len(trial["calls"]),
                            "runs": len(trial["runs"]), "path": str(target),
                            "gate": trial.get("final_gate", {}).get("decision"),
                            "error": trial.get("unhandled_error")})
            dump(args.output / "index.json", {"condition": "Dedicated CLI, unchanged complete descriptor",
                                               "model_requested": args.llm, "results": results,
                                               "stopped_on_access_error": stop})
            print(case["id"], "calls", len(trial["calls"]), "runs", len(trial["runs"]),
                  "gate", trial.get("final_gate", {}).get("decision"), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
