<?php
declare(strict_types=1);
namespace Monitor;
final class Telemetry {
    public static function validate(array $m): array {
        if (($m['type']??'')!=='telemetry' || ($m['v']??0)!==1) throw new \InvalidArgumentException('protocol_version');
        if (!preg_match('/^[a-f0-9]{16,32}$/',(string)($m['boot_id']??''))) throw new \InvalidArgumentException('boot_id');
        if (!isset($m['seq']) || !is_int($m['seq']) || $m['seq']<0 || $m['seq']>4294967295) throw new \InvalidArgumentException('seq');
        if (!in_array($m['reason']??'', ['boot','periodic','requested','alarm','recovered'],true)) throw new \InvalidArgumentException('reason');
        $in=$m['data']??null; if (!is_array($in)) throw new \InvalidArgumentException('data');
        $out=[];
        $ranges=['eco2_ppm'=>[0,100000],'bvoc_ppm'=>[0,10000],'iaq'=>[0,500],'static_iaq'=>[0,100000],'gas_percentage'=>[0,100],'compensated_gas'=>[-100,100],'raw_temperature_c'=>[-50,100],'raw_humidity_pct'=>[0,100],'light_lux'=>[0,200000],'temperature_c'=>[-50,100],'humidity_pct'=>[0,100],'pressure_hpa'=>[200,1300],'gas_ohm'=>[0,1000000000],'mq_adc_raw'=>[0,4095],'mq_adc_mv'=>[0,3300],'mq_ao_v'=>[0,6.6],'rssi_dbm'=>[-127,0],'uptime_s'=>[0,4294967295],'queue_dropped'=>[0,4294967295],'radar_uart_bytes'=>[0,4294967295],'radar_uart_age_ms'=>[0,4294967295],'sensor_age_ms'=>[0,4294967295]];
        foreach($ranges as $k=>$range) {
            $v=$in[$k]??null;
            if ($v!==null && (!is_int($v)&&!is_float($v) || !is_finite((float)$v) || $v<$range[0] || $v>$range[1])) throw new \InvalidArgumentException('value_'.$k);
            $out[$k]=$v;
        }
        foreach(['radar_presence','mq_enabled','mq_gpio','mq_smoke','mq_ready','bh1750_ok','bme688_ok','radar_ok'] as $k) {
            $v=$in[$k]??null; if ($v!==null && !is_bool($v)) throw new \InvalidArgumentException('bool_'.$k); $out[$k]=$v;
        }
        $hex=$in['radar_uart_hex']??'';
        if (!is_string($hex) || strlen($hex)>192 || !preg_match('/^[0-9a-fA-F]*$/',$hex)) throw new \InvalidArgumentException('radar_hex');
        $out['radar_uart_hex']=$hex;
        $epoch=$m['captured_at']??null;
        $age=$m['queue_age_s']??0;
        if (!is_int($age) || $age<0 || $age>4294967295) throw new \InvalidArgumentException('queue_age');
        if ($epoch!==null && (!is_int($epoch) || $epoch<1700000000 || $epoch>time()+120)) throw new \InvalidArgumentException('timestamp');
        if ($m['reason']==='requested' && !preg_match('/^[a-f0-9-]{36}$/',(string)($m['request_id']??''))) throw new \InvalidArgumentException('request_id');
        return $out;
    }
    public static function save(string $deviceId,array $m): array {
        $data=self::validate($m);
        $age=$m['queue_age_s']??0;
        $observed=$m['captured_at']??(time()-$age);
        $days=(int)(\settings()['retention_days']??60);
        if ($observed<time()-$days*86400) return ['dropped'=>'outside_retention','seq'=>$m['seq'],'boot_id'=>$m['boot_id']];
        $clock=isset($m['captured_at'])?'ntp':($age>0?'uptime':'server');
        $pdo=\db(); $pdo->beginTransaction();
        try {
            $sample=\query('INSERT INTO samples(device_id,boot_id,seq,observed_at,clock_quality,reason,data) VALUES(?,?,?,to_timestamp(?),?,?,?::jsonb) ON CONFLICT(device_id,boot_id,seq) DO NOTHING RETURNING *',[$deviceId,$m['boot_id'],$m['seq'],$observed,$clock,$m['reason'],\jsonv($data)])->fetch(\PDO::FETCH_ASSOC);
            if (!$sample) { $pdo->commit(); return ['duplicate'=>true,'seq'=>$m['seq'],'boot_id'=>$m['boot_id']]; }
            // Never generate a fresh incident from an old queued observation.
            $fresh=time()-$observed<=600;
            $cfg=json_decode(\query('SELECT config FROM devices WHERE id=?',[$deviceId])->fetchColumn(),true);
            if ($fresh && boolval($cfg['mq_enabled']??false) && ($data['mq_ready']??false)===true && ($data['mq_smoke']??null)!==null) self::alert($deviceId,(bool)$data['mq_smoke'],(int)$sample['id'],$data,$observed);
            if ($m['reason']==='requested') \query("UPDATE commands SET state='completed',result=?::jsonb WHERE id=? AND device_id=? AND state IN ('sent','acked') AND deadline>now()",[\jsonv(['sample_id'=>(int)$sample['id']]),$m['request_id'],$deviceId]);
            $pdo->commit(); $sample['data']=$data; return ['sample'=>$sample,'seq'=>$m['seq'],'boot_id'=>$m['boot_id']];
        } catch(\Throwable $e) { if ($pdo->inTransaction()) $pdo->rollBack(); throw $e; }
    }
    private static function alert(string $deviceId,bool $smoke,int $sampleId,array $data,int $observed): void {
        \query('INSERT INTO alert_state(device_id) VALUES(?) ON CONFLICT DO NOTHING',[$deviceId]);
        $state=\query('SELECT * FROM alert_state WHERE device_id=? FOR UPDATE',[$deviceId])->fetch(\PDO::FETCH_ASSOC);
        if ($state['last_observed_at'] && strtotime($state['last_observed_at'])>$observed) return;
        \query('UPDATE alert_state SET last_observed_at=to_timestamp(?) WHERE device_id=?',[$observed,$deviceId]);
        if ($smoke && !\boolv($state['active'])) {
            $incident=\uuid(); \query('INSERT INTO alerts(id,device_id,sample_id) VALUES(?,?,?)',[$incident,$deviceId,$sampleId]);
            \query('UPDATE alert_state SET active=true,incident_id=? WHERE device_id=?',[$incident,$deviceId]);
            $s=\settings(); $cooldown=(int)($s['mail_cooldown_s']??900);
            if (($s['mail_enabled']??false) && (!$state['last_mail_at'] || strtotime($state['last_mail_at'])<=time()-$cooldown)) {
                $name=\query('SELECT name FROM devices WHERE id=?',[$deviceId])->fetchColumn();
                \query('INSERT INTO mail_queue(device_id,incident_id,payload) VALUES(?,?,?::jsonb)',[$deviceId,$incident,\jsonv(['name'=>$name,'time'=>gmdate('c'),'data'=>$data])]);
                \query('UPDATE alert_state SET last_mail_at=now() WHERE device_id=?',[$deviceId]);
            }
        } elseif (!$smoke && \boolv($state['active'])) {
            \query('UPDATE alerts SET ended_at=now() WHERE id=?',[$state['incident_id']]);
            \query('UPDATE alert_state SET active=false,incident_id=NULL WHERE device_id=?',[$deviceId]);
        }
    }
}
