"""Generate CSV documentation and dimensionally correct verification/assembly PDFs."""
import pathlib,json,csv,collections,math
import pymupdf as fitz
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor,black,white
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
R=pathlib.Path(__file__).resolve().parents[1];F=R/'fabrication'
M=json.loads((F/'design_manifest.json').read_text(encoding='utf-8'));P=M['mechanics'];V=json.loads((R/'checks/design_validation.json').read_text(encoding='utf-8'))
pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))
def csvfile(name,heads,rows):
 with (F/name).open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.writer(f);w.writerow(heads);w.writerows(rows)
headers={'J1':('1x22 Female Header',2,'2.54mm pitch; straight through-hole; >=8.5mm body height; 25.40mm row spacing'), 'J2':('1x5 Female Header',1,'GY-302; 2.54mm pitch; >=8.5mm height'), 'J3':('1x6 Female Header',1,'BME688; 2.54mm pitch; >=8.5mm height'), 'J4':('1x5 Female Header',1,'LD2410C; 2.54mm pitch; >=8.5mm height'), 'J5':('1x4 Female Header',1,'MQ; 2.54mm pitch; >=8.5mm height')}
rows=[];groups=collections.defaultdict(list)
for c in M['components']:
 ref=c['ref'];value=c['value'];foot=c['footprint'].split(':')[1]
 if ref in headers:
  value,qty,note=headers[ref];rows.append([ref,value,qty,foot,'FIT',note]);continue
 if ref.startswith('TP'):continue
 if ref in ['JP1','JP2']:
  rows.append([ref,'3-pad copper solder selector',0,foot,'PCB FEATURE','Factory copper bridge 1-2=GND; cut before soldering 2-3=3V3']);continue
 if ref in ['J6','J13']:value='2-pin 5.08mm screw terminal';note='5V ONLY; pin1 positive pin2 GND; input wire clearance required'
 elif ref=='JP3':value='1x3 Male Header';note='2.54mm pitch; selector; one rated >=3A shunt only'
 elif ref=='J7':value='1x4 Male Header';note='2.54mm pitch; EXT_I2C 3V3/GND/SDA/SCL'
 elif ref in ['J8','J9','J10','J11','J12']:value='1x3 Male Header';note=c['value']+'; 2.54mm pitch; see interface pinout'
 else:note=c['description']
 groups[(value,foot,'DNP' if c['dnp'] else 'FIT',note)].append(ref)
for (value,foot,fit,note),refs in groups.items():rows.append([', '.join(refs),value,len(refs),foot,fit,note])
rows.extend([['JP3-SHUNT','2.54mm jumper cap',1,'Accessory','FIT','>=3A rated; default 2-3 EXT; never bridge all three pins'],['TP1-TP11','Plated test pads',0,'1.5mm pad / 0.7mm drill','PCB FEATURE','Optional test hooks or solder pins; no fitted part required'],['H1-H4','M3 mounting hardware',4,'3.2mm NPTH','OPTIONAL','Nylon standoffs recommended; no metal above antenna regions'],['MODULE-ESP','ESP32-S3 N16R8 44-pin board',1,'USER PROVIDED MODULE','USER INSTALLED','Dual Type-C CH343P board matching supplied photo; do not place in PCB SMT order'],['MODULE-GY','GY-302 / BH1750 module',1,'USER PROVIDED MODULE','USER INSTALLED','Sensing face up: ADDR/SDA/SCL/GND/VCC from carrier pin1; verify straight downward header'],['MODULE-BME','BME688 I2C module',1,'USER PROVIDED MODULE','USER INSTALLED','VCC/GND/SCL/SDA/SDO/CS must match actual module'],['MODULE-LD','HLK-LD2410C module',1,'USER PROVIDED MODULE','USER INSTALLED','TX/RX/OUT/GND/VCC; 3.3V logic'],['MODULE-MQ','MQ gas module',1,'USER PROVIDED MODULE','USER INSTALLED','Sensing face up: VCC/GND/DO/AO from carrier pin1; 5V heater; right-angle header needs replacement for horizontal mounting']])
csvfile('BOM.csv',['References','Value / Part','Quantity','Footprint','Population','Notes'],rows)
csvfile('netlist.csv',['Reference','Pin','Pin name','Net','Section','Value','DNP'],[[c['ref'],p['number'],p['name'],p['net'] or 'NO CONNECT',c['section'],c['value'],c['dnp']] for c in M['components'] for p in c['pins']])
csvfile('gpio_map.csv',['Function','GPIO','Direction','Interface','Protection / notes'],[['I2C SDA',8,'Bidirectional','J2.2 / J3.4 / J7.3','3.3V; R2 4.7k DNP'],['I2C SCL',9,'Output','J2.3 / J3.3 / J7.4','3.3V; R3 4.7k DNP'],['Radar RX (LD TX)',17,'Input','J4.1','R9 1k -> U1 ch1; 100k pulldown'],['Radar TX (LD RX)',18,'Output','J4.2','U1 ch2 -> R10 1k; 100k pulldown'],['Radar OUT',16,'Input','J4.3','R11 1k -> U1 ch3; 100k pulldown'],['MQ ADC',4,'Input ADC1','J5.4','6.8k / 7.5k divider; 100nF; U1 ch4; 100k pulldown'],['MQ DO',5,'Input','J5.3','AO3400A inverter; 10k 3V3 pullup; polarity inverted'],['Expansion',6,'User GPIO','J8.3','3.3V only'],['Expansion',7,'User GPIO','J9.3','3.3V only'],['Expansion',10,'User GPIO','J10.3','3.3V only'],['Expansion',11,'User GPIO','J11.3','3.3V only'],['Servo PWM',12,'Output','J12.3','R18 1k; independent servo 5V rail']])
j1=next(c for c in M['components'] if c['ref']=='J1')
csvfile('esp32_pinout.csv',['Carrier pad','Row','From antenna end','Photo silk','Assigned net'],[[p['number'],'LEFT' if int(p['number'])<=22 else 'RIGHT',((int(p['number'])-1)%22)+1,p['name'],p['net'] or 'NC'] for p in j1['pins']])
csvfile('interface_pinout.csv',['Reference','Pin','Pin label','Net','X mm','Y mm','Rotation deg'],[[c['ref'],p['number'],p['name'],p['net'],*c['position']] for c in M['components'] if c['ref'].startswith(('J','TP')) for p in c['pins']])
(F/'pcb_dimensions.txt').write_text('110.00 x 90.00 mm carrier bounding box\n2 layers, FR4 1.6 mm, 1 oz copper (35 um each side), green mask suggested\nUSB cutout: x=39.50..70.50 mm, y=64.50..90.00 mm\nBME isolation slot: x=84.50..104.50 mm, y=27.50..28.50 mm, radius 0.50 mm ends\n4 x 3.20 mm NPTH at (4,4), (106,4), (4,86), (106,86) mm\nSignal 0.30 mm; power main/MQ 1.00 mm; Q2 source escape 0.601 mm for <2 mm only\nSignal vias 0.80/0.40 mm; power vias 1.20/0.60 mm\nClearance >=0.20 mm; power class 0.25 mm; copper-to-edge >=0.30 mm\nESP32: row 25.40 mm, pitch 2.54 mm, 2x22, span 53.34 mm\nESP body 27.94 x 57.15 mm; total antenna length 63.389002 mm\nTop and USB pad-to-body offsets provisionally 1.905 mm EACH, NOT VERIFIED\nMECHANICAL_DIMENSION_PENDING / MECHANICAL VERIFICATION REQUIRED\n',encoding='utf-8')
def line(c,x1,y1,x2,y2):c.line(x1*mm,y1*mm,x2*mm,y2*mm)
def txt(c,x,y,s,size=9,color=black):c.setFillColor(color);c.setFont('STSong-Light',size);c.drawString(x*mm,y*mm,s)
def title(c,t):txt(c,15,281,t,17,HexColor('#124a66'));txt(c,15,272,'R1.1 - MECHANICAL VERIFICATION REQUIRED',10,HexColor('#b22828'))
def footer(c,p):txt(c,15,12,'ESP32-S3 SENSOR CARRIER | R1.1-PENDING | 100% PRINT / 禁止缩放打印',8);txt(c,186,12,str(p),8)
def calibration(c,y=22):
 c.setStrokeColor(black);c.setLineWidth(.25*mm);line(c,20,y,120,y)
 for x in range(20,121,10):line(c,x,y-1.5,x,y+1.5)
 txt(c,20,y+4,'100.00 mm 校准尺：打印后先用直尺确认长度。',9)
def outline(c,coords,x0,y0,scale=1):
 path=c.beginPath();path.moveTo((x0+coords[0][0]*scale)*mm,(y0-coords[0][1]*scale)*mm)
 for x,y in coords[1:]:path.lineTo((x0+x*scale)*mm,(y0-y*scale)*mm)
 c.drawPath(path)
pdf=F/'ESP32_FOOTPRINT_1_TO_1_CHECK.pdf';c=canvas.Canvas(str(pdf),pagesize=(210*mm,297*mm));c.setTitle('ESP32 footprint 1:1 verification - R1 mechanical pending')
title(c,'ESP32-S3 44Pin 开发板 1:1 封装校验')
txt(c,15,261,'依据：用户提供的带标注尺寸照片。孔位排距/针距有尺寸依据；端部偏移仍待确认。',9)
txt(c,15,255,'打印选 Actual Size / 实际大小 / 100%，关闭 Fit to Page。将实物排针放在孔中心十字上。',9)
cx=105;py=232;pitch=P['PIN_PITCH'];row=P['HEADER_ROW_SPACING']
span=(P['PINS_PER_ROW']-1)*pitch;topoff=P['FIRST_PIN_FROM_BODY_TOP'];usboff=P['LAST_PIN_FROM_USB_EDGE'];bodylength=span+topoff+usboff
c.setStrokeColor(HexColor('#d88a25'));c.setDash(1.2*mm,.8*mm);c.setLineWidth(.2*mm)
c.rect((cx-P['ESP_PCB_WIDTH']/2)*mm,(py-span-usboff)*mm,P['ESP_PCB_WIDTH']*mm,bodylength*mm,stroke=1,fill=0)
c.rect((cx-9)*mm,(py+topoff)*mm,18*mm,(P['ESP_TOTAL_LENGTH']-bodylength)*mm,stroke=1,fill=0);c.setDash()
for p in j1['pins']:
 n=int(p['number']);i=(n-1)%22;x=cx+(-1 if n<=22 else 1)*row/2;y=py-i*pitch
 c.setStrokeColor(black);c.setLineWidth(.1*mm)
 if n==1:c.rect((x-.5)*mm,(y-.5)*mm,mm,mm)
 else:c.circle(x*mm,y*mm,.5*mm)
 line(c,x-.85,y,x+.85,y);line(c,x,y-.85,x,y+.85)
 txt(c,x-21 if n<=22 else x+2.5,y-.7,f"{n:02d} {p['name']}",6.8)
txt(c,78,244,'ANTENNA / 天线端 ↑',9)
txt(c,78,170,'USB-C × 2 / USB 端 ↓',9)
c.setStrokeColor(HexColor('#124a66'));line(c,cx-row/2,166,cx+row/2,166)
for x in [cx-row/2,cx+row/2]:line(c,x,164,x,168)
txt(c,91,159,f'{row:.2f} mm 中心距',9)
line(c,153,py,153,py-span);line(c,151,py,155,py);line(c,151,py-span,155,py-span)
c.saveState();c.translate(158*mm,185*mm);c.rotate(90);txt(c,0,0,f'{span:.2f} mm = 21 × {pitch:.2f} mm',8);c.restoreState()
txt(c,15,146,f'橙色虚线为暂定板边：{topoff:.3f} mm 顶部偏移与 {usboff:.3f} mm USB 端偏移未获独立确认。',9,HexColor('#a86517'))
for y,s in [(134,'□ 两排所有 44 个孔中心重合；Pin1 在天线端左排 3V3。'),(125,'□ 左右丝印顺序与实物一致，USB 向下，天线向上。'),(116,'□ 实物板边与虚线轮廓匹配；两个 USB 插头外壳可自由插拔。'),(107,'□ 实物天线下方落在载板无铜区，BOOT/RST 按钮可操作。'),(93,'排针中心距实测 ______ mm     PCB 总宽实测 ______ mm'),(84,'矩形 PCB 长度 ______ mm     含天线总长 ______ mm'),(75,'天线端矩形板边 → 第一排针 ______ mm'),(66,'最后一脚 → USB 端板边 ______ mm'),(52,'确认人 __________    日期 __________    Revision / 购买链接 __________')]:txt(c,15,y,s,10)
calibration(c);footer(c,1);c.showPage();title(c,'整块载板 1:1 模块安装比对')
txt(c,15,260,'载板 110 × 90 mm；轮廓/安装孔/排针孔为 PCB 实际坐标。彩色模块区域仅是暂定包络。',9)
x0=50;y0=240;c.setLineWidth(.2*mm);c.setStrokeColor(black);outline(c,M['outline'],x0,y0)
colors=['#2b71a0','#608b29','#b08724','#904e8f','#bb562f']
for (name,(a,b,d,e)),color in zip(M['envelopes'].items(),colors):
 c.setStrokeColor(HexColor(color));c.setDash(1*mm,.6*mm);c.rect((x0+a)*mm,(y0-e)*mm,(d-a)*mm,(e-b)*mm);c.setDash();txt(c,x0+a+1,y0-b-3,name,7,HexColor(color))
for comp in M['components']:
 if comp['ref'] not in ['J1','J2','J3','J4','J5']:continue
 x,y,rot=comp['position']
 for p in comp['pins']:
  i=int(p['number'])-1
  if comp['ref']=='J1':dx=(-1 if i<22 else 1)*row/2;dy=(i%22)*pitch
  else:dx=i*2.54 if rot==90 else 0;dy=0 if rot==90 else i*2.54
  c.setStrokeColor(black);c.circle((x0+x+dx)*mm,(y0-y-dy)*mm,.5*mm)
for x,y in [(4,4),(106,4),(4,86),(106,86)]:c.circle((x0+x)*mm,(y0-y)*mm,1.6*mm)
c.setStrokeColor(HexColor('#124a66'));c.roundRect((x0+84.5)*mm,(y0-28.5)*mm,20*mm,1*mm,.5*mm)
for y,s in [(135,'□ GY-302 / BME688 / LD2410C / MQ 的实际针序与接口表完全一致。'),(125,'□ 各模块本体在虚线区域内，彼此不碰撞，感光窗与进气口未遮挡。'),(115,'□ 模块直针向下；弯针先换针；排母至少8.5 mm，检查底面间隙。'),(105,'□ LD2410C 天线面朝向被监测区域；ESP32 天线端朝外。'),(95,'□ USB 两根插头不碰载板、螺钉或端子。'),(85,'□ 外壳留 LIGHT WINDOW 与 BME 通风；MQ 热气流不经过 BME688。')]:txt(c,15,y,s,10)
txt(c,15,67,'传感器实际 PCB 长宽、排针相对板边位置、器件高度没有实物尺寸资料。',10,HexColor('#b22828'))
txt(c,15,59,'这些项目确认后才能发布 PRODUCTION VERIFIED Gerber。当前导出包为暂定制造文件。',10,HexColor('#b22828'))
calibration(c);footer(c,2);c.save()
# Assembly reference diagram: actual positions, enlarged for hand soldering.
a=canvas.Canvas(str(F/'assembly.pdf'),pagesize=(297*mm,210*mm));a.setTitle('Carrier assembly locator and first power-up checks')
txt(a,10,195,'ESP32-S3 CARRIER - 元件位置与安装说明',17,HexColor('#124a66'));txt(a,10,185,'Top view / 元件面 | R1.1-PENDING | 图中模块区域为暂定外形，不替代实物校验',10,HexColor('#b22828'))
scale=1.7;x0=15;y0=174;a.setStrokeColor(black);a.setLineWidth(.2*mm);outline(a,M['outline'],x0,y0,scale)
for name,(x1,y1,x2,y2) in M['envelopes'].items():
 a.setStrokeColor(HexColor('#9eacb7'));a.setDash(1*mm,mm);a.rect((x0+x1*scale)*mm,(y0-y2*scale)*mm,(x2-x1)*scale*mm,(y2-y1)*scale*mm);a.setDash();txt(a,x0+(x1+1)*scale,y0-(y1+2)*scale,name,8,HexColor('#1b617e'))
for comp in M['components']:
 x,y,rot=comp['position'];px=x0+x*scale;py=y0-y*scale
 if comp['ref']=='J1':
  for dx in [-row/2,row/2]:
   for i in range(22):a.circle((px+dx*scale)*mm,(py-i*pitch*scale)*mm,.6*mm)
  txt(a,px-12,py-42,'J1: 2 × 1x22',9);continue
 a.setStrokeColor(HexColor('#26758c'));a.circle(px*mm,py*mm,.7*mm)
 txt(a,px+1,py+.8,comp['ref'],7.2)
for y,s in [(170,'装配顺序：'),(159,'1. U1 TSSOP-14 与 Q1/Q2/Q3。'),(149,'2. 1206 电阻、电容、LED。'),(139,'3. C3 电解：确认正负。'),(129,'4. 排母、端子、排针。'),(119,'5. JP3 仅一枚跳帽，默认 EXT。'),(109,'6. R2 / R3 默认不安装。'),(94,'方向：'),(84,'ESP：天线上方 / USB 下方。'),(74,'LD：天线正面朝房间 (+Z)。'),(64,'BME：避开 MQ 热气流。'),(54,'GY：感光区域面向光窗。'),(39,'上电前：检查 5V/3V3 对地电阻；'),(29,'空板 EXT 供电时 3V3 应为 0V。')]:txt(a,211,y,s,9)
txt(a,15,8,'各接口详细针序见 interface_pinout.csv；器件数值见 BOM.csv；完整上电步骤见 README。',9);a.save()
for name in ['ESP32_FOOTPRINT_1_TO_1_CHECK','assembly']:
 doc=fitz.open(F/(name+'.pdf'))
 for i,page in enumerate(doc):page.get_pixmap(matrix=fitz.Matrix(1.8,1.8),alpha=False).save(str(R/'images'/f'{name}_{i+1}.png'))
print('CSV package; dimension notes; 2-page true-scale footprint PDF; assembly locator PDF created')
