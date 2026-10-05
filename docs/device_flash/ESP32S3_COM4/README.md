# ESP32-S3 实物烧录记录

2026-10-05，通过 COM4 / CH343 完成烧录。固件 `carrier-network-1.0.1`，16MB Flash、8MB PSRAM 已确认。实物已通过 WSS 认证，服务器已确认接收记录。

网站：[s.xuanknow.cn](https://s.xuanknow.cn/)。设备名称：ESP32-S3 环境监测。WSS 接口 `wss://s.xuanknow.cn/ws`，验证服务器证书，不跳过 TLS 验证。

Wi-Fi 名称 `<CONFIGURED_WIFI>`；密码按用户提供的值写入私有 NVS，未写入源码、预编译固件或公开交付包。设备令牌沿用网站上已创建的设备，未修改网站密码。上电自动连接，断线自动重试，正常 300 秒发送一次；网页“立即采样”会请求新的读数。

Windows 热点原先为自动频段、WPA3 混合模式；改为 2.4GHz / WPA2 后实物获取 IP。SSID 和密码未更改。若换手机／其它设备热点，保持名称、密码相同，关闭电脑同名热点以便重连。

用户确认：电路板尚未到货，传感器暂未接入。当前 BH1750 与 BME688 未检测到，雷达无 UART 数据符合此状态。程序会记录缺失传感器状态，光照、环境指标为空，不模拟测量值；MQ 保持禁用，接线及加热预热确认后再在网页启用。

| 信号 | ESP32 GPIO |
|---|---:|
| I2C SDA | 8 |
| I2C SCL | 9 |
| LD2410C TX → ESP RX | 17 |
| ESP TX → LD2410C RX | 18 |
| LD2410C OUT | 16 |
| MQ AO，经 R1.1 6.8k / 7.5k 分压及滤波 | 4 |
| MQ DO，经 R1.1 Q1 保护电路 | 5 |

后续接线按既有载板 R1.1 工程。成品 MQ 的 5V AO / DO 必须经过保护电路；Q1 导致 DO 极性反转，固件默认 GPIO5 HIGH 为报警。GY/BME 模块使用 3.3V；LD/MQ 使用 SENSOR_5V。原 PCB 的机械校验仍待确认，本次烧录没有改变其状态。

串口使用 115200 波特率。`STATUS` 显示网络状态；`WIFI_SCAN` 主动扫描配置热点；`CONFIG` 或开机后长按 BOOT 5 秒进入配网页面。日志中的 PSRAM 可用堆 `8386279` 字节符合 8MB 硬件，堆管理开销不会表示容量不足。

烧录前已完整备份原 16MiB Flash；备份仅存于工作区私有目录 `work/device_flash/private/original_flash_20261005.bin`，没有加入交付 ZIP。写入前检查了芯片、Flash、PSRAM 和安全状态；未操作 eFuse，未改变 Secure Boot／加密设置。五个初始写入部分及 1.0.1 应用更新均通过下载器哈希校验。

`serial_boot.log` 是最终重启实测日志；`serial_network_switch.log` 保留初次配网及切换热点的过程；`boot_verification.json` 是启动／网络结果；`flash_report.json` 包含完整哈希及设备信息。`website_verification.json` 记录实物在线、PostgreSQL 入库、网页立即采样和浏览器 WSS 的 7 项验证；验证用临时登录已撤销，用户密码没有修改，实物采样记录保留在网站。`website_physical_device.png` 是实际设备页面截图。
