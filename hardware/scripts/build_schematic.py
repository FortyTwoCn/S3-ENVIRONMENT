"""Generate a native, editable, self-contained KiCad 9 schematic from the PCB manifest."""
import json,pathlib,uuid,math
R=pathlib.Path(__file__).resolve().parents[1];D=json.loads((R/'fabrication/design_manifest.json').read_text());root=D['schematic_uuid'];lib=[];placed=[];extras=[]
q=lambda x:json.dumps(str(x),ensure_ascii=False)
uid=lambda:str(uuid.uuid4())
effect=lambda size=1:f'(effects (font (size {size} {size})))'
groups={s:[] for s in ['ESP32 Carrier','I2C Sensors','LD2410C Radar','MQ Gas Sensor','Power','Expansion','Test Points']}
for c in D['components']:groups[c['section']].append(c)
positions={
'ESP32 Carrier':[(85,66)],
'I2C Sensors':[(185,43),(250,43),(181,68),(243,68),(181,90),(243,90),(181,109)],
'LD2410C Radar':[(353,47),(428,47),(503,36),(365,85),(437,85),(509,85),(365,104),(437,104),(509,104),(555,40),(555,76)],
'MQ Gas Sensor':[(57+(i%3)*62,151+(i//3)*26) for i in range(12)],
'Power':[(275+(i%5)*62,155+(i//5)*31) for i in range(25)],
'Expansion':[(218+(i%6)*62,293+(i//6)*40) for i in range(18)],
'Test Points':[(42+(i%3)*55,282+(i//3)*22) for i in range(12)]
}
rects=[('ESP32 Carrier',12,18,145,120),('I2C Sensors',152,18,316,120),('LD2410C Radar',322,18,581,120),('MQ Gas Sensor',12,130,230,246),('Power',239,130,581,260),('Expansion',189,273,581,370),('Test Points',12,258,180,370)]
def note(txt,x,y,size=1.3):extras.append(f'(text {q(txt)} (at {x} {y} 0) {effect(size)} (uuid {q(uid())}))')
for title,x1,y1,x2,y2 in rects:
 extras.append(f'(rectangle (start {x1} {y1}) (end {x2} {y2}) (stroke (width 0.254) (type default)) (fill (type none)) (uuid {q(uid())}))');note(title,(x1+x2)/2,y1+4)
for section,comps in groups.items():
 if len(comps)>len(positions[section]):raise ValueError((section,len(comps)))
 for c,(cx,cy) in zip(comps,positions[section]):
  cx=round(cx/1.27)*1.27;cy=round(cy/1.27)*1.27
  ref=c['ref'];symid='Carrier:'+ref;N=len(c['pins']);nl=(N+1)//2;nr=N-nl;rows=max(nl,nr);height=max(5,rows*2.54)
  pins=[];coords=[]
  for i,pin in enumerate(c['pins']):
   side=0 if i<nl else 1;j=i if side==0 else i-nl;count=nl if side==0 else nr;px=(-15.24 if side==0 else 15.24);py=(count-1)*1.27-j*2.54
   ty=pin['type'];ty={'power_out':'power_out','power_in':'power_in'}.get(ty,ty)
   # Both 3V3 contacts are the same onboard regulator, one power driver declaration.
   if ref=='J1' and pin['number']=='2':ty='passive'
   pins.append(f'(pin {ty} line (at {px} {py} {0 if side==0 else 180}) (length 4) (name {q(pin["name"])} {effect(.85)}) (number {q(pin["number"])} {effect(.85)}))');coords.append((cx+px,cy-py,side,pin))
  if ref.startswith('R'):
   graphic='(rectangle (start -3 1.2) (end 3 -1.2) (stroke (width 0.2) (type default)) (fill (type none))) (polyline (pts (xy -11 0) (xy -3 0)) (stroke (width 0.2) (type default)) (fill (type none))) (polyline (pts (xy 3 0) (xy 11 0)) (stroke (width 0.2) (type default)) (fill (type none)))'
  elif ref.startswith('C'):
   graphic='(polyline (pts (xy -11 0) (xy -1 0)) (stroke (width 0.2) (type default)) (fill (type none))) (polyline (pts (xy 1 0) (xy 11 0)) (stroke (width 0.2) (type default)) (fill (type none))) (polyline (pts (xy -1 2) (xy -1 -2)) (stroke (width 0.4) (type default)) (fill (type none))) (polyline (pts (xy 1 2) (xy 1 -2)) (stroke (width 0.4) (type default)) (fill (type none)))'
  else:graphic=f'(rectangle (start -11 {height/2}) (end 11 {-height/2}) (stroke (width 0.254) (type default)) (fill (type background)))'
  short=c['value'];sz=.95 if len(short)<25 else .75
  props=f'(property "Reference" {q(ref)} (at 0 {height/2+2} 0) {effect(1)}) (property "Value" {q(short)} (at 0 {-height/2-2} 0) {effect(sz)}) (property "Footprint" {q(c["footprint"])} (at 0 0 0) (effects (font (size 1 1)) hide))'
  hidden=' (hide)' if ref.startswith(('R','C','TP')) else ''
  lib.append(f'(symbol {q(symid)} (pin_names (offset 0.7){hidden}) (in_bom yes) (on_board yes) {props} (symbol {q(ref+"_0_1")} {graphic}) (symbol {q(ref+"_1_1")} {" ".join(pins)}))')
  instprops=f'(property "Reference" {q(ref)} (at {cx} {cy-height/2-2} 0) {effect(1)}) (property "Value" {q(short)} (at {cx} {cy+height/2+2} 0) {effect(sz)}) (property "Footprint" {q(c["footprint"])} (at {cx} {cy} 0) (effects (font (size 1 1)) hide))'
  placed.append(f'(symbol (lib_id {q(symid)}) (at {cx} {cy} 0) (unit 1) (in_bom yes) (on_board yes) (dnp {"yes" if c["dnp"] else "no"}) (uuid {q(c["uuid"])}) {instprops} '+''.join(f'(pin {q(p["number"])} (uuid {q(uid())}))' for p in c['pins'])+f'(instances (project "esp32_sensor_carrier" (path {q("/"+root)} (reference {q(ref)}) (unit 1)))))')
  for x,y,side,pin in coords:
   nn=pin['net']
   if not nn:extras.append(f'(no_connect (at {x} {y}) (uuid {q(uid())}))');continue
   xx=x+(-3.81 if side==0 else 3.81)
   extras.append(f'(wire (pts (xy {x} {y}) (xy {xx} {y})) (stroke (width 0) (type default)) (uuid {q(uid())}))')
   # Global labels join the named nets without long cross-page wires.
   angle=0 if side==0 else 180
   extras.append(f'(global_label {q(nn)} (shape bidirectional) (at {xx} {y} {angle}) (fields_autoplaced) (effects (font (size .9 .9)) (justify {"right" if side==0 else "left"})) (uuid {q(uid())}))')
# Explicit power declarations: switched rails powered through passive selector/MOSFET.
lib.append('(symbol "Carrier:POWER_FLAG" (pin_names (offset 0) (hide)) (in_bom no) (on_board no) (property "Reference" "#FLG" (at 0 0 0) (effects (font (size 1 1)) hide)) (property "Value" "PWR_FLAG" (at 0 2.54 0) (effects (font (size 1 1)))) (symbol "POWER_FLAG_0_1" (polyline (pts (xy 0 0) (xy 0 1.27) (xy -1.27 1.27) (xy 0 2.54) (xy 1.27 1.27) (xy 0 1.27)) (stroke (width .15) (type default)) (fill (type none)))) (symbol "POWER_FLAG_1_1" (pin power_out line (at 0 0 90) (length 0) (name "pwr" (effects (font (size 1 1)))) (number "1" (effects (font (size 1 1)))))))')
for i,nn in enumerate(['GND','SENSOR_5V','5V_SERVO']):
 x=round((263+i*45)/1.27)*1.27;y=round(248/1.27)*1.27;ref='#FLG0'+str(i+1)
 placed.append(f'(symbol (lib_id "Carrier:POWER_FLAG") (at {x} {y} 0) (unit 1) (in_bom no) (on_board no) (dnp no) (uuid {q(uid())}) (property "Reference" {q(ref)} (at {x} {y} 0) (effects (font (size 1 1)) hide)) (property "Value" "PWR_FLAG" (at {x} {y-3} 0) {effect(.9)}) (pin "1" (uuid {q(uid())})) (instances (project "esp32_sensor_carrier" (path {q("/"+root)} (reference {q(ref)}) (unit 1)))))')
 extras.append(f'(global_label {q(nn)} (shape bidirectional) (at {x} {y} 0) (effects (font (size .9 .9)) (justify right)) (uuid {q(uid())}))')
note('USB / EXT selection is manual. Independent servo supply. 3V3 comes from inserted ESP32.',410,377,1.3)
note('MECHANICAL VERIFICATION REQUIRED - all module pin orders must match the real modules.',295,385,1.5)
note('MQ AO: 6.8k / 7.5k + 100k ADC load, 100nF. DO: MOSFET inverter. U1 provides power-off isolation.',295,392,1.2)
sch=f'(kicad_sch (version 20250114) (generator "eeschema") (uuid {q(root)}) (paper "A2") (title_block (title "ESP32-S3 Multi-Sensor Carrier") (rev "R1.1-PENDING") (comment 1 "Pluggable 44-pin board; photo spacing 25.40mm") (comment 2 "MECHANICAL_DIMENSION_PENDING")) (lib_symbols '+ '\n'.join(lib)+')\n'+'\n'.join(placed+extras)+f' (sheet_instances (path "/" (page "1"))))\n'
sch=sch.replace('(hide)', '(hide yes)').replace(' hide)', ' (hide yes))').replace('(fields_autoplaced)', '(fields_autoplaced yes)')
(R/'esp32_sensor_carrier.kicad_sch').write_text(sch,encoding='utf-8')
# Local library for maintenance and ERC library consistency.
(R/'carrier.kicad_sym').write_text(('(kicad_symbol_lib (version 20241209) (generator "kicad_symbol_editor")\n'+'\n'.join(s.replace('"Carrier:','"',1) for s in lib)+')\n').replace('(hide)','(hide yes)').replace(' hide)',' (hide yes))'),encoding='utf-8')
(R/'sym-lib-table').write_text('(sym_lib_table (lib (name "Carrier") (type "KiCad") (uri "${KIPRJMOD}/carrier.kicad_sym") (options "") (descr "Carrier connectors and protection circuits")))\n')
print('Generated schematic:',len(D['components']),'components in seven sections')
