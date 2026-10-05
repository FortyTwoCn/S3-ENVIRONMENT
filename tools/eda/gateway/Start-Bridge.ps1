param([string]$NodeExe='node')
$ErrorActionPreference = 'Stop'
$gatewayRoot = $PSScriptRoot
$nodeCommand = Get-Command $NodeExe -ErrorAction Stop
$nodeExe = $nodeCommand.Source
$bridgeScript = Join-Path $gatewayRoot 'scripts/bridge-server.mjs'
$logRoot = Join-Path $gatewayRoot 'logs'
New-Item -ItemType Directory -Path $logRoot -Force | Out-Null

function Find-EdaBridge {
    foreach ($gatewayPort in 49620..49629) {
        try {
            $state = Invoke-RestMethod -Uri "http://127.0.0.1:$gatewayPort/health" -TimeoutSec 1
            if ($state.service -eq 'easyeda-bridge') {
                return [pscustomobject]@{ port = $gatewayPort; health = $state }
            }
        } catch {}
    }
    return $null
}

$existingBridge = Find-EdaBridge
if ($existingBridge) {
    $existingBridge | ConvertTo-Json -Depth 6
    exit 0
}
if (!(Test-Path -LiteralPath $nodeExe)) { throw "Node runtime missing: $nodeExe" }
if (!(Test-Path -LiteralPath $bridgeScript)) { throw "Bridge script missing: $bridgeScript" }
$bridgeProcess = Start-Process -FilePath $nodeExe -ArgumentList @('"' + $bridgeScript + '"') -WorkingDirectory $gatewayRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logRoot 'bridge.stdout.log') -RedirectStandardError (Join-Path $logRoot 'bridge.stderr.log') -PassThru
Set-Content -LiteralPath (Join-Path $logRoot 'bridge.pid') -Value $bridgeProcess.Id -Encoding ascii
foreach ($attempt in 1..20) {
    Start-Sleep -Milliseconds 500
    $bridgeState = Find-EdaBridge
    if ($bridgeState) {
        [pscustomobject]@{ pid = $bridgeProcess.Id; port = $bridgeState.port; health = $bridgeState.health } | ConvertTo-Json -Depth 6
        exit 0
    }
    if ($bridgeProcess.HasExited) { throw 'Bridge exited; check logs/bridge.stderr.log' }
}
throw 'Bridge startup timed out; check logs'
