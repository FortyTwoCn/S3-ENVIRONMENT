import pathlib,json,pcbnew as p
R=pathlib.Path(__file__).resolve().parents[1];fn=R/'esp32_sensor_carrier.kicad_pcb';b=p.LoadBoard(str(fn));nets={n.GetNetname():n for n in b.GetNetsByNetcode().values()}
V=lambda pt:p.VECTOR2I(p.FromMM(pt[0]),p.FromMM(pt[1]))
for r in json.loads((R/'checks/manual_routes.json').read_text()):
 for a,c in zip(r['path'],r['path'][1:]):
  if a[2]!=c[2]:
   t=p.PCB_VIA(b);t.SetPosition(V(a));t.SetWidth(p.FromMM(1.2 if r['width']>.5 else .8));t.SetDrill(p.FromMM(.6 if r['width']>.5 else .4));t.SetViaType(p.VIATYPE_THROUGH);t.SetLayerPair(p.F_Cu,p.B_Cu)
  else:
   if a[:2]==c[:2]:continue
   t=p.PCB_TRACK(b);t.SetStart(V(a));t.SetEnd(V(c));t.SetWidth(p.FromMM(r['width']));t.SetLayer(p.F_Cu if a[2]==0 else p.B_Cu)
  t.SetNet(nets[r['net']]);b.Add(t)
# Explicit ground connection style for high-current / narrow thermal pads.
for fp in b.GetFootprints():
 if fp.GetReference() in ('J6','J7','J9'):
  for pad in fp.Pads():
   if pad.GetNetname()=='GND':pad.SetLocalZoneConnection(p.ZONE_CONNECTION_FULL)
# Remove the router's unused via listed by actual DRC; no waivers.
for v in json.loads((R/'checks/drc_routed.json').read_text(encoding='utf-8'))['violations']:
 if v['type']=='via_dangling':
  ids={i['uuid'] for i in v['items']}
  for t in list(b.GetTracks()):
   if t.m_Uuid.AsString() in ids:b.Remove(t)
b.BuildConnectivity();p.ZONE_FILLER(b).Fill(b.Zones());p.SaveBoard(str(fn),b);print('Applied routes and refilled GND')
