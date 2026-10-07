# Where are we? Reads the status file and logs written by run_all.sh on Lustre (login node, no GPU needed).
. (Join-Path $PSScriptRoot "hpc.config.ps1")
$cmd = @"
cd $RemoteDir/websemantic 2>/dev/null || { echo 'Nothing pushed yet'; exit 0; }
echo '== status'; cat status.json 2>/dev/null || echo 'run_all.sh not started'
echo '== answers per model'; for d in benchmark-reserve/runs/e1/*/; do echo "`$(basename `$d): `$(ls `$d | wc -l)"; done 2>/dev/null
echo '== GPU lane (last lines)'; tail -n 5 logs/gpu.log 2>/dev/null
echo '== CPU lane (last lines)'; tail -n 5 logs/cpu.log 2>/dev/null
"@
ssh $Remote $cmd
