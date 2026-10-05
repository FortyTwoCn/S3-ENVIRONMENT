# R1.1 系统性 Design Review

基于最终 KiCad PCB/原理图、XML网络表、全部规则启用的原生ERC/DRC、独立Gerber解析及3D/PDF视觉检查。PASS表示设计文件核对通过；PENDING表示还需要用户实物，不能以照片/近似模型代替。

| 项目 | 状态 | 结论/处理 |
|---|---|---|
| ESP32 Footprint | PENDING | 专用2x22、25.40mm排距；照片显式尺寸，两个端部偏移待核对 |
| Pin Number | PASS / 实物待核对 | 左1–22、右23–44，从天线到USB；44Pin按照片丝印重建，网络表与PCB一致 |
| GPIO | PASS | 8/9 I2C、17/18/16 radar、4/5 MQ；USB/PSRAM/strapping/RGB保留 |
| USB clearance | PENDING | 31×25.5mm中央开口；实物双USB插头外壳及板边偏移待验证 |
| BOOT access | PASS / PENDING | ESP整板上方无其他模块覆盖；实物装配高度待确认 |
| RESET access | PASS / PENDING | 同上 |
| ESP32 Antenna | PASS / PENDING | 两面铜/线/孔严格禁布，Gerber铜检查通过；真实板位置与外壳待验证 |
| LD2410 Antenna | PASS / PENDING | 天线半边靠左外沿，两面禁布；FACE UP +Z；真实贴片面/封装偏移待验证 |
| BME thermal isolation | PASS | 20×1mm圆头槽，模块区少铜；明确墙装方向及热气流条件 |
| BH1750 light path | PASS / PENDING | 左上边缘，LIGHT WINDOW；LED已移走；外壳窗需实际留出 |
| MQ heat | PASS / PENDING | 右下通风，BME/MQ包络无重叠；具体MQ型号/高度/气流待确认 |
| MQ 5V | PASS | SENSOR_5V，主干和分支1mm，近端10uF+100nF |
| ADC divider | PASS | 6.8k/7.5k+100k负载，5.25V+1%最坏2.6849V，滤波及断电隔离 |
| DO level | PASS | NMOS栅极输入+3V3漏极上拉，原始5V不直接到GPIO，反相已在固件/文档说明 |
| UART crossing | PASS | J4TX到ESP RX17，ESP TX18到J4RX，256000 8N1，厂家3.3V IO |
| I2C | PASS | 两模块共8/9，上拉DNP，CS上拉，ADDR/SDO默认铜桥到GND可改 |
| 3V3 | PASS | 来自ESP开发板，无板上独立3V3稳压器；空板3V3=0正确记录 |
| 5V | PASS / PENDING | 外部推荐5V2A；每支路按1A连续；实物USB路径满载能力待测 |
| GND | PASS | 上下铺铜、接地过孔/通孔连接；无天线区铺铜 |
| Power selection | PASS | 独立三网络一枚跳帽，默认建议EXT，不硬并联USB/EXT |
| Backfeed | PASS | U1断电隔离+下拉，MOS DO栅极隔离；序列验证算法，实物上电待做 |
| Test points | PASS | 11个测点，MQ原始AO与受保护ADC明确区分 |
| Mounting holes | PASS / PENDING | 4x3.2mm NPTH，独立钻孔解析正确；外壳螺钉/支柱高度待定 |
| Silkscreen | PASS | 名称、Pin1、接口针名、电源、方向/地址背面表；native DRC丝印0违规 |
| Module orientation | PASS / PENDING | BME用户确认1×6及背面针序；J2/J5已按感测面朝上镜像，铜线/丝印同步修正；模块直针向下，弯针及真实尺寸需实物核对 |
| ERC | PASS | 0错误/警告，显式NC/PWR_FLAG，无全局忽略/排除 |
| DRC | PASS | 0错误/警告、0未连接、0原理图一致性问题 |

审查中已修正：独立5V时信号反向供电风险（加TMUX1511）、MQ DO关机注入风险（用绝缘栅NMOS）、ADC裕量（6.8k）、USB大开口、雷达实际观察方向、GY旁LED光污染、铺铜局部热连接、悬空铜线和丝印干涉。每次影响PCB的修改均重新检查，最终实际报告见 `drc_final.json`。

照片复核新增修正：GY-302 / MQ 的正反面镜像针序，BME 1×6 几何核对，明确 MQ 弯针与平放方案不兼容及雷达需补焊排针。详见 `sensor_photo_review.md`。

最终判定：**ELECTRICAL_AND_ROUTING_PASS / MECHANICAL_PENDING / HARDWARE_BRINGUP_NOT_PERFORMED**。完整工程和暂定制造输出均可检查，不假装已经完成实物生产验证。
