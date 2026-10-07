# Bring results back from the HPC: answers, attempts, frozen contexts, replays (CSV), logs, status.
# A stable snapshot is copied on the server first, then archived, checksummed, fetched, verified and merged
# without overwriting (a same-name file with other content stops the merge). Then local scoring.
. (Join-Path $PSScriptRoot "hpc.config.ps1")
$ErrorActionPreference = "Stop"
function Check($what) { if ($LASTEXITCODE -ne 0) { throw "$what failed (exit $LASTEXITCODE)" } }

$stamp = Get-Date -Format "yyyyMMddTHHmmss"
$snap = "$RemoteDir/snap-$stamp"; $tgz = "$RemoteDir/ws-results-$stamp.tgz"     # unique names in the Lustre space
$dest = Join-Path $LocalRoot "hpc-results\$stamp"
New-Item -ItemType Directory -Force $dest | Out-Null
$steps = @(
    "set -e",
    "cd '$RemoteDir/websemantic'",
    "mkdir -p '$snap/benchmark-reserve' '$snap/semantic-sim-layer/evaluation/e1'",
    "cp -a benchmark-reserve/runs '$snap/benchmark-reserve/'",
    "cp -a logs '$snap/'",
    "for f in status-*.json; do if [ -e `"`$f`" ]; then cp -a `"`$f`" '$snap/'; fi; done",
    "find semantic-sim-layer/evaluation/e1 -maxdepth 1 -name 'e1-*' -exec cp -a {} '$snap/semantic-sim-layer/evaluation/e1/' +",
    "tar czf '$tgz' -C '$snap' .",
    "rm -rf '$snap'"
)
ssh $Remote ($steps -join "; ")
Check "Remote snapshot and archive"
$remoteSha = "$(ssh $Remote "sha256sum '$tgz' | cut -d' ' -f1")".Trim(); Check "Remote checksum"
scp "${Remote}:$tgz" (Join-Path $dest "results.tgz"); Check "Copy"
$localSha = (Get-FileHash (Join-Path $dest "results.tgz") -Algorithm SHA256).Hash.ToLower()
if ($localSha -ne $remoteSha) { throw "Checksum mismatch ($localSha vs $remoteSha)" }
ssh $Remote "rm -f '$tgz'"; Check "Remote cleanup"
tar -xzf (Join-Path $dest "results.tgz") -C $dest; Check "Extraction"

# Merge model answers into the local reserved folder; existing files are never overwritten.
# Same name with different content = collision: reported and the merge is refused (nothing is silently dropped).
$srcRuns = Join-Path $dest "benchmark-reserve\runs"; $dstRuns = Join-Path $LocalRoot "benchmark-reserve\runs"
$collisions = Get-ChildItem $srcRuns -Recurse -File | Where-Object {
    $local = Join-Path $dstRuns $_.FullName.Substring($srcRuns.Length + 1)
    (Test-Path $local) -and ((Get-FileHash $local).Hash -ne (Get-FileHash $_.FullName).Hash)
}
if ($collisions) { $collisions.FullName | Write-Host; throw "$(@($collisions).Count) collision(s): same name, different content. Merge refused; results kept in $dest" }
robocopy $srcRuns $dstRuns /E /XC /XN /XO /NFL /NDL /NJH /NJS | Out-Null
if ($LASTEXITCODE -ge 8) { throw "robocopy failed (exit $LASTEXITCODE)" }
$global:LASTEXITCODE = 0
# Server-side replays (e1-numeric-*.csv) stay in $dest\semantic-sim-layer\evaluation\e1 next to the logs.
$python = Join-Path $LocalRoot "semantic-sim-layer\.venv\Scripts\python.exe"
Get-ChildItem (Join-Path $dest "benchmark-reserve\runs\e1") -Directory | ForEach-Object {
    Write-Host "== scoring $($_.Name)"
    & $python (Join-Path $LocalRoot "semantic-sim-layer\evaluation\e1\score_e1.py") $_.Name; Check "Scoring $($_.Name)"
}
Write-Host "Results in $dest"
