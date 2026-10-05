#pragma once
#include <Arduino.h>
#include <Wire.h>

// Only measurements travel over the network. BSEC readiness/accuracy stay local.
struct AirReadings {
  float temperature=NAN, humidity=NAN, pressure=NAN, gas=NAN;
  float rawTemperature=NAN, rawHumidity=NAN;
  float iaq=NAN, staticIaq=NAN, eco2=NAN, bvoc=NAN;
  float gasPercentage=NAN, compensatedGas=NAN;
  uint32_t measuredAt=0, generation=0;
  bool ok=false;
};
extern AirReadings air;
bool beginAirQuality(TwoWire& wire);
void pollAirQuality();
