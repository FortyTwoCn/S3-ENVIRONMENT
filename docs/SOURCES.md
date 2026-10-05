# 技术资料与依赖来源

以下使用官方文档 / 项目仓库核对接口；具体 PHP 依赖版本以 composer.lock 为准，固件主依赖版本以 platformio.ini 为准。

| 资料 | 来源 | 本项目用途 |
|---|---|---|
| PHP Windows | https://www.php.net/downloads.php?os=windows | PHP 8.5.11 x64 NTS；官方归档 ZIP / SHA256 |
| PHP sessions | https://www.php.net/manual/en/features.session.security.management.php | 会话、Cookie、严格模式与令牌撤销 |
| Docker PHP 官方镜像 | https://github.com/docker-library/php/blob/master/8.5/bookworm/fpm/Dockerfile | 确认镜像已有 mbstring/sodium；额外安装 pdo_pgsql |
| Composer | https://getcomposer.org/download/ | 依赖锁定、安装与 advisory audit |
| Ratchet | https://github.com/ratchetphp/Ratchet | PHP RFC6455 服务 |
| Ratchet RFC6455 | https://github.com/ratchetphp/RFC6455 | 帧/消息大小上限、控制帧 |
| ReactPHP event loop | https://reactphp.org/event-loop/ | WebSocket 事件循环、派发定时器 |
| PHPMailer | https://github.com/PHPMailer/PHPMailer | SMTP / STARTTLS / SMTPS，邮箱授权码 |
| PostgreSQL 17 | https://www.postgresql.org/docs/17/ | JSONB、PDO SQL、索引、保留任务 |
| PostgreSQL dump | https://www.postgresql.org/docs/17/backup-dump.html | 备份 / 恢复 |
| Windows PostgreSQL | https://www.enterprisedb.com/download-postgresql-binaries | 本机便携 PostgreSQL 17.6 官方二进制 |
| Caddy TLS | https://caddyserver.com/docs/caddyfile/directives/tls | HTTPS、ACME 与首选根证书链 |
| Docker Compose merge | https://docs.docker.com/reference/compose-file/merge/ | production 文件端口 / 挂载覆盖 |
| Chart.js | https://www.chartjs.org/docs/latest/ | 线性时间坐标、趋势、缺失读数、Canvas 渲染 |
| Chart.js release | https://github.com/chartjs/Chart.js/releases/tag/v4.5.1 | 随包放置前端脚本与许可证，无运行时 CDN 依赖 |
| Arduino WebSockets | https://github.com/Links2004/arduinoWebSockets | beginSslWithCA、事件、ACK、socket cleanup / reconnect |
| BME 驱动 | https://github.com/adafruit/Adafruit_BME680 | BME688 的 BME68x 原始读数、beginReading / endReading |
| BH1750 | https://github.com/claws/BH1750 | I2C 地址、连续高分辨率读取 |
| ESP32 Arduino | https://docs.espressif.com/projects/arduino-esp32/en/latest/ | Wi-Fi、ADC、HardwareSerial、Preferences |
| PlatformIO board | https://docs.platformio.org/en/latest/boards/espressif32/esp32-s3-devkitc-1.html | 软件构建目标；N16R8 设置单独覆盖 |
| Let's Encrypt 根证书 | https://letsencrypt.org/certificates/ | ISRG Root X1；固件 PEM 来自 https://letsencrypt.org/certs/isrgrootx1.pem |
| Windows PHP CA bundle | https://curl.se/docs/caextract.html | Windows SMTP TLS 根证书集合 |

电路参数 / GPIO / 模块排针来源是同一工作区的 `outputs/hardware/fabrication/interface_pinout.csv`、`gpio_map.csv` 和现有固件测试工程；没有从通用 DevKit Footprint 推导实际 PCB 机械尺寸。

PHP 依赖随包保留许可证，Chart.js 提供 MIT 许可证，Arduino WebSockets 为 LGPL-2.1。预编译固件对应的完整应用源码与依赖版本均在本包；主机工具下载到本机缓存，不属于自写项目源码。
