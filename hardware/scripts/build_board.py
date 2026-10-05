"""Run with KiCad 9's bundled Python. Regenerate placement + un-routed PCB.
Routing is a separate step; changing mechanics invalidates old routes/Gerbers.
"""
import argparse, pathlib, json, uuid, os, csv
import pcbnew as p
ROOT=pathlib.Path(__file__).resolve().parents[1]
KICAD=pathlib.Path(p.__file__).resolve().parents[3]
LIB=KICAD/'share/kicad/footprints'
NAME='esp32_sensor_carrier'
for d in ('footprints/custom.pretty','fabrication','images','gerber','checks','sources'):(ROOT/d).mkdir(parents=True,exist_ok=True)
PARAMS=ROOT/'mechanical_parameters.json'
if not PARAMS.exists():
 PARAMS.write_text(json.dumps({'HEADER_ROW_SPACING':25.40,'PIN_PITCH':2.54,'PINS_PER_ROW':22,'ESP_PCB_WIDTH':27.94,'ESP_BODY_LENGTH':57.15,'ESP_TOTAL_LENGTH':63.389002,'FIRST_PIN_FROM_BODY_TOP':1.905,'LAST_PIN_FROM_USB_EDGE':1.905,'EDGE_OFFSETS_VERIFIED':False,'MECHANICAL_VERIFIED':False,'SENSOR_ENVELOPES_VERIFIED':False},indent=2)+'\n')
M=json.loads(PARAMS.read_text()); B=p.BOARD();B.SetCopperLayerCount(2)
B.GetDesignSettings().SetBoardThickness(p.FromMM(1.6))
V=lambda x,y:p.VECTOR2I(p.FromMM(x),p.FromMM(y))
def layers(*ids):
 result=p.LSET()
 for i in ids:result.AddLayer(i)
 return result
NETS={};COMPS=[];FPS={};sid=str(uuid.uuid4())
def net(name):
 if not name:return None
 if name not in NETS:
  obj=p.NETINFO_ITEM(B,name,len(NETS)+1);B.Add(obj);NETS[name]=obj
 return NETS[name]
def shape(owner,a,b,layer=p.F_SilkS,width=.15):
 s=p.PCB_SHAPE(owner)
 s.SetShape(p.SHAPE_T_SEGMENT);s.SetStart(V(*a));s.SetEnd(V(*b));s.SetLayer(layer);s.SetWidth(p.FromMM(width));owner.Add(s);return s
def rect(owner,x1,y1,x2,y2,layer=p.F_Fab,w=.1):
 for a,b in [((x1,y1),(x2,y1)),((x2,y1),(x2,y2)),((x2,y2),(x1,y2)),((x1,y2),(x1,y1))]:shape(owner,a,b,layer,w)
def text(owner,txt,x,y,layer=p.F_SilkS,size=.8,angle=0):
 t=p.PCB_TEXT(owner)
 t.SetText(txt);t.SetPosition(V(x,y));t.SetTextSize(V(size,size));t.SetTextThickness(p.FromMM(.12));t.SetLayer(layer)
 t.SetTextAngle(p.EDA_ANGLE(angle,p.DEGREES_T));
 if layer==p.B_SilkS:t.SetMirrored(True)
 owner.Add(t);return t
def pad(fp,num,x,y,drill=1.0,size=1.8):
 q=p.PAD(fp);q.SetNumber(str(num));q.SetPosition(V(x,y));q.SetSize(V(size,size));q.SetDrillSize(V(drill,drill));q.SetAttribute(p.PAD_ATTRIB_PTH)
 q.SetShape(p.PAD_SHAPE_RECT if num==1 else p.PAD_SHAPE_CIRCLE);q.SetLayerSet(layers(p.F_Cu,p.B_Cu,p.F_Mask,p.B_Mask));fp.Add(q);return q
def blank(name):
 fp=p.FOOTPRINT(B);fp.SetFPID(p.LIB_ID('custom',name));fp.SetAttributes(p.FP_THROUGH_HOLE);return fp
def standard(lib,name):
 fp=p.FootprintLoad(str(LIB/(lib+'.pretty')),name)
 if fp is None:raise RuntimeError(str(LIB/(lib+'.pretty'))+'/'+name)
 fp.SetFPID(p.LIB_ID('custom',name));return fp
def header(n,name):
 fp=blank(name)
 for i in range(n):pad(fp,i+1,0,i*2.54)
 rect(fp,-1.4,-1.4,1.4,(n-1)*2.54+1.4,p.F_SilkS)
 rect(fp,-1.6,-1.6,1.6,(n-1)*2.54+1.6,p.F_CrtYd,.05)
 rect(fp,-1.27,-1.27,1.27,(n-1)*2.54+1.27)
 return fp
def add(ref,value,fp,names,nets,x,y,rot=0,section='Power',types=None,dnp=False,desc=''):
 if x>=60:x+=10
 elif ref=='J1':x+=5
 fu=str(uuid.uuid5(uuid.NAMESPACE_URL,'sensor-carrier:'+ref));fp.SetReference(ref);fp.SetValue(value);fp.SetPosition(V(x,y));fp.SetOrientationDegrees(rot)
 fp.SetPath(p.KIID_PATH('/'+sid+'/'+fu));fp.Reference().SetVisible(False);fp.Value().SetVisible(False)
 fp.SetDNP(dnp);fp.SetExcludedFromBOM(False)
 for q in fp.Pads():
  idx=int(q.GetNumber())-1 if q.GetNumber() else -1
  if 0<=idx<len(nets) and nets[idx]:q.SetNet(net(nets[idx]))
  if ref in ('J6','J7') and 0<=idx<len(nets) and nets[idx]=='GND':q.SetLocalZoneConnection(p.ZONE_CONNECTION_FULL)
 B.Add(fp);FPS[ref]=fp
 # Self-contained footprint library, strip PCB net assignments and placement.
 cp=p.FOOTPRINT(fp);cp.SetPosition(V(0,0));cp.SetOrientationDegrees(0);cp.SetReference('REF**');cp.SetValue(fp.GetFPID().GetLibItemName())
 for q in cp.Pads():q.SetNetCode(0)
 p.PCB_IO_MGR.PluginFind(p.PCB_IO_MGR.KICAD_SEXP).FootprintSave(str(ROOT/'footprints/custom.pretty'),cp)
 COMPS.append({'ref':ref,'value':value,'footprint':'custom:'+str(fp.GetFPID().GetLibItemName()),'pins':[{'number':str(i+1),'name':n,'net':nn,'type':(types or ['passive']*len(names))[i]} for i,(n,nn) in enumerate(zip(names,nets))], 'section':section,'uuid':fu,'dnp':dnp,'description':desc,'position':[x,y,rot]})
 return fp
left=['3V3','3V3','RST','4','5','6','7','15','16','17','18','8','3','46','9','10','11','12','13','14','5V','GND']
right=['GND','TX43','RX44','1','2','42','41','40','39','38','37','36','35','0','45','48','47','21','20','19','GND','GND']
used={'3V3':'+3V3','5V':'ESP32_5V','GND':'GND','4':'MQ_ADC','5':'MQ_DO_3V3','6':'GPIO6','7':'GPIO7','8':'I2C_SDA','9':'I2C_SCL','10':'GPIO10','11':'GPIO11','12':'SERVO_PWM','16':'RADAR_OUT_ESP','17':'RADAR_TX_ESP','18':'RADAR_RX_ESP'}
ef=blank('ESP32-S3_N16R8_44PIN_CARRIER');S=M['HEADER_ROW_SPACING'];H=M['PIN_PITCH']*21
for side,pins in enumerate((left,right)):
 xx=(-1 if side==0 else 1)*S/2
 for i,pinname in enumerate(pins):pad(ef,side*22+i+1,xx,i*M['PIN_PITCH']);text(ef,pinname,xx+(-2.4 if side==0 else 2.4),i*M['PIN_PITCH'],p.F_Fab,.75)
 rect(ef,xx-1.4,-1.4,xx+1.4,H+1.4,p.F_SilkS)
 # Courtyards cover sockets; module envelope separately checked.
 rect(ef,xx-1.6,-1.6,xx+1.6,H+1.6,p.F_CrtYd,.05)
top=-M['FIRST_PIN_FROM_BODY_TOP'];bottom=H+M['LAST_PIN_FROM_USB_EDGE']; ant=bottom-M['ESP_TOTAL_LENGTH']
rect(ef,-M['ESP_PCB_WIDTH']/2,top,M['ESP_PCB_WIDTH']/2,bottom,p.F_Fab)
rect(ef,-9,ant,9,top,p.Dwgs_User)
text(ef,'ANTENNA',0,-.4,p.F_Fab,1);text(ef,'USB-C x2',0,bottom-2,p.F_Fab,1)
etypes=['power_out' if n in ('3V3','5V') else 'passive' if n=='GND' else 'input' if n in ('4','5','16','17') else 'output' if n in ('18','12') else 'bidirectional' for n in left+right]
add('J1','ESP32-S3 N16R8 / USER MODULE',ef,left+right,[used.get(n,'') for n in left+right],50,7.62,section='ESP32 Carrier',types=etypes,desc='Two 1x22 female sockets, top antenna / bottom USB; photo-based 25.40 mm spacing')
def mod(ref,title,names,nets,x,y,angle,envelope,section,types):
 fp=header(len(names),title.replace('/','_').replace(' ','_')+'_SOCKET')
 add(ref,title,fp,names,nets,x,y,angle,section,types,desc='Pluggable user provided module; envelope requires fit check')
 if x>=60:envelope=(envelope[0]+10,envelope[1],envelope[2]+10,envelope[3])
 rect(B,*envelope,p.Dwgs_User);rect(B,*envelope,p.F_Fab)
 return fp
mod('J2','GY-302 BH1750',['ADDR','SDA','SCL','GND','VCC'],['BH_ADDR','I2C_SDA','I2C_SCL','GND','+3V3'],9,25,90,(7,7,29,24),'I2C Sensors',['input','bidirectional','input','passive','power_in'])
mod('J3','BME688',['VCC','GND','SCL','SDA','SDO','CS'],['+3V3','GND','I2C_SCL','I2C_SDA','BME_ADDR','BME_CS'],74,25,90,(72,7,94,24),'I2C Sensors',['power_in','passive','input','bidirectional','input','input'])
mod('J4','LD2410C',['TX','RX','OUT','GND','VCC'],['RADAR_TX','RADAR_RX','RADAR_OUT','GND','SENSOR_5V'],24,52,0,(2,49,24,65),'LD2410C Radar',['output','input','output','passive','power_in'])
mod('J5','MQ GAS',['VCC','GND','DO','AO'],['SENSOR_5V','GND','MQ_DO_RAW','MQ_AO_RAW'],75,70,90,(70,37,96,69),'MQ Gas Sensor',['power_in','passive','open_collector','output'])
def res(ref,val,n1,n2,x,y,section='Power',rot=0,dnp=False,desc=''):
 return add(ref,val,standard('Resistor_SMD','R_1206_3216Metric'),['1','2'],[n1,n2],x,y,rot,section,dnp=dnp,desc=desc or '1206, 1%, 0.25 W')
def cap(ref,val,n1,x,y,section='Power',rot=0):
 return add(ref,val,standard('Capacitor_SMD','C_1206_3216Metric'),['+','GND'],[n1,'GND'],x,y,rot,section,desc='1206 X7R; 10uF >=16V; 100nF >=25V')
# Address jumpers with intentional factory copper bridge 1-2.
for ref,nn,x,y in [('JP1','BH_ADDR',10,29.5),('JP2','BME_ADDR',78,32)]:
 add(ref,'GND DEFAULT / 3V3 OPTION',standard('Jumper','SolderJumper-3_P1.3mm_Bridged12_RoundedPad1.0x1.5mm'),['GND','ADDR','3V3'],['GND',nn,'+3V3'],x,y,section='I2C Sensors',desc='Cut bridge 1-2 before soldering 2-3')
res('R1','10k','+3V3','BME_CS',92,32,'I2C Sensors')
res('R2','4.7k DNP','+3V3','I2C_SDA',26,21,'I2C Sensors',dnp=True)
res('R3','4.7k DNP','+3V3','I2C_SCL',26,25,'I2C Sensors',dnp=True)
# MQ protection and isolation.
res('R4','6.8k','MQ_AO_RAW','MQ_ADC_FILTER',77,36,'MQ Gas Sensor')
res('R5','7.5k','MQ_ADC_FILTER','GND',77,40,'MQ Gas Sensor')
cap('C1','100nF','MQ_ADC_FILTER',84,40,'MQ Gas Sensor')
res('R6','33k','MQ_DO_RAW','MQ_BASE',92,40,'MQ Gas Sensor')
res('R7','100k','MQ_BASE','GND',94,43,'MQ Gas Sensor')
res('R8','10k','+3V3','MQ_DO_3V3',87,32,'MQ Gas Sensor')
add('Q1','AO3400A',standard('Package_TO_SOT_SMD','SOT-23'),['G','S','D'],['MQ_BASE','GND','MQ_DO_3V3'],86,36,section='MQ Gas Sensor',types=['input','passive','open_collector'],desc='N-MOS inverter; 1=G 2=S 3=D; insulated gate prevents 5V signal back-power when 3V3 is off')
res('R21','10k','SENSOR_5V','MQ_DO_RAW',92,46,'MQ Gas Sensor')
MUX=['SENSOR_ENABLE','RADAR_TX_LIMIT','RADAR_TX_ESP','SENSOR_ENABLE','RADAR_RX_ESP','RADAR_RX_SWITCH','GND','RADAR_OUT_ESP','RADAR_OUT_LIMIT','SENSOR_ENABLE','MQ_ADC','MQ_ADC_FILTER','SENSOR_ENABLE','+3V3']
add('U1','TMUX1511PWR',standard('Package_SO','TSSOP-14_4.4x5mm_P0.65mm'),['SEL1','S1','D1','SEL2','S2','D2','GND','D3','S3','SEL3','D4','S4','SEL4','VDD'],MUX,29,43,section='LD2410C Radar',types=['input','passive','passive','input','passive','passive','power_in','passive','passive','input','passive','passive','input','power_in'],desc='Four powered-off protected SPST switches; SEL tied to SENSOR_5V, fail-safe 5.5V controls')
cap('C2','100nF','+3V3',29,37,'LD2410C Radar')
res('R20','10k','SENSOR_5V','SENSOR_ENABLE',28,34,'Power')
for ref,a,b,x,y in [('R9','RADAR_TX','RADAR_TX_LIMIT',28.5,51),('R10','RADAR_RX_SWITCH','RADAR_RX',28.5,55),('R11','RADAR_OUT','RADAR_OUT_LIMIT',28.5,59)]:res(ref,'1k',a,b,x,y,'LD2410C Radar')
for ref,nn,x,y in [('R12','RADAR_TX_ESP',18,38),('R13','RADAR_OUT_ESP',18,42),('R14','RADAR_RX',18,46),('R15','MQ_ADC',66,55)]:res(ref,'100k',nn,'GND',x,y,'LD2410C Radar' if ref!='R15' else 'MQ Gas Sensor',rot=0)
# External power source and reverse protection: Q2 drain=input, source=protected.
add('J6','5V ONLY EXT SENSOR',standard('TerminalBlock_Phoenix','TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal'),['EXT5V_RAW','GND'],['EXT_5V_RAW','GND'],80,82,section='Power')
add('Q2','AO3401A',standard('Package_TO_SOT_SMD','SOT-23'),['G','S','D'],['GND','EXT_5V','EXT_5V_RAW'],93,80,section='Power',types=['input','passive','passive'],desc='P-MOS reverse polarity protection, source on protected output; body diode raw -> protected')
add('JP3','USB / SENSOR / EXT',header(3,'POWER_SELECT_1x03'),['USB','SENSOR','EXT'],['ESP32_5V','SENSOR_5V','EXT_5V'],70,78,90,desc='One rated shunt only: 1-2 USB, 2-3 EXT; never bridge all three')
add('C3','100uF 16V',standard('Capacitor_THT','CP_Radial_D6.3mm_P2.50mm'),['+','-'],['SENSOR_5V','GND'],72,83,section='Power',desc='Low ESR polarized electrolytic, 6.3mm diameter, 2.5mm pitch')
cap('C4','10uF','SENSOR_5V',64,82)
cap('C5','100nF','SENSOR_5V',64,86)
cap('C6','10uF','SENSOR_5V',32,64,'LD2410C Radar',90)
cap('C7','100nF','SENSOR_5V',27,64,'LD2410C Radar',90)
cap('C8','10uF','SENSOR_5V',90,72.5,'MQ Gas Sensor')
cap('C9','100nF','SENSOR_5V',96,72.5,'MQ Gas Sensor')
cap('C10','10uF','+3V3',22,29)
cap('C11','100nF','+3V3',28,29)
for ref,rref,nn,xx,yy,rx,ry in [('D1','R16','+3V3',32,87,32,84),('D2','R17','SENSOR_5V',13,46,7,46)]:
 res(rref,'2.2k',nn,ref+'_A',rx,ry)
 add(ref,'GREEN' if ref=='D1' else 'AMBER',standard('LED_SMD','LED_1206_3216Metric'),['K','A'],['GND',ref+'_A'],xx,yy,section='Power')
# Expansion, safe GPIOs. Separate servo rail, no ESP32 5V linkage.
add('J7','EXT I2C',header(4,'EXT_I2C_1x04'),['3V3','GND','SDA','SCL'],['+3V3','GND','I2C_SDA','I2C_SCL'],32,12,section='Expansion')
for ref,gpio,yy in [('J8',6,8),('J9',7,18),('J10',10,32),('J11',11,42)]:
 add(ref,'GPIO'+str(gpio),header(3,'GPIO_1x03'),['GND','3V3','IO'+str(gpio)],['GND','+3V3','GPIO'+str(gpio)],68,yy,section='Expansion')
add('J12','SERVO',header(3,'SERVO_1x03'),['GND','5V_SERVO','SIGNAL'],['GND','5V_SERVO','SERVO_SIGNAL'],8,73,90,'Expansion')
add('J13','5V ONLY SERVO',standard('TerminalBlock_Phoenix','TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal'),['SERVO5V_RAW','GND'],['SERVO_5V_RAW','GND'],18,80,section='Expansion')
add('Q3','AO3401A',standard('Package_TO_SOT_SMD','SOT-23'),['G','S','D'],['GND','5V_SERVO','SERVO_5V_RAW'],32,80,section='Expansion',types=['input','passive','passive'],desc='Independent servo rail reverse polarity protection')
res('R18','1k','SERVO_PWM','SERVO_SIGNAL',32,69,'Expansion',90)
res('R19','100k','SERVO_SIGNAL','GND',25,70,'Expansion')
cap('C12','10uF','5V_SERVO',12,87,'Expansion')
cap('C13','100nF','5V_SERVO',19,88,'Expansion')
TP=[('TP1','TP_5V','SENSOR_5V',90,88),('TP2','TP_3V3','+3V3',32,25),('TP3','TP_GND','GND',32,29),('TP4','TP_SDA','I2C_SDA',32,22.5),('TP5','TP_SCL','I2C_SCL',32,8),('TP6','TP_LD_TX','RADAR_TX',32,51),('TP7','TP_LD_RX','RADAR_RX',32,55),('TP8','TP_LD_OUT','RADAR_OUT',32,59),('TP9','TP_MQ_AO_RAW','MQ_AO_RAW',97,32),('TP10','TP_MQ_ADC','MQ_ADC',97,40),('TP11','TP_MQ_DO','MQ_DO_3V3',97,36)]
for ref,title,nn,x,y in TP:
 tf=blank('TESTPOINT_THT_1.5mm');pad(tf,1,0,0,.7,1.5)
 rect(tf,-1,-1,1,1,p.F_CrtYd,.05)
 add(ref,title,tf,[title],[nn],x,y,section='Test Points',desc='1.5mm exposed pad with 0.7mm plated hole')
 text(B,ref,x+11.4 if ref=='TP10' else x+10 if x>=60 else x+3,y-1.7 if x>=60 else y,size=.8)
# Fabrication outline with USB plug access cut-out.
outline=[(0,0),(110,0),(110,90),(70.5,90),(70.5,64.5),(39.5,64.5),(39.5,90),(0,90),(0,0)]
for a,b in zip(outline,outline[1:]):shape(B,a,b,p.Edge_Cuts,.05)
# 1.0 mm thermal routing slot with rounded ends; x75..94 center line.
shape(B,(85,27.5),(104,27.5),p.Edge_Cuts,.05);shape(B,(104,28.5),(85,28.5),p.Edge_Cuts,.05)
for a,m,b in [((104,27.5),(104.5,28),(104,28.5)),((85,28.5),(84.5,28),(85,27.5))]:
 s=p.PCB_SHAPE(B);s.SetShape(p.SHAPE_T_ARC);s.SetArcGeometry(V(*a),V(*m),V(*b));s.SetLayer(p.Edge_Cuts);s.SetWidth(p.FromMM(.05));B.Add(s)
for i,(x,y) in enumerate([(4,4),(106,4),(4,86),(106,86)]):
 fp=standard('MountingHole','MountingHole_3.2mm_M3');fp.SetReference('H'+str(i+1));fp.SetPosition(V(x,y));fp.Reference().SetVisible(False);fp.Value().SetVisible(False);fp.SetAttributes(p.FP_BOARD_ONLY|p.FP_EXCLUDE_FROM_POS_FILES|p.FP_EXCLUDE_FROM_BOM);B.Add(fp)
 p.PCB_IO_MGR.PluginFind(p.PCB_IO_MGR.KICAD_SEXP).FootprintSave(str(ROOT/'footprints/custom.pretty'),fp)
def zone(rectangle,rule=False,tracks=False,name=''):
 z=p.ZONE(B);z.SetLayerSet(layers(p.F_Cu,p.B_Cu));z.SetZoneName(name)
 if rule:
  z.SetIsRuleArea(True);z.SetDoNotAllowCopperPour(True);z.SetDoNotAllowTracks(tracks);z.SetDoNotAllowVias(tracks);z.SetDoNotAllowPads(tracks);z.SetDoNotAllowFootprints(False)
 else:
  z.SetNet(net('GND'));z.SetLocalClearance(p.FromMM(.25));z.SetMinThickness(p.FromMM(.25));z.SetThermalReliefGap(p.FromMM(.25));z.SetThermalReliefSpokeWidth(p.FromMM(.4));z.SetPadConnection(p.ZONE_CONNECTION_THERMAL)
 z.Outline().NewOutline()
 x1,y1,x2,y2=rectangle
 for x,y in [(x1,y1),(x2,y1),(x2,y2),(x1,y2)]:z.Outline().Append(p.FromMM(x),p.FromMM(y))
 B.Add(z);return z
zone((.3,.3,109.7,89.7),name='GND BOTH LAYERS')
zone((44,0,66,13.4),True,True,'ESP32 ANTENNA KEEPOUT')
zone((0,47.5,19.5,67),True,True,'RADAR ANTENNA KEEPOUT')
zone((81,6,105,29),True,False,'BME THERMAL COPPER REDUCTION')
# Ground vias in safe board areas; additional connectivity verified after refill.
for x,y in [(2,20),(2,30),(2,37),(20,3),(30,4),(78,3),(108,18),(108,27),(108,44),(108,60),(108,71),(77,88),(37,84),(2,70),(36,34),(36,48),(73,29),(73,51)]:
 v=p.PCB_VIA(B);v.SetPosition(V(x,y));v.SetWidth(p.FromMM(.8));v.SetDrill(p.FromMM(.4));v.SetViaType(p.VIATYPE_THROUGH);v.SetLayerPair(p.F_Cu,p.B_Cu);v.SetNet(net('GND'));B.Add(v)
# Informative silk: module area is free for large labels, outline on fab/user layers.
for txt,x,y,sz in [('ESP32-S3',55,29,1.5),('N16R8 / 44 PIN',55,32,1),('ANTENNA ^',55,15.5,1),('USB-C x2 v',55,61,1),('GY-302 / BH1750',18,10,1),('LIGHT WINDOW ^',18,13,.8),('BME688',93,10,1.2),('AIR FLOW ^',93,13,.8),('MQ GAS / HOT',93,49,1.1),('LD2410C',10,53,.9),('FACE UP +Z',10,56,.8),('EXT 5V ONLY',92,73, .8),('USB SENSOR EXT',82.5,74.8, .8),('3V3',32,89,.8),('5V',7,43.5,.8),('SERVO: EXT 5V',22,72,.8),('MECH CHECK REQUIRED',55,57.5,.8)]:text(B,txt,x,y,size=sz)
for fp,names,xx,yy in [(FPS['J2'],['ADDR','SDA','SCL','GND','VCC'],9,25),(FPS['J3'],['VCC','GND','SCL','SDA','SDO','CS'],74,25),(FPS['J5'],['VCC','GND','DO','AO'],75,70)]:
 for i,n in enumerate(names):text(B,n,xx+(10 if xx>=60 else 0)+i*2.54,yy-3.6,size=.8,angle=90)
for i,n in enumerate(['TX','RX','OUT','GND','VCC']):text(B,n,20,52+i*2.54,size=.8)
for side,rr in enumerate((left,right)):
 for i,n in enumerate(rr):
  if n in ('3V3','GND','5V','4','5','8','9','16','17','18','6','7','10','11','12'):
   text(B,n,55+(-1 if side==0 else 1)*(S/2-3.3),7.62+i*2.54,size=.8)
text(B,'PIN 1',42.3,5,size=.8)
text(B,'ESP32 SENSOR CARRIER  R1.1',55,25,p.B_SilkS,1.0)
text(B,'SDA GPIO8    SCL GPIO9\nRADAR RX17 / TX18 / OUT16\nMQ ADC 4 / DO 5\nBH1750 0x23 / 0x5C\nBME688 0x76 / 0x77\nJP1/2: CUT GND BRIDGE\nBEFORE SELECTING 3V3\nJP3: ONE SHUNT ONLY\nSERVO: INDEPENDENT 5V\nMECHANICAL_DIMENSION_PENDING',55,46,p.B_SilkS,.9)
p.SaveBoard(str(ROOT/(NAME+'.kicad_pcb')),B)
manifest={'schematic_uuid':sid,'name':NAME,'mechanics':M,'components':COMPS,'outline':outline,'envelopes':{'ESP32': [55-M['ESP_PCB_WIDTH']/2,7.62+ant,55+M['ESP_PCB_WIDTH']/2,7.62+bottom],'GY302':[7,7,29,26.4],'BME688':[82,7,104,26.4],'LD2410C':[2,49,25.6,65],'MQ':[80,37,106,71.4]},'keepouts':{'ESP32':[44,0,66,13.4],'RADAR':[0,47.5,19.5,67]}}
(ROOT/'fabrication/design_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
(ROOT/'fp-lib-table').write_text('(fp_lib_table (lib (name "custom") (type "KiCad") (uri "${KIPRJMOD}/footprints/custom.pretty") (options "") (descr "Self-contained sensor carrier library")))\n')
project={'meta':{'filename':NAME+'.kicad_pro','version':1},'board':{'design_settings':{'rules':{'min_clearance':.2,'min_track_width':.25,'min_via_diameter':.6,'min_through_hole_diameter':.3,'min_copper_edge_clearance':.3,'min_hole_clearance':.25,'min_silk_clearance':.15,'min_silk_text_height':.6,'min_silk_text_thickness':.1},'defaults':{'track_width':.3,'via_diameter':.8,'via_drill':.4},'rule_severities':{'silk_over_copper':'warning','silk_overlap':'warning','courtyards_overlap':'error'}}},'net_settings':{'meta':{'version':4},'classes':[{'name':'Default','clearance':.2,'track_width':.3,'via_diameter':.8,'via_drill':.4,'pcb_color':'rgba(0,0,0,0)','schematic_color':'rgba(0,0,0,0)','wire_width':6,'bus_width':12,'line_style':0},{'name':'Power','clearance':.25,'track_width':1.0,'via_diameter':1.2,'via_drill':.6,'wire_width':6,'bus_width':12,'line_style':0}], 'netclass_patterns':[{'netclass':'Power','pattern':n} for n in ['SENSOR_5V','ESP32_5V','EXT_5V','EXT_5V_RAW','5V_SERVO','SERVO_5V_RAW']]},'schematic':{'meta':{'version':1}},'text_variables':{'DESIGN_STATUS':'MECHANICAL_DIMENSION_PENDING'}}
project['board']['design_settings']['rule_severities'].update({k:'warning' for k in ('footprint_filters_mismatch','footprint_type_mismatch','missing_courtyard','npth_inside_courtyard','pth_inside_courtyard')})
(ROOT/(NAME+'.kicad_pro')).write_text(json.dumps(project,indent=2)+'\n')
# Export DSN, strips plane fill but preserves keepouts and pads.
p.ExportSpecctraDSN(B,str(ROOT/(NAME+'.dsn')))
print('Generated PCB:',len(COMPS),'components,',len(NETS),'nets,',len(list(B.GetFootprints())),'footprints')
