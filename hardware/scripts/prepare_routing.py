"""Prepare DSN with conservative signal widths, wide power classes and no false planes."""
import pathlib,sexpdata as sx,json,re
from shapely.geometry import Polygon
R=pathlib.Path(__file__).resolve().parents[1];fn=R/'esp32_sensor_carrier.dsn'
sym=sx.Symbol
def parse(source):
 stack=[];root=None
 for token in re.findall(r'"[^"\n]*"|\(|\)|[^\s()]+',source.replace('(string_quote ")','(string_quote "quote")').replace('\\','/')):
  if token=='(':
   obj=[]
   if stack:stack[-1].append(obj)
   else:root=obj
   stack.append(obj)
  elif token==')':stack.pop()
  else:
   if token.startswith('"'):value=token[1:-1]
   else:
    try:value=float(token) if '.' in token else int(token)
    except ValueError:value=sym(token)
   stack[-1].append(value)
 return root
def dumps(obj):
 if isinstance(obj,list):return '('+' '.join(dumps(x) for x in obj)+')'
 if isinstance(obj,sym):return str(obj)
 if isinstance(obj,str):return '"'+obj+'"'
 return str(obj)
tree=parse(fn.read_text())
def key(a):return str(a[0]) if isinstance(a,list) and a else ''
for node in tree:
 if key(node)=='structure':
  # Router must route real GND connectivity, not assume the entire outline is a plane.
  node[:]=[x for x in node if key(x)!='plane' and not(key(x)=='keepout' and '81000' in dumps(x) and '-6000' in dumps(x))]
  for x in node:
   if key(x)=='rule':x[:]=[sym('rule'),[sym('width'),300],[sym('clearance'),210]]
   if key(x)=='boundary':
    a=x[1];coords=list(zip(a[3::2],a[4::2]));poly=Polygon(coords).buffer(-400,join_style='mitre')
    x[1]=[sym('path'),sym('pcb'),0,*[round(v,3) for xy in poly.exterior.coords for v in xy]]
   if key(x)=='keepout' and key(x[2])=='polygon' and str(x[2][1])=='signal':
    a=x[2];poly=Polygon(list(zip(a[3::2],a[4::2]))).buffer(400)
    x[2]=[sym('polygon'),sym('signal'),0,*[round(v,3) for xy in poly.exterior.coords for v in xy]]
 if key(node)=='network':
  node[:]=[x for x in node if key(x)!='class']
  power=['SENSOR_5V','ESP32_5V','EXT_5V','EXT_5V_RAW','5V_SERVO','SERVO_5V_RAW']
  nets=[x[1] for x in node if key(x)=='net'];normal=[n for n in nets if str(n) not in power]
  node.append([sym('class'),'Default',*normal,[sym('circuit'),[sym('use_via'),'Via[0-1]_800:400_um']],[sym('rule'),[sym('width'),300],[sym('clearance'),210]]])
  node.append([sym('class'),'Power',*power,[sym('circuit'),[sym('use_via'),'Via[0-1]_1200:600_um']],[sym('rule'),[sym('width'),1000],[sym('clearance'),250]]])
 if key(node)=='library':
  via=[sym('padstack'),'Via[0-1]_1200:600_um',[sym('shape'),[sym('circle'),'F.Cu',1200]],[sym('shape'),[sym('circle'),'B.Cu',1200]],[sym('attach'),sym('off')]]
  node.append(via)
for node in tree:
 if key(node)=='structure':
  for x in node:
   if key(x)=='via':x.append('Via[0-1]_1200:600_um')
fn.write_text(dumps(tree).replace('(string_quote "quote")','(string_quote ")'));print('Prepared DSN: signal 0.30mm, power 1.0mm, GND fully routed; thermal pour-only area permits tracks')
