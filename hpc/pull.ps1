# Bring results back from the HPC (answers, attempts, contexts, replays, logs, status), verify, merge, then score locally.
. (Join-Path $PSScriptRoot "hpc.config.ps1")
function Check($what) { if ($LASTEXITCODE -ne 0) { throw "$what failed (exit $LASTEXITCODE)" } }

$stamp = Get-Date -Format "yyyyMMddTHHmmss"
$remoteTgz = "$RemoteDir/ws-results-$stamp.tgz"                   # unique name, inside the user's Lustre space
$dest = Join-Path $LocalRoot "hpc-results\$stamp"
New-Item -ItemType Directory -Force $dest | Out-Null
ssh $Remote "cd $RemoteDir/websemantic && tar czf $remoteTgz benchmark-reserve/runs logs repro status-*.json && sha256sum $remoteTgz"; Check "Remote archive"
$remoteSha = (ssh $Remote "sha256sum $remoteTgz | cut -d' ' -f1").Trim(); Check "Remote checksum"
scp "${Remote}:$remoteTgz" (Join-Path $dest "results.tgz"); Check "Copy"
$localSha = (Get-FileHash (Join-Path $dest "results.tgz") -Algorithm SHA256).Hash.ToLower()
if ($localSha -ne $remoteSha) { throw "Checksum mismatch ($localSha vs $remoteSha)" }
ssh $Remote "rm -f $remoteTgz"; Check "Remote cleanup"
tar -xzf (Join-Path $dest "results.tgz") -C $dest; Check "Extraction"
# Merge model answers into the local reserved folder; existing files are never overwritten.
robocopy (Join-Path $dest "benchmark-reserve\runs") (Join-Path $LocalRoot "benchmark-reserve\runs") /E /XC /XN /XO /NFL /NDL /NJH /NJS | Out-Null
if ($LASTEXITCODE -ge 8) { throw "robocopy failed (exit $LASTEXITCODE)" }
$python = Join-Path $LocalRoot "semantic-sim-layer\.venv\Scripts\python.exe"
Get-ChildItem (Join-Path $LocalRoot "benchmark-reserve\runs\e1") -Directory | ForEach-Object {
    Write-Host "== scoring $($_.Name)"
    & $python (Join-Path $LocalRoot "semantic-sim-layer\evaluation\e1\score_e1.py") $_.Name; Check "Scoring $($_.Name)"
}
Write-Host "Results in $dest"
