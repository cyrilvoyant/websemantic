# Push the project to the HPC: build the archive (no secrets), copy it over SSH, unpack it on Lustre.
# Usage (PowerShell, from anywhere):  & "...\semantic-sim-layer\hpc\push.ps1"
. (Join-Path $PSScriptRoot "hpc.config.ps1")

$python = Join-Path $LocalRoot "semantic-sim-layer\.venv\Scripts\python.exe"
& $python (Join-Path $PSScriptRoot "build_archive.py") $Archive
if ($LASTEXITCODE -ne 0) { throw "Archive build failed" }

ssh $Remote "mkdir -p $RemoteDir"
if ($LASTEXITCODE -ne 0) { throw "SSH failed: check the connection" }
scp $Archive "${Remote}:$RemoteDir/websemantic-hpc.zip"
if ($LASTEXITCODE -ne 0) { throw "Copy failed" }
# Unpack without touching previous results (runs/ and logs/ are never in the archive).
ssh $Remote "cd $RemoteDir && unzip -oq websemantic-hpc.zip && rm websemantic-hpc.zip && sed -i 's/\r$//' websemantic/semantic-sim-layer/hpc/*.sh && echo 'pushed:' && ls websemantic"
Write-Host "Done. In a JupyterLab terminal (H200 session, Lustre mounted on /workspace):"
Write-Host "  cd /workspace/websemantic/websemantic/semantic-sim-layer && nohup bash hpc/run_all.sh > /workspace/websemantic/run_all.out 2>&1 &"
