# Where are we? Lane status files, valid answers vs attempts per model, last log lines (login node, Python 3.6 is enough).
. (Join-Path $PSScriptRoot "hpc.config.ps1")
$py = @'
import glob, json, os
base = os.path.expanduser("BASE")
for lane in ("gpu", "cpu"):
    try:
        print(lane, json.load(open(os.path.join(base, "status-%s.json" % lane))))
    except Exception:
        print(lane, "no status yet")
for d in sorted(glob.glob(os.path.join(base, "benchmark-reserve/runs/e1/*/"))):
    answers = valid = 0
    for f in glob.glob(os.path.join(d, "*.json")):
        if os.path.basename(f).startswith("contexts-"):
            continue
        answers += 1
        try:
            valid += "parsed" in json.load(open(f))
        except Exception:
            pass
    attempts = sum(1 for _ in open(os.path.join(d, "attempts.jsonl"))) if os.path.exists(os.path.join(d, "attempts.jsonl")) else 0
    print("%s: %d answers (%d with valid JSON), %d attempts" % (os.path.basename(d.rstrip("/")), answers, valid, attempts))
'@
$py = $py.Replace("BASE", "$RemoteDir/websemantic")
$py | ssh $Remote "python3 -"
ssh $Remote "cd $RemoteDir/websemantic 2>/dev/null && for f in logs/gpu.log logs/cpu.log; do echo == `$f; tail -n 5 `$f 2>/dev/null; done"
