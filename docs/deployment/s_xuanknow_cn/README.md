# s.xuanknow.cn 服务器部署记录

交付日期：2026-10-04（Asia/Shanghai）。

**2026-10-05 更新：实物已烧录 `carrier-network-1.0.1`，重启自动联网、WSS 上传、PostgreSQL 入库和网页立即采样均已验证。传感器暂未接入，MQ 告警保持关闭。** 下文保留初次服务器部署记录；当前实物结果见 [烧录记录](../../device_flash/ESP32S3_COM4/README.md)。

网站：<https://s.xuanknow.cn>

服务器：192.144.227.206。使用已有宝塔、Nginx、PHP 8.5.10 和 PostgreSQL 18.0 直接部署。没有安装或使用 Docker。SSL 由用户通过宝塔配置；网站已同步为 HTTPS/WSS，Secure Cookie 已启用，两个后台进程已重启。

最新检查：11 项 HTTPS/WSS 检查通过，包括固件 ISRG Root X1 根证书及域名校验、HTTP 到 HTTPS 跳转、记住登录、Secure Cookie、浏览器及设备 WSS、读数入库广播和立即采样。实际证书链验证未关闭。临时测试设备、读数、命令及测试登录令牌已清理，已有网站密码和数据库配置已保留。

## 已完成

- 站点程序目录：/www/wwwroot/s.xuanknow.cn，网站运行目录：/www/wwwroot/s.xuanknow.cn/public。
- 保留已有数据库名、用户名、密码和端口；将 Docker 主机名 db 修正为 127.0.0.1。
- 原数据库为空，已先导出备份，再创建项目表及索引；当前历史保留 60 天。
- 生成 APP_KEY、网站密码及密码摘要；.env 为 www:www、权限 600。
- 会话目录为 .runtime/sessions，www:www、权限 700。
- 修正宝塔 .user.ini 的 open_basedir，使 PHP 可读取上级 src、vendor 和 .env；限制仍保留在整个项目及 /tmp。
- Nginx /ws 反向代理至 127.0.0.1:8081；内部端口不直接暴露。
- 使用现有宝塔 Supervisor 启动单个 WebSocket 和单个 worker，自动启动及自动重启。
- 已创建“ESP32-S3 环境监测”设备。默认 300 秒上报、MQ 告警关闭，等待实物接入。
- 已清理模拟设备、模拟读数、模拟命令和测试登录令牌。

部署初始网站密码与设备令牌保存在这台电脑受访问权限限制的 work/remote_deploy/private/connection-details.txt，不写入此报告或源码发布包。如果你已修改网站密码，使用你设置的新密码。

## 检查结果

18 项服务器联调通过：公网登录页、未登录接口限制、.env 不可下载、密码登录、记住登录、浏览器和设备 WebSocket 鉴权、读数入库、实时广播、重传去重、立即采样命令下发及完成、历史/曲线/CSV 查询、设备重连、默认参数。

6 项 Chromium 浏览器检查通过：登录与实时连接、设备离线显示、配置值、390px 手机布局、退出登录、无 JavaScript 错误。截图为真实部署页面；没有实物读数，因此指标显示 --。

首次 HTTP 部署的登录及带设备令牌联调通过 SSH 隧道完成。SSL 配置后的检查通过公网 HTTPS/WSS 完成，域名主机名、Origin 和证书校验保持启用。HTTPS 检查使用临时测试令牌，没有更改网站密码。

Nginx 配置测试通过，Supervisor 两个进程 RUNNING，Supervisor 服务已启用开机启动。未重启整台服务器，以免影响其它站点。

初次部署时尚未烧录或接入实际 ESP32；截至 2026-10-05 已完成开发板联网验证。SMTP 和实际邮箱投递尚未验证，后台邮件和定期清理进程已经运行。

## 当前 ESP32 配网

- 主机：s.xuanknow.cn
- 端口：443
- 路径：/ws
- TLS：开启
- 令牌：见私有接入信息文件
- Wi-Fi：填写你现场的 2.4GHz Wi-Fi
- MQ：确认硬件供电、预热、ADC 和 DO 后，再在网页启用

HTTP 入口已由宝塔自动跳转至 HTTPS。设备应直接使用 WSS/443，不能依赖 WebSocket 的 HTTP 跳转。

## HTTPS 配置维护

SSL 由你在宝塔中管理。以下网站配置同步已执行；以后更改网站地址时可在服务器终端执行：

~~~bash
sudo -u www /www/server/php/85/bin/php \
  /www/wwwroot/s.xuanknow.cn/bin/set-public-url.php \
  https://s.xuanknow.cn

/www/server/panel/pyenv/bin/supervisorctl \
  -c /etc/supervisor/supervisord.conf \
  restart sensor-monitor-websocket sensor-monitor-worker
~~~

set-public-url.php 会备份 .env，并同步 APP_URL、WS_PUBLIC_URL、COOKIE_SECURE。它不会更换数据库密码、APP_KEY 或网站密码。

随后网站地址为 https://s.xuanknow.cn，设备使用 WSS/443，路径仍为 /ws，令牌保持不变。固件默认信任 ISRG Root X1；其它证书根需要在设备配网页面填写对应根证书。

## 修改网站密码

~~~bash
sudo -u www /www/server/php/85/bin/php \
  /www/wwwroot/s.xuanknow.cn/bin/password.php

/www/server/panel/pyenv/bin/supervisorctl \
  -c /etc/supervisor/supervisord.conf \
  restart sensor-monitor-websocket sensor-monitor-worker
~~~

密码至少 12 个字符、最多 72 个 UTF-8 字节。按终端提示输入；原记住登录会撤销。设备令牌与网站密码独立。

SMTP 账号、授权码、收件邮箱及保留天数在网页“配置”里设置。保管 .env 和数据库备份，APP_KEY 是 SMTP 授权码的解密密钥。

## 运维及备份

Supervisor 配置：

/www/server/panel/plugin/supervisor/profile/sensor-monitor.ini

进程名：

- sensor-monitor-websocket
- sensor-monitor-worker

查看运行状态：

~~~bash
/www/server/panel/pyenv/bin/supervisorctl -c /etc/supervisor/supervisord.conf status
~~~

日志：

- /www/wwwlogs/s.xuanknow.cn.error.log
- /www/wwwlogs/sensor-monitor-websocket.log
- /www/wwwlogs/sensor-monitor-worker.log

上线前备份目录：

/root/sensor-monitor-deploy-20261004T123753Z

含原 .env、Nginx 站点配置、.user.ini 和 PostgreSQL 数据导出，权限限制为 root。备份含敏感配置，不应放进 public 或对外分享。

本次只修改这个监测站点及其新增后台进程配置。原始本机密钥文件未改动；用于测试的本机 SSH 端口转发会在交付前关闭。

PHP CLI 存在扩展重复加载提示，Ratchet 依赖在 PHP 8.5 下有弃用提示；当前功能检查通过。没有修改其它站点共用的 PHP 配置，错误日志仍保留。

## 参考资料

WebSocket 反代配置依据 [Nginx 官方文档](https://nginx.org/en/docs/http/websocket.html)。证书链与固件 CA 的对应资料见 [Let's Encrypt 官方证书说明](https://letsencrypt.org/certificates/)。
