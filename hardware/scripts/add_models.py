"""Add portable library models and explicitly approximate user-module envelopes.
Run with ordinary Python; does not change pads, tracks, or connectivity.
"""
import pathlib, shutil, json, sexpdata as sx
R=pathlib.Path(__file__).resolve().parents[1]
V=R.parents[1]/'work/kicad9/share/kicad/3dmodels'
D=R/'3d';D.mkdir(exist_ok=True)
k=lambda a:str(a[0]) if isinstance(a,list) and a else ''
child=lambda a,key:next(x for x in a if k(x)==key)
tree=sx.loads((R/'esp32_sensor_carrier.kicad_pcb').read_text(encoding='utf-8'))
manifest=json.loads((R/'fabrication/design_manifest.json').read_text(encoding='utf-8'))
files={}
def portable(source):
 name=pathlib.Path(source).name
 src=V/source
 assert src.exists(),src
 shutil.copy2(src,D/name)
 return '${KIPRJMOD}/3d/'+name
def model(name,x=0,y=0,z=0):
 return sx.loads(f'(model "{name}" (offset (xyz {x} {y} {z})) (scale (xyz 1 1 1)) (rotate (xyz 0 0 0)))')
def socket(n):return portable(f'Connector_PinSocket_2.54mm.3dshapes/PinSocket_1x{n:02d}_P2.54mm_Vertical.step')
def header(n):return portable(f'Connector_PinHeader_2.54mm.3dshapes/PinHeader_1x{n:02d}_P2.54mm_Vertical.step')
def box(center,size,color):
 xyz=' '.join(str(round(t/2.54,6)) for t in center); wh=' '.join(str(round(t/2.54,6)) for t in size)
 return f'Transform {{ translation {xyz} children [ Shape {{ appearance Appearance {{ material Material {{ diffuseColor {color} }} }} geometry Box {{ size {wh} }} }} ] }}\n'
params=manifest['mechanics'];halfrow=params['HEADER_ROW_SPACING']/2
spec={'J1':[model(socket(22),-halfrow),model(socket(22),halfrow)],'J2':[model(socket(5))],'J3':[model(socket(6))],'J4':[model(socket(5))],'J5':[model(socket(4))],'JP3':[model(header(3))],'J7':[model(header(4))]}
for ref in ('J8','J9','J10','J11','J12'):spec[ref]=[model(header(3))]
# Local VRML uses historical KiCad 0.1-inch units. Module PCB undersides at 8.5 mm.
for ref,key in [('J1','ESP32'),('J2','GY302'),('J3','BME688'),('J4','LD2410C'),('J5','MQ')]:
 comp=next(c for c in manifest['components'] if c['ref']==ref); ox,oy,angle=comp['position'];x1,y1,x2,y2=manifest['envelopes'][key]
 # The green planes represent the reserved envelope, including header clearance,
 # not an exact physical PCB outline. Keep socket pad centers inside that envelope.
 if ref=='J1':y1=oy-params['FIRST_PIN_FROM_BODY_TOP']
 dx=(x1+x2)/2-ox;dy=(y1+y2)/2-oy;w=x2-x1;h=y2-y1
 cx,cy=(dx,-dy) if angle==0 else (-dy,-dx)
 if angle==90:w,h=h,w
 text='#VRML V2.0 utf8\n# APPROXIMATE USER MODULE ENVELOPE, NOT A VERIFIED PART MODEL\n'+box((cx,cy,9.3),(w,h,1.6),'0.02 0.16 0.1')
 if ref=='J1':
  text+=box((0,-8.5,11.7),(17,19,3.2),'0.62 0.62 0.62')
  top=-params['FIRST_PIN_FROM_BODY_TOP'];bottom=21*params['PIN_PITCH']+params['LAST_PIN_FROM_USB_EDGE'];ant_top=bottom-params['ESP_TOTAL_LENGTH']
  text+=box((0,-(ant_top+top)/2,9.3),(18,top-ant_top,1.6),'0.035 0.035 0.035')
  for x in (-5.8,5.8):text+=box((x,-54.5,11.1),(8.5,6.5,3.6),'0.65 0.65 0.65')
 if ref=='J5':
  # Approximate MQ heated can envelope; vertical axis VRML Y rotated to PCB Z.
  text+=box((cx,cy,18.1),(19,19,16),'0.57 0.57 0.57')
 name=f'{key}_APPROXIMATE_ENVELOPE.wrl';(D/name).write_text(text,encoding='utf-8');spec[ref].append(model('${KIPRJMOD}/3d/'+name))
for fp in tree:
 if k(fp)!='footprint':continue
 ref=next(n[2] for n in fp if k(n)=='property' and n[1]=='Reference')
 for m in [n for n in fp if k(n)=='model']:
  if str(m[1]).startswith('${KICAD9_3DMODEL_DIR}/'):m[1]=portable(m[1].split('}/',1)[1])
 if ref in spec:
  fp[:]=[n for n in fp if k(n)!='model'];fp.extend(spec[ref])
 files[fp[1].split(':')[-1]]=[n for n in fp if k(n)=='model']
for name,mods in files.items():
 path=R/'footprints/custom.pretty'/(name+'.kicad_mod');lib=sx.loads(path.read_text(encoding='utf-8'))
 lib[:]=[n for n in lib if k(n)!='model'];lib.extend(mods);path.write_text(sx.dumps(lib)+'\n',encoding='utf-8')
(R/'esp32_sensor_carrier.kicad_pcb').write_text(sx.dumps(tree)+'\n',encoding='utf-8')
(D/'README.md').write_text('STEP files copied from KiCad 9.0.9 standard 3D library. Source: https://gitlab.com/kicad/libraries/kicad-packages3D ; CC-BY-SA 4.0 with KiCad library exception.\n\n*_APPROXIMATE_ENVELOPE.wrl models are original illustrative envelopes. They are not measured module models. Header alignment and module outline must be checked against the actual modules before fabrication. Module PCB underside is assumed 8.5 mm above the carrier.\n',encoding='utf-8')
print('Portable models added:',len(list(D.glob('*.step'))),'STEP and 5 approximate module envelopes')
