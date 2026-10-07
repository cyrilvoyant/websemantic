# The SSH login node has no GPU and Python 3.6 (checked 7 Oct 2026): run_all.sh must be started from a
# JupyterLab terminal of an H200 session, where /workspace = /lustre/data/cyril.voyant.kg.
. (Join-Path $PSScriptRoot "hpc.config.ps1")
Write-Host "In a JupyterLab terminal (H200 session, Lustre mounted on /workspace), run:"
Write-Host "  cd /workspace/semantic/websemantic/semantic-sim-layer && nohup bash hpc/run_all.sh > /workspace/semantic/run_all.out 2>&1 &"
Write-Host "Then follow from this PC with status.ps1."
