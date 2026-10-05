# 暂定制造文件

**MECHANICAL VERIFICATION REQUIRED / MECHANICAL_DIMENSION_PENDING**

`PROVISIONAL_MECHANICAL_DIMENSION_PENDING/` 为已完成电气和布线检查的真实导出文件。尚未把用户实物放到1:1图上确认，不是 PRODUCTION VERIFIED。

里面的 `.gtl/.gbl` 为铜层，`.gts/.gbs` 为阻焊，`.gto/.gbo` 为丝印，`.gm1` 为外框/USB开口/BME热隔离槽。PTH和NPTH各独立 `.drl`，SVG钻孔图是检查参考，不作为单独制造层。装配是手工焊接，未包含钢网/贴片机程序。可单独压缩这7层+2钻孔文件作为厂家上传包，但必须先完成README的实物核对表。

规格：110×90mm最大外形、2层FR4、1.6mm、1oz铜、常规绿油。Edge.Cuts包含内部非金属化热隔离槽与向板底开放的USB开口，四角M3孔由NPTH钻孔定义。检查结果和文件SHA256见 `checks/gerber_validation.json`。任何机械修改后重导出，不复用这份暂定Gerber。
