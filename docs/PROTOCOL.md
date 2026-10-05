# WebSocket 数据协议 v1

端点为同域 `/ws`，公网用 WSS。本项目使用普通 RFC6455 WebSocket，不是 Socket.IO 或 MQTT。

## 设备鉴权

连接建立后 10 秒内发送：

```json
{"type":"hello","v":1,"role":"device","token":"64字符设备令牌","firmware":"carrier-network-1.0.0"}
```

成功返回 `welcome`，包括 `device_id`、`server_time`、`config_version` 和 `config`。设备按 config 工作；配置改变时服务器推送 `config`，设备用 `config_ack` 返回版本号。设备只被允许上传本令牌对应的设备数据。

浏览器通过已登录的 PHP API 获取 30 秒、单次使用的票据，再发送 `role: browser` 的 hello。浏览器身份检查 Origin；浏览器连接只接收通知，写操作走带 CSRF 的 HTTP API。

## 样本

```json
{
  "type": "telemetry", "v": 1,
  "boot_id": "e52b7c4a8955bde0", "seq": 1,
  "captured_at": 1791000000, "queue_age_s": 0,
  "reason": "periodic",
  "data": {
    "light_lux": 420.5,
    "temperature_c": 26.1,
    "humidity_pct": 51.3,
    "pressure_hpa": 1010.2,
    "gas_ohm": 93500,
    "bh1750_ok": true, "bme688_ok": true,
    "radar_presence": true, "radar_ok": true,
    "radar_uart_bytes": 2048, "radar_uart_age_ms": 20,
    "radar_uart_hex": "f4f3f2f1",
    "mq_enabled": true,
    "mq_adc_raw": 1240, "mq_adc_mv": 940.0, "mq_ao_v": 1.856,
    "mq_gpio": false, "mq_ready": true, "mq_smoke": false,
    "rssi_dbm": -53, "uptime_s": 300,
    "queue_dropped": 0, "sensor_age_ms": 25
  }
}
```

`boot_id` 每次上电随机变化，`seq` 同一次上电递增。唯一键为 `(device_id, boot_id, seq)`。`captured_at` 为 UTC epoch 秒，未 NTP 校时则为 null；`queue_age_s` 在实际发送时更新，服务器可估计该读数已排队多久。缺失 / 无效指标应为 null，不能用 0 代替。

reason 可选 `boot`、`periodic`、`requested`、`alarm`、`recovered`。请求采样时同时包含 `request_id`。固件 1.0.2 开始增加可选布尔字段 `mq_enabled`：关闭时，`mq_enabled=false`、`mq_ready=false`，`mq_adc_raw`、`mq_adc_mv`、`mq_ao_v`、`mq_gpio`、`mq_smoke` 全部为 null，避免未接模块的悬空读数成为测量数据。启用但尚未完成预热时可查看原始 ADC / GPIO，`mq_smoke` 仍为 null。老版固件没有 `mq_enabled` 时服务器保留兼容，存为 null；不能据此推断旧记录中的模块连接状态。新增字段不改变协议版本号。

收到合法样本并提交数据库后返回：

```json
{"type":"telemetry_ack","boot_id":"e52b7c4a8955bde0","seq":1,"dropped":null}
```

客户端在匹配 ACK 后移除缓存，10 秒没有 ACK 会重发；重复样本仍会得到 ACK。已超出配置保留期的补传返回 `dropped: outside_retention`，客户端可丢弃。临时服务失败返回 `error: server_error`，客户端保留样本。

消息和单帧上限 8192 字节，每连接每分钟最多 180 条应用消息。未鉴权 10 秒关闭，无应用心跳 90 秒关闭。JSON 字段、数值范围、时间与角色均在服务端校验。

## 立即采样

网页 POST `api.php?action=command`，请求体为 `{"device_id":"UUID"}`，带 `X-CSRF-Token`。在线设备收到：

```json
{"type":"command","command":"sample_now","request_id":"命令UUID"}
```

设备先发送 `command_ack`，启动新的采样周期，然后上传 `reason: requested`、相同 request_id 的读数。服务器以新样本 ID 完成该命令。超时 20 秒，不把旧缓存读数当成采样成功。

## 心跳与通知

设备 / 浏览器每约 25 秒发送 `{"type":"ping"}`，服务器返回 `pong`。服务器向已鉴权浏览器发送 `sample`、`device_status`、`refresh_commands` 与 `config_ack`。告警邮件逻辑只处理足够新的、MQ 已启用且就绪的样本，按采样时间忽略较旧状态变化。

所有样本的 metrics 放入 PostgreSQL JSONB，接口固定字段进行校验。浏览器通过 history / chart / export API 查看、聚合和导出，不能直接访问数据库。
