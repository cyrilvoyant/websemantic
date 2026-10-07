# Bring results back from the HPC (answers, numeric replays, logs), then score locally.
. (Join-Path $PSScriptRoot "hpc.config.ps1")
$dest = Join-Path $LocalRoot "hpc-results"
New-Item -ItemType Directory -Force $dest | Out-Null
ssh $Remote "cd $RemoteDir/websemantic && tar czf /tmp/ws-results.tgz benchmark-reserve/runs logs status.json semantic-sim-layer/evaluation/e1/*.csv semantic-sim-layer/evaluation/e1/*.json 2>/dev/null; ls -lh /tmp/ws-results.tgz"
scp "${Remote}:/tmp/ws-results.tgz" (Join-Path $dest "ws-results.tgz")
if ($LASTEXITCODE -ne 0) { throw "Copy failed" }
ssh $Remote "rm -f /tmp/ws-results.tgz"
tar -xzf (Join-Path $dest "ws-results.tgz") -C $dest
# Merge model answers into the local reserved folder (existing files are kept).
$src = Join-Path $dest "benchmark-reserve\runs"
robocopy $src (Join-Path $LocalRoot "benchmark-reserve\runs") /E /XC /XN /XO /NFL /NDL /NJH /NJS | Out-Null
$python = Join-Path $LocalRoot "semantic-sim-layer\.venv\Scripts\python.exe"
Get-ChildItem (Join-Path $LocalRoot "benchmark-reserve\runs\e1") -Directory | ForEach-Object {
    Write-Host "== scoring $($_.Name)"
    & $python (Join-Path $LocalRoot "semantic-sim-layer\evaluation\e1\score_e1.py") $_.Name
}
