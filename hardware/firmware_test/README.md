# ESP32-S3 N16R8 载板测试固件

实际为16MB Flash + 8MB OPI PSRAM开发板。构建基类是 `esp32-s3-devkitc-1`，已显式覆盖Flash容量、QIO/OPI和16MB分区；这不意味着底板使用官方开发板机械尺寸。

## 编译与烧录

PlatformIO espressif32 6.12.0、Arduino ESP32 2.0.17，BH1750 1.3.0、Adafruit BME680 2.0.5。两个环境均已编译SUCCESS；未给用户实物烧录。

连接照片右侧 **CH343P转串口 USB-C**，通常使用：

```sh
pio run -e yd_uart
pio run -e yd_uart -t upload --upload-port COMx
pio device monitor --port COMx --baud 115200
```

连接芯片直连的 **USB&OTG USB-C**，使用：

```sh
pio run -e yd_native_usb
pio run -e yd_native_usb -t upload --upload-port COMx
pio device monitor --port COMx --baud 115200
```

`COMx` 换成 Windows 设备管理器显示的端口；原生USB下载前后端口可能变化。首次不能自动进入下载时，按住BOOT，点RST，再松BOOT；成功下载后RST。CH343P方式 `CDC_ON_BOOT=0`，原生USB方式 `CDC_ON_BOOT=1`，串口115200。启动输出Flash/PSRAM实际大小，预期16777216/8388608字节；若不匹配先核对实物型号和内存设置。

## 预编译文件

`prebuilt/yd_uart/` 与 `prebuilt/yd_native_usb/` 各包含：

| 文件 | Flash offset |
|---|---|
| bootloader.bin | **0x0000**（ESP32-S3） |
| partitions.bin | 0x8000 |
| boot_app0.bin | 0xe000 |
| firmware.bin | 0x10000 |

优先使用PlatformIO上传以自动选用正确工具和参数。如果用Espressif Flash Download Tool，选择ESP32-S3、16MB、按上述地址放四个文件；不要使用普通ESP32的0x1000 bootloader地址。固件目录中有SHA256 manifest，方便确认文件未混用。不要仅把应用firmware.bin写到0地址。

实际bootloader镜像头经esptool校验为 **DIO / 80MHz / 16MB**，校验和与SHA256有效。PlatformIO对QIO构建使用DIO模式的启动镜像，应用仍配置QIO Flash/OPI PSRAM；独立下载工具按镜像头选择DIO，不要擅自把启动头改成QIO。检查记录在 `checks/firmware_image_info.log`。

## 测试行为

I2C GPIO8/9、100kHz；扫描默认0x23/0x76，并尝试备用0x5C/0x77。BH1750读Lux；BME688读温湿压和气体电阻，使用320°C/150ms加热测试。这个库提供原始BME68x读数，不包含BSEC IAQ算法，不会给出未经校准的CO2/ppm。

雷达UART1 RX17/TX18、256000 8N1；OUT16。持续接收，串口每秒打印最多96字节十六进制片段和累计字节数，用于连线验证，不是完整雷达协议解析器。Presence直接读OUT。

MQ ADC4使用12bit/11dB，32次平均，打印Raw/校准毫伏及按R4=6.8k、R5=7.5k、R15=100k负载估计的原始AO。DO5经过底板Q1反相，打印高表示原始DO低；仅在SENSOR_5V存在时解释。固件没有驱动Servo或额外GPIO。

所有传感器插拔及地址/电源跳帽调整先断电。完整六步上电顺序见硬件README。运行结果必须结合万用表和用户实际模块检查；编译成功不等于已做实物测试。
