param([string]$PublicUrl='')
$ErrorActionPreference='Stop'
$monitorRoot=$PSScriptRoot
$monitorRuntime=Join-Path $monitorRoot '.runtime'
New-Item -ItemType Directory -Force $monitorRuntime | Out-Null
$monitorWorkspaceTools=Join-Path (Split-Path (Split-Path $monitorRoot -Parent) -Parent) 'work/monitor_tools'
if(Test-Path (Join-Path $monitorWorkspaceTools 'php/php.exe')){$monitorTools=$monitorWorkspaceTools}else{$monitorTools=Join-Path $monitorRuntime 'tools'}
New-Item -ItemType Directory -Force $monitorTools | Out-Null
function Get-MonitorTool([string]$Url,[string]$Archive,[string]$Target,[string]$Executable,[string]$Sha256=''){
    if(Test-Path $Executable){return}
    $monitorArchivePath=Join-Path $monitorTools $Archive
    Write-Host "下载 $Archive（仅首次需要）"
    Invoke-WebRequest -Uri $Url -OutFile $monitorArchivePath
    if($Sha256 -and (Get-FileHash $monitorArchivePath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $Sha256){throw "校验失败：$Archive"}
    New-Item -ItemType Directory -Force $Target | Out-Null
    Expand-Archive -LiteralPath $monitorArchivePath -DestinationPath $Target -Force
}
$monitorPhp=Join-Path $monitorTools 'php/php.exe'
Get-MonitorTool 'https://downloads.php.net/~windows/releases/archives/php-8.5.11-nts-Win32-vs17-x64.zip' 'php.zip' (Join-Path $monitorTools 'php') $monitorPhp '0ea96e0d2b9b737a6036f05cf4e95c49313faa6d0f27bd97edb2742503f0c043'
$monitorPg=Join-Path $monitorTools 'pg/pgsql/bin'
Get-MonitorTool 'https://get.enterprisedb.com/postgresql/postgresql-17.6-1-windows-x64-binaries.zip' 'postgres.zip' (Join-Path $monitorTools 'pg') (Join-Path $monitorPg 'pg_ctl.exe') 'd378882abd001a186735acd6f6ba716bca6ccd192e800412d4fd15ed25376b3e'
$monitorCaddy=Join-Path $monitorTools 'caddy/caddy.exe'
Get-MonitorTool 'https://github.com/caddyserver/caddy/releases/download/v2.11.7/caddy_2.11.7_windows_amd64.zip' 'caddy.zip' (Join-Path $monitorTools 'caddy') $monitorCaddy
$monitorCa=Join-Path $monitorTools 'cacert.pem'
if(-not(Test-Path $monitorCa)){Invoke-WebRequest -Uri 'https://curl.se/ca/cacert.pem' -OutFile $monitorCa}
$monitorIni=Join-Path $monitorRuntime 'php.ini'
$monitorPhpExt=Join-Path (Split-Path $monitorPhp -Parent) 'ext'
@"
extension_dir="$monitorPhpExt"
extension=pdo_pgsql
extension=openssl
extension=sodium
extension=mbstring
openssl.cafile="$monitorCa"
date.timezone=UTC
memory_limit=256M
display_errors=Off
log_errors=On
"@ | Set-Content -LiteralPath $monitorIni -Encoding utf8
if(-not(Test-Path (Join-Path $monitorRoot 'server/vendor/autoload.php'))){throw '缺少 server/vendor；请下载完整发布包，或先在 server/ 执行 composer install'}
$monitorEnvFile=Join-Path $monitorRoot 'server/.env'
if(-not(Test-Path $monitorEnvFile)){
    if(-not $PublicUrl){
        $monitorNet=Get-NetIPConfiguration | Where-Object { $_.IPv4DefaultGateway -and $_.IPv4Address } | Select-Object -First 1
        $monitorIp=if($monitorNet){$monitorNet.IPv4Address.IPAddress | Select-Object -First 1}else{'127.0.0.1'}
        $PublicUrl="http://${monitorIp}:8080"
    }
    if($PublicUrl -notmatch '^http://[^/]+:8080$'){throw 'Windows 本机/局域网启动器使用 http://电脑IP:8080；公网请使用 Docker HTTPS 配置'}
    $monitorSecurePassword=Read-Host '设置网站密码（至少 12 字符，最多 72 字节）' -AsSecureString
    $monitorPlain=[System.Net.NetworkCredential]::new('',$monitorSecurePassword).Password
    try{$monitorPlain | & $monitorPhp -c $monitorIni (Join-Path $monitorRoot 'server/bin/setup.php') "--url=$PublicUrl" --local}catch{throw}finally{$monitorPlain=$null}
    if($LASTEXITCODE -ne 0){throw '网站配置生成失败'}
    $monitorEnvText=Get-Content -LiteralPath $monitorEnvFile -Raw
    $monitorEnvText=$monitorEnvText -replace "DB_HOST='db'","DB_HOST='127.0.0.1'"
    $monitorEnvText=$monitorEnvText -replace "DB_PORT='5432'","DB_PORT='54330'"
    $monitorSessionDir=(Join-Path $monitorRuntime 'sessions').Replace('\','/')
$monitorEnvText=$monitorEnvText -replace "SESSION_PATH='/tmp/sensor-sessions'","SESSION_PATH='$monitorSessionDir'"
    Set-Content -LiteralPath $monitorEnvFile -Value $monitorEnvText -Encoding utf8
}
$monitorConfig=@{}
foreach($monitorLine in Get-Content -LiteralPath $monitorEnvFile){if($monitorLine -match '^([A-Z0-9_]+)=(.*)$'){$monitorConfig[$matches[1]]=$matches[2].Trim().Trim("'").Trim('"')}}
if($monitorConfig.DB_HOST -ne '127.0.0.1' -or $monitorConfig.DB_PORT -ne '54330'){throw '此 .env 属于其它部署环境，启动器不会改写它。请按 README 的 Docker/手动方式运行。'}
$monitorData=Join-Path $monitorRuntime 'pgdata'
if(-not(Test-Path (Join-Path $monitorData 'PG_VERSION'))){
    $monitorPwFile=Join-Path $monitorRuntime 'db-init-password.txt'
    [System.IO.File]::WriteAllText($monitorPwFile,$monitorConfig.DB_PASSWORD,[System.Text.UTF8Encoding]::new($false))
    & (Join-Path $monitorPg 'initdb.exe') -D $monitorData -U $monitorConfig.DB_USER -A scram-sha-256 --encoding=UTF8 --locale=C "--pwfile=$monitorPwFile"
    if($LASTEXITCODE -ne 0){throw 'PostgreSQL 初始化失败'}
    # Clear temporary password content using a single native filesystem API.
    [System.IO.File]::WriteAllText($monitorPwFile,'',[System.Text.UTF8Encoding]::new($false))
}
& (Join-Path $monitorPg 'pg_ctl.exe') -D $monitorData status *> $null
if($LASTEXITCODE -ne 0){
    & (Join-Path $monitorPg 'pg_ctl.exe') -D $monitorData -l (Join-Path $monitorRuntime 'postgres.log') -o '-h 127.0.0.1 -p 54330' start
    if($LASTEXITCODE -ne 0){throw 'PostgreSQL 启动失败'}
}
$env:PGPASSWORD=$monitorConfig.DB_PASSWORD
try{& (Join-Path $monitorPg 'createdb.exe') -h 127.0.0.1 -p 54330 -U $monitorConfig.DB_USER $monitorConfig.DB_NAME 2>$null}finally{$env:PGPASSWORD=$null}
& $monitorPhp -c $monitorIni (Join-Path $monitorRoot 'server/bin/migrate.php')
if($LASTEXITCODE -ne 0){throw '数据库迁移失败'}
$monitorPidFile=Join-Path $monitorRuntime 'processes.json'
if(Test-Path $monitorPidFile){throw '进程记录已存在；请先运行 stop_windows.ps1，避免重复服务'}
$monitorCaddyConfig=Join-Path $monitorRuntime 'Caddyfile'
@"
{
    admin off
}
:8080 {
    @ws path /ws
    handle @ws {
        reverse_proxy 127.0.0.1:8081
    }
    handle {
        reverse_proxy 127.0.0.1:8082
    }
}
"@ | Set-Content -LiteralPath $monitorCaddyConfig -Encoding utf8
# Bind DB, PHP HTTP and raw WS to loopback; Caddy exposes only port 8080.
$env:WS_BIND='127.0.0.1'
$monitorStarts=@(
    @{Name='web';Exe=$monitorPhp;Args=@('-c',"`"$monitorIni`"",'-S','127.0.0.1:8082','-t',"`"$(Join-Path $monitorRoot 'server/public')`"","`"$(Join-Path $monitorRoot 'server/public/router.php')`"")},
    @{Name='websocket';Exe=$monitorPhp;Args=@('-c',"`"$monitorIni`"","`"$(Join-Path $monitorRoot 'server/bin/websocket.php')`"")},
    @{Name='worker';Exe=$monitorPhp;Args=@('-c',"`"$monitorIni`"","`"$(Join-Path $monitorRoot 'server/bin/worker.php')`"")},
    @{Name='proxy';Exe=$monitorCaddy;Args=@('run','--config',"`"$monitorCaddyConfig`"")}
)
$monitorProcesses=@()
foreach($monitorStart in $monitorStarts){
    $monitorProc=Start-Process -FilePath $monitorStart.Exe -ArgumentList $monitorStart.Args -WorkingDirectory (Join-Path $monitorRoot 'server') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $monitorRuntime "$($monitorStart.Name).log") -RedirectStandardError (Join-Path $monitorRuntime "$($monitorStart.Name).err.log")
    $monitorProcesses+=@{Name=$monitorStart.Name;Pid=$monitorProc.Id;Executable=$monitorStart.Exe;StartTime=$monitorProc.StartTime.ToUniversalTime().ToString('o')}
}
$monitorProcesses | ConvertTo-Json | Set-Content -LiteralPath $monitorPidFile -Encoding utf8
Start-Sleep -Seconds 2
foreach($monitorRecorded in $monitorProcesses){if(-not(Get-Process -Id $monitorRecorded.Pid -ErrorAction SilentlyContinue)){throw "服务 $($monitorRecorded.Name) 启动失败，请查看 .runtime 日志"}}
Write-Host "网站已启动：$($monitorConfig.APP_URL)"
Write-Host 'ESP32 和电脑需在同一局域网；Windows 防火墙需允许私有网络 TCP 8080。'
Write-Host '停止网站：运行 stop_windows.ps1；所有真实数据保存在 .runtime/pgdata。'
