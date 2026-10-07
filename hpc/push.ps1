# Push the project to the HPC: allow-listed archive with secret scan and SHA-256, copy over SSH, verify, unpack.
# Never overwrites an active campaign: refuses if a status file reports a running lane.
. (Join-Path $PSScriptRoot "hpc.config.ps1")
function Check($what) { if ($LASTEXITCODE -ne 0) { throw "$what failed (exit $LASTEXITCODE)" } }

$python = Join-Path $LocalRoot "semantic-sim-layer\.venv\Scripts\python.exe"
& $python (Join-Path $PSScriptRoot "build_archive.py") $Archive; Check "Archive build"
$localSha = (Get-Content "$Archive.sha256" -Raw).Trim()

ssh $Remote "mkdir -p $RemoteDir"; Check "SSH mkdir"
$active = ssh $Remote "cd $RemoteDir/websemantic 2>/dev/null && grep -l -E '\""step\"": \""(install|server|e1|replay|reproducibility)\""' status-gpu.json status-cpu.json 2>/dev/null"
if ($active) { throw "A campaign is running on the server ($active): push refused." }
scp $Archive "${Remote}:$RemoteDir/websemantic-hpc.zip"; Check "Copy"
$remoteSha = (ssh $Remote "sha256sum $RemoteDir/websemantic-hpc.zip | cut -d' ' -f1").Trim(); Check "Remote checksum"
if ($remoteSha -ne $localSha) { throw "Checksum mismatch after copy ($remoteSha vs $localSha)" }
ssh $Remote "cd $RemoteDir && unzip -oq websemantic-hpc.zip && rm websemantic-hpc.zip && sed -i 's/\r$//' websemantic/semantic-sim-layer/hpc/*.sh && ls websemantic"; Check "Unpack"
Write-Host "Pushed and verified (sha256 $localSha)."
Write-Host "In a JupyterLab terminal (H200 session, /workspace = /lustre/data/cyril.voyant.kg):"
Write-Host "  cd /workspace/semantic/websemantic/semantic-sim-layer && nohup bash hpc/run_all.sh > /workspace/semantic/run_all.out 2>&1 &"
