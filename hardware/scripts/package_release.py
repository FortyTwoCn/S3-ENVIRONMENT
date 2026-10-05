"""Copy actual build artifacts and assemble a checked, portable delivery archive."""
import pathlib,json,shutil,hashlib,zipfile,re
R=pathlib.Path(__file__).resolve().parents[1];W=R.parents[1]/'work'
proof={}
for env in ['yd_uart','yd_native_usb']:
 log=(R/'checks'/f'firmware_{env}.log').read_text(encoding='utf-8-sig');assert '[SUCCESS]' in log
 dest=R/'firmware_test/prebuilt'/env;dest.mkdir(parents=True,exist_ok=True)
 for name in ['bootloader.bin','partitions.bin','firmware.bin']:
  src=R/'firmware_test/.pio/build'/env/name
  # If packaging a previously cleaned release, keep existing verified binaries.
  if src.exists():shutil.copy2(src,dest/name)
  assert (dest/name).is_file()
 app0=W/'platformio/packages/framework-arduinoespressif32/tools/partitions/boot_app0.bin'
 if app0.exists():shutil.copy2(app0,dest/'boot_app0.bin')
 hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in dest.glob('*.bin')}
 (dest/'SHA256.json').write_text(json.dumps(hashes,indent=2)+'\n',encoding='utf-8')
 ram=int(re.search(r'RAM:.*used (\d+) bytes',log).group(1));flash=int(re.search(r'Flash:.*used (\d+) bytes',log).group(1))
 proof[env]={'status':'SUCCESS','RAM_bytes':ram,'Flash_app_bytes':flash,'files_sha256':hashes}
(R/'checks/firmware_build.json').write_text(json.dumps({'toolchain':'PlatformIO 6.2.0 / espressif32 6.12.0 / Arduino ESP32 2.0.17','N16R8_settings':'16MB Flash QIO / OPI PSRAM / custom 16MB partitions','environments':proof,'hardware_uploaded':False,'hardware_tested':False},indent=2)+'\n',encoding='utf-8')
drc=json.loads((R/'checks/drc_final.json').read_text(encoding='utf-8'));erc=json.loads((R/'checks/erc.json').read_text(encoding='utf-8'))
assert not drc['violations'] and not drc['unconnected_items'] and not drc['schematic_parity']
assert not any(s['violations'] for s in erc['sheets'])
assert json.loads((R/'checks/design_validation.json').read_text(encoding='utf-8'))['status']=='ELECTRICAL_AND_ROUTING_PASS_MECHANICAL_PENDING'
assert json.loads((R/'checks/gerber_validation.json').read_text(encoding='utf-8'))['status']=='PARSE_AND_ANTENNA_COPPER_KEEPOUT_PASS_MECHANICAL_PENDING'
photo=json.loads((R/'checks/sensor_photo_review.json').read_text(encoding='utf-8'))
assert photo['release']=='R1.1-PENDING' and all(c['status']=='PASS' for c in photo['checks'])
required=['esp32_sensor_carrier.kicad_pro','esp32_sensor_carrier.kicad_sch','esp32_sensor_carrier.kicad_pcb','README.md','Design_Summary.md','fabrication/BOM.csv','fabrication/netlist.csv','fabrication/gpio_map.csv','fabrication/ESP32_FOOTPRINT_1_TO_1_CHECK.pdf','fabrication/schematic.pdf','fabrication/assembly.pdf','images/pcb_3d.png','images/pcb_front.png','images/pcb_back.png','images/schematic.png']
for f in required:assert (R/f).stat().st_size>20,f
files=[]
for p in R.rglob('*'):
 if not p.is_file():continue
 rel=p.relative_to(R)
 if any(x in ['.pio','__pycache__'] for x in rel.parts) or p.suffix in ['.lck','.kicad_prl','.dsn'] or p.name=='release_manifest.json':continue
 if rel.parts[0]=='checks' and p.name in ['drc_routed.json','manual_routes.json','drc_initial.json','drc_placement.json','erc_initial.json']:continue
 files.append(p)
manifest={'release':'R1.1-PENDING','manufacturing_status':'MECHANICAL_DIMENSION_PENDING; not PRODUCTION VERIFIED','tool_version':'KiCad 9.0.9','hardware_tested':False,'file_sha256':{p.relative_to(R).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files}}
(R/'release_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');files.append(R/'release_manifest.json')
z=R.parent/'ESP32_S3_Sensor_Carrier_R1_1_PENDING.zip'
with zipfile.ZipFile(z,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
 for p in files:archive.write(p,'hardware/'+p.relative_to(R).as_posix())
with zipfile.ZipFile(z) as archive:assert archive.testzip() is None
print('Release archive:',z,'Files:',len(files),'Size MB:',round(z.stat().st_size/1e6,2))
fabzip=R.parent/'ESP32_S3_Carrier_Gerbers_R1_1_PROVISIONAL.zip'
with zipfile.ZipFile(fabzip,'w',zipfile.ZIP_DEFLATED) as archive:
 for p in (R/'gerber/PROVISIONAL_MECHANICAL_DIMENSION_PENDING').iterdir():
  if p.suffix.lower() not in ['.svg']:archive.write(p,p.name)
 archive.writestr('MECHANICAL_VERIFICATION_REQUIRED.txt','R1.1-PENDING. DO NOT ORDER BEFORE 1:1 PHYSICAL VERIFICATION.\n110x90mm maximum outline; 2-layer FR4, 1.6mm, 1oz.\nIncludes USB cutout and rounded non-plated BME isolation slot in Edge.Cuts.\n4x3.2mm M3 NPTH, separate plated/nonplated drill files.\nNot PRODUCTION VERIFIED.\n')
print('Provisional fabrication archive:',fabzip)
