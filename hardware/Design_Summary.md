# Design Summary - R1.1 photo review

完成的是 **ESP32-S3 多传感器可插拔载板**：所有成品模块插排母，PCB 铜箔替代面包板和杜邦线。KiCad 9 原理图、已布线 PCB、BOM、网络/接线表、PDF、制造文件和测试固件均已生成。

**当前状态：电气与布线检查通过；MECHANICAL_DIMENSION_PENDING。未完成用户实物的机械比对与上电测试，不是 PRODUCTION VERIFIED。**

## PCB

| 项目 | 结果 |
|---|---|
| 外形 | 110×90mm，中央 USB 开口 31×25.5mm |
| 工艺 | 2层 FR4，1.6mm，1oz/面，常规低成本通孔工艺 |
| 安装孔 | 四角4×3.2mm M3 NPTH，建议尼龙支柱 |
| 走线 | 信号0.30mm；传感器5V/MQ等主干1.00mm；Q2仅约1.76mm局部引出0.601mm |
| 过孔 | 信号0.80/0.40mm；电源1.20/0.60mm |
| 地平面 | 上下GND，过孔/通孔连接；两个天线区两面禁铜 |
| 布局 | GY左上光窗，BME右上通风+热隔离槽，LD左侧天线区，MQ右下散热 |

## ESP32 与机械

专用 `ESP32-S3_N16R8_44PIN_CARRIER`：**2×1x22 2.54mm 排母，中心距25.40mm**，开发板可拔出。来自用户照片的显式尺寸：板宽27.94mm、矩形长度57.15mm、含突出天线长度63.389002mm、排针首末跨度53.34mm。照片显示CH343P、双Type-C、N16R8，外观符合YD板族。

公共库资源已逐项比较：EasyEDA `ESP32-S3-DEVKIT-44PIN-LAYOUT-PCB` 排距23.114mm且右排缺孔；`ESP32-S3-DevKitC-1 N16R8` 与官方图排距22.86mm，都不适配照片25.40mm。来源、资源ID、机械图与拒用原因完整记录在 `sources/footprint_sources.md`。

**未确认：** ESP32 第一脚与矩形顶边偏移、最后脚与USB边偏移，当前暂定各1.905mm；传感器具体板边/排针偏移/高度和针序；USB插头本体空间。提供两页真实1:1 PDF供实物核对。模块包络没有平面交叠，但包络仍需实际模块验证。3D使用标准排母/器件模型加暂定模块模型，不把近似模型当实测证据。

## GPIO

| 功能 | GPIO | 方向 |
|---|---:|---|
| I2C SDA | 8 | 双向 |
| I2C SCL | 9 | 时钟输出 |
| 雷达RX，接LD TX | 17 | 输入 |
| 雷达TX，接LD RX | 18 | 输出 |
| 雷达OUT | 16 | 输入 |
| MQ ADC | 4 | ADC1输入 |
| MQ DO | 5 | 保护后反相输入 |
| 普通扩展 | 6/7/10/11 | 用户自定义 |
| 舵机PWM | 12 | 输出，经1k |

用户指定主GPIO未改变。GPIO19/20、35/36/37、0/3/45/46和48均没有接普通扩展。完整44Pin针序及接口方向见CSV。

## Power

```text
ESP32 USB ─→ 开发板5V ─→ JP3.1
          └→ 开发板3V3 ─→ GY、BME、逻辑、扩展
外部J6 5V ─→ Q2 PMOS ─→ JP3.3
JP3.2 SENSOR_5V ─→ LD2410C、MQ、滤波及5V指示
J13独立5V ─→ Q3 PMOS ─→ 舵机接口
全部共地。
```

一枚跳帽：1–2=USB，2–3=EXT；没有USB与外部5V硬并联。推荐完整测试用EXT模式+ESP自己USB，J6稳压5V建议1A、推荐2A容量。载板每个独立传感器/舵机电源支路按1A连续使用。实际开发板USB路径额定电流没有资料，USB模式满载能力尚需实测。大舵机用独立粗线电源。

## Sensors / Interfaces

| 模块/接口 | 排母 | Pin1起针序 | 电源/地址 |
|---|---|---|---|
| GY-302 BH1750，J2 | 1x5 | ADDR SDA SCL GND VCC | 3V3，0x23；可改0x5C |
| BME688，J3 | 1x6 | VCC GND SCL SDA SDO CS | 3V3，0x76；可改0x77，CS 10k上拉 |
| LD2410C，J4 | 1x5 | TX RX OUT GND VCC | SENSOR_5V；256000 8N1；3.3V逻辑 |
| MQ，J5 | 1x4 | VCC GND DO AO | SENSOR_5V；AO/DO保护后入ESP |
| I2C扩展，J7 | 1x4排针 | 3V3 GND SDA SCL | OLED等 |
| GPIO扩展，J8–J11 | 各1x3排针 | GND 3V3 GPIO | GPIO6/7/10/11 |
| Servo，J12 | 1x3排针 | GND 5V_SERVO SIGNAL | GPIO12；独立J13电源 |

R2/R3 I2C 4.7k上拉默认DNP。JP1/JP2地址选择默认铜桥到GND；改3V3前必须切断旧桥。TP1–TP11覆盖电源、I2C、UART/OUT、原始MQ AO、保护后ADC和DO。

## Protection 与可靠性调整

| 电路 | 最终实现/原因 |
|---|---|
| MQ AO | 6.8k/7.5k 1%分压+100nF；含100kADC下拉负载，5V输入约2.532V、5.25V最坏1%误差约2.685V。比初始4.7k方案留更多ADC测量余量 |
| MQ DO | AO3400A NMOS+3V3 10k上拉；兼容5V开集/上拉/推挽，GPIO极性反相，避免5V与断电反灌 |
| LD串口/OUT | 厂家3.3V逻辑，TX/RX/OUT各1k；TX→RX交叉正确 |
| 独立电源反灌 | TMUX1511PWR四路断电保护开关，隔离雷达三线和MQ ADC；控制由SENSOR_5V驱动；敏感节点100k下拉 |
| 电源反接 | 外部传感器及舵机各AO3401A PMOS，无肖特基大压降 |
| 光照 | 3V3 LED移到载板下边缘，远离BH1750 |
| 温度/天线 | BME局部减少铜与20×1mm隔离槽；MQ/BME约37.5mm中心距；两天线两面严格禁铜；墙装时避免MQ位于BME正下方 |

除了上述可靠性调整和独立舵机电源，没有改变项目核心目标或主GPIO。UART IO仍基于真正LD2410C的3.3V定义；U1不是5V电平转换器，实物异型模块需先确认。

## 验证与制造

| 项目 | 实际结果 |
|---|---|
| ERC | 0 error / 0 warning |
| DRC | 0 error / 0 warning |
| Unconnected / Unrouted | 0 |
| Schematic parity | 0 |
| 自动连接/安全/布局检查 | 47项PASS，机械确认PENDING；所有DRC规则为error/warning，无ignore类别 |
| Gerber独立解析 | 7层全部解析；143 PTH / 4 NPTH；两个天线两面无铜检查PASS |
| Firmware | CH343P串口和原生USB两环境均实际编译SUCCESS |
| 实物测试 | 未烧录/未上电，不能声称所有传感器已经实际工作 |
| Gerber状态 | 已导出暂定包，**PROVISIONAL_MECHANICAL_DIMENSION_PENDING** |
| 适合正式生产 | **完成1:1实物尺寸/针序/插头验证后才可正式下单；当前未生产验证** |

下一步按 `fabrication/ESP32_FOOTPRINT_1_TO_1_CHECK.pdf` 核对开发板和模块，核对成功后使用同次最终导出的制造文件；任何尺寸改动都需要重布线及重新检查。装配和首次上电的六步说明、万用表节点与烧录方法见 README。最终验收仍以到手PCB插上用户实物后运行测试固件为准。

## 实物照片修订记录

BME688：原接口为连续 1×6，2.54mm，不是 3×2；实际PCB六个孔中心处于同一直线。用户确认背面 CS/SDO/SDA/SCL/GND/VCC，感测面朝上后的 VCC/GND/SCL/SDA/SDO/CS 与 J3 一致。

R1.1 修正 GY-302/MQ 的正反面镜像针序，接口焊盘位置保持不变。J2 顶视为 ADDR/SDA/SCL/GND/VCC，J5 为 VCC/GND/DO/AO；AO 从 J5.4 到 GPIO4，DO 从 J5.3 到 GPIO5。GPIO与供电架构没有修改。原理图、铜线、丝印、CSV、装配图和制造文件一同更新，并重新执行原生检查。

平放安装要求模块直针向下；MQ 现有弯针需替换。雷达尚未装排针，需要补焊。完整机械尺寸和被遮挡丝印仍需实物核对，当前保留 MECHANICAL_DIMENSION_PENDING，未生产验证。
