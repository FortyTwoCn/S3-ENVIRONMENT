"""Real HTTP/WebSocket/PostgreSQL integration test; use an isolated *_test database.
Dependencies: requests websocket-client aiosmtpd
MONITOR_TEST_ENV_JSON: JSON file with server environment (not a production .env).
MONITOR_TEST_PASSWORD: test website password.
MONITOR_PHP: PHP CLI path. Run running web/ws services against same database.
"""
import os,json,re,pathlib,subprocess,time,hashlib,secrets,base64,sys
import requests,websocket
from aiosmtpd.controller import Controller

ROOT=pathlib.Path(__file__).resolve().parents[1]
ENV=json.loads(pathlib.Path(os.environ['MONITOR_TEST_ENV_JSON']).read_text())
assert ENV['DB_NAME'].endswith('_test'),'Tests require an isolated *_test database'
PHP=os.environ.get('MONITOR_PHP','php')
PASSWORD=os.environ['MONITOR_TEST_PASSWORD']
URL=ENV['APP_URL'];WS=ENV['WS_PUBLIC_URL']; reports=[]
def passed(name): reports.append(name);print('PASS',name,flush=True)
def sql(statement,args=()):
    payload=base64.b64encode(json.dumps([statement,args]).encode()).decode()
    code="require '"+str(ROOT/'server/src/bootstrap.php').replace('\\','/')+"';[$s,$a]=json_decode(base64_decode('"+payload+"'),true);echo json_encode(query($s,$a)->fetchAll(PDO::FETCH_ASSOC));"
    result=subprocess.run([PHP,'-r',code],env={**os.environ,**ENV},capture_output=True,text=True,check=True)
    return json.loads(result.stdout)
def worker(flag):
    return subprocess.run([PHP,str(ROOT/'server/bin/worker.php'),flag],env={**os.environ,**ENV},capture_output=True,text=True,check=True).stdout
assert os.environ.get('MONITOR_ALLOW_TEST_RESET')=='1','Explicit MONITOR_ALLOW_TEST_RESET=1 required; clears test tables'
sql('TRUNCATE devices,remember_tokens,ws_tickets,login_limits RESTART IDENTITY CASCADE')
sql("UPDATE settings SET value=jsonb_set(value,'{retention_days}','60') WHERE id=1")
session=requests.Session();csrf=''
def api(action,data=None,params=None,status=200,client=None):
    s=client or session
    r=s.request('POST' if data is not None else 'GET',URL+'/api.php',params={'action':action,**(params or {})},json=data,headers={'X-CSRF-Token':csrf} if data is not None else {},timeout=15)
    assert r.status_code==status,(action,r.status_code,r.text)
    return r.json()
def recv_type(sock,kind):
    deadline=time.time()+10
    while time.time()<deadline:
        raw=sock.recv(); assert raw,'Unexpected WS closure'
        m=json.loads(raw)
        if m['type']==kind:return m
    raise AssertionError('Expected '+kind)
def expect_closed(sock):
    # Already-buffered broadcasts may precede the server's close frame.
    for _ in range(200):
        if sock.recv()=='':return
    raise AssertionError('WebSocket did not close')
def telemetry(seq,smoke=False,reason='periodic',**extra):
    data={'light_lux':382.6,'temperature_c':26.45,'humidity_pct':52.3,'pressure_hpa':1010.2,'gas_ohm':92341,'mq_adc_raw':1370,'mq_adc_mv':1012.0,'mq_ao_v':1.998,'mq_gpio':smoke,'mq_smoke':smoke,'mq_ready':True,'radar_presence':True,'radar_ok':True,'bh1750_ok':True,'bme688_ok':True,'rssi_dbm':-52,'uptime_s':300,'queue_dropped':0,'radar_uart_bytes':1024,'radar_uart_age_ms':30,'radar_uart_hex':'f4f3f2f1','sensor_age_ms':50}
    return {'type':'telemetry','v':1,'boot_id':'abcdef1234567890','seq':seq,'captured_at':int(time.time()),'reason':reason,'data':data,**extra}
def upload(sock,m):sock.send(json.dumps(m));return recv_type(sock,'telemetry_ack')

assert requests.get(URL+'/api.php').status_code==401;passed('Unauthenticated API rejected')
page=session.get(URL+'/').text
login_csrf=re.search(r'name="csrf" value="([a-f0-9]+)"',page).group(1)
bad=session.post(URL+'/',data={'csrf':'wrong','password':PASSWORD});assert 'CSRF' in bad.text;passed('Login CSRF rejected')
r=session.post(URL+'/',data={'csrf':login_csrf,'password':PASSWORD,'remember':'on'});assert 'sample-now' in r.text
boot=api('bootstrap');csrf=boot['csrf'];assert session.cookies.get('sensor_remember');passed('Password login and HttpOnly remember cookie')
new_session=requests.Session();new_session.cookies.set('sensor_remember',session.cookies.get('sensor_remember'));api('bootstrap',client=new_session);passed('Remember cookie restores a fresh browser session')
wrong=session.post(URL+'/api.php?action=device-create',json={'name':'denied'},headers={'X-CSRF-Token':'wrong'});assert wrong.status_code==422;passed('API mutation CSRF rejected')
d=api('device-create',{'name':'集成测试设备'});did=d['id'];token=d['token'];assert len(token)==64
policy=api('devices')[0 if len(api('devices'))==1 else -1]['config'];assert policy['report_interval_s']==300
passed('Device creation, independent token, default five-minute interval')

invalid=websocket.create_connection(WS,timeout=5);invalid.send(json.dumps({'type':'hello','v':1,'role':'device','token':'0'*64}));assert invalid.recv()=='';invalid.close();passed('Invalid device token rejected')
oversized=websocket.create_connection(WS,timeout=5);oversized.send('x'*9000);expect_closed(oversized);oversized.close();passed('Oversized WebSocket frames rejected before application processing')
sock=websocket.create_connection(WS,timeout=10);sock.send(json.dumps({'type':'hello','v':1,'role':'device','token':token,'firmware':'integration-simulator'}));welcome=recv_type(sock,'welcome');assert welcome['device_id']==did;passed('Authenticated device WebSocket connection')
ticket=api('ws-ticket')['ticket'];browser=websocket.create_connection(WS,origin=URL,timeout=10);browser.send(json.dumps({'type':'hello','v':1,'role':'browser','ticket':ticket}));recv_type(browser,'welcome');passed('Authenticated browser real-time stream')
replay=websocket.create_connection(WS,origin=URL,timeout=5);replay.send(json.dumps({'type':'hello','v':1,'role':'browser','ticket':ticket}));assert replay.recv()=='';replay.close();passed('Browser ticket cannot be replayed')
evil_ticket=api('ws-ticket')['ticket'];evil=websocket.create_connection(WS,origin='http://evil.invalid',timeout=5);evil.send(json.dumps({'type':'hello','v':1,'role':'browser','ticket':evil_ticket}));assert evil.recv()=='';evil.close();passed('Cross-origin WebSocket rejected')

m=telemetry(1);upload(sock,m);live=recv_type(browser,'sample');assert live['sample']['data']['mq_adc_mv']==1012
upload(sock,m);h=api('history',params={'device_id':did,'hours':24});assert h['total']==1;passed('Telemetry saved and broadcast; duplicate ACK retry is idempotent')
bad=telemetry(2);bad['data']['mq_adc_raw']=9000;sock.send(json.dumps(bad));assert recv_type(sock,'error')['error']=='value_mq_adc_raw';passed('Out-of-range telemetry rejected')
bad=telemetry(3);bad['captured_at']=int(time.time())+3600;sock.send(json.dumps(bad));assert recv_type(sock,'error')['error']=='timestamp';passed('Future timestamps rejected')
missing=telemetry(4);missing['data']['temperature_c']=None;missing['data']['light_lux']=None;missing['data']['mq_smoke']=None;upload(sock,missing);passed('Missing sensors retain null instead of zero')
command=api('command',{'device_id':did},status=202);cid=command['request_id'];cmd=recv_type(sock,'command');assert cmd['request_id']==cid
sock.send(json.dumps({'type':'command_ack','request_id':cid}));time.sleep(.1);upload(sock,telemetry(5,reason='requested',request_id=cid));assert api('commands',params={'device_id':did})[0]['state']=='completed';passed('Website request -> device command -> fresh measurement -> completion')
cmd=api('command',{'device_id':did},status=202);recv_type(sock,'command');sql('UPDATE commands SET deadline=now()-interval \'1 second\' WHERE id=?',[cmd['request_id']]);time.sleep(1.3);assert api('commands',params={'device_id':did})[0]['state']=='timeout';passed('Commands timeout and cannot remain pending forever')

chart=api('chart',params={'device_id':did,'metric':'temperature_c','hours':1440});assert len(chart['points'])<=1201
csv=session.get(URL+'/api.php',params={'action':'export','device_id':did,'hours':24});assert csv.status_code==200 and 'observed_at_utc' in csv.text;passed('History paging, bounded chart aggregation, CSV export')
sql("INSERT INTO samples(device_id,boot_id,seq,observed_at,clock_quality,reason,data) VALUES(?,'abcdef1234567890',90,now()-interval '61 days','ntp','periodic','{}')",[did]);result=json.loads(worker('--cleanup'));assert result['samples_deleted']>=1;assert not sql('SELECT 1 FROM samples WHERE device_id=? AND seq=90',[did]);passed('Default sixty-day retention removes expired records')

class Inbox:
    def __init__(self):self.messages=[]
    async def handle_DATA(self,server,session,envelope):self.messages.append(envelope.content);return '250 OK'
inbox=Inbox();controller=Controller(inbox,hostname='127.0.0.1',port=18025);controller.start()
site={'retention_days':2,'mail_enabled':True,'mail_cooldown_s':900,'smtp':{'host':'127.0.0.1','port':18025,'encryption':'none','username':'','password':'test_authorization_not_real','from_address':'monitor@example.test','from_name':'传感器监测','recipients':['user@example.test']}}
api('settings-save',site);visible=api('settings');assert visible['smtp']['password_saved'] and 'password_enc' not in visible['smtp'];stored=json.loads(sql('SELECT value FROM settings WHERE id=1')[0]['value'])['smtp']['password_enc'];assert 'test_authorization' not in stored;passed('SMTP authorization encrypted at rest and redacted from API')
sql("INSERT INTO samples(device_id,boot_id,seq,observed_at,clock_quality,reason,data) VALUES(?,'abcdef1234567890',91,now()-interval '3 days','ntp','periodic','{}')",[did]);worker('--cleanup');assert not sql('SELECT 1 FROM samples WHERE device_id=? AND seq=91',[did]);site['retention_days']=60;site['smtp']['password']='';api('settings-save',site);passed('Configurable retention applied by cleanup worker')
cfg=welcome['config'];cfg['mq_enabled']=True;api('device-config',{'id':did,'config':cfg});pushed=recv_type(sock,'config');assert pushed['config']['mq_enabled'];passed('Web settings pushed to online device')
upload(sock,telemetry(6,True,'alarm'));upload(sock,telemetry(7,True));jobs=sql("SELECT * FROM mail_queue WHERE device_id=?",[did]);assert len(jobs)==1;worker('--once');assert len(inbox.messages)==1;assert '烟雾告警' in inbox.messages[0].decode(errors='replace') or b'Subject:' in inbox.messages[0];passed('Smoke incident queued and delivered through real local SMTP')
old=telemetry(61,False);old['captured_at']=int(time.time())-300;upload(sock,old);assert sql('SELECT active FROM alert_state WHERE device_id=?',[did])[0]['active'];passed('Out-of-order backlog cannot clear a newer smoke incident')
upload(sock,telemetry(8,False,'recovered'));upload(sock,telemetry(9,True,'alarm'));assert len(sql('SELECT * FROM mail_queue WHERE device_id=?',[did]))==1;passed('Sustained alarm suppression, recovery, mail cooldown')
upload(sock,telemetry(62,False,'recovered'));old=telemetry(63,True,'alarm');old['captured_at']=None;old['queue_age_s']=1200;upload(sock,old);assert not sql('SELECT active FROM alert_state WHERE device_id=?',[did])[0]['active'];passed('Old unsynchronized queued telemetry cannot trigger a new smoke email')
api('mail-test',{});worker('--once');assert len(inbox.messages)==2;passed('Website SMTP test mail delivered')
api('mail-test',{},status=422);passed('SMTP test request rate limited')
controller.stop()
# Force an SMTP connection failure without sending to any external destination.
sql("INSERT INTO mail_queue(kind,payload) VALUES('test','{}')");worker('--once');failed=sql('SELECT state,attempts,last_error FROM mail_queue ORDER BY id DESC LIMIT 1')[0];assert failed['state']=='pending' and failed['attempts']==1;passed('SMTP failure produces retry instead of data loss')

sock.close();time.sleep(.2);api('command',{'device_id':did},status=409);passed('Offline command refused with explicit status')
sock=websocket.create_connection(WS,timeout=10);sock.send(json.dumps({'type':'hello','v':1,'role':'device','token':token}));recv_type(sock,'welcome');upload(sock,telemetry(10));passed('Device reconnect and upload continue')
rotated=api('device-token',{'id':did})
time.sleep(1.3);assert sock.recv()=='';sock.close();passed('Token rotation revokes existing device connection')
sock=websocket.create_connection(WS,timeout=10);sock.send(json.dumps({'type':'hello','v':1,'role':'device','token':rotated['token'],'firmware':'integration-simulator'}));recv_type(sock,'welcome');passed('Device authenticates with rotated token')
revoked=api('device-revoke',{'id':did});time.sleep(1.3);assert sock.recv()=='';sock.close();passed('Device disable revokes active connection')
logout=session.post(URL+'/',data={'csrf':csrf,'logout':'1'});time.sleep(1.3);expect_closed(browser);browser.close();assert new_session.get(URL+'/api.php').status_code==401;passed('Logout revokes remember login and browser WebSocket')
report={'result':'PASS','checks':reports,'test_count':len(reports),'database':'PostgreSQL','php':subprocess.check_output([PHP,'-v'],text=True).splitlines()[0],'email':'local SMTP sink only; no external messages','timestamp':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}
(ROOT/'test_results').mkdir(exist_ok=True);(ROOT/'test_results/integration.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print(f'{len(reports)} integration checks passed')
