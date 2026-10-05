<?php
declare(strict_types=1);
require dirname(__DIR__).'/src/bootstrap.php';
$target=dirname(__DIR__).'/.env';
if (!is_file($target) || !is_writable($target)) { fwrite(STDERR,"需要可写的 server/.env；Docker 部署请在主机挂载该文件后运行。\n"); exit(1); }
fwrite(STDERR,"请输入新网站密码（至少 12 字符；勿在公共终端输入）：\n");
$password=rtrim(fgets(STDIN),"\r\n");
if(preg_match_all('/./us',$password)<12){fwrite(STDERR,"密码太短\n");exit(1);}
if(strlen($password)>72){fwrite(STDERR,"密码不能超过 72 个 UTF-8 字节\n");exit(1);}
$hash=password_hash($password,PASSWORD_DEFAULT);
$text=file_get_contents($target);
$text=preg_replace_callback('/^ADMIN_PASSWORD_HASH=.*$/m',fn()=>"ADMIN_PASSWORD_HASH='".$hash."'",$text);
file_put_contents($target,$text,LOCK_EX); @chmod($target,0600);
query('DELETE FROM remember_tokens'); query('DELETE FROM ws_tickets');
echo "密码已更新，旧登录已撤销。Docker 服务使用环境变量，需重建 web/websocket/worker 容器以加载新值。\n";
