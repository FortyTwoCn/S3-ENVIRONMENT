<?php
declare(strict_types=1);
require dirname(__DIR__).'/src/bootstrap.php';
use Monitor\Auth;
header('Content-Type: application/json; charset=utf-8'); header('Cache-Control: no-store');
header('X-Content-Type-Options: nosniff');
function respond(mixed $value,int $status=200): never { http_response_code($status); echo jsonv($value); exit; }
function body(): array {
    if ((int)($_SERVER['CONTENT_LENGTH']??0)>16384) throw new InvalidArgumentException('请求过大');
    $v=json_decode(file_get_contents('php://input'),true,32,JSON_THROW_ON_ERROR); if (!is_array($v)) throw new InvalidArgumentException('JSON 对象无效'); return $v;
}
function device(string $id): array {
    if (!preg_match('/^[a-f0-9-]{36}$/',$id)) throw new InvalidArgumentException('设备 ID 无效');
    $r=query('SELECT * FROM devices WHERE id=?',[$id])->fetch(PDO::FETCH_ASSOC); if (!$r) respond(['error'=>'设备不存在'],404); return $r;
}
function rangeParams(): array {
    $hours=max(1,min(87600,(int)($_GET['hours']??24)));
    $end=isset($_GET['to'])?strtotime($_GET['to']):time(); $start=isset($_GET['from'])?strtotime($_GET['from']):($end-$hours*3600);
    if (!$end || !$start || $start>=$end || $end-$start>366*86400) throw new InvalidArgumentException('时间范围无效，最多 366 天');
    return [gmdate('c',$start),gmdate('c',$end)];
}
try {
    $action=$_GET['action']??'bootstrap';
    if (!Auth::loggedIn()) respond(['error'=>'请登录'],401);
    if ($_SERVER['REQUEST_METHOD']==='POST') Auth::csrf();
    $get=['bootstrap','devices','history','chart','alerts','settings','commands','ws-ticket','export'];
    if (in_array($action,$get,true) && $_SERVER['REQUEST_METHOD']!=='GET') respond(['error'=>'方法不允许'],405);
    if (!in_array($action,$get,true) && $_SERVER['REQUEST_METHOD']!=='POST') respond(['error'=>'方法不允许'],405);
    if ($action==='bootstrap') respond(['csrf'=>$_SESSION['csrf'],'ws_url'=>envv('WS_PUBLIC_URL'),'remember_days'=>(int)envv('REMEMBER_DAYS','30')]);
    if ($action==='ws-ticket') {
        $ticket=bin2hex(random_bytes(32)); query("INSERT INTO ws_tickets VALUES(?,now()+interval '30 seconds',?)",[hash('sha256',$ticket),$_SESSION['selector']]); respond(['ticket'=>$ticket]);
    }
    if ($action==='devices') {
        $rows=query("SELECT d.id,d.name,d.enabled,d.config,d.config_version,d.last_seen,d.firmware,(d.connected AND d.last_seen>now()-interval '90 seconds') AS online,(SELECT row_to_json(s) FROM (SELECT id,observed_at,received_at,clock_quality,reason,data FROM samples WHERE device_id=d.id ORDER BY observed_at DESC,id DESC LIMIT 1) s) AS latest FROM devices d ORDER BY created_at")->fetchAll(PDO::FETCH_ASSOC);
        foreach($rows as &$r) { $r['config']=json_decode($r['config'],true); $r['latest']=$r['latest']?json_decode($r['latest'],true):null; $r['online']=boolv($r['online']); $r['enabled']=boolv($r['enabled']); } respond($rows);
    }
    if ($action==='device-create') {
        $in=body(); $name=trim((string)($in['name']??'')); if (mb_strlen($name)<1 || mb_strlen($name)>80) throw new InvalidArgumentException('设备名称须为 1–80 字符');
        $token=bin2hex(random_bytes(32)); $id=uuid(); query('INSERT INTO devices(id,name,token_hash,config) VALUES(?,?,?,?::jsonb)',[$id,$name,hash('sha256',$token),jsonv(deviceDefaults())]); respond(['id'=>$id,'token'=>$token,'note'=>'令牌只显示一次，请复制到设备配网页面']);
    }
    if ($action==='device-config') {
        $in=body(); $d=device((string)($in['id']??'')); $config=validateDeviceConfig($in['config']??[]);
        query('UPDATE devices SET config=?::jsonb,config_version=config_version+1 WHERE id=?',[jsonv($config),$d['id']]);
        if (!$config['mq_enabled']) {
            query('UPDATE alerts SET ended_at=now() WHERE id IN (SELECT incident_id FROM alert_state WHERE device_id=?) AND ended_at IS NULL',[$d['id']]);
            query('UPDATE alert_state SET active=false,incident_id=NULL WHERE device_id=?',[$d['id']]);
        }
        respond(['ok'=>true,'config'=>$config]);
    }
    if ($action==='device-revoke') {
        $in=body(); $d=device((string)($in['id']??'')); query('UPDATE devices SET enabled=false WHERE id=?',[$d['id']]); respond(['ok'=>true]);
    }
    if ($action==='device-token') {
        $in=body(); $d=device((string)($in['id']??'')); $token=bin2hex(random_bytes(32)); query('UPDATE devices SET token_hash=?,enabled=true WHERE id=?',[hash('sha256',$token),$d['id']]);
        // Active connection must reauthenticate after token rotation.
        query('UPDATE devices SET config_version=config_version+1 WHERE id=?',[$d['id']]); respond(['id'=>$d['id'],'token'=>$token]);
    }
    if ($action==='command') {
        $in=body(); $d=device((string)($in['device_id']??''));
        if (!boolv($d['enabled']) || !boolv($d['connected']) || !$d['last_seen'] || strtotime($d['last_seen'])<time()-90) respond(['error'=>'设备离线，请等待自动重连'],409);
        if (query("SELECT 1 FROM commands WHERE device_id=? AND state IN ('queued','sent','acked') AND deadline>now()",[$d['id']])->fetchColumn()) respond(['error'=>'已有采样请求在等待设备响应'],409);
        $id=uuid(); query("INSERT INTO commands(id,device_id,type,deadline) VALUES(?,?,'sample_now',now()+interval '20 seconds')",[$id,$d['id']]); respond(['request_id'=>$id,'state'=>'queued'],202);
    }
    if ($action==='commands') { $d=device((string)($_GET['device_id']??'')); respond(query('SELECT id,state,created_at,result FROM commands WHERE device_id=? ORDER BY created_at DESC LIMIT 10',[$d['id']])->fetchAll(PDO::FETCH_ASSOC)); }
    if (in_array($action,['history','chart','export'],true)) {
        $d=device((string)($_GET['device_id']??'')); [$start,$end]=rangeParams();
        if ($action==='chart') {
            $metrics=['eco2_ppm','bvoc_ppm','iaq','static_iaq','gas_percentage','compensated_gas','raw_temperature_c','raw_humidity_pct','light_lux','temperature_c','humidity_pct','pressure_hpa','gas_ohm','mq_adc_mv','mq_ao_v','radar_presence','mq_smoke'];
            $metric=$_GET['metric']??'temperature_c'; if (!in_array($metric,$metrics,true)) throw new InvalidArgumentException('指标无效');
            $bucket=max(1,(int)ceil((strtotime($end)-strtotime($start))/1200));
            $expr=in_array($metric,['radar_presence','mq_smoke'],true)?"CASE WHEN data->>'$metric'='true' THEN 1 WHEN data->>'$metric'='false' THEN 0 END":"(data->>'$metric')::double precision";
            $rows=query("SELECT floor(extract(epoch FROM observed_at)/?)*?*1000 AS x,avg($expr) AS y,min($expr) AS lo,max($expr) AS hi,count(*) AS n FROM samples WHERE device_id=? AND observed_at>=? AND observed_at<=? GROUP BY 1 ORDER BY 1",[$bucket,$bucket,$d['id'],$start,$end])->fetchAll(PDO::FETCH_ASSOC);
            foreach($rows as &$r) foreach(['x','y','lo','hi','n'] as $k) $r[$k]=$r[$k]===null?null:(float)$r[$k];
            respond(['points'=>$rows,'bucket_s'=>$bucket,'report_interval_s'=>$d['config']?json_decode($d['config'],true)['report_interval_s']:300,'metric'=>$metric,'from'=>$start,'to'=>$end,'aggregation'=>'mean_min_max']);
        }
        if ($action==='export') {
            header('Content-Type: text/csv; charset=utf-8'); header('Content-Disposition: attachment; filename="sensor-data.csv"');
            $out=fopen('php://output','w'); fwrite($out,"\xEF\xBB\xBF");
            $keys=['eco2_ppm','bvoc_ppm','iaq','static_iaq','gas_percentage','compensated_gas','raw_temperature_c','raw_humidity_pct','light_lux','temperature_c','humidity_pct','pressure_hpa','gas_ohm','radar_presence','mq_adc_raw','mq_adc_mv','mq_ao_v','mq_gpio','mq_smoke','mq_ready'];
            fputcsv($out,array_merge(['observed_at_utc','received_at_utc','clock_quality','reason'],$keys),',','"','');
            $cursor=query('SELECT observed_at,received_at,clock_quality,reason,data FROM samples WHERE device_id=? AND observed_at>=? AND observed_at<=? ORDER BY observed_at,id LIMIT 200000',[$d['id'],$start,$end]);
            while($row=$cursor->fetch(PDO::FETCH_ASSOC)) { $data=json_decode($row['data'],true); $values=array_map(fn($k)=>is_bool($data[$k]??null)?($data[$k]?'1':'0'):($data[$k]??''),$keys); fputcsv($out,array_merge(array_slice($row,0,4),$values),',','"',''); } fclose($out); exit;
        }
        $page=max(1,min(100000,(int)($_GET['page']??1))); $size=50;
        $count=(int)query('SELECT count(*) FROM samples WHERE device_id=? AND observed_at>=? AND observed_at<=?',[$d['id'],$start,$end])->fetchColumn();
        $rows=query('SELECT id,observed_at,received_at,clock_quality,reason,data FROM samples WHERE device_id=? AND observed_at>=? AND observed_at<=? ORDER BY observed_at DESC,id DESC LIMIT 50 OFFSET ?',[$d['id'],$start,$end,($page-1)*$size])->fetchAll(PDO::FETCH_ASSOC);
        foreach($rows as &$row) $row['data']=json_decode($row['data'],true); respond(['rows'=>$rows,'total'=>$count,'page'=>$page,'page_size'=>$size]);
    }
    if ($action==='alerts') respond(query('SELECT a.*,d.name FROM alerts a JOIN devices d ON d.id=a.device_id ORDER BY started_at DESC LIMIT 100')->fetchAll(PDO::FETCH_ASSOC));
    if ($action==='settings') {
        $s=settings(); $s['smtp']['password_saved']=!empty($s['smtp']['password_enc']); unset($s['smtp']['password_enc']);
        $s['plain_smtp_allowed']=envv('SMTP_ALLOW_PLAIN','0')==='1';
        $s['mail_jobs']=query('SELECT id,kind,state,attempts,created_at,sent_at,last_error FROM mail_queue ORDER BY id DESC LIMIT 20')->fetchAll(PDO::FETCH_ASSOC); respond($s);
    }
    if ($action==='settings-save') {
        $in=body(); $s=settings();
        foreach(['retention_days'=>[1,3650],'mail_cooldown_s'=>[60,86400]] as $key=>$range) { $v=filter_var($in[$key]??null,FILTER_VALIDATE_INT); if ($v===false || $v<$range[0] || $v>$range[1]) throw new InvalidArgumentException($key.' 超出范围'); $s[$key]=$v; }
        if (!is_bool($in['mail_enabled']??null)) throw new InvalidArgumentException('mail_enabled 无效'); $s['mail_enabled']=$in['mail_enabled'];
        $smtp=$in['smtp']??[];
        $host=trim((string)($smtp['host']??'')); if ($host!=='' && !preg_match('/^[A-Za-z0-9.:-]{1,253}$/',$host)) throw new InvalidArgumentException('SMTP 主机无效');
        $port=filter_var($smtp['port']??587,FILTER_VALIDATE_INT); if (!$port || $port<1 || $port>65535) throw new InvalidArgumentException('SMTP 端口无效');
        $mode=$smtp['encryption']??'tls'; if (!in_array($mode,['tls','ssl','none'],true) || ($mode==='none' && envv('SMTP_ALLOW_PLAIN','0')!=='1')) throw new InvalidArgumentException('SMTP 加密模式无效');
        $from=trim((string)($smtp['from_address']??'')); if ($from!=='' && !filter_var($from,FILTER_VALIDATE_EMAIL)) throw new InvalidArgumentException('发件邮箱无效');
        $recipients=$smtp['recipients']??[]; if (!is_array($recipients) || count($recipients)>10) throw new InvalidArgumentException('收件人最多 10 个');
        foreach($recipients as $r) if (!is_string($r) || !filter_var($r,FILTER_VALIDATE_EMAIL)) throw new InvalidArgumentException('收件邮箱无效');
        if ($s['mail_enabled'] && ($host==='' || $from==='' || !$recipients)) throw new InvalidArgumentException('启用告警前请填写 SMTP、发件人和收件人');
        $oldPassword=$s['smtp']['password_enc']??'';
        $password=(string)($smtp['password']??''); if (strlen($password)>1024) throw new InvalidArgumentException('授权码过长');
        $s['smtp']=['host'=>$host,'port'=>$port,'encryption'=>$mode,'username'=>mb_substr((string)($smtp['username']??''),0,253),'password_enc'=>$password!==''?encryptSecret($password):$oldPassword,'from_address'=>$from,'from_name'=>mb_substr((string)($smtp['from_name']??'传感器监测'),0,80),'recipients'=>array_values(array_unique($recipients))];
        query('UPDATE settings SET value=?::jsonb WHERE id=1',[jsonv($s)]); respond(['ok'=>true]);
    }
    if ($action==='mail-test') {
        $s=settings(); if (!$s['smtp']['host'] || !$s['smtp']['from_address'] || !$s['smtp']['recipients']) throw new InvalidArgumentException('请先保存 SMTP 设置');
        if (query("SELECT 1 FROM mail_queue WHERE kind='test' AND created_at>now()-interval '1 minute'")->fetchColumn()) throw new InvalidArgumentException('请等待一分钟后再次发送测试邮件');
        $id=query("INSERT INTO mail_queue(kind,payload) VALUES('test','{}') RETURNING id")->fetchColumn(); respond(['job_id'=>$id,'state'=>'pending']);
    }
    if ($action==='mail-retry') { $in=body(); query("UPDATE mail_queue SET state='pending',attempts=0,next_attempt=now(),last_error=NULL WHERE id=? AND state='failed'",[(int)($in['id']??0)]); respond(['ok'=>true]); }
    respond(['error'=>'接口不存在'],404);
} catch(InvalidArgumentException|JsonException $e) { respond(['error'=>$e->getMessage()],422); }
catch(Throwable $e) { error_log('API failure: '.$e->getMessage()); respond(['error'=>'服务暂时不可用，请检查数据库和服务日志'],503); }
