# 四个传感器实物照片复核 - R1.1

依据 `sources/actual_sensor_modules.jpg`，以及用户文字确认的 BME688 背面针序。所有“左→右”必须附带观察面和模块本体方向，不能把模块背面与底板顶视混用。

本版安装条件：GY-302、BME688、MQ 的感测面朝上，模块本体位于底板顶视中排针的上方；雷达天线面朝上，模块本体在竖直排母的左侧。底板焊竖直排母，模块焊直针向下。

| 模块 | 照片所见/确认 | R1.1 底板 Pin1→末脚 | 处理 |
|---|---|---|---|
| BME688 | 背面 CS / SDO / SDA / SCL / GND / VCC，用户逐脚文字确认 | VCC / GND / SCL / SDA / SDO / CS | 原 J3 已是 1×6，针序正确，保持不变 |
| GY-302 | 照片空白背面，上→下部分可读；结合原始完整 VCC / GND / SCL / SDA / ADDR 定义 | ADDR / SDA / SCL / GND / VCC | J2 镜像针序，同步修正铜线/丝印/原理图/CSV；完整实物丝印仍需核对 |
| MQ | 背面 AO / DO / GND / VCC，后两针部分被电位器遮住；原始完整定义相同 | VCC / GND / DO / AO | J5 镜像针序，同步修正；AO=J5.4，DO=J5.3 |
| LD2410C | 天线面 TX / RX / OUT / GND / VCC 清楚可见 | TX / RX / OUT / GND / VCC | 与原接口/厂家手册一致，GPIO17接TX、GPIO18接RX、GPIO16接OUT |

**BME 六脚是在同一直线上的 1×6，不是 3×2。** 实际 PCB：X=84.00 / 86.54 / 89.08 / 91.62 / 94.16 / 96.70 mm，Y 均为 25.00 mm；首末针中心距 12.70 mm。自动检查直接读取实际 PCB 几何，并与 XML 网络表和 CSV 比较，见 `sensor_photo_review.json` 和 `fabrication/sensor_socket_review.csv`。

## 发现的机械问题

- MQ 现有弯针与本版平放安装不兼容。需要拆换成直针，从模块背面向下插排母；不要直接掰针造成焊盘损坏。BME/GY 的针脚安装方式也需在实物上检查，不能仅凭照片断言全部可直接插入。
- 雷达照片中五孔未装排针，需要在背面补焊 1×5 直针。厂家手册的天线图形、22×16 mm 标称尺寸、2.54 mm 针距和接口与照片一致；仍要核对实际板边/排针偏移，照片不是尺寸量具。
- 保留弯针让模块站立，会改变包络、光窗、热气流和朝向。本版继续采用已说明的平放方案；站立方案需要另行调整机械布局。
- GY-302 感光芯片在照片不可见的另一面，应朝光窗；BME 感测面/气孔应朝通风侧；MQ 金属探头朝上。不能用照片中朝上显示标签的背面作为感测面。
- 一张没有标尺的照片不能完成四块模块本体尺寸、孔距误差、插接高度和 PCB 碰撞的生产验证。真实 MQ 型号仍未知，测试固件不会据此编造浓度 ppm。

## 修正与检查

R1.1 修正了 J2 / J5 八个焊盘的网络、对应原理图和丝印，并重新布线、铺铜、执行 ERC / DRC / schematic parity、连接/电压检查和 Gerber 天线铜区检查。GPIO 和供电架构没有变化。BME、雷达接口保持正确连接。

最终原始检查记录在 `erc.json`、`drc_final.json`、`design_validation.json`、`gerber_validation.json`，以这些真实结果为准。**ERC/DRC 通过表示设计文件一致和制造规则通过，不等同于插入这些实物已经工作。**

状态：**MECHANICAL_DIMENSION_PENDING / PHYSICAL PINOUT CHECK PENDING / HARDWARE_NOT_TESTED**。不要使用 R1 的旧制造文件。
