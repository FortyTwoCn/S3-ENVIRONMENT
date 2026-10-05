import pathlib,sys,pcbnew as p,xml.etree.ElementTree as ET,json
R=pathlib.Path(__file__).resolve().parents[1];name=R/'esp32_sensor_carrier.kicad_pcb'
b=p.LoadBoard(str(name));ok=p.ImportSpecctraSES(b,sys.argv[1]);print('Import session:',ok)
fps={f.GetReference():f for f in b.GetFootprints()};nets={n.GetNetname():n for n in b.GetNetsByNetcode().values()}
xml=ET.parse(R/'fabrication/netlist.xml')
for nn in xml.findall('.//nets/net'):
 n=nn.attrib['name']
 if n not in nets:
  ni=p.NETINFO_ITEM(b,n,len(nets));b.Add(ni);nets[n]=ni
 for node in nn.findall('node'):
  fp=fps.get(node.attrib['ref'])
  if fp:
   for pad in fp.Pads():
    if pad.GetNumber()==node.attrib['pin']:pad.SetNet(nets[n])
for c in json.loads((R/'fabrication/design_manifest.json').read_text())['components']:
 fps[c['ref']].SetValue(c['value']);fps[c['ref']].SetDNP(c['dnp']);fps[c['ref']].SetExcludedFromBOM(False)
b.BuildConnectivity();p.ZONE_FILLER(b).Fill(b.Zones());p.SaveBoard(str(name),b)
print('Tracks + vias:',len(list(b.GetTracks())))
