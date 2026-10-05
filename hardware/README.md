# ESP32-S3 多传感器可插拔载板 R1.1

**MECHANICAL VERIFICATION REQUIRED — MECHANICAL_DIMENSION_PENDING**

本工程已完成原理图、实际双层 PCB 布线、铺铜、制造文件和测试固件。KiCad 9.0.9 实际执行结果：ERC 0 错误/警告，DRC 0 错误/警告，Unconnected 0，原理图/PCB 一致性问题 0。自动网络、电压、模块包络及天线禁布区检查通过。**实物端部偏移、传感器板尺寸/针序及 USB 插头包络尚未物理验证；当前 Gerber 为暂定版，未标记 PRODUCTION VERIFIED。**

这是一块替代面包板和杜邦线的底板。ESP32 开发板、GY-302、BME688、LD2410C、MQ 都是用户提供的成品模块，插入排母，维修时可拔出。底板没有重新设计 ESP32 最小系统，也没有把传感器裸芯片放到底板上。

## 2026-10-02 实物照片复核 - R1.1

新照片保存在 `sources/actual_sensor_modules.jpg`，详细记录在 `checks/sensor_photo_review.md` / `.json`。

**BME688 是连续单排 1×6，针距 2.54 mm，首末针中心距 12.70 mm；原工程已采用这个排列。** 用户确认照片背面左→右为 **CS / SDO / SDA / SCL / GND / VCC**。本工程让感测面向上，模块本体位于排针上方，因此底板顶视左→右为 **VCC / GND / SCL / SDA / SDO / CS**，原 BME 接口无需修改。

GY-302 与 MQ 照片也显示背面。R1 的两个接口沿用了背面顺序，感测面朝上且本体保持当前区域时，顺序必须镜像。**R1.1 已修正 J2=ADDR / SDA / SCL / GND / VCC，J5=VCC / GND / DO / AO**，相应焊盘、原理图、铜线、丝印、CSV 和制造输出同时更新。GPIO 功能不变。不要使用 R1 的旧接线表和制造文件。

**装配方式仍按平放设计：公针从模块背面向下，插入底板竖直排母。** 照片中 MQ 的 90° 弯针不能直接按此方式平放插入，需要换为直针；BME/GY 也必须检查针脚是否满足向下插入要求。保留弯针而让模块站立，会改变模块的碰撞包络、光窗、进气口和雷达朝向，需要另做机械布局，不能套用当前平放校验图。雷达的五个孔在照片中没有装排针，需要在背面焊装 1×5 直针，保持天线面朝上。

雷达的正面天线图形和 TX / RX / OUT / GND / VCC 排列与厂家 LD2410C 手册一致。GY 的部分针名、MQ 的 VCC 丝印在照片中被排针/电位器遮住，镜像处理结合了本项目已有完整针名，**逐脚实物核对仍为 PENDING**。这张照片没有毫米标尺，也不能完成模块尺寸、高度、排针焊接方向的物理验证。

## 文件与打开方式

用 **KiCad 9** 打开 `esp32_sensor_carrier.kicad_pro`，再打开原理图和 PCB。实际生成并验证的格式为 KiCad 9；如使用 KiCad 8，请先在 KiCad 9 中转换/另存并重新检查，不能保证 KiCad 8 直接读取全部 KiCad 9 字段。符号和封装库随工程提供，`sym-lib-table`、`fp-lib-table` 使用 `${KIPRJMOD}` 相对路径，13 个标准 STEP 模型和 5 个暂定模块包络模型也随工程提供。

| 路径 | 内容 |
|---|---|
| `esp32_sensor_carrier.kicad_sch` | A2、七个功能分区的可编辑原理图 |
| `esp32_sensor_carrier.kicad_pcb` | 已完成布线/铺铜的 110×90 mm 双层载板 |
| `mechanical_parameters.json` | 开发板排距、针距、外形和待验证偏移参数 |
| `footprints/custom.pretty/ESP32-S3_N16R8_44PIN_CARRIER.kicad_mod` | 专用 44Pin 整板载板封装 |
| `fabrication/BOM.csv` | 底板器件、排母、跳帽，以及单独标出的用户模块 |
| `fabrication/gpio_map.csv`、`interface_pinout.csv`、`esp32_pinout.csv` | GPIO、各接口针序、44 个开发板脚位 |
| `fabrication/netlist.csv`、`netlist.xml` | 人可读网络表与 KiCad 实际导出的 XML 网络表 |
| `fabrication/ESP32_FOOTPRINT_1_TO_1_CHECK.pdf` | A4 两页，100% 打印的开发板及全板机械校验图 |
| `fabrication/schematic.pdf`、`assembly.pdf` | 原理图和焊接元件定位图 |
| `gerber/PROVISIONAL_MECHANICAL_DIMENSION_PENDING/` | 七个 Gerber 层、独立 PTH/NPTH 钻孔及 SVG 钻孔图 |
| `checks/` | 原始 ERC/DRC、自动审查、Gerber 检查及两种固件编译记录 |
| `images/` | 原理图、PCB 正背面、3D、Gerber/Cu 图及 PDF 渲染预览 |
| `firmware_test/` | PlatformIO Arduino 源代码、两种 USB 预编译固件 |
| `sources/footprint_sources.md` | 公共库/官方尺寸对比及所有电气资料来源 |

CSV 使用 UTF-8 BOM，便于 Windows Excel 正确显示。先看 `Design_Summary.md`，再按照本文件进行装配。

## PCB 与布局

- 最大外形 **110×90 mm**，FR4、1.6 mm、双层、每面 1 oz 铜；常规工艺，无特殊阻抗/盲埋孔。
- 四角 4×3.2 mm M3 非金属化孔，中心 `(4,4), (106,4), (4,86), (106,86)` mm。
- 下方中央 31 mm 宽 USB 开口，从 y=64.5 延伸到 y=90，给双 Type-C 插头让位。
- ESP32 位于中央，天线端朝板顶，USB 端朝中央开口。其他模块不会覆盖 BOOT/RST 所在整板区域。
- GY-302 左上方靠边；BME688 右上方靠边；LD2410C 左下方靠边；MQ 右下方靠边。
- BME688 与 MQ 暂定中心距约 37.5 mm，板体之间留约 10.6 mm。BME 区域减少铺铜，下面有 **20×1 mm、圆头热隔离槽**。槽不是割断整块板，连接排针仍有足够的 FR4 支承。
- 默认信号 0.30 mm。SENSOR_5V 主干、MQ 分支、外部电源/舵机主干为 1.00 mm。Q2 SOT-23 源极处仅有总长约 1.76 mm 的 0.601 mm 局部引出线，其余 EXT_5V 为 1.00 mm。它在 1 A 下的铜损耗很小，最终 DRC 也通过。
- 信号过孔 0.80/0.40 mm，电源过孔 1.20/0.60 mm；规则不小于用户要求的常规安全尺寸。最小铜间距 0.20 mm，电源类 0.25 mm，铜到板边 0.30 mm。
- 上下 GND 铺铜，通过接地过孔及大量接地通孔连接。两个天线区均禁止两面铜、走线、焊盘和过孔。导出的 Gerber 已由独立解析器检查，天线区铜像素为零。

## ESP32 开发板与专用封装

用户照片显示 **CH343P、双 Type-C、BOOT/RST、GPIO48 RGB、S3-N16R8、双排各 22Pin**，外观与 YD-ESP32-S3 系列一致。模组上的 N16R8 表示 16 MB Flash、8 MB PSRAM，不能用无线模组 SMD 封装代替整个开发板载板封装。

采用 `custom:ESP32-S3_N16R8_44PIN_CARRIER`，底板实际焊 **2×1x22、2.54 mm 直插排母**，不焊死开发板。建议所有传感器排母和 ESP 排母选择 **本体高度至少 8.5 mm** 的同类直插产品，确保插入后模块底面不压到低矮的底板元件。排母焊脚对应 1.0 mm 钻孔、1.8 mm 焊盘，第一脚为方形焊盘。

| 参数 | 当前值 | 依据/状态 |
|---|---:|---|
| 每侧针数 | 22 | 照片和 2100 mil 跨度一致 |
| 针距 | 2.54 mm | 照片 21 个间隔跨 53.34 mm |
| HEADER_ROW_SPACING | **25.40 mm** | 照片明确标注 1000 mil / 25.40 mm |
| 矩形板宽 | 27.94 mm | 照片 1100 mil / 27.94 mm |
| 矩形 PCB 长 | 57.15 mm | 照片 2250 mil / 57.15 mm |
| 包含突出天线总长 | 63.389002 mm | 照片 2495.63 mil，精确单位换算 |
| 天线端矩形板边到第一脚 | 暂定 **1.905 mm** | 未确认；不是照片比例估算的实测值 |
| 最后一脚到 USB 端边缘 | 暂定 **1.905 mm** | 未确认；暂按剩余长度等分 |

必须核对的五项：两排中心距、PCB 总宽、PCB 总长、第一脚到矩形顶边偏移、最后一脚到 USB 端边缘偏移。还应核对天线突出部分和 USB 插头外壳。现有资料能确定排距/针距，却不能证明端部偏移相等。

**公共库三重核对结果为 PENDING，不能写 MECHANICALLY VERIFIED。** EasyEDA 的两项已知公共资源已取得并逐项查看，第一项排距 23.114 mm 且右排只找到 21 个孔，第二项及 Espressif 官方资料排距 22.86 mm；都与照片 25.40 mm 不符。本项目因此根据照片的显式尺寸重建专用封装，保留毫米精度。完整名称、资源 ID、官方图链接及拒用原因见 `sources/footprint_sources.md`。

编号约定：元件面正视、天线上方、USB 下方，**左排从上至下 1…22，右排从上至下 23…44**；不是绕封装一圈的 DIP 编号。两排从天线端到 USB 端的丝印如下：

```text
左：3V3 3V3 RST 4 5 6 7 15 16 17 18 8 3 46 9 10 11 12 13 14 5V GND
右：GND TX43 RX44 1 2 42 41 40 39 38 37 36 35 0 45 48 47 21 20 19 GND GND
```

GPIO19/20 保留给 USB；GPIO35/36/37 不接底板电路；GPIO0/3/45/46 不作为扩展；GPIO48 保留给板载 RGB；GPIO43/44 留给 CH343P 调试串口。未使用的开发板引脚在原理图中明确 No Connect。GPIO 分配没有改变用户指定的七个主功能。

## GPIO 与接口

| 功能 | ESP32 GPIO | 底板路径 |
|---|---:|---|
| I2C SDA | 8 | J2.2、J3.4、J7.3 |
| I2C SCL | 9 | J2.3、J3.3、J7.4 |
| Radar RX，接 LD TX | 17 | J4.1 → R9 → U1 通道 1 → GPIO17 |
| Radar TX，接 LD RX | 18 | GPIO18 → U1 通道 2 → R10 → J4.2 |
| Radar OUT | 16 | J4.3 → R11 → U1 通道 3 → GPIO16 |
| MQ ADC | 4 | J5.4 → 分压/滤波 → U1 通道 4 → GPIO4 |
| MQ DO | 5 | J5.3 → Q1 NMOS 反相保护 → GPIO5 |
| 普通扩展 | 6、7、10、11 | J8/J9/J10/J11 的第 3 脚 |
| Servo PWM | 12 | R18 1k → J12.3 |

所有排针序号以方形焊盘/Pin1 端为起点，按 2.54 mm 间距向后数。不要仅凭模块“名字”确定方向，实物丝印必须逐脚匹配。

| 接口 | Pin1 → 最后一脚 | 电压/用途 |
|---|---|---|
| J2，GY-302/BH1750 排母 | ADDR / SDA / SCL / GND / VCC | VCC=3V3；感光区域朝上，PCB 边缘留 LIGHT WINDOW |
| J3，BME688 排母 | VCC / GND / SCL / SDA / SDO / CS | VCC=3V3；CS 经 10k 上拉到 3V3 |
| J4，LD2410C 排母 | TX / RX / OUT / GND / VCC | VCC=SENSOR_5V，3.3V UART/OUT |
| J5，MQ 排母 | VCC / GND / DO / AO | VCC=SENSOR_5V，AO/DO 均有保护 |
| J6，外部传感器输入端子 | EXT_5V_RAW / GND | 稳压 5V ONLY，经 Q2 反接保护 |
| JP3，电源选择 | USB / SENSOR / EXT | 一枚跳帽；1–2 USB，2–3 EXT |
| J7，EXT_I2C | 3V3 / GND / SDA / SCL | 可接 3.3V OLED 等 I2C 模块 |
| J8 / J9 / J10 / J11 | GND / 3V3 / GPIO6、7、10、11 | 3.3V GPIO；仅预留接口，没有蜂鸣器/继电器驱动 |
| J12，Servo | GND / 5V_SERVO / SIGNAL | SIGNAL=GPIO12；电源只来自独立 J13 |
| J13，Servo 电源端子 | SERVO_5V_RAW / GND | 稳压 5V ONLY，经 Q3 反接保护 |

GPIO 扩展脚不能直接驱动继电器线圈或大电流蜂鸣器；后续模块需自带驱动。I2C OLED 若自带上拉，仍需检查总线上拉等效值。

Servo SIGNAL 是 **3.3V 输出预留**，没有5V信号转换器；使用接受3.3V信号、且不会把SIGNAL上拉到5V或反向供电的舵机/驱动模块。普通GPIO扩展也仅允许3.3V逻辑。

## 电源树与选择跳帽

```text
ESP32 USB → 开发板内部电源 → ESP32_5V ─→ JP3 pin1
                          └→ +3V3 → GY-302、BME688、逻辑/扩展、3V3 LED

J6 外部 5V → Q2 PMOS 反接保护 → EXT_5V ─→ JP3 pin3
                                      JP3 pin2 = SENSOR_5V
                                          ├→ MQ heater/module
                                          ├→ LD2410C
                                          └→ 滤波、5V LED、U1 SEL 控制

J13 独立舵机 5V → Q3 PMOS → 5V_SERVO → J12 pin2
所有电源负极与底板 GND 相连。
```

**推荐首次完整测试使用 B 模式：ESP32 自己接 USB，传感器接 J6 外部 5V，JP3 跳帽放 2–3。** 外部输入建议能力至少 5V 1A，推荐稳压 5V 2A，额定范围按 5V±5% 设计。输出电流能力大不会“强行灌入”器件，实际由负载决定。载板传感器及舵机独立支路分别按 **1A 连续** 使用，非大功率配电板。

A 模式：关掉所有电源后，将唯一跳帽移到 JP3 1–2，只用 ESP32 USB 给 SENSOR_5V 供电。**照片没有开发板 USB 路径的电流额定资料，因此 A 模式能否带满 MQ+LD+Wi-Fi 负载取决于实物 USB 线、电源及开发板 5V 路径容量，未作满载实测。** 观察 5V 压降/复位，容量不足用 B 模式。

B 模式：跳帽 2–3，J6 接独立 5V。EXT_5V 只给传感器，不会自动给 ESP32 或 USB 供电。ESP32 仍需自己的 USB；3V3 由它的稳压器提供。JP3 铜网络彼此独立，严禁焊成三个脚同时导通、严禁放两枚跳帽。换跳帽/插拔模块先断电。

下面按全部工作时的**设计预留**计算，不是未知型号模块的实测电流：

| 负载 | 5V侧设计预留 | 供电来源 |
|---|---:|---|
| ESP32 Wi-Fi/BT/Flash/PSRAM、开发板电路 | 0.60A | ESP USB |
| GY/BME/逻辑与少量扩展 | 0.05A | ESP板3V3，计入ESP USB负载 |
| MQ模块/加热器 | 0.50A | SENSOR_5V |
| LD2410C及5V指示/余量 | 0.30A | SENSOR_5V |
| 合计，不含舵机 | **1.45A** | A模式全部走USB；B模式USB约0.65A、外部约0.80A |

因此传感器支路按1A连续、外部电源推荐5V2A；MQ实际电流必须在首板确认。按35um铜、1.00mm线宽、100mm路径估算铜电阻约0.049Ω，1A时压降约49mV、铜损耗约49mW；实际路径长度各异，还需加连接器和PMOS压降，最终以满载TP1测量为准。

Q2/Q3 为 AO3401A，Gate=GND、Source=保护后输出、Drain=输入；正确接法的体二极管先向输出充电，再由低电阻 MOS 导通，避免串联肖特基的大压降。它们是反接保护，不能替代稳压器。

SENSOR_5V 入口有 C3 100uF 电解+C4 10uF+C5 100nF；雷达附近 C6/C7；MQ 附近 C8/C9；3V3 总线 C10/C11。U1 本地 C2 100nF；舵机支路 C12/C13。D1=3V3 绿灯，D2=SENSOR_5V 黄灯，均为 2.2k 限流。D1 被移到下边缘，减轻对 BH1750 光照测量的影响；如需要黑暗测量，可不装 LED。

大功率舵机使用自己的电源和粗线直接接舵机，保留共地与 GPIO12 信号连接；不要让超过 1A 的舵机电流经过本载板。现有测试固件不驱动舵机，也不主动驱动普通扩展 GPIO。

## I2C 与地址选择

BH1750 与 BME688 共用 GPIO8/9，默认固件速度 100kHz。底板 R2=SDA 上拉、R3=SCL 上拉，均预留 4.7k，**默认 DNP**。先使用模块已有上拉；若确实没有上拉，再安装 R2/R3。不要为了“保险”全部并联强上拉。

| 地址选择 | 默认 | 可改为 |
|---|---|---|
| JP1，BH_ADDR | 铜桥 1–2，ADDR=GND，0x23 | 切断 1–2 后焊 2–3，ADDR=3V3，0x5C |
| JP2，BME_ADDR | 铜桥 1–2，SDO=GND，0x76 | 切断 1–2 后焊 2–3，SDO=3V3，0x77 |

地址选择不是供电选择跳帽。两个地址焊盘都有出厂铜桥，改地址必须先割断旧铜桥并检查不再短接；否则会把 3V3 与 GND 短接。BME CS 由 R1 10k 上拉保证 I2C，后续需要 SPI 可拆掉 R1 并重新设计连接，当前底板并未提供完整 SPI 总线。

## MQ 模拟与数字保护

MQ 模块使用 5V 时 AO/DO 不直接进入 ESP32。

```text
MQ_AO_RAW ─ R4 6.8k ─ MQ_ADC_FILTER ─ U1 ch4 ─ MQ_ADC / GPIO4
                         │                         │
                         R5 7.5k                   R15 100k
                         │                         │
                         GND                       GND
                         │
                 C1 100nF（MQ_ADC_FILTER 到 GND）
```

使用 **6.8k/7.5k、1%**，比用户初始建议 4.7k/7.5k 留出更多 ESP32-S3 ADC 可测量余量；GPIO 不变。U1 导通时 R15 100k 也负载 ADC，因此有效下拉约 6.977k，实际标称比例 **0.5064**，AO=5.00V 时 GPIO4 约 **2.532V**。考虑 5.25V 输入及最不利 1% 电阻误差，最高约 **2.685V**，低于 ADC 11dB 的约 2.9V 有效范围与 3.3V GPIO 电源。100nF 滤波时间常数约 0.34ms；固件使用 12bit/11dB、多次平均及校准毫伏读数。实际 MQ 的 AO 输出阻抗还可能使读数下降，最终需要实测校准。

DO 采用器件少的 **Q1 AO3400A NMOS 反相接口**：R6 33k 输入、R7 100k Gate 下拉，Drain 经 R8 10k 拉到 3V3。R21 10k 将原始 DO 上拉到 SENSOR_5V，兼容 LM393 开集输出，也兼容已经有 5V 上拉或推挽的模块。MOS 栅极绝缘，5V 不送入 ESP32；实物模块低电平需能吸收附加约 0.5mA 上拉电流。

**GPIO5 极性反相：MQ 原始 DO 低 → GPIO5 高。** 常见模块原始报警为低，则保护后的高表示触发。具体触发阈值由 MQ 模块电位器决定。在 SENSOR_5V 关闭时，这个输入不能解释为有效气体报警。

## 雷达逻辑与独立电源时序

Hi-Link 编制的 LD2410C 手册给出 5V 推荐供电、TX/RX/OUT 为 **3.3V IO**、UART 默认 **256000、8N1**、OUT 有人时高。连接为 TX→ESP RX17，ESP TX18→RX，OUT→GPIO16。R9/R10/R11 均 1k，提供串联保护和调试拆分。

仅有串联电阻不能阻止“传感器外部 5V 仍开启、ESP32 断 USB”时的信号反向供电。因此增设 **U1 TMUX1511PWR** 四路带 powered-off protection 的开关，同时隔离雷达 TX/RX/OUT 和 MQ ADC。U1 供电=3V3；四个控制脚经 R20 10k 由 SENSOR_5V 控制，允许控制高电平到 5.5V，即使 U1 未供电。没有 SENSOR_5V 或 3V3 时开关关闭；R12/R13/R14/R15 100k 使敏感节点落地。按数据手册最大断电漏电 2uA、100k±1% 计算节点不超过约 0.202V。

**U1 是电源时序隔离器，不是把 5V UART 降成 3.3V 的转换器。** 采用的是厂家 LD2410C 的 3.3V IO 定义；如果手中模块 TX/OUT 测得超过 3.3V，必须停止插入并改相应电平保护，不要替换成任意“同名”5V 输出克隆。传感器端子 5V 与 GPIO 网络没有直接铜连接。

## 天线、光路、热与安装方向

ESP32 两面禁铜区域为 `(44,0)–(66,13.4)` mm，LD 雷达区域为 `(0,47.5)–(19.5,67)` mm，均有禁止走线、焊盘、过孔、铺铜的 rule area。ESP32 天线伸向顶边，LD 天线对应底板左侧边缘。不要让金属螺钉、其他 PCB、电池、金属外壳进入这些区域或遮挡前方。

**LD2410C 的主要观察方向是贴片天线板的正面法向，不是 PCB 平面内沿着板边“射出去”。** 丝印 `FACE UP +Z` 表示正面朝模块上方；墙装时让这一面朝房间。把天线半边放在左边缘是为了远离底板铜和金属，不能代替正确的雷达朝向。

GY-302 感光面朝上，位于板边，外壳应预留 LIGHT WINDOW。BME 进气口朝通风侧；MQ 金属加热罐上方不要覆盖。不仅要看平面距离，还要看重力热气流：若将底板挂墙，**旋转到 BME 与 MQ 横向排列，避免 MQ 在 BME 正下方**。正常水平放置时让两个模块上方分别通风。BME 自身测气体时也有加热器，测试固件返回原始温湿压/电阻值，没有环境温度补偿或 BSEC IAQ 算法。

3D 图包含真实排母/器件库模型，以及明确标为 APPROXIMATE_ENVELOPE 的模块模型。它用于检查当前布局的平面包络、排母方向、USB 开口、四角孔和元件高度关系；不代表用户模块已被精确建模。实际照片中的 USB 插头尺寸和 BOOT/RST 高度也必须核对。

## 测试点

| 丝印 | 测量网络 | 预期 |
|---|---|---|
| TP1 / TP_5V | SENSOR_5V | 约 5V，取决于 JP3 位置 |
| TP2 / TP_3V3 | +3V3 | 有 ESP USB 时约 3.3V |
| TP3 / TP_GND | GND | 万用表/逻辑分析仪共地 |
| TP4 / TP_SDA | I2C_SDA | 3.3V I2C |
| TP5 / TP_SCL | I2C_SCL | 3.3V I2C |
| TP6 / TP_LD_TX | RADAR_TX | 雷达原始 TX，3.3V |
| TP7 / TP_LD_RX | RADAR_RX | 雷达 RX，ESP 输出方向 |
| TP8 / TP_LD_OUT | RADAR_OUT | 雷达原始 OUT，3.3V |
| TP9 / TP_MQ_AO_RAW | MQ_AO_RAW | 可能到 5.25V，不能直接接 ESP GPIO |
| TP10 / TP_MQ_ADC | MQ_ADC | 受保护 ADC，设计最坏约 2.685V |
| TP11 / TP_MQ_DO | MQ_DO_3V3 | 保护后反相数字信号，0/3.3V |

## 装配与首次上电

先打印并完成 1:1 校验，确认下列检查后再下单。焊接先 U1（TSSOP-14、0.65mm 脚距，建议助焊剂/拖焊），再 SOT-23、1206 电阻电容/LED，最后电解、电源端子和排母。U1 是必装保护器件，不能省略或用导线代替。C3 为有极性电解，D1/D2 按定位图与封装 K/A 方向安装。R2/R3 默认不焊。

**Step 1：不插任何用户模块。** 断电测量 3V3/5V 对地阻值、地址铜桥、电源选择没有短接。JP3 2–3，J6 接限流的稳压 5V，测 TP1 约 5V，D2 亮。此时 **TP2=0V、D1 熄灭是正常现象**，因为 3V3 来自尚未插入的 ESP32；空板不会自己产生 3V3。也可用实验电源受控注入 3.3V 测试逻辑，但不要在 ESP32 插入后同时向 3V3 强行供电。

**Step 2：全部断电，插 ESP32，再接 ESP USB。** 天线上、USB 下，排母无错位，BOOT/RST 可按，双 Type-C 插头可访问。测 TP2 3.3V，D1 亮；烧录 `yd_uart` 或 `yd_native_usb` 固件，检查串口显示 16MB Flash / 8MB PSRAM，USB、BOOT、RESET、串口正常。

**Step 3：断电插 GY-302，再上电。** I2C 扫描出现 0x23，改变光照能改变 Light Lux；JP1 改地址才应出现 0x5C。

**Step 4：断电插 BME688。** 默认扫描出现 0x23 和 0x76，温湿压及 BME Gas（ohm）能打印。CS 为高；JP2 改为 3V3 后地址为 0x77。

**Step 5：断电插 LD2410C，保持 B 模式。** 外部传感器 5V 与 ESP USB 都开启；测 LD TX/OUT 高电平不超过 3.3V，串口持续收到雷达十六进制数据，移动/静止存在状态与 OUT/打印值相符。用逻辑分析仪设置 256000、8N1。确认 ESP RX17 接 LD TX，不要反接。

**Step 6：最后插 MQ。** 断电核对 AO/DO/GND/VCC 排序，之后先用万用表测 TP9、TP10。设计要求原始 AO 不超过稳压 5V 最高 5.25V、TP10 保持明显低于 3.3V，计算上界约 2.685V。检查 MQ ADC Raw、毫伏值与万用表一致，调电位器观察反相后的 MQ Digital。预热时间依具体 MQ 型号决定，未提供型号不能宣称已经校准浓度。

建议插MQ之前先做最高电平模拟：全部断电、MQ保持未插，临时连接 **J5.4 AO 与 J5.1 VCC**；开启ESP USB和SENSOR_5V，测TP9/TP10。TP10应约等于TP9×0.5064（名义5V时约2.532V），而不是5V。确认后全部断电、撤掉临时连线，再插MQ。这是一次性台架测试，不保留到成品中。最坏5.25V/电阻误差上界仍按自动审查的2.685V判断。

最后再尝试 USB 模式 A，确认满载无明显 5V 压降、ESP 重启或 USB 线过热。两种电源先后开关也要实测：只有外部 SENSOR_5V 时 3V3 不应被抬高；只有 ESP USB 而传感器外部 5V 关闭时，雷达侧 RX 不应被 ESP 反向供电。当前工程的自动电压检查不能代替这一步硬件上电测试。

## 测试固件

详见 `firmware_test/README.md`。安装 PlatformIO 后在该目录执行：

```sh
pio run -e yd_uart
pio run -e yd_uart -t upload --upload-port COMx
pio device monitor --port COMx --baud 115200
```

CH343P 的串口 USB 使用 `yd_uart`；芯片直连 USB 使用 `yd_native_usb`。固件配置 QIO Flash + OPI PSRAM、16MB Flash 分区，`board=esp32-s3-devkitc-1` 只是 PlatformIO 软件构建基类，不是本载板机械封装。两种配置均已实际编译通过，日志在 checks 中；还没有向用户实物烧录，也没有硬件运行验证。

每两秒输出 Light Lux、Temperature、Humidity、Pressure、BME Gas 电阻、Radar Presence、MQ ADC Raw、校准毫伏、估计原始 AO 和 MQ Digital；每秒输出雷达 UART 数据片段与总字节数。BME688 使用兼容 BME68x 的库读取原始数据；没有 BSEC 算法/训练模型，因此不会打印伪造的 IAQ/CO2/ppm。

## 设计审查与制造状态

系统性审查结果见 `checks/design_review.md`，机器可读结果见 `design_validation.json`。实际运行 `kicad-cli sch erc`、`pcb drc --schematic-parity --all-track-errors`；没有“全部忽略错误”，没有 ERC/DRC exclusions。ESP 电源输出明确建模，独立电源用 PWR_FLAG，未用引脚用 No Connect。未安装的 I2C 上拉仍在原理图/BOM 清楚标成 DNP。

Gerber 由最终 PCB 导出，而不是手工伪造。独立 Gerbonara 解析器读取全部层/钻孔：7 层、143 个 PTH 钻孔、4 个 3.2mm NPTH，ESP 和雷达区域两面铜检查通过。解析器对 KiCad 标准 G90 钻孔头位置及 RoundRect 宏额外参数有兼容性提示，均记录在 `gerber_validation.json`，解析和几何校验成功。

制造包放在 **PROVISIONAL_MECHANICAL_DIMENSION_PENDING** 目录；**电气/布线设计完成，制造几何可导出，实物匹配确认后才可正式下单。** 不会凭公共库名称或照片外观写成 PRODUCTION VERIFIED。参数改变后必须重新生成封装/布局、重新布线和铺铜、执行 ERC/DRC/网络审查，再导出新的 Gerber，不能只改 README 状态。

### 打板前检查表

- [ ] PDF 按 100% 打印，100mm 校准尺正确。
- [ ] 开发板两排 22Pin 全部与孔中心重合，针序与照片/CSV 一致。
- [ ] 确认排距、总宽、总长、第一脚到顶边、最后脚到 USB 边五项尺寸。
- [ ] GY/BME/LD/MQ 实际针序与 J2/J3/J4/J5 一致；PCB 包络和排母高度匹配。
- [ ] 两个 USB 插头不碰底板，BOOT/RST 可操作。
- [ ] 两块天线的真实位置落在无铜区，外壳/螺钉/其他模块不遮挡。
- [ ] GY 留光窗，BME 留进气口，MQ 通风且热气流不经过 BME。
- [ ] 核对 MQ 具体型号与加热电流；传感器 5V 和实际开发板 USB 电源能力足够。
- [ ] 确认实物 LD2410C 的 TX/OUT 为 3.3V 电平。
- [ ] JP3 只放一个跳帽；JP1/JP2 改地址前切断默认铜桥；R2/R3 DNP。
- [ ] 确认使用最新 DRC 0 / ERC 0 / Unconnected 0 的 PCB 与同次导出的 Gerber。
- [ ] 查看 Gerber 各层、USB 开口、圆头热隔离槽及四个独立 NPTH。
- [ ] 下单规格：2 层 FR4 1.6mm 1oz，常规绿油，孔槽按 Edge.Cuts/钻孔文件加工。

## 参数化与维护

`mechanical_parameters.json` 中 `HEADER_ROW_SPACING` 等值容易修改，`scripts/build_board.py` 使用 KiCad 9 自带 Python 生成专用封装和初始布局。`scripts/build_schematic.py` 生成原理图；`scripts/make_deliverables.py` 生成 CSV 和 1:1 PDF。源代码随包交付。

**build_board.py 会重建未布线 PCB，覆盖现有布局/走线；先另存工程副本再运行。** 它依赖完整 KiCad 标准库，当前最终 PCB 已由后续布局、布线和审查步骤修正。重新生成后按实物尺寸更新位置、重新布线；不能把旧路由会话直接套在改排距的新板上。`scripts/validate_design.py` 同时核对设计 manifest、实际 XML netlist 和 PCB 导出 pad 网络，`scripts/check_gerbers.py` 检查实际导出的制造文件。

最终 PCB 和制造文件是交付依据；`scripts/` 是维护工具，不需要运行脚本才能正常打开工程。公共库/芯片数据表和固件依赖链接集中在 sources，方便日后追溯。

