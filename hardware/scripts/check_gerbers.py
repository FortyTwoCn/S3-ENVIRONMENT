"""Parse exported fabrication files independently and inspect copper keepouts."""
import pathlib,json,warnings,hashlib
import numpy as np
import pymupdf as fitz
from gerbonara import LayerStack
R=pathlib.Path(__file__).resolve().parents[1];F=R/'gerber/PROVISIONAL_MECHANICAL_DIMENSION_PENDING'
with warnings.catch_warnings(record=True) as observed:
 warnings.simplefilter('always');stack=LayerStack.open(F,lazy=False)
 notes=[str(x.message) for x in observed]
expected={('top','copper'),('bottom','copper'),('top','mask'),('bottom','mask'),('top','silk'),('bottom','silk'),('mechanical','outline')}
assert set(stack.graphic_layers)==expected
assert len(stack.drill_npth.objects)==4
holes=[{'x':o.x,'y':o.y,'diameter':o.tool.diameter} for o in stack.drill_npth.objects]
assert all(abs(o['diameter']-3.2)<.001 for o in holes)
M=json.loads((R/'fabrication/design_manifest.json').read_text(encoding='utf-8'));checks=[]
for side,label in [('top','front'),('bottom','back')]:
 svg=str(stack.graphic_layers[(side,'copper')].to_svg(force_bounds=((0,-90),(110,0)),fg='black',bg='white'))
 path=R/'images'/f'copper_{label}.svg';path.write_text(svg,encoding='utf-8')
 doc=fitz.open(path);pdf=fitz.open('pdf',doc.convert_to_pdf());pix=pdf[0].get_pixmap(matrix=fitz.Matrix(4,4),alpha=False);pix.save(str(R/'images'/f'copper_{label}.png'))
 a=np.frombuffer(pix.samples,np.uint8).reshape(pix.height,pix.width,pix.n)
 for name,(x1,y1,x2,y2) in M['keepouts'].items():
  # Exclude 0.4 mm perimeter to eliminate sampling/anti-alias ambiguity.
  left=int((x1+.4)/110*pix.width);right=int((x2-.4)/110*pix.width)
  top=int((y1+.4)/90*pix.height);bottom=int((y2-.4)/90*pix.height)
  roi=a[top:bottom,left:right,:3];dark=int(np.count_nonzero(np.min(roi,axis=2)<200))
  checks.append({'layer':side,'keepout':name,'dark_pixels':dark,'checked_pixels':int(roi.shape[0]*roi.shape[1]),'status':'PASS' if dark==0 else 'FAIL'})
  assert dark==0,(side,name,dark)
 # Gerbonara's readable SVG is also delivered for independent viewer inspection.
 (R/'images'/f'gerber_{label}.svg').write_text(str(stack.to_svg(side_re=side+'|mechanical',force_bounds=((0,-90),(110,0)))),encoding='utf-8')
report={'status':'PARSE_AND_ANTENNA_COPPER_KEEPOUT_PASS_MECHANICAL_PENDING','parser':'Gerbonara 1.6.3','layers':sorted('/'.join(x) for x in stack.graphic_layers),'PTH_drill_hits':len(stack.drill_pth.objects),'NPTH_drill_hits':len(stack.drill_npth.objects),'NPTH_holes_mm':holes,'antenna_copper_raster_checks':checks,'parser_notes':notes,'files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in F.iterdir() if p.is_file()}}
(R/'checks/gerber_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(f"7 Gerber layers parsed; {report['PTH_drill_hits']} PTH / {report['NPTH_drill_hits']} M3 NPTH; both antenna keepouts copper-free on both sides")
