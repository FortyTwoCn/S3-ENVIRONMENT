param(
  [Parameter(Mandatory=$true)][string]$Port,
  [ValidateSet('yd_uart','yd_native_usb')][string]$Variant='yd_uart',
  [string]$Python='python'
)
$ErrorActionPreference='Stop'
$monitorFirmwareDir=Join-Path $PSScriptRoot "prebuilt/$Variant"
if(-not(Test-Path (Join-Path $monitorFirmwareDir 'firmware.bin'))){throw '缺少预编译固件'}
# esptool v4 is used for the flags below. No erase_flash: retains previously saved NVS.
& $Python -m esptool --chip esp32s3 --port $Port --baud 460800 --before default_reset --after hard_reset write_flash --flash_mode dio --flash_freq 80m --flash_size 16MB 0x0 (Join-Path $monitorFirmwareDir 'bootloader.bin') 0x8000 (Join-Path $monitorFirmwareDir 'partitions.bin') 0xe000 (Join-Path $monitorFirmwareDir 'boot_app0.bin') 0x10000 (Join-Path $monitorFirmwareDir 'firmware.bin')
if($LASTEXITCODE -ne 0){throw '烧录失败，请确认 COM 口、USB 线与 BOOT/RST 状态'}
Write-Host '烧录完成。打开 115200 波特率串口，查看首次配网热点与密码。'
