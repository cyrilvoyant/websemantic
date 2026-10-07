# Start run_all.sh on the HPC over SSH (detached). If the SSH shell has no GPU, the GPU lane reports it in status.json.
. (Join-Path $PSScriptRoot "hpc.config.ps1")
ssh $Remote "cd $RemoteDir/websemantic/semantic-sim-layer && nohup bash hpc/run_all.sh > $RemoteDir/websemantic/run_all.out 2>&1 < /dev/null & echo started"
Write-Host "Follow with: & '$PSScriptRoot\status.ps1'"
