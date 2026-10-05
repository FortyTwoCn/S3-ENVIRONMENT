<?php
declare(strict_types=1);
if (PHP_SAPI !== 'cli') { http_response_code(404); exit; }
$url=rtrim((string)($argv[1]??''),'/');
$parts=parse_url($url);
if (!filter_var($url,FILTER_VALIDATE_URL) || !in_array($parts['scheme']??'', ['http','https'],true)
    || !empty($parts['path']) || !empty($parts['query']) || !empty($parts['fragment'])
    || !empty($parts['user']) || !empty($parts['pass'])) {
    fwrite(STDERR,"Usage: php bin/set-public-url.php https://s.xuanknow.cn\n");
    exit(1);
}
$root=dirname(__DIR__);
$target=$root.'/.env';
if (!is_file($target) || !is_readable($target) || !is_writable($target)) {
    fwrite(STDERR,"The project .env must exist and be readable and writable.\n");exit(1);
}
$directory=$root.'/.runtime/config-backups';
if (!is_dir($directory) && !mkdir($directory,0700,true)) { fwrite(STDERR,"Cannot create backup directory.\n");exit(1); }
$original=file_get_contents($target);
$backup=$directory.'/.env.'.gmdate('YmdHis').'.'.bin2hex(random_bytes(3));
if (file_put_contents($backup,$original,LOCK_EX)===false) { fwrite(STDERR,"Cannot back up .env.\n");exit(1); }
chmod($backup,0600);
$secure=($parts['scheme']==='https');
$values=['APP_URL'=>$url,'WS_PUBLIC_URL'=>preg_replace('#^http#','ws',$url).'/ws','COOKIE_SECURE'=>$secure?'1':'0'];
$text=$original;
foreach($values as $key=>$value) {
    $line=$key."='".$value."'";
    $pattern='/^\s*'.preg_quote($key,'/').'\s*=.*$/m';
    if (preg_match($pattern,$text)) $text=preg_replace_callback($pattern,fn()=>$line,$text);
    else $text=rtrim($text)."\n".$line."\n";
}
if (file_put_contents($target,$text,LOCK_EX)===false) { fwrite(STDERR,"Cannot write .env.\n");exit(1); }
chmod($target,0600);
echo "APP_URL, WS_PUBLIC_URL and COOKIE_SECURE updated. Database credentials, APP_KEY and password hash preserved.\n";
echo "Restart sensor-monitor-websocket and sensor-monitor-worker through BaoTa Supervisor.\n";

