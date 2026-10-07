# Push the project to the HPC: allow-listed archive with secret scan and SHA-256, copy over SSH, verify, unpack.
# Refuses while a campaign is running (fresh heartbeat) and on any unclear answer from the server.
. (Join-Path $PSScriptRoot "hpc.config.ps1")
$ErrorActionPreference = "Stop"
function Check($what) { if ($LASTEXITCODE -ne 0) { throw "$what failed (exit $LASTEXITCODE)" } }
$dir = "'$RemoteDir'"; $ws = "'$RemoteDir/websemantic'"; $zip = "'$RemoteDir/websemantic-hpc.zip'"   # quoted remote paths

$python = Join-Path $LocalRoot "semantic-sim-layer\.venv\Scripts\python.exe"
& $python (Join-Path $PSScriptRoot "build_archive.py") $Archive; Check "Archive build"
$localSha = (Get-Content "$Archive.sha256" -Raw).Trim()

# Campaign state: exactly one token, ABSENT / IDLE / ACTIVE; anything else (SSH failure included) stops the push.
$state = ssh $Remote "cd $ws 2>/dev/null || { echo ABSENT; exit 0; }; if [ -f heartbeat ] && [ `$(( `$(date +%s) - `$(stat -c %Y heartbeat) )) -lt 300 ]; then echo ACTIVE; else echo IDLE; fi"
Check "Campaign state query"
$state = "$state".Trim()
if ($state -eq "ACTIVE") { throw "A campaign is running on the server (heartbeat < 5 min): push refused." }
if ($state -notin @("ABSENT", "IDLE")) { throw "Unexpected campaign state '$state': push refused." }

ssh $Remote "mkdir -p $dir"; Check "Remote mkdir"
scp $Archive "${Remote}:$RemoteDir/websemantic-hpc.zip"; Check "Copy"
$remoteSha = "$(ssh $Remote "sha256sum $zip | cut -d' ' -f1")".Trim(); Check "Remote checksum"
if ($remoteSha -ne $localSha) { throw "Checksum mismatch after copy ($remoteSha vs $localSha)" }
ssh $Remote "cd $dir && unzip -oq websemantic-hpc.zip && rm websemantic-hpc.zip && sed -i 's/\r`$//' websemantic/semantic-sim-layer/hpc/*.sh && ls websemantic"; Check "Unpack"
Write-Host "Pushed and verified (sha256 $localSha, server state was $state)."
Write-Host "In a JupyterLab terminal (H200 session, /workspace = /lustre/data/cyril.voyant.kg), smoke test first:"
Write-Host "  cd /workspace/semantic/websemantic/semantic-sim-layer && MODE=smoke nohup bash hpc/run_all.sh > /workspace/semantic/run_smoke.out 2>&1 &"
Write-Host "Full campaign only after the smoke test is checked:"
Write-Host "  cd /workspace/semantic/websemantic/semantic-sim-layer && MODE=full nohup bash hpc/run_all.sh > /workspace/semantic/run_full.out 2>&1 &"
