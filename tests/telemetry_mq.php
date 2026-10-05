<?php
declare(strict_types=1);
require __DIR__.'/../server/src/Telemetry.php';

function check(bool $condition,string $message): void {
    if (!$condition) throw new RuntimeException($message);
}
$message=['type'=>'telemetry','v'=>1,'boot_id'=>'abcdef1234567890','seq'=>0,'reason'=>'boot','data'=>['mq_enabled'=>false,'mq_ready'=>false,'mq_adc_raw'=>null,'mq_adc_mv'=>null,'mq_ao_v'=>null,'mq_gpio'=>null,'mq_smoke'=>null]];
$data=Monitor\Telemetry::validate($message);
check($data['mq_enabled']===false,'Disabled MQ marker must survive validation');
foreach(['mq_adc_raw','mq_adc_mv','mq_ao_v','mq_gpio','mq_smoke'] as $key) check($data[$key]===null,'Disabled MQ must preserve null '.$key);
$message['data']['mq_enabled']=true;$message['data']['mq_adc_mv']=1012;$message['data']['mq_gpio']=true;
$data=Monitor\Telemetry::validate($message);
check($data['mq_enabled']===true&&$data['mq_adc_mv']===1012&&$data['mq_gpio']===true,'Enabled MQ readings must survive');
$message['data']['mq_enabled']='false';$rejected=false;
try {Monitor\Telemetry::validate($message);}catch(InvalidArgumentException $e){$rejected=$e->getMessage()==='bool_mq_enabled';}
check($rejected,'String MQ marker must be rejected');
unset($message['data']['mq_enabled']);
check(Monitor\Telemetry::validate($message)['mq_enabled']===null,'Older firmware must remain compatible');
echo json_encode(['status'=>'PASS','checks'=>9,'scope'=>'MQ nullable telemetry, boolean marker, legacy compatibility']).PHP_EOL;
