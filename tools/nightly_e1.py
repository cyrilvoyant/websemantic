"""Frozen local E1 campaign, incremental private reports, and bounded overnight resume.

No external backend is changed. Only Gemini is called; numeric replay is a
controlled-completion experiment, not an autonomous agent execution.
"""

import argparse
import csv
import ctypes
import hashlib
import importlib
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

CONDITIONS = "F000,F100,F010,F001,F110,F101,F011,F111"
DOMAINS = ("tls", "lqlequiv", "pyrcel")


def alive(pid):
    if not pid:
        return False
    kernel = ctypes.windll.kernel32
    kernel.OpenProcess.argtypes = (ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong)
    kernel.OpenProcess.restype = ctypes.c_void_p
    kernel.GetExitCodeProcess.argtypes = (ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong))
    kernel.CloseHandle.argtypes = (ctypes.c_void_p,)
    handle = kernel.OpenProcess(0x1000, False, pid)
    if not handle:
        return False
    try:
        code = ctypes.c_ulong()
        return bool(kernel.GetExitCodeProcess(handle, ctypes.byref(code))) and code.value == 259
    finally:
        kernel.CloseHandle(handle)


def atomic(path, data):
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(temp, path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", required=True)
    ap.add_argument("--wait-pid", type=int, default=0)
    ap.add_argument("--report-only", action="store_true")
    ap.add_argument("--fresh", action="store_true", help="Never import historical answers")
    ap.add_argument("--until", required=True, help="Europe/Paris ISO local time")
    args = ap.parse_args()
    repo = Path(__file__).resolve().parents[1]
    base = repo.parent
    out = Path(args.output).resolve()
    out.mkdir(parents=True, exist_ok=True)
    until = datetime.fromisoformat(args.until).replace(tzinfo=ZoneInfo("Europe/Paris"))
    shadow = out / "source"
    reserved = base / "benchmark-reserve"
    frozen_reserve = out / "benchmark-reserve"
    log_path = base / "trilog.md"
    started = time.monotonic()
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    state = {"started_utc": datetime.now(timezone.utc).isoformat(), "deadline": until.isoformat(),
             "source_revision": revision, "fresh": args.fresh}

    def note(message):
        stamp = datetime.now(ZoneInfo("Europe/Paris")).isoformat(timespec="seconds")
        print(stamp, message, flush=True)
        with log_path.open("a", encoding="utf-8") as f:
            f.write("\n\n## " + stamp + " — campagne locale nocturne\n\n" + message + "\n")

    def progress(step, **extra):
        state.update(step=step, updated_utc=datetime.now(timezone.utc).isoformat(), **extra)
        atomic(out / "status.json", state)

    def expired():
        return datetime.now(timezone.utc) >= until

    # An immutable source snapshot prevents contexts from changing during calls.
    for entry in ("src", "descriptors", "packs", "ontology", "docs", "agent", "evaluation/e1",
                  "external/tunnel-load-simulator", "external/LQL-Equiv-web", "external/pyrcel"):
        shutil.copytree(repo / entry, shadow / entry, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns(".git", "__pycache__", ".venv", "*.pyc", "e1-*.csv", "e1-*.json"))
    for entry in ("AGENTS.md", "llm.md", "LLM-CONTRACT.md"):
        shutil.copy2(repo / entry, shadow / entry)
    for domain in DOMAINS:
        shutil.copytree(reserved / domain, frozen_reserve / domain, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns("runs", "__pycache__"))
    inventory = {str(f.relative_to(out)): hashlib.sha256(f.read_bytes()).hexdigest()
                 for folder in (shadow, frozen_reserve) for f in folder.rglob("*") if f.is_file()}
    atomic(out / "frozen-files.json", inventory)
    sys.path.insert(0, str(shadow / "evaluation/e1"))
    sys.path.insert(0, str(shadow / "src"))
    harness = importlib.import_module("run_e1")
    score = importlib.import_module("score_e1")
    numeric = importlib.import_module("numeric_e1")
    harness.REPO = score.REPO = numeric.REPO = shadow
    # No secret is copied to the snapshot.
    harness.REPO = repo
    harness.load_key()
    harness.REPO = shadow
    harness.RESERVE = frozen_reserve
    score.RESERVE = numeric.RESERVE = frozen_reserve
    if not args.report_only and not os.environ.get("GEMINI_API_KEY"):
        progress("blocked", reason="Gemini key missing")
        note("Campagne non lancée : clé Gemini absente. Aucun appel effectué.")
        return
    model = "gemini-3.5-flash-lite"
    folder = model + "__" + out.name
    answers = frozen_reserve / "runs/e1" / folder
    answers.mkdir(parents=True, exist_ok=True)
    target_count = sum(sum(bool(line.strip()) for line in (frozen_reserve / d / (c + ".jsonl")).read_text(encoding="utf-8").splitlines())
                       for d in DOMAINS for c in ("pilot", "qualifiers")) * 8 * 3
    instr_hash = hashlib.sha256(harness.INSTRUCTIONS.encode()).hexdigest()[:12]
    expected = {}
    for domain in DOMAINS:
        for corpus in ("pilot", "qualifiers"):
            for line in (frozen_reserve / domain / (corpus + ".jsonl")).read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                case = json.loads(line)
                for condition in CONDITIONS.split(","):
                    ctx = hashlib.sha256(harness.context(domain, condition).encode()).hexdigest()[:12]
                    for rep in (1, 2, 3):
                        expected[(case["id"], condition, rep)] = (ctx, instr_hash, harness.request_hash(case["turns"][0]))
    atomic(out / "protocol.json", {"model": model, "conditions": CONDITIONS.split(","), "domains": DOMAINS,
                                   "repetitions": 3, "target": target_count, "fresh": args.fresh,
                                   "instruction_hash": instr_hash, "numeric_scope": "controlled completion"})
    note(f"Démarrage superviseur local : cible {target_count} réponses, huit conditions × corpus pilot/qualifiers × trois répétitions, fresh={args.fresh}. Sources/corpus figés et SHA256, aucun backend original modifié. Attente du processus existant PID {args.wait_pid} avant tout nouvel appel ; rapports incrémentaux privés dans {out}.")

    def import_matching():
        if args.fresh:
            return 0
        copied = 0
        original = reserved / "runs/e1" / model
        for f in original.glob("*.json"):
            try:
                a = json.loads(f.read_text(encoding="utf-8"))
                key = (a["case_id"], a["condition"], a["rep"])
                if harness.stored_key(a) != expected.get(key) or a.get("http_error") or a.get("network_error"):
                    continue
                dest = answers / f"{key[0]}_{key[1]}_r{key[2]}.json"
                if not dest.exists():
                    dest.write_bytes(f.read_bytes())
                    copied += 1
            except (KeyError, ValueError, OSError):
                continue
        return copied

    def report():
        # Manifests stay available but must not be scored as answers.
        hidden = []
        for f in answers.glob("contexts-*.json"):
            dest = out / "contexts" / f.name
            dest.parent.mkdir(exist_ok=True)
            shutil.move(str(f), dest)
            hidden.append(dest)
        if not any(answers.glob("*.json")):
            return
        sys.argv = ["score", folder]
        score.main()
        rows = list(csv.DictReader((shadow / "evaluation/e1" / ("e1-scores-" + folder + ".csv")).open(encoding="utf-8")))
        grouped = defaultdict(list)
        for r in rows:
            grouped[(r["domain"], r["condition"])].append(r)
        tab = []
        for (domain, condition), records in sorted(grouped.items()):
            row = {"domain": domain, "condition": condition, "n": len(records)}
            for field in ("parsed_ok", "decision_ok", "premature_execute", "unsupported", "field_error"):
                vals = [float(r[field]) for r in records if r.get(field) not in (None, "")]
                row[field] = sum(vals) / len(vals) if vals else None
                row[field + "_n"] = len(vals)
            tab.append(row)
        with (out / "table-progress.csv").open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(tab[0]))
            writer.writeheader()
            writer.writerows(tab)
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            plt.rcParams.update({"font.family": "serif", "font.size": 10, "axes.spines.top": False,
                                 "axes.spines.right": False, "savefig.bbox": "tight"})
            fig, axes = plt.subplots(1, 3, figsize=(11, 3.3), sharey=True)
            for ax, domain in zip(axes, DOMAINS):
                rs = [r for r in tab if r["domain"] == domain]
                ax.bar([r["condition"][1:] for r in rs], [r["decision_ok"] if r["decision_ok"] is not None else float("nan") for r in rs], color="#3b6381")
                ax.set(title=domain, xlabel="O / C / P", ylim=(0, 1))
                ax.tick_params(axis="x", rotation=45)
                for index, row in enumerate(rs):
                    value = row["decision_ok"]
                    if value is not None:
                        ax.text(index, min(value + 0.025, 0.96), f"n={row['decision_ok_n']}",
                                ha="center", va="bottom", fontsize=7)
            axes[0].set_ylabel("Decision agreement (available responses)")
            fig.tight_layout()
            fig.savefig(out / "decision-agreement.pdf")
            fig.savefig(out / "decision-agreement.png", dpi=200)
            plt.close(fig)
            fig, axes = plt.subplots(1, 3, figsize=(11, 3.3), sharey=True)
            for ax, domain in zip(axes, DOMAINS):
                rs = [r for r in tab if r["domain"] == domain and r["field_error"] is not None]
                ax.bar([r["condition"][1:] for r in rs], [1 - r["field_error"] for r in rs], color="#688b70")
                ax.set(title=domain, xlabel="O / C / P", ylim=(0, 1))
                ax.tick_params(axis="x", rotation=45)
                for index, row in enumerate(rs):
                    ax.text(index, min(1 - row["field_error"] + 0.025, 0.96), f"n={row['field_error_n']}",
                            ha="center", va="bottom", fontsize=7)
            axes[0].set_ylabel("Mean expected-field accuracy (available responses)")
            fig.tight_layout()
            fig.savefig(out / "parameter-agreement.pdf")
            fig.savefig(out / "parameter-agreement.png", dpi=200)
            plt.close(fig)
        except ImportError:
            progress("reporting", plot_status="matplotlib unavailable")
        numeric_counts = {}
        for domain in DOMAINS:
            try:
                sys.argv = ["numeric", folder, domain]
                numeric.main()
                path = shadow / "evaluation/e1" / f"e1-numeric-{folder}-{domain}.csv"
                data = list(csv.DictReader(path.open(encoding="utf-8")))
                numeric_counts[domain] = dict(Counter(r["status"] for r in data))
            except Exception as exc:  # noqa: BLE001 - backend failures remain explicit outcomes
                numeric_counts[domain] = {"job_error": type(exc).__name__}
        atomic(out / "numeric-status.json", numeric_counts)
        snapshot = out / "reports" / f"{len(rows):06d}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}"
        snapshot.mkdir(parents=True, exist_ok=True)
        for result in (shadow / "evaluation/e1").glob("e1-*"):
            if result.is_file():
                shutil.copy2(result, snapshot / result.name)
        for name in ("table-progress.csv", "numeric-status.json", "decision-agreement.pdf", "decision-agreement.png", "parameter-agreement.pdf", "parameter-agreement.png"):
            if (out / name).exists():
                shutil.copy2(out / name, snapshot / name)
        progress("reported", scored=len(rows), target=target_count, numeric=numeric_counts)
        note(f"Rapport local mis à jour : {len(rows)}/{target_count} réponses notées ; table-progress.csv, figures si matplotlib disponible, CSV numériques et numeric-status.json. Résultats partiels, sans tests inférentiels tant que blocs non complets ; complétion numérique depuis références explicitée.")

    if args.report_only:
        import_matching()
        report()
        progress("report_only_finished")
        return
    original_write = harness.write_atomic
    new_since_report = 0

    def write_and_report(path, text):
        nonlocal new_since_report
        original_write(path, text)
        if path.name.startswith("contexts-"):
            return
        new_since_report += 1
        if new_since_report >= 50:
            report()
            new_since_report = 0

    harness.write_atomic = write_and_report
    last_n = -1
    while alive(args.wait_pid) and not expired():
        import_matching()
        n = len(list(answers.glob("*.json")))
        if n >= last_n + 50:
            report()
            last_n = n
        progress("waiting_existing_campaign", available=n, target=target_count)
        time.sleep(60)
    import_matching()
    report()
    if expired():
        progress("deadline", reason="existing campaign still active or morning reached")
        return
    original_gemini = harness.gemini
    consecutive_429 = 0

    class StopCampaign(Exception):
        pass

    def call(prompt, requested_model):
        nonlocal consecutive_429
        if expired():
            raise StopCampaign("Morning deadline reached")
        try:
            result = original_gemini(prompt, requested_model)
            consecutive_429 = 0
            return result
        except urllib.error.HTTPError as exc:
            if exc.code == 429:
                consecutive_429 += 1
                if consecutive_429 >= 5:
                    harness.log_attempt(answers, {"time": datetime.now(timezone.utc).isoformat(),
                                                  "outcome": "http_429_stopped", "model": model,
                                                  "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest()})
                    raise StopCampaign("Five consecutive quota refusals; calls stopped") from exc
            elif exc.code in (401, 403, 404):
                raise StopCampaign(f"Provider configuration refused: HTTP {exc.code}") from exc
            raise

    harness.gemini = call
    # Short bounded batches produce reports between domains/corpora, with safe resume.
    try:
        for rep in (1, 2, 3):
            for corpus in ("pilot", "qualifiers"):
                for domain in DOMAINS:
                    if expired():
                        raise StopCampaign("Morning deadline reached")
                    progress("collecting", rep=rep, corpus=corpus, domain=domain)
                    sys.argv = ["run", "--model", model, "--tag", out.name, "--domains", domain,
                                "--conditions", CONDITIONS, "--corpus", corpus, "--reps", str(rep), "--pause", "6"]
                    # Harness writes to a private, frozen reserve; no global folder collision.
                    harness.main()
                    report()
        progress("finished", elapsed_seconds=time.monotonic() - started)
        note("Passes de collecte achevées. Lire status.json et les refus/tentatives : fin des passes ne garantit pas la complétude. Aucun autre fournisseur ni H200 lancé.")
    except StopCampaign as exc:
        report()
        progress("stopped", reason=str(exc), elapsed_seconds=time.monotonic() - started)
        note("Collecte arrêtée : " + str(exc) + ". Les réponses et rapports disponibles sont conservés ; aucun changement de modèle pour contourner les quotas.")


if __name__ == "__main__":
    main()
