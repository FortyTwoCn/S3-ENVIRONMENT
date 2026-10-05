$ErrorActionPreference='Stop'
$monitorRuntime=Join-Path $PSScriptRoot '.runtime'
$monitorPidFile=Join-Path $monitorRuntime 'processes.json'
if(Test-Path $monitorPidFile){
    foreach($monitorRecorded in (Get-Content $monitorPidFile -Raw | ConvertFrom-Json)){
        $monitorProc=Get-Process -Id $monitorRecorded.Pid -ErrorAction SilentlyContinue
        $monitorStarted=[DateTime]$monitorRecorded.StartTime
        if($monitorProc -and $monitorProc.Path -eq $monitorRecorded.Executable -and $monitorProc.StartTime.ToUniversalTime() -eq $monitorStarted.ToUniversalTime()){Stop-Process -Id $monitorProc.Id}
    }
    Move-Item -LiteralPath $monitorPidFile -Destination (Join-Path $monitorRuntime ('processes-stopped-'+(Get-Date -Format 'yyyyMMddHHmmss')+'.json'))
}
$monitorWorkspaceTools=Join-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) 'work/monitor_tools'
$monitorPg=if(Test-Path (Join-Path $monitorWorkspaceTools 'pg/pgsql/bin/pg_ctl.exe')){Join-Path $monitorWorkspaceTools 'pg/pgsql/bin/pg_ctl.exe'}else{Join-Path $monitorRuntime 'tools/pg/pgsql/bin/pg_ctl.exe'}
if(Test-Path (Join-Path $monitorRuntime 'pgdata/PG_VERSION')){& $monitorPg -D (Join-Path $monitorRuntime 'pgdata') stop -m fast}
Write-Host '本机服务已停止，数据和配置均保留。'
