<?php
declare(strict_types=1);
require __DIR__.'/../server/src/Telemetry.php';
function expect(bool $ok,string $why): void {if(!$ok)throw new RuntimeException($why);}
$values=['eco2_ppm'=>823.5,'bvoc_ppm'=>0.672,'iaq'=>76.2,'static_iaq'=>81.4,'gas_percentage'=>63.8,'compensated_gas'=>10.93,'raw_temperature_c'=>26.82,'raw_humidity_pct'=>44.3];
$message=['v'=>1,'type'=>'telemetry','boot_id'=>'abcdef1234567890','seq'=>1,'reason'=>'periodic','data'=>$values];
$validated=Monitor\Telemetry::validate($message);
foreach($values as $key=>$value)expect($validated[$key]===$value,'Value lost: '.$key);
$message['data']=[];$validated=Monitor\Telemetry::validate($message);
foreach($values as $key=>$value)expect($validated[$key]===null,'Old firmware must produce null: '.$key);
foreach(['eco2_ppm'=>'800','iaq'=>501,'gas_percentage'=>100.1,'bvoc_ppm'=>-0.1,'raw_humidity_pct'=>101,'compensated_gas'=>INF] as $key=>$bad){
  $message['data']=[$key=>$bad];$rejected=false;
  try{Monitor\Telemetry::validate($message);}catch(InvalidArgumentException $e){$rejected=$e->getMessage()==='value_'.$key;}
  expect($rejected,'Malformed measurement accepted: '.$key);
}
$message['data']=['bsec_accuracy'=>3,'bsec_run_in'=>true,'bsec_stabilized'=>true];
$validated=Monitor\Telemetry::validate($message);
foreach(['bsec_accuracy','bsec_run_in','bsec_stabilized'] as $key)expect(!array_key_exists($key,$validated),'Unrequested status stored: '.$key);
echo json_encode(['status'=>'PASS','checks'=>25,'scope'=>'BSEC measurements, legacy nulls, bounds, omitted calibration states']).PHP_EOL;
