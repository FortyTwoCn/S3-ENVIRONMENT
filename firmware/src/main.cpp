#include <Arduino.h>
#include <Wire.h>
#include <WiFi.h>
#include <WebServer.h>
#include <WebSocketsClient.h>
#include <Preferences.h>
#include <ArduinoJson.h>
#include <BH1750.h>
#include <Adafruit_BME680.h>
#include <esp_system.h>
#include <esp_heap_caps.h>
#include <utility>
#include <time.h>
#include "root_ca.h"

// Carrier R1.1: do not substitute another ESP32 board's pin order.
constexpr int SDA_PIN=8, SCL_PIN=9, LD_RX_PIN=17, LD_TX_PIN=18;
constexpr int LD_OUT_PIN=16, MQ_ADC_PIN=4, MQ_DO_PIN=5, CONFIG_BUTTON=0;
constexpr float MQ_RTOP=6800, MQ_RBOTTOM=7500, MQ_RLOAD=100000;
constexpr float MQ_RLOW=1.0f/(1.0f/MQ_RBOTTOM+1.0f/MQ_RLOAD);
constexpr float MQ_AO_SCALE=(MQ_RTOP+MQ_RLOW)/MQ_RLOW;
constexpr char VERSION[]="carrier-network-1.0.2";
constexpr size_t QUEUE_SIZE=256; // bounded RAM, not flash: avoids continuous NVS wear

Preferences prefs;
WebServer portal(80);
WebSocketsClient ws;
BH1750 light;
Adafruit_BME680 bme(&Wire);
HardwareSerial radar(1);

struct ConnectionConfig { String ssid,password,host,path,token,ca; uint16_t port=443; bool tls=true; } cfg;
struct Policy {
  uint32_t interval=300, warmup=180, debounce=3, clear=10;
  bool mqEnabled=false; String mode="digital";
  int threshold=2000,hysteresis=100,alarmLevel=1;
} policy;
struct Sensors {
  float lux=NAN,temp=NAN,humidity=NAN,pressure=NAN,gas=NAN,adcMv=0,aoV=0;
  uint16_t adcRaw=0; bool gpio=false,presence=false,lightOk=false,bmeOk=false;
  bool ready=false,smoke=false;
  uint32_t sampledAt=0;
} sensors;
struct QueuedSample {
  char* payload=nullptr; uint32_t seq=0,capturedMs=0; bool event=false;
  QueuedSample()=default;
  QueuedSample(const QueuedSample&)=delete;
  QueuedSample& operator=(const QueuedSample&)=delete;
  QueuedSample(QueuedSample&& other) noexcept { *this=std::move(other); }
  QueuedSample& operator=(QueuedSample&& other) noexcept {
    if(this!=&other){free(payload);payload=other.payload;seq=other.seq;capturedMs=other.capturedMs;event=other.event;other.payload=nullptr;}
    return *this;
  }
  void reset(){free(payload);payload=nullptr;}
  ~QueuedSample(){free(payload);}
};
QueuedSample queueItems[QUEUE_SIZE]; size_t queueCount=0;
String bootId,apPassword,portalCsrf,pendingRequest;
uint32_t sequence=0,queueDropped=0,bootMs=0,nextReport=0,nextSense=0,nextWifi=0,nextWs=0,nextPing=0;
uint32_t mqEnabledAt=0,conditionSince=0,buttonSince=0,bmeReadyAt=0,lastUartAt=0,uartTotal=0;
uint32_t wifiBackoff=1000,wsBackoff=1000,ackDeadline=0;
bool portalActive=false,wsStarted=false,wsAuthenticated=false,inFlight=false;
bool bmePresent=false,lightPresent=false,conditionInitialized=false,lastCondition=false;
uint32_t sentSeq=0; String uartHex;
String serialLine;
volatile uint8_t wifiDisconnectReason=0;
wl_status_t lastWifiStatus=WL_NO_SHIELD;
bool wifiScanActive=false;
uint32_t nextTimeWarning=0;

void printNetworkStatus(){
  Serial.printf("Network: SSID=%s status=%d reason=%u password_bytes=%u token_configured=%d TLS=%d host=%s port=%u\n",cfg.ssid.c_str(),static_cast<int>(WiFi.status()),wifiDisconnectReason,static_cast<unsigned>(cfg.password.length()),cfg.token.length()==64,cfg.tls,cfg.host.c_str(),cfg.port);
  if(WiFi.status()==WL_CONNECTED){
    Serial.printf("Wi-Fi IP=%s gateway=%s DNS=%s RSSI=%d channel=%d time_valid=%d WS_authenticated=%d\n",WiFi.localIP().toString().c_str(),WiFi.gatewayIP().toString().c_str(),WiFi.dnsIP().toString().c_str(),WiFi.RSSI(),WiFi.channel(),time(nullptr)>=1700000000,wsAuthenticated);
  }
}

void printSensorStatus(){
  Serial.printf("Sensors: BH1750_present=%d read_ok=%d BME688_present=%d read_ok=%d MQ_enabled=%d radar_uart_bytes=%lu\n",lightPresent,sensors.lightOk,bmePresent,sensors.bmeOk,policy.mqEnabled,static_cast<unsigned long>(uartTotal));
  Serial.printf("I2C: SDA=GPIO%d level=%d SCL=GPIO%d level=%d\n",SDA_PIN,digitalRead(SDA_PIN),SCL_PIN,digitalRead(SCL_PIN));
  if(sensors.lightOk)Serial.printf("Light lux=%.2f\n",sensors.lux);
  if(sensors.bmeOk)Serial.printf("BME: temperature=%.2f C humidity=%.2f %% pressure=%.2f hPa gas=%.0f ohm\n",sensors.temp,sensors.humidity,sensors.pressure,sensors.gas);
  if(!policy.mqEnabled)Serial.println("MQ disabled: floating ADC/GPIO values are not uploaded");
}

void scanI2c(){
  Serial.printf("I2C scan start: SDA=GPIO%d SCL=GPIO%d levels=%d/%d\n",SDA_PIN,SCL_PIN,digitalRead(SDA_PIN),digitalRead(SCL_PIN));
  if(digitalRead(SDA_PIN)==LOW||digitalRead(SCL_PIN)==LOW){Serial.println("I2C scan skipped: bus held LOW; check power, GND, SDA/SCL and shorts");return;}
  int found=0,errors=0;
  for(uint8_t address=8;address<120;address++){
    Wire.beginTransmission(address);const uint8_t error=Wire.endTransmission();
    if(error==0){
      found++;Serial.printf("I2C ACK address=0x%02X\n",address);
      if(address==0x76||address==0x77){
        Wire.beginTransmission(address);Wire.write(0xD0);
        if(Wire.endTransmission(false)==0&&Wire.requestFrom(address,static_cast<uint8_t>(1))==1)Serial.printf("BME chip_id=0x%02X (BME68x expected 0x61)\n",Wire.read());
      }
    }else if(error!=2)errors++;
    delay(1);
  }
  Serial.printf("I2C scan complete: found=%d bus_errors=%d expected BH1750=0x23/0x5C BME688=0x76/0x77\n",found,errors);
}

void initializeI2cSensors(){
  lightPresent=light.begin(BH1750::CONTINUOUS_HIGH_RES_MODE,0x23,&Wire);if(!lightPresent)lightPresent=light.begin(BH1750::CONTINUOUS_HIGH_RES_MODE,0x5C,&Wire);
  bmePresent=bme.begin(0x76);if(!bmePresent)bmePresent=bme.begin(0x77);
  sensors.lightOk=sensors.bmeOk=false;sensors.lux=sensors.temp=sensors.humidity=sensors.pressure=sensors.gas=NAN;
  if(bmePresent){bme.setTemperatureOversampling(BME680_OS_8X);bme.setHumidityOversampling(BME680_OS_2X);bme.setPressureOversampling(BME680_OS_4X);bme.setIIRFilterSize(BME680_FILTER_SIZE_3);bme.setGasHeater(320,150);}
  Serial.printf("BH1750=%s BME688=%s LD UART=256000 8N1\n",lightPresent?"found":"missing",bmePresent?"found":"missing");
}

bool due(uint32_t now,uint32_t deadline){ return static_cast<int32_t>(now-deadline)>=0; }
String randomHex(size_t count){ String s; s.reserve(count*2); for(size_t i=0;i<count;i++){char h[3];snprintf(h,sizeof(h),"%02x",static_cast<uint8_t>(esp_random()));s+=h;} return s; }
String escapeHtml(String s){s.replace("&","&amp;");s.replace("<","&lt;");s.replace(">","&gt;");s.replace("\"","&quot;");s.replace("'","&#39;");return s;}
void applyPolicy(JsonVariantConst c,bool persist){
  const bool wasEnabled=policy.mqEnabled;
  policy.interval=constrain(c["report_interval_s"]|300,30,3600);
  policy.warmup=constrain(c["mq_warmup_s"]|180,0,86400);
  policy.debounce=constrain(c["smoke_debounce_s"]|3,1,60);
  policy.clear=constrain(c["smoke_clear_s"]|10,1,300);
  policy.threshold=constrain(c["mq_adc_threshold_mv"]|2000,1,2850);
  policy.hysteresis=constrain(c["mq_adc_hysteresis_mv"]|100,0,500);
  policy.alarmLevel=constrain(c["mq_alarm_gpio_level"]|1,0,1);
  policy.mqEnabled=c["mq_enabled"]|false;
  policy.mode=c["mq_mode"].as<String>(); if(policy.mode!="analog"&&policy.mode!="either")policy.mode="digital";
  if(policy.mqEnabled&&!wasEnabled)mqEnabledAt=millis();
  conditionInitialized=false;
  if(!policy.mqEnabled){sensors.ready=false;sensors.smoke=false;}
  nextReport=millis()+policy.interval*1000;
  if(persist){String text;serializeJson(c,text);if(text!=prefs.getString("policy",""))prefs.putString("policy",text);}
  Serial.printf("Policy: interval=%lus MQ=%d warmup=%lus\n",static_cast<unsigned long>(policy.interval),policy.mqEnabled,static_cast<unsigned long>(policy.warmup));
}
void loadConnection(){
  cfg.ssid=prefs.getString("ssid","");cfg.password=prefs.getString("wifi_pass","");
  cfg.host=prefs.getString("host","");cfg.path=prefs.getString("path","/ws");cfg.port=prefs.getUShort("port",443);
  cfg.token=prefs.getString("token","");cfg.tls=prefs.getBool("tls",true);cfg.ca=prefs.getString("ca","");
  DynamicJsonDocument doc(1024);if(!deserializeJson(doc,prefs.getString("policy","{}")))applyPolicy(doc.as<JsonVariantConst>(),false);
}
bool configComplete(){return cfg.ssid.length()>0&&cfg.host.length()>0&&cfg.token.length()==64;}
bool portalClient(){return portal.client().remoteIP()[0]==192&&portal.client().remoteIP()[1]==168&&portal.client().remoteIP()[2]==4;}
void portalPage(){
  if(!portalClient()){portal.send(403,"text/plain","AP clients only");return;}
  String html="<!doctype html><html lang='zh-CN'><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>ESP32-S3 配网</title><style>body{font-family:system-ui;max-width:560px;margin:24px auto;padding:16px;color:#18333c}label{display:block;margin:16px 0}input,textarea{box-sizing:border-box;display:block;width:100%;padding:10px;margin-top:6px}button{padding:12px;background:#087b72;color:white;border:0}small{color:#566}</style><h1>ESP32-S3 配网</h1><p>填写 Wi-Fi 和监测网站的设备接入参数。</p><form method='post' action='/save'><input type='hidden' name='csrf' value='"+portalCsrf+"'>";
  html+="<label>Wi-Fi 名称<input name='ssid' maxlength='32' required value='"+escapeHtml(cfg.ssid)+"'></label><label>Wi-Fi 密码<input type='password' name='password' maxlength='63' placeholder='留空保留当前密码；开放网络勾选下方'></label><label><input type='checkbox' name='open' style='width:auto;display:inline'> 使用开放 Wi-Fi</label>";
  html+="<label>网站主机（仅域名 / IP，不含 https://）<input name='host' maxlength='253' required value='"+escapeHtml(cfg.host)+"'></label><label>WebSocket 端口<input type='number' name='port' min='1' max='65535' value='"+String(cfg.port)+"' required></label><label>WebSocket 路径<input name='path' maxlength='100' value='"+escapeHtml(cfg.path)+"' required></label>";
  html+="<label>设备令牌<input name='token' maxlength='64' minlength='64' type='password' placeholder='首次必填；留空保留当前令牌'></label><label><input type='checkbox' name='tls' style='width:auto;display:inline' "+String(cfg.tls?"checked":"")+"> 启用 WSS / TLS（公网必须启用）</label><label>自定义根 CA 证书（可选）<textarea name='ca' maxlength='3500' rows='4' placeholder='留空使用内置 ISRG Root X1；非 Let’s Encrypt 证书需粘贴对应根 CA'>"+escapeHtml(cfg.ca)+"</textarea></label><small>根 CA 用于验证服务器；不会跳过证书验证。修改后自动重启并连接。</small><p><button type='submit'>保存并连接</button></p></form></html>";
  portal.sendHeader("Cache-Control","no-store");portal.send(200,"text/html; charset=utf-8",html);
}
void portalSave(){
  if(!portalClient()||portal.arg("csrf")!=portalCsrf){portal.send(403,"text/plain","Invalid request");return;}
  String ssid=portal.arg("ssid"),pass=portal.arg("password"),host=portal.arg("host"),token=portal.arg("token"),path=portal.arg("path"),ca=portal.arg("ca");
  const int port=portal.arg("port").toInt();
  if(ssid.length()<1||ssid.length()>32||host.length()<1||host.length()>253||host.indexOf('/')>=0||host.indexOf(' ')>=0||port<1||port>65535||!path.startsWith("/")||path.length()>100||ca.length()>3500){portal.send(422,"text/plain","Invalid fields");return;}
  if(!token.length())token=cfg.token;
  bool validToken=token.length()==64;for(size_t i=0;i<token.length();i++)validToken=validToken&&isxdigit(token[i]);
  if(!validToken){portal.send(422,"text/plain","64-character token required");return;}
  if(portal.hasArg("open"))pass="";else if(!pass.length())pass=cfg.password;
  if(pass.length()>63 || (pass.length()>0&&pass.length()<8)){portal.send(422,"text/plain","Wi-Fi password must have 8-63 characters or be explicitly open");return;}
  prefs.putString("ssid",ssid);prefs.putString("wifi_pass",pass);prefs.putString("host",host);prefs.putString("path",path);prefs.putUShort("port",port);prefs.putString("token",token);prefs.putBool("tls",portal.hasArg("tls"));prefs.putString("ca",ca);
  portal.send(200,"text/html; charset=utf-8","<meta charset='utf-8'><h2>已保存，设备正在重启并连接。</h2><p>可断开配网 Wi-Fi，返回监测网站。</p>");delay(700);ESP.restart();
}
void startPortal(){
  if(portalActive)return;ws.disconnect();wsAuthenticated=false;wsStarted=false;
  WiFi.disconnect();WiFi.mode(WIFI_AP);String id=String(static_cast<uint32_t>(ESP.getEfuseMac()),HEX);String ssid="SensorCarrier-"+id;
  apPassword=randomHex(6);portalCsrf=randomHex(16);
  WiFi.softAP(ssid.c_str(),apPassword.c_str());portalActive=true;
  portal.on("/",HTTP_GET,portalPage);portal.on("/save",HTTP_POST,portalSave);portal.onNotFound([](){portal.sendHeader("Location","/");portal.send(302,"text/plain","");});portal.begin();
  Serial.printf("\nSETUP AP: %s\nTemporary AP password: %s\nOpen http://192.168.4.1\n",ssid.c_str(),apPassword.c_str());
}
void setNumber(JsonObject obj,const char* key,float value){if(isfinite(value))obj[key]=value;else obj[key]=nullptr;}
void queueTelemetry(const char* reason,const String& requestId=""){
  const bool event=strcmp(reason,"alarm")==0||strcmp(reason,"recovered")==0;
  if(queueCount>=QUEUE_SIZE){
    // Drop oldest ordinary record first, preserving event records where possible.
    size_t removeAt=0;for(size_t i=0;i<queueCount;i++)if(!queueItems[i].event){removeAt=i;break;}
    if(inFlight&&removeAt==0&&queueCount>1)removeAt=1;
    for(size_t i=removeAt+1;i<queueCount;i++)queueItems[i-1]=std::move(queueItems[i]);queueCount--;queueDropped++;
  }
  DynamicJsonDocument doc(4096);doc["v"]=1;doc["type"]="telemetry";doc["boot_id"]=bootId;doc["seq"]=sequence++;
  // Timestamp is the sensor measurement time, not reconnect/upload time.
  const time_t epoch=time(nullptr);if(epoch>=1700000000)doc["captured_at"]=static_cast<uint32_t>(epoch)-((millis()-sensors.sampledAt)/1000);else doc["captured_at"]=nullptr;
  doc["reason"]=reason;if(requestId.length())doc["request_id"]=requestId;
  JsonObject data=doc.createNestedObject("data");
  setNumber(data,"light_lux",sensors.lux);setNumber(data,"temperature_c",sensors.temp);setNumber(data,"humidity_pct",sensors.humidity);setNumber(data,"pressure_hpa",sensors.pressure);setNumber(data,"gas_ohm",sensors.gas);
  data["bh1750_ok"]=sensors.lightOk;data["bme688_ok"]=sensors.bmeOk;
  const bool radarOk=uartTotal>0&&millis()-lastUartAt<5000;data["radar_ok"]=radarOk;
  if(radarOk)data["radar_presence"]=sensors.presence;else data["radar_presence"]=nullptr;
  data["radar_uart_bytes"]=uartTotal;if(uartTotal)data["radar_uart_age_ms"]=millis()-lastUartAt;else data["radar_uart_age_ms"]=nullptr;data["radar_uart_hex"]=uartHex;
  data["mq_enabled"]=policy.mqEnabled;
  if(policy.mqEnabled){data["mq_adc_raw"]=sensors.adcRaw;data["mq_adc_mv"]=sensors.adcMv;data["mq_ao_v"]=sensors.aoV;data["mq_gpio"]=sensors.gpio;}
  else{data["mq_adc_raw"]=nullptr;data["mq_adc_mv"]=nullptr;data["mq_ao_v"]=nullptr;data["mq_gpio"]=nullptr;}
  data["mq_ready"]=sensors.ready;if(sensors.ready)data["mq_smoke"]=sensors.smoke;else data["mq_smoke"]=nullptr;
  data["rssi_dbm"]=WiFi.status()==WL_CONNECTED?WiFi.RSSI():-127;data["uptime_s"]=(millis()-bootMs)/1000;data["queue_dropped"]=queueDropped;data["sensor_age_ms"]=millis()-sensors.sampledAt;
  const size_t bytes=measureJson(doc)+1;
  char* buffer=static_cast<char*>(heap_caps_malloc(bytes,MALLOC_CAP_SPIRAM|MALLOC_CAP_8BIT));
  if(!buffer&&ESP.getFreeHeap()>bytes+96000)buffer=static_cast<char*>(malloc(bytes));
  if(!buffer){queueDropped++;Serial.println("Queue allocation failed; check N16R8 PSRAM configuration");return;}
  auto &item=queueItems[queueCount++];item.seq=doc["seq"].as<uint32_t>();item.capturedMs=sensors.sampledAt;item.event=event;item.reset();item.payload=buffer;serializeJson(doc,item.payload,bytes);
  Serial.printf("Sample %lu %s: lux=%.1f T=%.2f RH=%.1f MQ_enabled=%d MQ=%.0fmV smoke=%d ready=%d queue=%u\n",static_cast<unsigned long>(item.seq),reason,sensors.lux,sensors.temp,sensors.humidity,policy.mqEnabled,policy.mqEnabled?sensors.adcMv:NAN,sensors.smoke,sensors.ready,static_cast<unsigned>(queueCount));
  if((event||requestId.length())&&queueCount>1){
    // Immediate requests and alarms bypass ordinary backlog; preserve current in-flight ACK.
    const size_t at=inFlight?1:0;QueuedSample urgent=std::move(queueItems[queueCount-1]);
    for(size_t i=queueCount-1;i>at;i--)queueItems[i]=std::move(queueItems[i-1]);queueItems[at]=std::move(urgent);
  }
}
void receiveRadar(){
  uint8_t recent[32];size_t count=0;
  for(int budget=0;radar.available()&&budget<1024;budget++){
    uint8_t value=static_cast<uint8_t>(radar.read());recent[count++%32]=value;uartTotal++;lastUartAt=millis();
  }
  if(count){uartHex="";size_t n=min(count,static_cast<size_t>(32));size_t start=count>32?count%32:0;for(size_t i=0;i<n;i++){char h[3];snprintf(h,3,"%02x",recent[(start+i)%32]);uartHex+=h;}}
}
void evaluateSmoke(){
  const uint32_t now=millis();sensors.ready=policy.mqEnabled&&(now-mqEnabledAt)/1000>=policy.warmup;
  if(!sensors.ready){conditionInitialized=false;return;}
  const bool digitalAlarm=static_cast<int>(sensors.gpio)==policy.alarmLevel;
  const bool analogAlarm=sensors.adcMv>=(sensors.smoke?max(0,policy.threshold-policy.hysteresis):policy.threshold);
  const bool condition=policy.mode=="analog"?analogAlarm:policy.mode=="either"?(digitalAlarm||analogAlarm):digitalAlarm;
  if(!conditionInitialized||condition!=lastCondition){conditionSince=now;lastCondition=condition;conditionInitialized=true;}
  const uint32_t wait=(condition?policy.debounce:policy.clear)*1000;
  if(condition!=sensors.smoke&&now-conditionSince>=wait){sensors.smoke=condition;queueTelemetry(condition?"alarm":"recovered");}
}
void finishSensorCycle(){
  sensors.sampledAt=millis();sensors.presence=digitalRead(LD_OUT_PIN);sensors.gpio=digitalRead(MQ_DO_PIN);
  uint32_t raw=0,mv=0;for(int i=0;i<16;i++){raw+=analogRead(MQ_ADC_PIN);mv+=analogReadMilliVolts(MQ_ADC_PIN);}
  sensors.adcRaw=raw/16;sensors.adcMv=mv/16.0f;sensors.aoV=sensors.adcMv*MQ_AO_SCALE/1000;
  evaluateSmoke();
  if(pendingRequest.length()){queueTelemetry("requested",pendingRequest);pendingRequest="";}
}
void pollSensors(){
  const uint32_t now=millis();
  if(bmeReadyAt&&due(now,bmeReadyAt)){
    const bool ok=bme.endReading();bmeReadyAt=0;sensors.bmeOk=ok;
    if(ok){sensors.temp=bme.temperature;sensors.humidity=bme.humidity;sensors.pressure=bme.pressure/100.0f;sensors.gas=bme.gas_resistance;}
    else sensors.temp=sensors.humidity=sensors.pressure=sensors.gas=NAN;
    finishSensorCycle();
  }
  if(due(now,nextSense)&&!bmeReadyAt){
    nextSense=now+2000;
    if(lightPresent){sensors.lux=light.readLightLevel();sensors.lightOk=isfinite(sensors.lux)&&sensors.lux>=0;if(!sensors.lightOk)sensors.lux=NAN;}
    if(bmePresent){bmeReadyAt=bme.beginReading();if(!bmeReadyAt){sensors.bmeOk=false;sensors.temp=sensors.humidity=sensors.pressure=sensors.gas=NAN;finishSensorCycle();}}
    else finishSensorCycle();
  }
}
void wsEvent(WStype_t type,uint8_t* payload,size_t length){
  if(type==WStype_CONNECTED){
    DynamicJsonDocument hello(512);hello["type"]="hello";hello["v"]=1;hello["role"]="device";hello["token"]=cfg.token;hello["firmware"]=VERSION;String message;serializeJson(hello,message);ws.sendTXT(message);Serial.println("WS connected; authenticating");
  } else if(type==WStype_DISCONNECTED){
    wsAuthenticated=false;inFlight=false;
    const uint32_t retry=wsBackoff+(esp_random()%800);nextWs=millis()+retry;
    // Keep calling the library loop: it owns socket cleanup and reconnect timing.
    // Re-running begin() from this callback could discard an active socket.
    ws.setReconnectInterval(retry);wsBackoff=min(wsBackoff*2,static_cast<uint32_t>(60000));Serial.println("WS disconnected; retry scheduled");
  } else if(type==WStype_TEXT){
    DynamicJsonDocument doc(4096);if(deserializeJson(doc,payload,length))return;
    String kind=doc["type"].as<String>();
    if(kind=="welcome"){
      wsAuthenticated=true;wsBackoff=1000;ws.setReconnectInterval(1000);nextPing=millis()+25000;inFlight=false;applyPolicy(doc["config"],true);if(sequence==0)nextReport=millis()+1000;Serial.println("WS authenticated");
    }else if(kind=="config"){
      applyPolicy(doc["config"],true);DynamicJsonDocument ack(128);ack["type"]="config_ack";ack["version"]=doc["config_version"];String msg;serializeJson(ack,msg);ws.sendTXT(msg);
    }else if(kind=="telemetry_ack"){
      if(queueCount&&doc["boot_id"].as<String>()==bootId&&doc["seq"].as<uint32_t>()==queueItems[0].seq){Serial.printf("Telemetry acknowledged: seq=%lu\n",static_cast<unsigned long>(queueItems[0].seq));for(size_t i=1;i<queueCount;i++)queueItems[i-1]=std::move(queueItems[i]);queueCount--;queueItems[queueCount].reset();inFlight=false;}
    }else if(kind=="command"&&doc["command"]=="sample_now"){
      const String id=doc["request_id"].as<String>();if(id.length()!=36)return;
      // A command requests a NEW completed sensor cycle, never only cached values.
      pendingRequest=id;nextSense=millis();DynamicJsonDocument ack(128);ack["type"]="command_ack";ack["request_id"]=id;String msg;serializeJson(ack,msg);ws.sendTXT(msg);
    }else if(kind=="error"){
      const String error=doc["error"].as<String>();Serial.printf("Server error: %s\n",error.c_str());
      if(error!="server_error"&&inFlight&&queueCount){for(size_t i=1;i<queueCount;i++)queueItems[i-1]=std::move(queueItems[i]);queueCount--;queueItems[queueCount].reset();queueDropped++;inFlight=false;}
    }
  }
}
void networkLoop(){
  if(portalActive){portal.handleClient();return;}
  const uint32_t now=millis();
  if(wifiScanActive){
    const int count=WiFi.scanComplete();
    if(count==WIFI_SCAN_RUNNING)return;
    int matches=0;for(int i=0;i<count;i++)if(WiFi.SSID(i)==cfg.ssid){matches++;Serial.printf("Wi-Fi target visible: channel=%d RSSI=%d security=%d\n",WiFi.channel(i),WiFi.RSSI(i),static_cast<int>(WiFi.encryptionType(i)));}
    Serial.printf("Wi-Fi scan complete: networks=%d target_matches=%d\n",count,matches);
    WiFi.scanDelete();wifiScanActive=false;nextWifi=now;
  }
  const wl_status_t status=WiFi.status();
  if(status!=lastWifiStatus){lastWifiStatus=status;printNetworkStatus();}
  if(WiFi.status()!=WL_CONNECTED){
    if(wsAuthenticated||wsStarted){ws.disconnect();wsStarted=false;wsAuthenticated=false;inFlight=false;}
    if(due(now,nextWifi)){WiFi.disconnect();WiFi.begin(cfg.ssid.c_str(),cfg.password.c_str());nextWifi=now+max(static_cast<uint32_t>(15000),wifiBackoff)+(esp_random()%1000);wifiBackoff=min(wifiBackoff*2,static_cast<uint32_t>(60000));Serial.println("Wi-Fi connection attempt");}
    return;
  }
  wifiBackoff=1000;
  // Valid time is required for CA certificate checks. SNTP continues in background.
  if(cfg.tls&&time(nullptr)<1700000000){if(due(now,nextTimeWarning)){Serial.println("Waiting for NTP time before verified TLS connection");nextTimeWarning=now+15000;}return;}
  if(!wsStarted&&due(now,nextWs)){
    wsStarted=true;
    ws.setReconnectInterval(1000);ws.onEvent(wsEvent);
    if(cfg.tls){const char* ca=cfg.ca.length()?cfg.ca.c_str():DEFAULT_ROOT_CA;ws.beginSslWithCA(cfg.host.c_str(),cfg.port,cfg.path.c_str(),ca,"");}
    else ws.begin(cfg.host.c_str(),cfg.port,cfg.path.c_str(),"");
  }
  if(wsStarted)ws.loop();
  if(!wsAuthenticated)return;
  if(due(now,nextPing)){ws.sendTXT("{\"type\":\"ping\"}");nextPing=now+25000;}
  if(inFlight&&due(now,ackDeadline)){inFlight=false;}
  if(queueCount&&!inFlight){
    DynamicJsonDocument message(4096);deserializeJson(message,queueItems[0].payload);
    message["queue_age_s"]=(millis()-queueItems[0].capturedMs)/1000;
    String payload;serializeJson(message,payload);
    if(ws.sendTXT(payload)){inFlight=true;sentSeq=queueItems[0].seq;ackDeadline=now+10000;}
  }
}
void configurationTrigger(){
  const uint32_t now=millis();
  if(digitalRead(CONFIG_BUTTON)==LOW){if(!buttonSince)buttonSince=now;if(now-buttonSince>5000)startPortal();}else buttonSince=0;
  while(Serial.available()){char c=Serial.read();if(c=='\n'||c=='\r'){serialLine.trim();if(serialLine=="CONFIG")startPortal();else if(serialLine=="STATUS"){printNetworkStatus();printSensorStatus();}else if(serialLine=="I2C_SCAN")scanI2c();else if(serialLine=="SENSOR_RETRY"){if(bmeReadyAt)Serial.println("Sensor retry deferred: reading in progress; retry command shortly");else{initializeI2cSensors();nextSense=millis();}}else if(serialLine=="REBOOT")ESP.restart();else if(serialLine=="WIFI_SCAN"&&!portalActive&&!wifiScanActive){WiFi.scanDelete();wifiScanActive=WiFi.scanNetworks(true)>=WIFI_SCAN_RUNNING;Serial.println("Wi-Fi diagnostic scan started");}serialLine="";}else if(serialLine.length()<40)serialLine+=c;}
}
void setup(){
  Serial.begin(115200);delay(800);Serial.println("\nESP32-S3 Sensor Carrier Network Firmware");
  Serial.printf("Firmware %s | flash=%u PSRAM=%u\n",VERSION,ESP.getFlashChipSize(),ESP.getPsramSize());
  Serial.println("MQ DO is inverted: typical alarm = GPIO5 HIGH. Serial commands: CONFIG, STATUS, WIFI_SCAN, I2C_SCAN, SENSOR_RETRY, REBOOT. Hold BOOT 5s after boot to configure.");
  bootMs=millis();bootId=randomHex(8);prefs.begin("sensor_net",false);loadConnection();mqEnabledAt=millis();
  pinMode(CONFIG_BUTTON,INPUT_PULLUP);pinMode(LD_OUT_PIN,INPUT);pinMode(MQ_DO_PIN,INPUT);pinMode(MQ_ADC_PIN,INPUT);
  analogReadResolution(12);analogSetPinAttenuation(MQ_ADC_PIN,ADC_11db);
  radar.setRxBufferSize(2048);radar.begin(256000,SERIAL_8N1,LD_RX_PIN,LD_TX_PIN);
  Wire.begin(SDA_PIN,SCL_PIN);Wire.setClock(100000);Wire.setTimeOut(50);
  initializeI2cSensors();scanI2c();
  WiFi.onEvent([](WiFiEvent_t event,WiFiEventInfo_t info){if(event==ARDUINO_EVENT_WIFI_STA_DISCONNECTED){wifiDisconnectReason=info.wifi_sta_disconnected.reason;Serial.printf("Wi-Fi disconnected: reason=%u\n",wifiDisconnectReason);}});
  if(!configComplete())startPortal();else{WiFi.mode(WIFI_STA);WiFi.setAutoReconnect(false);configTime(0,0,"pool.ntp.org","time.cloudflare.com","ntp.aliyun.com");nextWifi=millis();}
  nextSense=millis();nextReport=millis()+5000;
}
void loop(){
  receiveRadar();configurationTrigger();pollSensors();networkLoop();
  const uint32_t now=millis();
  if(due(now,nextReport)&&sensors.sampledAt&&!bmeReadyAt){queueTelemetry(sequence==0?"boot":"periodic");nextReport=now+policy.interval*1000;}
  delay(2);
}
