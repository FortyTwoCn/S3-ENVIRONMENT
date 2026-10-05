# 封装来源与电气依据

## ESP32 Carrier Footprint Source

Name: **ESP32-S3_N16R8_44PIN_CARRIER**

Library: **本工程 custom.pretty，按用户尺寸照片重建整个开发板载板封装**。

Source: 用户提供的 CH343P 双 Type-C 开发板尺寸照片，保存在本目录 `actual_esp32_dimensioned.jpg`。不是 ESP32-S3-WROOM-1 的 SMD 封装。

Pin Count: 44；Pin Pitch: 2.54 mm；Header Row Spacing: 25.40 mm；Board Width: 27.94 mm；Rectangular Board Length: 57.15 mm；Overall Length with antenna: 63.389002 mm。

Verification: **PENDING**。排距和外形取自照片显式标注，并非按像素比例猜测。端部偏移尚未确认，暂定 1.905 mm。1:1 PDF 为最后物理核对工具。

## 搜索和比较现有资源

所有 EasyEDA 几何单位按 10mil = 0.254mm 换算，保留原始数据精度。资源名称不能证明实物一致。

| 来源/资源 | 检查结果 | 与用户照片比较 | 采用 |
|---|---|---|---|
| [EasyEDA ESP32-S3-DEVKIT-44PIN-LAYOUT-PCB](https://easyeda.com/modules/ESP32-S3-DEVKIT-44PIN-LAYOUT-PCB_c0005cf1e3c044369ebef8b7691cd4be)，ID `c0005cf1e3c044369ebef8b7691cd4be` | 下载并查看公开模块 JSON；两排 x=4020/4111 原始单位，中心距 23.114mm；左22、右21个排针孔；针距2.54mm | 排距不匹配，右排孔数不满足44Pin | 否 |
| [EasyEDA ESP32-S3-DevKitC-1 N16R8](https://easyeda.com/modules/ESP32-S3-DevKitC-1-N16R8_e3c561d1621749a48c1a4fdc01093e5f)，ID `e3c561d1621749a48c1a4fdc01093e5f` | 下载并查看完整板 JSON；两排 x=4052.5/4142.5，中心距22.86mm；各22Pin、针距2.54mm；板框约25.39995×62.73988mm；CP2102，双Type-C | 用户照片25.40mm排距、27.94mm板宽、CH343P；不是同一板型 | 否 |
| [嘉立创官方料号 ESP32_S3_DevKitCN16R8，C9900253635](https://jlcpcb.com/partdetail/56483469-ESP32_S3_DevKitCN16R8/C9900253635) | 官方器件页检索到；公开 footprint viewer 没有提供可提取的孔坐标，组件 API 未认证返回403 | 缺少机械数据，不能证明匹配 | 否 |
| [嘉立创开源广场 ESP32_S3_44P_多路供电扩展板](https://oshwhub.com/liuhai001/project_vdcscyvu) | 检索到候选；页面访问未能提取工程尺寸 | 没有核实排距/USB/针序 | 否 |
| [Espressif 官方 DevKitC-1 V1 机械 PDF](https://dl.espressif.com/dl/PCB_ESP32-S3-DevKitC-1_V1_20210312CB.pdf) | 下载官方机械图；板宽25.4mm、长62.74mm、两侧边到针中心1.27mm，得到排距22.86mm | 25.4是官方**板宽**，用户照片25.4是**排针中心距**；不可混用 | 否 |
| [YD-ESP32-S3 板资料仓库](https://github.com/profharris/YD-ESP32-S3_ESP32-S3-WROOM-1_Dev) | 描述44Pin、双Type-C、CH343P、比官方多一针距宽、约1.1×2.5英寸 | 板族/外观与照片一致，可交叉支持，但没有证实具体实物端部偏移 | 仅板族参考 |

公开 API 复查地址：`https://easyeda.com/api/components/<上表资源ID>`。这两项是用户贡献公共资源，不能当官方实物检验结论。三重验证 A公共库/B官方图/C实物照片没有得到同一板型一致结果，因此选择专用封装，保留 PENDING 状态。

## 电气原始资料

| 资料 | 本设计使用的信息 |
|---|---|
| [Espressif ESP32-S3 数据表](https://www.espressif.com/sites/default/files/documentation/esp32-s3_datasheet_en.pdf) | 3.3V GPIO；ADC 11dB有效范围约0–2.9V；100nF输入滤波建议 |
| [Espressif DevKitC-1 官方用户指南](https://documentation.espressif.com/esp-dev-kits/en/latest/esp32s3/esp32-s3-devkitc-1/user_guide_v1.1.html) | GPIO/USB功能、Octal存储器与GPIO35–37限制；官方不同revision的RGB脚不可混用 |
| [Hi-Link 编制 HLK-LD2410C manual v1.00](https://www.sudo.is/docs/esphome/components/ld2410/HLK-LD2410C_manual_v1.00.pdf) | 第7页22×16mm、2.54mm、TX/RX/OUT/GND/VCC；第8页3.3V IO、256000 8N1、推荐5V且电源能力>200mA。链接为镜像，内容为厂家手册 |
| [TI TMUX1511 数据表](https://www.ti.com/lit/ds/symlink/tmux1511.pdf) | SPST通道/引脚；powered-off protection；fail-safe控制到5.5V；最大断电漏电2uA；开关导通电阻上限4.5Ω |
| [Bosch BME688 数据表](https://www.bosch-sensortec.com/media/boschsensortec/downloads/datasheets/bst-bme688-ds000.pdf) | I2C CS高，SDO地址0x76/0x77，测气体有内部加热器 |
| [ROHM BH1750FVI 数据表镜像](https://dfimg.dfrobot.com/enshop/image/data/SEN0097/BH1750FVI.pdf) | 3.3V工作，ADDR低/高0x23/0x5C |
| [AOS AO3401A 数据表](https://www.aosmd.com/sites/default/files/res/data_sheets/AO3401A.pdf) | P-MOS反接保护、SOT-23 G/S/D与低导通电阻 |
| [AOS AO3400A 数据表](https://www.aosmd.com/sites/default/files/res/data_sheets/AO3400A.pdf) | NMOS G/S/D；Vgs=2.5V已有导通电阻指标；绝缘Gate保护MQ DO |
| [KiCad 9 CLI 手册](https://docs.kicad.org/9.0/en/cli/cli.html) | 原理图/PCB检查、Gerber/钻孔/PDF/3D导出 |
| [PlatformIO ESP32-S3-DevKitC-1 软件配置文档](https://docs.platformio.org/en/latest/boards/espressif32/esp32-s3-devkitc-1.html) | 构建基类；本工程显式覆盖N16R8 Flash/PSRAM参数 |

资料访问日期：2026-10-02。传感器 PCB 本体尺寸/排针相对板边位置（除 LD 厂家本体尺寸）未有实物图纸；README 中包络均为暂定。未取得具体 MQ 型号/完整模块原理图，DO 电路因此设计为兼容5V开集/上拉/推挽的低速接口。

## 工具与依赖

KiCad 9.0.9 官方 Windows 安装包使用可移植解包工具目录运行；普通 Python 用于文档与独立审查，KiCad Python 用于 PCB API；Freerouting 2.2.4 完成主体路由，再逐项修正并由原生 DRC 检查；Gerbonara 1.6.3 独立解析制造文件；ReportLab 生成真尺寸 PDF，PyMuPDF 实际渲染检查。

固件：PlatformIO 6.2.0，espressif32 6.12.0，Arduino ESP32 2.0.17；BH1750 1.3.0、Adafruit BME680 2.0.5。源代码见 [claws/BH1750](https://github.com/claws/BH1750)、[Adafruit BME680](https://github.com/adafruit/Adafruit_BME680)、[PlatformIO espressif32](https://github.com/platformio/platform-espressif32)。标准封装和 STEP 来源为 KiCad 标准库，许可见 `3d/README.md`；暂定模块 VRML 是本工程自建包络。
