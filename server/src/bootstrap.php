<?php
declare(strict_types=1);
require dirname(__DIR__) . '/vendor/autoload.php';
Dotenv\Dotenv::createImmutable(dirname(__DIR__))->safeLoad();
date_default_timezone_set('UTC');
function envv(string $key, string $default = ''): string { $v=$_ENV[$key] ?? getenv($key); return $v===false || $v===null ? $default : (string)$v; }
function db(bool $reset=false): PDO {
    static $pdo;
    if ($reset) $pdo=null;
    if (!$pdo) {
        $pdo = new PDO('pgsql:host='.envv('DB_HOST','db').';port='.envv('DB_PORT','5432').';dbname='.envv('DB_NAME','sensor_monitor'), envv('DB_USER','sensor_monitor'), envv('DB_PASSWORD'), [PDO::ATTR_ERRMODE=>PDO::ERRMODE_EXCEPTION,PDO::ATTR_EMULATE_PREPARES=>false]);
        $pdo->exec("SET TIME ZONE 'UTC'");
    }
    return $pdo;
}
function query(string $sql, array $args=[]): PDOStatement {
    try { $s=db()->prepare($sql); $s->execute($args); return $s; }
    catch(PDOException $e) {
        if (str_starts_with((string)$e->getCode(),'08') || preg_match('/server closed|connection (?:lost|not open|unexpectedly)|no connection/i',$e->getMessage())) {
            try { db(true); } catch(PDOException) { /* next request/tick retries construction */ }
        }
        throw $e;
    }
}
function uuid(): string { $h=bin2hex(random_bytes(16)); return substr($h,0,8).'-'.substr($h,8,4).'-4'.substr($h,13,3).'-a'.substr($h,17,3).'-'.substr($h,20); }
function jsonv(mixed $value): string { return json_encode($value,JSON_THROW_ON_ERROR|JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES); }
function boolv(mixed $v): bool { return $v===true || $v===1 || $v==='1' || $v==='t'; }
function settings(): array {
    $r=query('SELECT value FROM settings WHERE id=1')->fetchColumn();
    return $r ? json_decode($r,true,512,JSON_THROW_ON_ERROR) : [];
}
function encryptSecret(string $plain): string {
    $key=hex2bin(envv('APP_KEY')); if (!$key || strlen($key)!==32) throw new RuntimeException('Invalid APP_KEY');
    $nonce=random_bytes(SODIUM_CRYPTO_SECRETBOX_NONCEBYTES);
    return base64_encode($nonce.sodium_crypto_secretbox($plain,$nonce,$key));
}
function decryptSecret(string $cipher): string {
    if ($cipher==='') return '';
    $raw=base64_decode($cipher,true); $key=hex2bin(envv('APP_KEY'));
    if (!$raw || !$key) throw new RuntimeException('Invalid secret');
    $plain=sodium_crypto_secretbox_open(substr($raw,24),substr($raw,0,24),$key);
    if ($plain===false) throw new RuntimeException('Secret decryption failed'); return $plain;
}
function deviceDefaults(): array { return ['report_interval_s'=>300,'mq_enabled'=>false,'mq_warmup_s'=>180,'smoke_debounce_s'=>3,'smoke_clear_s'=>10,'mq_mode'=>'digital','mq_adc_threshold_mv'=>2000,'mq_adc_hysteresis_mv'=>100,'mq_alarm_gpio_level'=>1]; }
function validateDeviceConfig(array $in): array {
    $out=deviceDefaults();
    foreach(['report_interval_s'=>[30,3600],'mq_warmup_s'=>[0,86400],'smoke_debounce_s'=>[1,60],'smoke_clear_s'=>[1,300],'mq_adc_threshold_mv'=>[1,2850],'mq_adc_hysteresis_mv'=>[0,500],'mq_alarm_gpio_level'=>[0,1]] as $k=>$range) {
        if (array_key_exists($k,$in)) { $v=filter_var($in[$k],FILTER_VALIDATE_INT); if ($v===false || $v<$range[0] || $v>$range[1]) throw new InvalidArgumentException('参数超出范围: '.$k); $out[$k]=$v; }
    }
    if (isset($in['mq_enabled'])) { if (!is_bool($in['mq_enabled'])) throw new InvalidArgumentException('mq_enabled 必须是布尔值'); $out['mq_enabled']=$in['mq_enabled']; }
    if (isset($in['mq_mode'])) { if (!in_array($in['mq_mode'],['digital','analog','either'],true)) throw new InvalidArgumentException('MQ 模式无效'); $out['mq_mode']=$in['mq_mode']; }
    return $out;
}
