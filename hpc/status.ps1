# Where are we? Heartbeat, lane status files, per answer folder: files, parsed JSON, schema-valid answers, attempts.
# Runs on the login node (Python 3.6 is enough). An SSH failure is reported as such, never as an empty status.
. (Join-Path $PSScriptRoot "hpc.config.ps1")
$py = @'
import glob, json, os, time
base = "BASE"
hb = os.path.join(base, "heartbeat")
print("now", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
      "| heartbeat", "%d s ago" % (time.time() - os.path.getmtime(hb)) if os.path.exists(hb) else "none")
for lane in ("gpu", "cpu"):
    try:
        print(lane, json.load(open(os.path.join(base, "status-%s.json" % lane))))
    except Exception as exc:
        print(lane, "no readable status (%s)" % type(exc).__name__)
DECISIONS = {"execute", "clarify", "refuse"}
for d in sorted(glob.glob(os.path.join(base, "benchmark-reserve/runs/e1/*/"))):
    files = parsed = valid = 0
    for f in glob.glob(os.path.join(d, "*.json")):
        if os.path.basename(f).startswith("contexts-"):
            continue
        files += 1
        try:
            p = json.load(open(f)).get("parsed")
        except Exception:
            continue
        if isinstance(p, dict):
            parsed += 1
            valid += p.get("decision") in DECISIONS and isinstance(p.get("values", []), list)
    attempts = sum(sum(1 for _ in open(a)) for a in glob.glob(os.path.join(d, "attempts*.jsonl")))  # one file per client
    print("%s: %d answer files, %d parsed JSON objects, %d schema-valid answers, %d attempts"
          % (os.path.basename(d.rstrip("/")), files, parsed, valid, attempts))
'@
$py = $py.Replace("BASE", "$RemoteDir/websemantic")
$py | ssh $Remote "python3 -"
if ($LASTEXITCODE -ne 0) { Write-Host "SSH/status query FAILED (exit $LASTEXITCODE): state unknown"; exit 1 }
ssh $Remote "cd '$RemoteDir/websemantic' && L=`$(ls -td logs/*/ 2>/dev/null | head -1) && echo == latest campaign `$L && for f in gpu.log cpu.log e1.log cpu-failures.log repro/summary.txt; do echo == `$f; if [ -f `"`$L`$f`" ]; then tail -n 5 `"`$L`$f`" || exit 1; else echo pending; fi; done"
if ($LASTEXITCODE -ne 0) { Write-Host "SSH/log query FAILED (exit $LASTEXITCODE)"; exit 1 }
