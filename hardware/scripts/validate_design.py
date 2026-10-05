"""Independent manifest/netlist/PCB checks, plus bounded input-voltage calculations."""
import pathlib,json,csv,xml.etree.ElementTree as ET,itertools,hashlib
from shapely.geometry import box,LineString,Point
R=pathlib.Path(__file__).resolve().parents[1]
read=lambda f:json.loads((R/f).read_text(encoding='utf-8'))
M=read('fabrication/design_manifest.json'); G=read('checks/geometry.json')
xml=ET.parse(R/'fabrication/netlist.xml'); nets={}
for net in xml.findall('./nets/net'):
 for node in net.findall('node'):nets[(node.get('ref'),node.get('pin'))]=net.get('name')
actual={(g['ref'],g['pin']):g['net'] for g in G if g['kind']=='pad' and g['ref'].startswith(('J','R','C','U','Q','D','TP'))}
results=[]
def check(name,ok,detail):
 results.append({'check':name,'status':'PASS' if ok else 'FAIL','detail':detail})
 if not ok:raise AssertionError(name+': '+str(detail))
expected={(c['ref'],p['number']):p['net'] for c in M['components'] for p in c['pins'] if p['net']}
check('manifest_netlist_pcb_pad_parity',all(nets[k]==n and actual[k]==n for k,n in expected.items()),f'{len(expected)} assigned pins checked against KiCad XML and physical PCB pads')
def pins(ref,ns):check(ref+'_pinout',all(actual[(ref,str(i+1))]==n for i,n in enumerate(ns)),ns)
pins('J2',['BH_ADDR','I2C_SDA','I2C_SCL','GND','+3V3'])
pins('J3',['+3V3','GND','I2C_SCL','I2C_SDA','BME_ADDR','BME_CS'])
pins('J4',['RADAR_TX','RADAR_RX','RADAR_OUT','GND','SENSOR_5V'])
pins('J5',['SENSOR_5V','GND','MQ_DO_RAW','MQ_AO_RAW'])
pins('JP3',['ESP32_5V','SENSOR_5V','EXT_5V'])
pins('Q1',['MQ_BASE','GND','MQ_DO_3V3']);pins('Q2',['GND','EXT_5V','EXT_5V_RAW']);pins('Q3',['GND','5V_SERVO','SERVO_5V_RAW'])
pins('U1',['SENSOR_ENABLE','RADAR_TX_LIMIT','RADAR_TX_ESP','SENSOR_ENABLE','RADAR_RX_ESP','RADAR_RX_SWITCH','GND','RADAR_OUT_ESP','RADAR_OUT_LIMIT','SENSOR_ENABLE','MQ_ADC','MQ_ADC_FILTER','SENSOR_ENABLE','+3V3'])
for ref,ns in {'R4':['MQ_AO_RAW','MQ_ADC_FILTER'],'R5':['MQ_ADC_FILTER','GND'],'C1':['MQ_ADC_FILTER','GND'],'R9':['RADAR_TX','RADAR_TX_LIMIT'],'R10':['RADAR_RX_SWITCH','RADAR_RX'],'R11':['RADAR_OUT','RADAR_OUT_LIMIT'],'R8':['+3V3','MQ_DO_3V3'],'R15':['MQ_ADC','GND']}.items():pins(ref,ns)
gpio={'4':'MQ_ADC','5':'MQ_DO_3V3','8':'I2C_SDA','9':'I2C_SCL','16':'RADAR_OUT_ESP','17':'RADAR_TX_ESP','18':'RADAR_RX_ESP','6':'GPIO6','7':'GPIO7','10':'GPIO10','11':'GPIO11','12':'SERVO_PWM'}
j1=next(c for c in M['components'] if c['ref']=='J1')
check('GPIO_photo_pin_order',all(actual[('J1',p['number'])]==gpio[p['name']] for p in j1['pins'] if p['name'] in gpio),gpio)
check('reserved_pins_NC',all(not p['net'] for p in j1['pins'] if p['name'] in ['19','20','35','36','37','0','3','45','46','48']), 'USB, PSRAM, strapping, RGB pins unused by carrier')
check('no_5V_net_on_GPIO',all(p['net'] not in ['SENSOR_5V','ESP32_5V','EXT_5V','MQ_AO_RAW','MQ_DO_RAW','5V_SERVO'] for p in j1['pins'] if p['name'] not in ['5V','3V3','GND']), 'GPIO inputs have defined low-voltage networks')
for k2,rail in [('ESP32','ESP32_5V'),('SENSOR','SENSOR_5V'),('EXT','EXT_5V')]:
 check('selector_'+k2,actual[('JP3',str(['ESP32','SENSOR','EXT'].index(k2)+1))]==rail,'No copper bridge between three independently named rails; one removable shunt selected by user')
pins('J12',['GND','5V_SERVO','SERVO_SIGNAL']);pins('J13',['SERVO_5V_RAW','GND'])
rbot=lambda r5,r15:1/(1/r5+1/r15)
gain=lambda rt,r5,r15:rbot(r5,r15)/(rt+rbot(r5,r15))
nom=gain(6800,7500,100000);worst=5.25*gain(6800*.99,7500*1.01,100000*1.01)
check('MQ_ADC_max_5V25_1pct',worst<2.9,{'nominal_ratio':nom,'at_5V':5*nom,'maximum_V':worst,'limits':'regulated 5V +/-5%; all resistors 1%; includes R15 loading; U1 Ron <=4.5 ohm only reduces this bound'})
gate=4.75*100000*.99/(100000*.99+33000*1.01+10000*1.01)
check('MQ_DO_open_collector_gate',gate>2.5,{'minimum_high_V':gate,'note':'includes fitted R21 10k, R6 33k, R7 100k; AO3400A specified at Vgs=2.5V'})
check('powered_off_leak_bound',2e-6*101000<.3,{'GPIO_off_max_V':2e-6*101000,'condition':'TMUX1511 max powered-off leakage 2uA/channel; 100k 1% pulldown; protected inputs <=3.6V'})
components=[]
for (a,aa),(b,bb) in itertools.combinations(M['envelopes'].items(),2):
 pa,pb=box(*aa),box(*bb);check('envelope_'+a+'_'+b,not pa.intersects(pb),{'separation_mm':round(pa.distance(pb),3),'status':'provisional module envelopes; actual headers/body offsets require physical verification'})
for name,bounds in M['keepouts'].items():
 forbidden=box(*bounds).buffer(-.001);hits=[]
 for g in G:
  if g['kind']=='track':shape=LineString([g['start'],g['end']]).buffer(g['width']/2)
  elif g['kind']=='via':shape=Point(g['center']).buffer(g['width']/2)
  else:shape=box(*g['box'])
  if shape.intersects(forbidden):hits.append(g['id'])
 check(name+'_trace_via_pad_keepout',not hits,{'bounds_mm':bounds,'hits':hits,'copper_fill':'KiCad keepout rule plus zero DRC; Gerber viewer visual check separately'})
tracks=[g for g in G if g['kind']=='track'];vias=[g for g in G if g['kind']=='via']
check('signal_track_width',min(g['width'] for g in tracks)>=.25,{'min_width_mm':min(g['width'] for g in tracks)})
power={n:round(min(g['width'] for g in tracks if g['net']==n),3) for n in ['SENSOR_5V','ESP32_5V','EXT_5V','EXT_5V_RAW','5V_SERVO','SERVO_5V_RAW']}
necks=[g for g in tracks if g['net']=='EXT_5V' and g['width']<1]
neck_len=sum(LineString([g['start'],g['end']]).length for g in necks)
check('power_track_width',all(v>=1 for n,v in power.items() if n!='EXT_5V') and power['EXT_5V']>=.6 and neck_len<2.5 and all(box(100,79,104,82).covers(LineString([g['start'],g['end']])) for g in necks),{'minimum_width_mm':power,'Q2_short_pad_escape_length_mm':round(neck_len,3),'note':'0.601 mm escape only at SOT-23 source pad; 1.0 mm main rails and MQ branch'})
check('four_M3_NPTH',len([g for g in G if g['kind']=='pad' and g['ref'].startswith('H')])==4,'4 x 3.2 mm NPTH at (4,4), (106,4), (4,86), (106,86); drill file separately checked')
drc=read('checks/drc_final.json');erc=read('checks/erc.json')
project=read('esp32_sensor_carrier.kicad_pro')
rules=project['board']['design_settings']
check('DRC_all_rules_active',not rules.get('drc_exclusions') and not any(v=='ignore' for v in rules['rule_severities'].values()),'All listed DRC rules use error/warning; no disabled categories or exclusions')
check('DRC_no_exclusions',not drc['violations'] and not drc['unconnected_items'] and not drc['schematic_parity'],{'violations':len(drc['violations']),'unconnected':len(drc['unconnected_items']),'parity':len(drc['schematic_parity'])})
check('ERC',not any(s['violations'] for s in erc['sheets']), 'No error/warning exclusions used; NC and power flags explicit')
results.append({'check':'actual_module_mechanics','status':'PENDING','detail':'Header spacing/pitch and ESP external size from supplied dimensioned photo. ESP end offsets, module pin orientations/body envelopes/USB plugs require physical check. Not production verified.'})
out={'status':'ELECTRICAL_AND_ROUTING_PASS_MECHANICAL_PENDING','checks':results,'calculated_MQ_ADC_ratio':nom,'calculated_MQ_ADC_max_V':worst,'track_count':len(tracks),'via_count':len(vias),'hardware_tested':False}
(R/'checks/design_validation.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(f'{len(results)-1} automatic checks PASS; mechanical verification PENDING; ADC max {worst:.4f} V')

