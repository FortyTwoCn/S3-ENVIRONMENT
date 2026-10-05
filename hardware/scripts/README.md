# 工程维护脚本

最终 `.kicad_pcb` 已布线。正常使用直接打开 KiCad 工程，无需执行脚本。

`build_board.py` 使用 KiCad 9 自带 Python，读取 `mechanical_parameters.json`，生成参数化专用44Pin封装/器件/初始布局。**它覆盖当前PCB，输出未布线板；必须在副本运行。** `build_schematic.py` 为普通Python，生成原理图。`prepare_routing.py` 准备DSN；`import_routes.py` 导入Freerouting SES并按实际KiCad XML netlist同步网络；`complete_routes.py`/`apply_routes.py` 是后续连通性修正工具，不适合未经检查地直接套用旧中间文件。修改排距后必须重新布线，不沿用旧制造文件。

最终审查工具：

- `refill.py`：KiCad Python，重新填充地平面。
- `export_geometry.py`：KiCad Python，提取实际PCB pad/track/via几何供自动检查。
- `validate_design.py`：普通Python+Shapely，检查manifest/实际netlist/实际PCB网络、ADC误差、断电保护、模块包络、天线与电源线宽，并读取真实ERC/DRC报告。
- `check_gerbers.py`：普通Python+Gerbonara/PyMuPDF/Numpy，独立解析制造文件及栅格检查天线铜区。
- `make_deliverables.py`：普通Python+ReportLab/PyMuPDF，生成CSV、尺寸说明、1:1PDF及装配PDF。
- `add_models.py`：普通Python+sexpdata，添加便携STEP及暂定模块3D包络；从完整KiCad库取得模型，涉及偏移的数值需随实物参数复核。
- `package_release.py`：打包源文件、模型、验证记录和两种实编译固件，生成SHA256 manifest，排除编译缓存/临时锁文件。
- `validate_sensor_photo.py`：R1.1新增，从实物背面针序及安装视角核对四个单排接口；验证实际PCB孔中心/针距，并与XML网络表及CSV逐脚比较。BME688背面针序来自用户文字确认，GY/MQ部分遮挡针名仍需实物核对。

路由修正工具依赖 `checks/geometry.json` 与当前DRC结果；几何数据由当前PCB重新导出，发行ZIP排除了过期路由DRC和会话中间数据。最终审查结果、几何数据和KiCad/Gerber文件都包含在ZIP内。最终布局有人工审查修正，重建脚本的初始布局不能取代最终布局。

KiCad CLI验证示例：

```sh
kicad-cli sch export netlist esp32_sensor_carrier.kicad_sch --format kicadxml -o fabrication/netlist.xml
kicad-cli sch erc esp32_sensor_carrier.kicad_sch --format json -o checks/erc.json
kicad-cli pcb drc esp32_sensor_carrier.kicad_pcb --format json --schematic-parity --all-track-errors -o checks/drc_final.json
```

运行后先检查退出状态和报告，不能仅因为输出了JSON就宣称通过。
