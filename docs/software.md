# ESP32-S3 多传感器网络监测站

这套工程把现有 ESP32-S3 载板上的传感器读数，经 Wi-Fi / WebSocket 上传至 PHP 网站，使用 PostgreSQL 保存。网页支持密码登录、记住登录、历史表格、曲线、CSV 导出、立即采样、设备配置与 SMTP 烟雾通知。

已包含完整网站源码、PHP 依赖、数据库结构、ESP32 源码、两种 USB 版本的预编译固件、Windows 启停脚本、Docker 公网部署配置和测试结果。没有将 Wi-Fi 密码、网站密码或实际邮箱授权码写进固件。网页截图使用明确标注的模拟数据。

**网站已部署到 https://s.xuanknow.cn；2026-10-05 已通过 COM4 给实物烧录 `carrier-network-1.0.2`，确认 16MB Flash、8MB PSRAM、自动联网、WSS 上传和 PostgreSQL 入库，网页“立即采样”已得到实物响应。1.0.2 修复 MQ 未启用时上传悬空读数的问题，增加 I2C 扫描和传感器重试命令。当前两块 I2C 模块尚未应答，MQ 未连接、雷达未供电，不能声称四传感器测量已通过。最新验证见 `test_results/physical_bringup_1.0.2.json`；`physical_flash.json` 和 `physical_website.json` 保留 1.0.1 的历史联网验证。** 原 PCB 的机械验证状态仍以 `hardware/README.md` 为准。

## 1. 先在这台 Windows 电脑启动

在本目录打开 PowerShell：

```powershell
powershell -ExecutionPolicy Bypass -File .\start_windows.ps1
```

首次运行设置网站密码。启动器自动选择电脑的局域网 IP，网站端口为 `8080`；最后会打印完整访问地址。也可以自己指定：

```powershell
powershell -ExecutionPolicy Bypass -File .\start_windows.ps1 -PublicUrl "http://192.168.1.23:8080"
```

这里的 IP 要换成电脑的实际局域网 IP。浏览器必须使用生成配置时的同一个地址，ESP32 也须能访问它。不要把 `localhost` / `127.0.0.1` 填成 ESP32 的网站主机——在 ESP32 上它们指向设备自身。

启动器会启动 PostgreSQL、PHP 页面服务、PHP WebSocket 服务、邮件/清理任务与 Caddy，窗口均在后台运行。这台电脑已有本项目下载的工具时会复用；换电脑后会下载官方 Windows PHP、PostgreSQL 和 Caddy。完整发布包已包含 `server/vendor/`，无需先安装 Composer。

真实数据保存在 `.runtime/pgdata`，配置保存在 `server/.env`。关闭 PowerShell 窗口不会自动停止后台服务；停止请执行：

```powershell
powershell -ExecutionPolicy Bypass -File .\stop_windows.ps1
```

停止和重新启动都会保留数据。若需要 ESP32 从局域网访问，允许 Windows 防火墙的**私有网络 TCP 8080**；其它数据库与内部服务端口只绑定本机。建议为电脑设置固定 DHCP 地址，避免 IP 改变后需要重新配网。此启动方式用于本机 / 可信局域网；公网使用下方 HTTPS 部署。

## 2. 烧录 ESP32-S3

这块实物是双 Type-C、CH343P、44Pin 的 N16R8 开发板。PlatformIO 使用 DevKitC 软件目标构建，显式配置 **16MB Flash / QIO / 8MB OPI PSRAM**；不据此替换实际 PCB 封装。

优先用 USB 转串口 Type-C，烧录 `yd_uart`，然后从该 USB 串口查看 115200 波特率日志。另一份 `yd_native_usb` 将 `Serial` 输出到 ESP32 的原生 USB CDC。

### 直接烧录预编译固件

安装 Python 和 esptool 4：

```powershell
python -m pip install "esptool>=4.9,<5"
.\firmware\flash.ps1 -Port COM5 -Variant yd_uart
```

把 `COM5` 改成实际端口。下载器无法自动进入下载模式时，按住 BOOT、按一下 RST、释放 BOOT，再重试。不要在重新上电前一直按住 BOOT，否则会进入 ROM 下载模式。

`firmware/prebuilt/<版本>/` 中也提供 `merged_flash.bin`，可以用支持 ESP32-S3 的烧录工具在 **0x0000** 写入。合并镜像的空隙包括 NVS 区域，写入后会清除原配网信息；更新已有配置的设备优先用上述 `flash.ps1` 分立文件方式。四个分立文件的地址是：

| 文件 | 地址 |
|---|---:|
| bootloader.bin | 0x0000 |
| partitions.bin | 0x8000 |
| boot_app0.bin | 0xE000 |
| firmware.bin | 0x10000 |

烧录脚本不执行整片擦除，已保存的配网信息通常可保留。改变分区布局或使用其它工程后应重新确认 NVS 状态。

### 从源码构建

```powershell
python -m pip install platformio
python -m platformio run --project-dir firmware -e yd_uart
python -m platformio run --project-dir firmware -e yd_uart -t upload --upload-port COM5
python -m platformio device monitor --port COM5 --baud 115200
```

另一环境名为 `yd_native_usb`。`platformio.ini` 已固定 Arduino / 主要传感器和 WebSocket 库版本，代码不需要填写 Wi-Fi 密码即可编译。

固件 1.0.1 增加不显示密码或令牌的串口诊断：输入 `STATUS` 查看连接、IP、校时与认证状态；输入 `WIFI_SCAN` 扫描配置的热点，查看频段、安全模式和信号。扫描是主动诊断操作，可能短暂影响连接，正常运行无需执行。`Telemetry acknowledged: seq=...` 表示服务器已接收对应记录。Windows 热点建议固定为 2.4GHz；这台电脑的 WPA3 混合模式连接失败，改用 WPA2 后实物取得了 IP。

## 3. 首次配网与设备接入

1. 登录网站，进入“配置”，输入设备名称并“创建设备”。复制只显示一次的 **64 字符设备令牌**。网站会同时显示 WebSocket 主机、端口、路径和 TLS 要求。
2. ESP32 首次启动时开启 `SensorCarrier-xxxx` 热点。**临时热点密码在 115200 串口打印，每次进入配网会重新生成**。
3. 用手机或电脑连接该热点；手动访问 `http://192.168.4.1`。不依赖系统自动弹出配网页面。
4. 填写 2.4GHz Wi-Fi 的 SSID 和密码、网站主机、端口、路径 `/ws` 与设备令牌。主机只填域名或 IP，不含 `https://`。
5. Windows 局域网示例：主机 `192.168.1.23`、端口 `8080`、TLS 关闭。公网示例：主机 `sensors.example.com`、端口 `443`、TLS 开启。
6. 保存后设备重启，自动连接 Wi-Fi，向 WebSocket 服务发送鉴权消息。网站显示在线，并收到初始读数；随后默认每 **300 秒**发送一次。

以后更改配网：设备正常运行后按住 BOOT 约 5 秒，或者在串口发送 `CONFIG` 加换行。填写空白 Wi-Fi 密码 / 令牌时保留当前值；开放 Wi-Fi 需要明确勾选“使用开放 Wi-Fi”。保存配置保存在 NVS，重启自动使用。

WSS 使用 CA 校验，**没有 `setInsecure()` 降级路径**。默认内置 Let's Encrypt 的 ISRG Root X1；其它 CA 可以在配网页面粘贴对应根证书，最大 3500 字节。若域名使用其它证书链，应先核实根证书。启用 WSS 后必须能完成 NTP 校时；默认使用 `pool.ntp.org`、`time.cloudflare.com`、`ntp.aliyun.com`，防火墙需允许相应 NTP 访问。

## 4. 与现有 PCB 的对应关系

使用当前 `hardware` 工程 R1.1 的网络和实际接口次序：

| 信号 | ESP32 GPIO | 模块 / 功能 |
|---|---:|---|
| I2C SDA | 8 | GY-302 与 BME688 共用 |
| I2C SCL | 9 | GY-302 与 BME688 共用 |
| Radar RX | 17 | 接 LD2410C TX |
| Radar TX | 18 | 接 LD2410C RX |
| Radar OUT | 16 | 人体存在输出 |
| MQ ADC | 4 | 分压 / 滤波后的模拟输入 |
| MQ DO | 5 | 经底板 MOSFET 反相后的数字输入 |
| 配网按钮 | 0 | 只读取板载 BOOT 按钮，不作为扩展输出 |

GPIO19/20、35/36/37、45/46 不作普通外设接口；GPIO6/7/10/11、舵机接口保留，不由本程序主动驱动。

| 底板接口 | 从 PCB Pad 1 开始的引脚标签 |
|---|---|
| J2 / GY-302 | ADDR、SDA、SCL、GND、VCC |
| J3 / BME688 | VCC、GND、SCL、SDA、SDO、CS |
| J4 / LD2410C | TX、RX、OUT、GND、VCC |
| J5 / MQ | VCC、GND、DO、AO |

**按 PCB 丝印和 Pad 编号插模块，不能拿初始文字中的排针顺序替代当前 R1.1 文件。** 使用面包板测试时直接按 GPIO 表和电源网络连接即可，仍需保留所有 5V→3.3V 保护电路。

- BH1750 默认地址 `0x23`，找不到会尝试 `0x5C`。
- BME688 默认 `0x76`，找不到会尝试 `0x77`。使用 Adafruit BME680/BME68x 驱动读取 BME688 原始温湿度、气压和气体电阻；没有 BSEC 的 IAQ / CO₂ 算法。
- LD2410C 串口 `256000 / 8N1`，TX→GPIO17、RX←GPIO18，OUT→GPIO16。保存 UART 活动状态、累计字节、近期十六进制片段；人体存在主要依据 OUT，UART 无活动时以缺失状态显示。此版本未解析距离/运动能量，也不发送雷达参数设置命令。
- MQ 电路按 **Rtop=6.8k、Rbottom=7.5k、ADC 侧 100k 下拉**计算：`Rlow=7.5k∥100k≈6.9767k`；`ADC/AO≈0.5064146`；`AO≈ADC×1.9746667`。正常 AO=5V 时 ADC≈2.532V。若仍用最初面包板的 4.7k 分压或其它电路，请修改固件对应常量，不能套用本比例。
- GPIO5 经过 Q1 **反相**：典型 MQ 原始 DO 为 LOW 时，GPIO5 是 HIGH。网页默认 HIGH 为告警电平，可按实际模块验证后改为 LOW。

## 5. 电源与初次上电

ESP32 仍通过开发板 USB 供电，GY-302 / BME688 使用开发板 3.3V。MQ 与 LD2410C 使用 `SENSOR_5V`，由 JP3 的**一只跳帽**选择开发板 5V 或外部 5V，不能同时短接两侧。MQ 加热器和雷达推荐独立 5V / 2A 供电，外部供电与 USB 共地。程序不更改该电源架构，也不让伺服接口从 ESP32 默认取电。

建议先按硬件工程 bring-up 顺序检查电源、USB、BH1750、BME688、雷达，最后接 MQ。确认 GPIO4 对地电压安全、分压比例正确，以及实际 DO 在阈值前后的极性。

网站默认 **不启用 MQ 烟雾判定**。底板没有传感器 5V 在位检测；未插 MQ / 未供电时，GPIO5 的下拉/上拉状态可能与告警相同。确认 MQ 供电与阈值后，再在网页勾选“确认 MQ 已供电，启用烟雾检测”。不应仅凭插上 ESP32 就自动把该信号当成烟雾。

固件 1.0.2 开始，`mq_enabled=false` 时原始 ADC、分压电压、AO 电压和 GPIO5 均上传 `null`；网站显示“未启用”，不把悬空读数当作 MQ 数据。每条新记录带 `mq_enabled` 标志。旧版固件留下的历史记录保留原样，旧记录中的数值不证明 MQ 当时已连接。即使启用 MQ，程序也不能自动判断模拟模块是否真实插入，启用前仍需人工检查供电和保护电路。

串口 115200 新增 `I2C_SCAN`（扫描 GPIO8/SDA、GPIO9/SCL）、`SENSOR_RETRY`（重新初始化两块 I2C 模块，无需重新烧录）和 `REBOOT`。`STATUS` 同时打印检测状态与 SDA/SCL 电平。正常地址为 BH1750 `0x23/0x5C`、BME688 `0x76/0x77`。若扫描为 0 个设备，先检查模块端 3.3V、共地、排针焊接、杜邦线接触及 SDA/SCL 实际导通；图纸上连接正确不代表实物已导通。串口诊断期间不要发送 `CONFIG`，除非确实需要重新配网。

默认预热 180 秒、持续触发 3 秒、持续恢复 10 秒。预热和首次老化时长应按**实际 MQ 型号**调整；180 秒不是所有型号充分老化的保证。网页支持数字 DO、模拟 ADC 或二者任一触发；模拟阈值单位为 **分压后的 ADC mV**，默认阈值 2000mV、回差 100mV，须按实际基线设定。

MQ 原始 ADC / 电压与 BME 气体电阻不能直接理解为烟雾浓度 ppm、IAQ 或 CO₂。网页保存和显示实际原始量。

## 6. 通信、断线与立即采样

```text
ESP32 传感器 → Wi-Fi → WebSocket/WSS → PHP WebSocket 服务 → PostgreSQL
                                      ↓
浏览器 ← 实时通知 + 历史 PHP API        邮件队列 → PHP worker → SMTP
浏览器 → 立即采样 API → commands 表 → WebSocket → ESP32 新采样 → 保存 / ACK
```

- 正常约每 2 秒完成一次本地传感器读取；默认每 5 分钟上报一次。BME 读取采用异步等待，MQ 持续触发后立即生成告警记录，不等待常规 5 分钟周期。
- Wi-Fi / WebSocket 断开自动重试，带退避和随机抖动，最长约 60 秒。DNS、TCP、TLS 建连仍可能占用一段时间，不能把本程序的采样周期理解为硬实时保证。
- 设备与网页均每约 25 秒发送心跳；无心跳约 90 秒视为离线。浏览器断线会重连，并保留最近数据；还有 15 秒一次的 HTTP 刷新作为补偿。
- 固件内存队列最多 256 条，优先使用 N16R8 的 PSRAM，需确认串口显示 8MB PSRAM。正常 5 分钟间隔约能缓存 **21 小时 20 分钟**；告警 / 请求也占用队列。满时优先丢弃旧的普通记录，并上报丢弃计数；断电 / 重启会丢失内存缓存。
- 样本具有随机 `boot_id` 和递增 `seq`；收到服务器 ACK 才移出队列，重传不会重复入库。告警 / 立即采样优先于普通补传积压。
- 正常使用 NTP 采样时间；未校时的局域网测试使用服务器接收时间及排队年龄估计，表中标记时间质量。迟到超过 10 分钟的数据不产生新的当前邮件告警，乱序旧数据不会解除较新的告警。
- “立即采样”要求在线设备完成一个新的采样周期，最多等待 20 秒。数据库命令状态区分等待、已下发、已接受、已完成、离线和超时。
- 网页修改设备上报 / MQ 参数会在线同步；离线设备在下次鉴权时取得最新配置。

## 7. 登录、存储和邮件

首次安装设置一个网站密码，数据库不存明文网站密码。登录页默认勾选“记住登录”，持久 Cookie 默认 **30 天**；有效期可在 `server/.env` 的 `REMEMBER_DAYS` 修改。它使用随机令牌，数据库只保存摘要，并带 HttpOnly / SameSite；HTTPS 部署还带 Secure。退出会撤销该浏览器的记住登录和实时通道；清除 Cookie 或到期后需重新输入密码。

设备令牌与网页密码独立。令牌只在创建 / 重置时显示一次；重置和停用会撤销旧连接。设备令牌放在 WebSocket 的鉴权消息中，未拼进 URL 查询参数。浏览器实时连接使用短期、一次性登录票据，检查 Origin；写接口检查 CSRF。

默认保存最近 **60 天**。在“配置 → 历史保留天数”修改，范围 1–3650 天。后台 worker 每小时按采样时间分批删除过期记录，告警 / 邮件记录也按该保留期清理；删除不依赖有人打开网页。数据量较大时需监测 PostgreSQL 存储并做好备份。

SMTP 可填写主机、端口、STARTTLS/SSL、用户名、邮箱授权码、发件邮箱与最多 10 个收件人。常见搭配为 STARTTLS/587 或 SSL/465，按实际邮箱服务商文档配置。

1. 保存 SMTP 设置，点击“发送测试邮件”，在邮件记录中确认已发送并实际检查邮箱。
2. 确认设备 MQ 已启用、供电、预热并验证阈值，再启用“烟雾邮件告警”。
3. 烟雾持续期间只建立一次邮件任务；稳定恢复后允许下次事件，默认两次告警邮件最短间隔 900 秒。
4. 失败会按 30s、60s、120s…重试，最多 6 次；最终失败可在网页“重新发送”。SMTP 任务与设备 WebSocket 分开，不会因邮件服务慢而阻塞设备连接。

授权码用 libsodium 和 `APP_KEY` 在数据库中加密，网页读取配置时不回显。留空保留旧授权码。**备份数据库时同时备份原 `APP_KEY` / `.env`，不要重新生成密钥，否则无法解密旧授权码。** 默认不允许无加密 SMTP；只有隔离本机 SMTP 测试时可设 `SMTP_ALLOW_PLAIN=1`。运行中的重试是至少一次投递，SMTP 成功后进程异常的极小窗口仍可能重复发送；稳定 Message-ID 有助收件服务器去重。

## 8. 公网部署：Docker / Linux

需要 Linux 主机、Docker Engine、Compose **2.24.4 或更新版本**以及解析到服务器的域名；公开 80/443，数据库不公开。不要把项目直接放入共享虚拟主机：需要能运行长期 PHP WebSocket / worker 进程。

上传整个目录（含 `server/public/assets`），进入项目根目录：

```sh
sh deployment/install.sh
```

输入完整地址如 `https://sensors.example.com` 和网站密码。脚本生成 `server/.env`，不会覆盖已存在的配置。

```sh
docker compose --env-file server/.env -f compose.yaml -f compose.production.yaml up -d --build
docker compose --env-file server/.env -f compose.yaml -f compose.production.yaml ps
```

公网配置使用 Caddy 自动申请 / 续期 HTTPS，优先 Let's Encrypt ISRG Root X1 证书链；WebSocket 同域路径 `/ws`。首次启动 PostgreSQL 自动建立表，Docker 容器 `restart: unless-stopped`，主机重启后随 Docker 服务恢复。

只做局域网 Docker 测试时，安装时填写 `http://电脑IP:8080`：

```sh
docker compose --env-file server/.env up -d --build
```

`.env` 必须满足：

| 配置 | 公网示例 / 用途 |
|---|---|
| APP_URL | `https://sensors.example.com`，无尾部子目录 |
| WS_PUBLIC_URL | `wss://sensors.example.com/ws` |
| COOKIE_SECURE | 公网 HTTPS 为 `1` |
| SITE_ADDRESS | `sensors.example.com` |
| APP_KEY | 安装器生成的 64 位 hex；保管原值 |
| ADMIN_PASSWORD_HASH | 安装器生成的密码摘要 |
| DB_HOST / PORT | Docker 中 `db` / `5432` |
| DB_NAME / USER / PASSWORD | 安装器生成，已有数据库不应随意改密码 |
| REMEMBER_DAYS | 默认 `30` |

`server/.env.example` 是格式参考，包含的占位符不能直接用于上线。网站根目录应为 `server/public`，不能将 `.env`、数据库脚本、vendor 或固件当作静态网页公开。

检查日志：

```sh
docker compose --env-file server/.env logs --tail=100 web websocket worker proxy
```

更新 `.env` 环境变量后，重新运行 `up -d --force-recreate`，普通 restart 不会载入新的容器环境。恢复备份或升级时执行：

```sh
docker compose --env-file server/.env exec web php bin/migrate.php
```

数据库备份脚本：`sh deployment/backup.sh`。它保存 PostgreSQL dump 和 `.env`，备份目录权限限制为当前用户。恢复到准备好的数据库时：

```sh
docker compose --env-file server/.env exec -T db sh -c 'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists' < backups/database-时间.dump
```

该恢复命令会替换目标库中的现有内容，先保留当前备份。若在公网叠加配置中操作运行状态，也可给 compose 命令加相同的 `-f` 文件。

## 9. 手动部署 / 宝塔

提供 `deployment/nginx.conf.example` 和 `deployment/supervisor.conf.example`。准备 PHP 8.3+（本机实测 8.5.11）与 `pdo_pgsql`、`mbstring`、`sodium`、`openssl`、PostgreSQL 17。

生成 `.env` 后改成实际数据库地址 / 用户 / 密码；将网站根目录设为 `server/public`，安装 HTTPS，反代 `/ws` 到 `127.0.0.1:8081`。示例 Nginx 的 PHP socket 路径需要按主机版本修改。

```sh
cd /opt/sensor_monitor/server
composer install --no-dev --prefer-dist
php bin/setup.php --url=https://sensors.example.com
php bin/migrate.php
php bin/websocket.php
php bin/worker.php
```

最后两项应通过 Supervisor 长期运行，不应只在会关闭的 SSH 会话中执行。手动部署 `.env` 必须允许 PHP / worker 运行用户读取，且避免其它用户读取；`WS_BIND` 改为 `127.0.0.1`。整套服务只启动**一个** WebSocket 实例；当前设计面向少量实验设备，未加入多实例消息总线。

## 10. 网站密码修改

Windows / 手动部署运行 `php server/bin/password.php`，按提示输入新密码；需可写的 `.env` 和可访问的数据库。程序撤销旧登录令牌，不改变设备令牌或 SMTP 密钥。Windows 修改后用停止 / 启动脚本重启。

Docker 中可把主机 `.env` 挂载进一次性 web 容器：

```sh
docker compose --env-file server/.env run --rm -v "$PWD/server/.env:/app/.env" web php bin/password.php
docker compose --env-file server/.env up -d --force-recreate web websocket worker
```

密码至少 12 个字符，最多 72 个 UTF-8 字节。命令行提示输入可能可见，不在公共终端输入。

## 11. 验证与故障排查

交付检查见 `test_results/`。实际执行了 PHP + PostgreSQL + WebSocket 集成测试、Chromium 网页检查、具有证书校验的 HTTPS/WSS 反代测试、Windows 启停测试和两种固件编译。SMTP 使用本机邮件接收器，未向实际外部邮箱发送。Compose / Caddy 配置已校验；当前 Windows 没有 Docker daemon，未声称已实际启动 Docker 容器或申请公网证书。

首次实物验收建议：

1. 确认硬件电源 / 插接方向及 R1.1 保护电路；读取串口 Flash / PSRAM 容量，预期分别 16777216 / 8388608 字节。
2. 配网后网站显示在线；确认光照、温湿度 / 气压、气体电阻和雷达读数，缺失模块应显示 `--`。
3. 点击“立即采样”，应在 20 秒内显示“已取得新读数”。
4. 暂停 Wi-Fi 或网站后恢复，确认设备和网页自行重连；补传数据不得重复入库。
5. 先验证 MQ 真实 DO 极性、ADC 电压、预热 / 基线，再启用烟雾检测。
6. 设置邮箱并发测试邮件；安全地模拟 MQ 输出触发，确认持续信号只发一次邮件，恢复后出现结束时间。
7. 检查默认 300 秒上报和数据库保留天数；备份 `.env` 与数据库。

常见问题：

| 现象 | 检查 |
|---|---|
| 设备连不上 Wi-Fi | 2.4GHz、SSID、密码；本版本为普通 Wi-Fi 接入，不配置校园 WPA2 Enterprise 门户认证 |
| Wi-Fi 通但 WSS 未连 | NTP、DNS、443 可达、域名与证书根 CA、令牌、`/ws` 路径 |
| 页面离线、历史仍可看 | WebSocket 常驻进程、反代 Upgrade、心跳；历史 HTTP 与实时通道独立 |
| CSRF / 来源不匹配 | 访问地址与 APP_URL 必须完全一致，包括协议和端口 |
| I2C 模块缺失 | 3.3V、共地、GPIO8/9、地址跳桥、CS HIGH、实际模块插接次序 |
| LD UART 无数据 | SENSOR_5V、TX→RX 交叉、256000 波特率 |
| MQ 一启用就告警 | 未供电、未预热、DO 极性或实际阈值，别把未插模块的 GPIO 状态当烟雾 |
| SMTP 失败 | 邮箱授权码、端口/加密、发件人匹配、云主机出站 SMTP 限制；查看邮件记录 |
| Windows 工具缺 DLL | 安装 Microsoft Visual C++ 2015–2022 x64 运行库 |

`tests/integration.py` 仅允许隔离的 `*_test` 数据库，并要求 `MONITOR_ALLOW_TEST_RESET=1`；**会清空测试表，不能指向真实监测库**。浏览器脚本创建“模拟数据”设备。测试所需环境文件和密码未放入交付包。

## 12. 工程目录

```text
sensor_monitor/
├── README.md
├── start_windows.ps1 / stop_windows.ps1
├── compose.yaml / compose.production.yaml
├── server/
│   ├── public/             PHP 页面/API、CSS、JS、离线可用 Chart.js
│   ├── src/                登录、数据校验、WebSocket、邮件与保留任务
│   ├── bin/                安装、迁移、WebSocket、worker、改密码
│   ├── database/schema.sql
│   ├── composer.json / composer.lock / vendor/
│   └── .env.example
├── firmware/
│   ├── src/main.cpp / include/root_ca.h
│   ├── platformio.ini / partitions_16mb.csv
│   ├── prebuilt/yd_uart/ 和 yd_native_usb/
│   └── flash.ps1
├── deployment/             Caddy、Nginx、Supervisor、备份
├── docs/                   协议、来源和设计说明
├── tests/ / test_results/
└── screenshots/            模拟数据的桌面/手机截图
```

第三方实现与对应文档见 `docs/SOURCES.md`；PHP 依赖许可证随 vendor 和 Composer 元数据提供。项目代码为此次任务生成的实现，没有改变传感器载板的核心接线、电源选择或插拔设计。
