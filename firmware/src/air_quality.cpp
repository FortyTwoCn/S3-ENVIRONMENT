#include "air_quality.h"
#include <bsec2.h>
#include <Preferences.h>

AirReadings air;
static Bsec2 algorithm;
static bool active=false, firstStateSaved=false;
static uint32_t stateSavedAt=0, errorLoggedAt=0;
static uint8_t iaqAccuracy=0;
static constexpr uint32_t STATE_PERIOD_MS=6UL*60*60*1000;
static constexpr char STATE_PROFILE[]="2610-33v3s4d";
// Bosch's generic IAQ profile, 3.3 V, LP (3 seconds), 4-day baseline history.
// BME688 supports this BME68x forced-mode IAQ profile. No gas classifier is loaded.
static const uint8_t configuration[]={
#include "config/bme680/bme680_iaq_33v_3s_4d/bsec_iaq.txt"
};

static void outputReady(const bme68xData input,const bsecOutputs outputs,const Bsec2 source){
  if(!outputs.nOutputs)return;
  for(uint8_t i=0;i<outputs.nOutputs;i++){
    const bsecData& value=outputs.output[i];
    // Accuracy 0 denotes unavailable/calibrating, not a validated estimate.
    const float estimate=value.accuracy>0?value.signal:NAN;
    switch(value.sensor_id){
      case BSEC_OUTPUT_RAW_TEMPERATURE:air.rawTemperature=value.signal;break;
      case BSEC_OUTPUT_RAW_HUMIDITY:air.rawHumidity=value.signal;break;
      case BSEC_OUTPUT_RAW_PRESSURE:air.pressure=value.signal;break; // library supplies hPa
      case BSEC_OUTPUT_RAW_GAS:air.gas=value.signal;break;
      case BSEC_OUTPUT_SENSOR_HEAT_COMPENSATED_TEMPERATURE:air.temperature=value.signal;break;
      case BSEC_OUTPUT_SENSOR_HEAT_COMPENSATED_HUMIDITY:air.humidity=value.signal;break;
      case BSEC_OUTPUT_IAQ:air.iaq=estimate;iaqAccuracy=value.accuracy;break;
      case BSEC_OUTPUT_STATIC_IAQ:air.staticIaq=estimate;break;
      case BSEC_OUTPUT_CO2_EQUIVALENT:air.eco2=estimate;break;
      case BSEC_OUTPUT_BREATH_VOC_EQUIVALENT:air.bvoc=estimate;break;
      case BSEC_OUTPUT_GAS_PERCENTAGE:air.gasPercentage=estimate;break;
      // Compensated gas is a processed resistance signal, not an accuracy-rated estimate.
      case BSEC_OUTPUT_COMPENSATED_GAS:air.compensatedGas=value.signal;break;
      default:break;
    }
  }
  air.measuredAt=millis();air.generation++;
  air.ok=isfinite(air.temperature)&&isfinite(air.humidity)&&isfinite(air.pressure)&&isfinite(air.gas);
}

bool beginAirQuality(TwoWire& wire){
  active=false;air=AirReadings{};iaqAccuracy=0;
  uint8_t address=0x76;
  bool present=algorithm.begin(address,wire);
  if(!present){address=0x77;present=algorithm.begin(address,wire);}
  if(!present||!algorithm.setConfig(configuration))return false;
  // Additional enclosure/ESP heat offset is intentionally zero until measured.
  // BSEC still compensates its own heater using the matching 3.3 V profile.
  algorithm.setTemperatureOffset(0.0f);
  Preferences state;
  if(state.begin("bsec-state",true)){
    uint8_t saved[BSEC_MAX_STATE_BLOB_SIZE];
    if(state.getString("profile","")==STATE_PROFILE&&state.getBytesLength("blob")==sizeof(saved)){
      state.getBytes("blob",saved,sizeof(saved));
      if(!algorithm.setState(saved)){
        // Reject invalid stored state and restart with a clean algorithm instance.
        Serial.println("BSEC saved state rejected; starting a new baseline");
        if(!algorithm.begin(address,wire)||!algorithm.setConfig(configuration)){state.end();return false;}
      }else Serial.println("BSEC baseline restored");
    }
    state.end();
  }
  bsecSensor wanted[]={BSEC_OUTPUT_IAQ,BSEC_OUTPUT_STATIC_IAQ,BSEC_OUTPUT_CO2_EQUIVALENT,
    BSEC_OUTPUT_BREATH_VOC_EQUIVALENT,BSEC_OUTPUT_RAW_TEMPERATURE,BSEC_OUTPUT_RAW_HUMIDITY,
    BSEC_OUTPUT_RAW_PRESSURE,BSEC_OUTPUT_RAW_GAS,BSEC_OUTPUT_SENSOR_HEAT_COMPENSATED_TEMPERATURE,
    BSEC_OUTPUT_SENSOR_HEAT_COMPENSATED_HUMIDITY,BSEC_OUTPUT_GAS_PERCENTAGE,BSEC_OUTPUT_COMPENSATED_GAS};
  if(!algorithm.updateSubscription(wanted,ARRAY_LEN(wanted),BSEC_SAMPLE_RATE_LP))return false;
  algorithm.attachCallback(outputReady);active=true;
  Serial.printf("BSEC version %u.%u.%u.%u; generic IAQ 3.3V / 3s\n",algorithm.version.major,algorithm.version.minor,algorithm.version.major_bugfix,algorithm.version.minor_bugfix);
  return true;
}

void pollAirQuality(){
  if(!active)return;
  if(!algorithm.run()&&(algorithm.status<0||algorithm.sensor.status<0)){
    const uint32_t now=millis();
    const uint32_t generation=air.generation;air=AirReadings{};air.generation=generation;
    if(now-errorLoggedAt>10000){Serial.printf("BSEC error=%d sensor=%d\n",algorithm.status,algorithm.sensor.status);errorLoggedAt=now;}
  }
  // run() can wait for a measurement and invoke a callback with a later millis().
  // Read now afterwards so unsigned subtraction never marks that new sample stale.
  const uint32_t now=millis();
  if(air.measuredAt&&now-air.measuredAt>10000){
    const uint32_t generation=air.generation;air=AirReadings{};air.generation=generation;
  }
  // Save a useful baseline once, then at most once per six hours. Never store every sample.
  if(air.ok&&iaqAccuracy==3&&(!firstStateSaved||now-stateSavedAt>=STATE_PERIOD_MS)){
    uint8_t saved[BSEC_MAX_STATE_BLOB_SIZE];
    if(algorithm.getState(saved)){
      Preferences state;
      if(state.begin("bsec-state",false)){
        const size_t written=state.putBytes("blob",saved,sizeof(saved));
        state.putString("profile",STATE_PROFILE);state.end();
        if(written==sizeof(saved)){firstStateSaved=true;stateSavedAt=now;Serial.println("BSEC baseline saved");}
      }
    }
  }
}
