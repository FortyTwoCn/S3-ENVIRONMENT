#include <Arduino.h>
#include <Wire.h>
#include <BH1750.h>
#include <Adafruit_BME680.h>

constexpr int SDA_PIN=8, SCL_PIN=9, RADAR_RX=17, RADAR_TX=18;
constexpr int RADAR_OUT=16, MQ_ADC=4, MQ_DO=5;
// R4=6.8k, R5=7.5k, R15=100k after the isolation switch.
// Include R15 loading; U1's <=4.5 ohm on resistance is negligible here.
constexpr float R_TOP=6800.0f, R_BOTTOM=7500.0f, R_ADC=100000.0f;
constexpr float R_EFFECTIVE=1.0f/(1.0f/R_BOTTOM+1.0f/R_ADC);
constexpr float MQ_SCALE=(R_TOP+R_EFFECTIVE)/R_EFFECTIVE;
BH1750 light;
Adafruit_BME680 bme(&Wire);
HardwareSerial radar(1);
bool light_ok=false,bme_ok=false;
uint8_t uart_bytes[96]; size_t uart_count=0; uint32_t uart_total=0;
uint32_t next_report=0, next_uart=0;

void scanI2C(){
  Serial.println("I2C scan (default: BH1750=0x23, BME688=0x76):");
  for(uint8_t a=1;a<127;++a){
    Wire.beginTransmission(a);
    if(Wire.endTransmission()==0) Serial.printf("  Found 0x%02X\n",a);
  }
}
void receiveRadar(){
  while(radar.available()){
    const uint8_t v=static_cast<uint8_t>(radar.read());
    ++uart_total;
    if(uart_count<sizeof(uart_bytes))uart_bytes[uart_count++]=v;
  }
}
void setup(){
  Serial.begin(115200);
  const uint32_t until=millis()+2000;
  while(!Serial && static_cast<int32_t>(until-millis())>0)delay(10);
  Serial.println("\nESP32-S3 carrier R1 bring-up / mechanical verification required");
  Serial.printf("Flash: %u bytes; PSRAM: %u bytes\n",ESP.getFlashChipSize(),ESP.getPsramSize());
  if(ESP.getFlashChipSize()!=16u*1024u*1024u || ESP.getPsramSize()!=8u*1024u*1024u)
    Serial.println("CHECK: expected N16R8. Verify flash/PSRAM board settings and real module.");
  Serial.println("Connect sensors only with power OFF. USB/EXT power selection uses ONE shunt.");
  Serial.println("MQ DO is inverted by Q1: HIGH corresponds to raw DO LOW. Interpret only with SENSOR_5V present.");
  Wire.begin(SDA_PIN,SCL_PIN); Wire.setClock(100000);
  scanI2C();
  light_ok=light.begin(BH1750::CONTINUOUS_HIGH_RES_MODE,0x23,&Wire);
  if(!light_ok)light_ok=light.begin(BH1750::CONTINUOUS_HIGH_RES_MODE,0x5C,&Wire);
  bme_ok=bme.begin(0x76);
  if(!bme_ok)bme_ok=bme.begin(0x77);
  if(bme_ok){
    bme.setTemperatureOversampling(BME680_OS_8X);
    bme.setHumidityOversampling(BME680_OS_2X);
    bme.setPressureOversampling(BME680_OS_4X);
    bme.setIIRFilterSize(BME680_FILTER_SIZE_3);
    bme.setGasHeater(320,150);
  }
  pinMode(RADAR_OUT,INPUT); pinMode(MQ_DO,INPUT); pinMode(MQ_ADC,INPUT);
  analogReadResolution(12); analogSetPinAttenuation(MQ_ADC,ADC_11db);
  radar.setRxBufferSize(2048); radar.begin(256000,SERIAL_8N1,RADAR_RX,RADAR_TX);
  Serial.printf("BH1750: %s; BME688: %s; UART: 256000 8N1 RX17 TX18\n",light_ok?"OK":"missing",bme_ok?"OK":"missing");
  next_report=millis()+2000; next_uart=millis()+1000;
}
void loop(){
  receiveRadar();
  const uint32_t now=millis();
  if(static_cast<int32_t>(now-next_uart)>=0){
    next_uart=now+1000;
    Serial.printf("Radar UART Data (%u total bytes):",uart_total);
    for(size_t i=0;i<uart_count;++i)Serial.printf(" %02X",uart_bytes[i]);
    if(uart_count==0)Serial.print(" no data - check SENSOR_5V and TX->RX crossing");
    Serial.println();uart_count=0;
  }
  if(static_cast<int32_t>(now-next_report)>=0){
    next_report=now+2000;
    if(light_ok)Serial.printf("Light Lux: %.2f\n",light.readLightLevel());
    else Serial.println("Light Lux: module missing");
    if(bme_ok && bme.performReading()){
      Serial.printf("Temperature: %.2f C; Humidity: %.2f %%RH; Pressure: %.2f hPa; BME Gas: %.0f ohm\n",bme.temperature,bme.humidity,bme.pressure/100.0f,static_cast<float>(bme.gas_resistance));
    }else Serial.println("BME688: module missing / read failed");
    uint32_t raw=0,mv=0;
    for(int i=0;i<32;++i){raw+=analogRead(MQ_ADC);mv+=analogReadMilliVolts(MQ_ADC);delayMicroseconds(500);}
    const float adc_mv=mv/32.0f;
    Serial.printf("Radar Presence: %d; MQ ADC Raw: %lu; ADC: %.1f mV; MQ AO estimated: %.3f V; MQ Digital: %d (inverted)\n",digitalRead(RADAR_OUT),static_cast<unsigned long>(raw/32),adc_mv,adc_mv*MQ_SCALE/1000.0f,digitalRead(MQ_DO));
    if(adc_mv>2850)Serial.println("CHECK MQ AO / 5V supply: ADC approaching calibrated range limit.");
    Serial.println("Gas resistance and MQ voltage are raw tests, not calibrated IAQ/CO2/ppm.");
  }
  delay(2);
}
