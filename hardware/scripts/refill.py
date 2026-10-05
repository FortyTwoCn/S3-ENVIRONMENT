import pcbnew as p,pathlib
r=pathlib.Path(__file__).resolve().parents[1];fn=r/'esp32_sensor_carrier.kicad_pcb';b=p.LoadBoard(str(fn));b.BuildConnectivity();p.ZONE_FILLER(b).Fill(b.Zones());p.SaveBoard(str(fn),b);print('Refilled ground zones')
