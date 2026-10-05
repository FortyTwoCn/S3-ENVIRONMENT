"""Check physical socket rows against photo pin orders and documented mounting view."""
from pathlib import Path
import json,csv,hashlib,math
import xml.etree.ElementTree as ET
R=Path(__file__).resolve().parents[1]
G=json.loads((R/'checks/geometry.json').read_text(encoding='utf-8'))
xml=ET.parse(R/'fabrication/netlist.xml')
nets={(n.get('ref'),n.get('pin')):net.get('name') for net in xml.findall('./nets/net') for n in net.findall('node')}
back={
    'J2':['VCC','GND','SCL','SDA','ADDR'],
    'J3':['CS','SDO','SDA','SCL','GND','VCC'],
    'J5':['AO','DO','GND','VCC'],
}
front={ref:list(reversed(labels)) for ref,labels in back.items()}
front['J4']=['TX','RX','OUT','GND','VCC']
labelnet={
    'J2':{'VCC':'+3V3','GND':'GND','SCL':'I2C_SCL','SDA':'I2C_SDA','ADDR':'BH_ADDR'},
    'J3':{'VCC':'+3V3','GND':'GND','SCL':'I2C_SCL','SDA':'I2C_SDA','SDO':'BME_ADDR','CS':'BME_CS'},
    'J4':{'VCC':'SENSOR_5V','GND':'GND','TX':'RADAR_TX','RX':'RADAR_RX','OUT':'RADAR_OUT'},
    'J5':{'VCC':'SENSOR_5V','GND':'GND','DO':'MQ_DO_RAW','AO':'MQ_AO_RAW'},
}
with (R/'fabrication/interface_pinout.csv').open(encoding='utf-8-sig',newline='') as f:
    interface={(a['Reference'],a['Pin']):a for a in csv.DictReader(f)}
rows=[];checks=[]
for ref,labels in front.items():
    pads=sorted([g for g in G if g['kind']=='pad' and g['ref']==ref],key=lambda g:int(g['pin']))
    assert len(pads)==len(labels)
    horizontal=ref!='J4'
    constant=1 if horizontal else 0
    assert max(p['center'][constant] for p in pads)-min(p['center'][constant] for p in pads)<.00001
    pitch=[math.dist(a['center'],b['center']) for a,b in zip(pads,pads[1:])]
    assert all(abs(p-2.54)<.00001 for p in pitch)
    for pad,label in zip(pads,labels):
        expected=labelnet[ref][label];k=(ref,pad['pin'])
        assert pad['net']==nets[k]==interface[k]['Net']==expected
        assert interface[k]['Pin label']==label
        assert pad['layers']==[0,1]
        rows.append([ref,pad['pin'],label,expected,*pad['center'],'MODULE SENSING FACE UP'])
    checks.append({'socket':ref,'status':'PASS','top_view_pin1_to_last':labels,
                   'single_row':True,'pitch_mm':2.54,'pin_count':len(pads),
                   'first_to_last_center_distance_mm':math.dist(pads[0]['center'],pads[-1]['center']),
                   'pin_coordinates_mm':[p['center'] for p in pads]})
with (R/'fabrication/sensor_socket_review.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f);w.writerow(['Socket','Physical pad','Pin label','Net','Actual X mm','Actual Y mm','Mounting view']);w.writerows(rows)
report={'release':'R1.1-PENDING','status':'SOCKET_GEOMETRY_NETLIST_AND_PHOTO_VIEW_PASS_PHYSICAL_VERIFICATION_PENDING',
        'source_photo':'sources/actual_sensor_modules.jpg',
        'source_photo_sha256':hashlib.sha256((R/'sources/actual_sensor_modules.jpg').read_bytes()).hexdigest(),
        'BME_back_order_user_text_confirmed':back['J3'],
        'mounting':'Horizontal; sensing faces UP; GY/BME/MQ body above socket row in carrier top view. Radar face up, body to the left of its vertical socket.',
        'changed_socket_nets':['J2.1','J2.2','J2.4','J2.5','J5.1','J5.2','J5.3','J5.4'],
        'GPIO_changed':False,'BME_geometry_changed':False,'checks':checks,
        'pending':['Complete GY/MQ physical silk check: some labels covered in photograph',
                   'Straight downward module male headers for horizontal mounting; replace MQ right-angle header',
                   'Fit straight downward 1x5 header to radar',
                   'Actual module dimensions, body-to-header offsets and heights',
                   'Actual assembly on 100% printed mechanical drawings'],
        'physical_verified':False,'hardware_tested':False}
(R/'checks/sensor_photo_review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Four sockets: single rows and 2.54mm pitch PASS; physical pads / XML / CSV / photo view PASS. Actual assembly PENDING.')
