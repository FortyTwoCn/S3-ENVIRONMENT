"""Browser QA with explicitly simulated telemetry, real backend and actual Chart.js.
Environment variables match integration.py. Requires playwright, requests, websocket-client.
Does not erase test tables; creates a separate simulated device.
"""
import os,json,pathlib,re,time,threading,math
import requests,websocket
from playwright.sync_api import sync_playwright,expect
ROOT=pathlib.Path(__file__).resolve().parents[1]
ENV=json.loads(pathlib.Path(os.environ['MONITOR_TEST_ENV_JSON']).read_text())
assert ENV['DB_NAME'].endswith('_test')
URL=ENV['APP_URL'];PASSWORD=os.environ['MONITOR_TEST_PASSWORD'];s=requests.Session()
csrf=re.search(r'name="csrf" value="([a-f0-9]+)"',s.get(URL).text).group(1)
s.post(URL,data={'csrf':csrf,'password':PASSWORD,'remember':'on'})
csrf=s.get(URL+'/api.php?action=bootstrap').json()['csrf']
def api(action,data):
    r=s.post(URL+'/api.php',params={'action':action},json=data,headers={'X-CSRF-Token':csrf},timeout=10);assert r.ok,r.text;return r.json()
d=api('device-create',{'name':'宿舍环境 · 模拟数据'});did=d['id'];token=d['token']
sock=websocket.create_connection(ENV['WS_PUBLIC_URL'],timeout=10)
sock.send(json.dumps({'type':'hello','v':1,'role':'device','token':token,'firmware':'browser-test-simulator'}));welcome=json.loads(sock.recv())
seq=0
def sample(epoch,request=None):
    global seq
    phase=seq/15
    data={'temperature_c':25.4+1.4*math.sin(phase),'humidity_pct':51+5*math.cos(phase),'pressure_hpa':1010.2+math.sin(phase)*1.2,'light_lux':340+160*math.sin(phase/2),'gas_ohm':92000+11000*math.cos(phase),'radar_presence':seq%10<7,'radar_ok':True,'mq_adc_raw':1230+seq%30,'mq_adc_mv':925+30*math.cos(phase),'mq_ao_v':1.85,'mq_gpio':False,'mq_smoke':None,'mq_ready':False,'bh1750_ok':True,'bme688_ok':True,'rssi_dbm':-54,'uptime_s':300,'queue_dropped':0,'radar_uart_bytes':1536,'radar_uart_age_ms':10,'radar_uart_hex':'f4f3f2f1','sensor_age_ms':10}
    if 40<=seq<=44:data['temperature_c']=None;data['bme688_ok']=False
    m={'type':'telemetry','v':1,'boot_id':'1122334455667788','seq':seq,'captured_at':epoch,'reason':'requested' if request else 'periodic','data':data};seq+=1
    if request:m['request_id']=request
    return m
for i in range(96):
    sock.send(json.dumps(sample(int(time.time())-(95-i)*300)))
    assert json.loads(sock.recv())['type']=='telemetry_ack'
stop=threading.Event()
def device_loop():
    sock.settimeout(.5);ping_at=time.time()+20
    while not stop.is_set():
        try:
            m=json.loads(sock.recv())
            if m['type']=='command':
                sock.send(json.dumps({'type':'command_ack','request_id':m['request_id']}));sock.send(json.dumps(sample(int(time.time()),m['request_id'])))
            elif m['type']=='config':sock.send(json.dumps({'type':'config_ack','version':m['config_version']}))
        except websocket.WebSocketTimeoutException:pass
        except Exception:break
        if time.time()>ping_at:sock.send(json.dumps({'type':'ping'}));ping_at=time.time()+20
t=threading.Thread(target=device_loop,daemon=True);t.start()
images=ROOT/'screenshots';images.mkdir(exist_ok=True);checks=[]
def passed(name):checks.append(name);print('PASS',name,flush=True)
with sync_playwright() as p:
    browser=p.chromium.launch()
    context=browser.new_context(viewport={'width':1440,'height':1080},locale='zh-CN',timezone_id='Asia/Shanghai')
    page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(URL);page.locator('[name=password]').fill(PASSWORD);page.get_by_role('button',name='进入监测站').click()
    page.locator('#device').select_option(did)
    page.wait_for_selector('#trend-chart[data-ready=true]')
    expect(page.locator('#stream-status')).to_have_text('实时通道已连接')
    assert page.locator('#device-status').inner_text()=='设备在线';assert page.locator('#history tr').count()==50
    passed('Real login, online device, chart and paginated history render')
    canvas_pixels=page.locator('#trend-chart').evaluate("c=>{const a=c.getContext('2d').getImageData(0,0,c.width,c.height).data;let n=0;for(let i=3;i<a.length;i+=4)if(a[i])n++;return n}")
    assert canvas_pixels>1000;passed('Chart canvas contains actual plotted pixels')
    page.screenshot(path=str(images/'dashboard_desktop.png'),full_page=True)
    page.get_by_role('button',name='立即采样',exact=True).click();expect(page.locator('#commands')).to_contain_text('已取得新读数');passed('Browser button triggers and displays completed device sampling')
    page.locator('#metric').select_option('mq_adc_mv');page.locator('#hours').select_option('168');assert 'metric=mq_adc_mv' in page.url and 'hours=168' in page.url;passed('Metric and time filters persist in URL')
    page.get_by_role('button',name='下一页').click();expect(page.locator('#page-info')).to_contain_text('第 2');passed('Table paging works')
    with page.expect_download() as dl:page.locator('#export').click()
    assert dl.value.suggested_filename=='sensor-data.csv';passed('CSV export downloads from real database')
    page.get_by_role('button',name='配置',exact=True).click();page.locator('#site-settings [name=host]').fill('smtp.user-input.example');page.locator('#site-settings [name=password]').fill('test_edit_buffer');page.locator('#device-config [name=report_interval_s]').fill('420')
    page.wait_for_timeout(16500)
    assert page.locator('#site-settings [name=password]').input_value()=='test_edit_buffer';assert page.locator('#device-config [name=report_interval_s]').input_value()=='420';passed('Background refresh preserves unsaved settings and passwords')
    page.locator('#site-settings [name=password]').fill('');page.screenshot(path=str(images/'settings_desktop.png'),full_page=True)
    page.get_by_role('button',name='监测',exact=True).click();page.set_viewport_size({'width':390,'height':844});page.wait_for_timeout(700);page.screenshot(path=str(images/'dashboard_mobile.png'),full_page=True)
    import struct
    assert struct.unpack('>I',(images/'dashboard_mobile.png').read_bytes()[16:20])[0]==390
    assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth+1');passed('Mobile portrait has no document overflow')
    page.get_by_role('button',name='配置',exact=True).click();page.screenshot(path=str(images/'settings_mobile.png'),full_page=True);assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth+1');passed('Mobile configuration controls fit viewport')
    cookies=context.cookies();remember=[c for c in cookies if c['name']=='sensor_remember'];assert remember[0]['httpOnly']
    second=browser.new_context();second.add_cookies(remember);p2=second.new_page();p2.goto(URL);p2.wait_for_selector('#sample-now');passed('Browser restart simulation retains login without password')
    assert not errors,errors;passed('No browser JavaScript runtime errors')
    browser.close()
stop.set();t.join(timeout=2);sock.close()
report={'result':'PASS','test_count':len(checks),'checks':checks,'data':'simulated sensor values through real WebSocket/PHP/PostgreSQL; not physical readings','screenshots':['dashboard_desktop.png','dashboard_mobile.png','settings_desktop.png','settings_mobile.png']}
(ROOT/'test_results/browser.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
