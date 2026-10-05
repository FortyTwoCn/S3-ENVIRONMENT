import pcbnew as p,pathlib,json
R=pathlib.Path(__file__).resolve().parents[1];b=p.LoadBoard(str(R/'esp32_sensor_carrier.kicad_pcb'))
objs=[]
def pt(v):return [p.ToMM(v.x),p.ToMM(v.y)]
for fp in b.GetFootprints():
 for pad in fp.Pads():
  bb=pad.GetBoundingBox();objs.append({'id':pad.m_Uuid.AsString(),'kind':'pad','net':pad.GetNetname(),'center':pt(pad.GetPosition()),'box':[p.ToMM(bb.GetX()),p.ToMM(bb.GetY()),p.ToMM(bb.GetRight()),p.ToMM(bb.GetBottom())],'layers':[l for l in (0,1) if pad.IsOnLayer(p.F_Cu if l==0 else p.B_Cu)],'ref':fp.GetReference(),'pin':pad.GetNumber()})
for t in b.GetTracks():
 if isinstance(t,p.PCB_VIA):objs.append({'id':t.m_Uuid.AsString(),'kind':'via','net':t.GetNetname(),'center':pt(t.GetPosition()),'width':p.ToMM(t.GetWidth(p.F_Cu)),'layers':[0,1]})
 else:objs.append({'id':t.m_Uuid.AsString(),'kind':'track','net':t.GetNetname(),'start':pt(t.GetStart()),'end':pt(t.GetEnd()),'width':p.ToMM(t.GetWidth()),'layers':[0 if t.GetLayer()==p.F_Cu else 1]})
(R/'checks/geometry.json').write_text(json.dumps(objs))
print('Geometry exported:',len(objs))
