# Shared settings for the HPC scripts. Edit RemoteDir once Cyril gives the final directory.
$Remote    = "cyril.voyant.kg@10.68.6.58"
$RemoteDir = "/lustre/data/cyril.voyant.kg/websemantic"     # seen as /workspace/websemantic inside JupyterLab
$LocalRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)   # ...\Documents\websemantic
$Archive   = Join-Path $LocalRoot "websemantic-hpc.zip"
