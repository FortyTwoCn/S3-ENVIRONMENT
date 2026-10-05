<?php
declare(strict_types=1);
$options=getopt('',['url:','password-stdin','local']);
$root=dirname(__DIR__); $target=$root.'/.env';
if (file_exists($target)) { fwrite(STDERR,".env 已存在，为保护数据和登录密钥，安装程序不会覆盖它。\n"); exit(1); }
$url=rtrim((string)($options['url']??'http://localhost:8080'),'/');
if (!filter_var($url,FILTER_VALIDATE_URL) || !in_array(parse_url($url,PHP_URL_SCHEME),['http','https'],true)) { fwrite(STDERR,"URL 无效\n"); exit(1); }
if (!in_array(parse_url($url,PHP_URL_PATH),[null,'','/'],true) || parse_url($url,PHP_URL_QUERY) || parse_url($url,PHP_URL_FRAGMENT) || parse_url($url,PHP_URL_USER)) { fwrite(STDERR,"请使用网站根地址，不能带子目录、查询参数或用户名。\n"); exit(1); }
$isLocal=isset($options['local']); $secure=str_starts_with($url,'https://');
if (!$secure && !$isLocal) { fwrite(STDERR,"公网部署应使用 https://；本机/可信局域网测试请显式加 --local\n"); exit(1); }
fwrite(STDERR,"设置网站密码（至少 12 字符；终端可能显示输入，勿在公共终端使用）：\n");
$password=rtrim(fgets(STDIN),"\r\n");
if (preg_match_all('/./us',$password)<12) { fwrite(STDERR,"密码太短\n"); exit(1); }
if (strlen($password)>72) { fwrite(STDERR,"密码不能超过 72 个 UTF-8 字节\n"); exit(1); }
$vals=['APP_URL'=>$url,'APP_KEY'=>bin2hex(random_bytes(32)),'ADMIN_PASSWORD_HASH'=>password_hash($password,PASSWORD_DEFAULT),'DB_HOST'=>'db','DB_PORT'=>'5432','DB_NAME'=>'sensor_monitor','DB_USER'=>'sensor_monitor','DB_PASSWORD'=>bin2hex(random_bytes(24)),'COOKIE_SECURE'=>$secure?'1':'0','REMEMBER_DAYS'=>'30','WS_PUBLIC_URL'=>preg_replace('#^http#','ws',$url).'/ws','WS_BIND'=>'0.0.0.0','WS_PORT'=>'8081','SMTP_ALLOW_PLAIN'=>'0','SESSION_PATH'=>'/tmp/sensor-sessions'];
if ($secure) $vals['SITE_ADDRESS']=(string)parse_url($url,PHP_URL_HOST);
$s=''; foreach($vals as $k=>$v) $s.=$k."='".$v."'\n";
file_put_contents($target,$s); @chmod($target,0600);
echo ".env 已生成。请保管 APP_KEY；它用于解密 SMTP 授权码。\n";
