<?php
declare(strict_types=1);
namespace Monitor;
final class Auth {
    public static function start(): void {
        if (session_status()===PHP_SESSION_ACTIVE) return;
        $path=\envv('SESSION_PATH'); if ($path) { if (!is_dir($path)) mkdir($path,0700,true); session_save_path($path); }
        ini_set('session.use_strict_mode','1'); ini_set('session.gc_maxlifetime','86400');
        session_name('sensor_session');
        session_set_cookie_params(['lifetime'=>0,'path'=>'/','secure'=>\envv('COOKIE_SECURE','1')==='1','httponly'=>true,'samesite'=>'Strict']);
        session_start();
        if (empty($_SESSION['authenticated']) && isset($_COOKIE['sensor_remember'])) {
            $parts=explode(':',$_COOKIE['sensor_remember']);
            if (count($parts)===2 && preg_match('/^[a-f0-9]{24}$/',$parts[0]) && preg_match('/^[a-f0-9]{64}$/',$parts[1])) {
                $r=\query('SELECT * FROM remember_tokens WHERE selector=? AND expires_at>now()',[$parts[0]])->fetch(\PDO::FETCH_ASSOC);
                if ($r && hash_equals($r['validator_hash'],hash('sha256',$parts[1]))) { session_regenerate_id(true); $_SESSION['authenticated']=true; $_SESSION['selector']=$parts[0]; }
            }
        }
        // A revoked remember token also invalidates an existing session and WS tickets.
        if (!empty($_SESSION['selector']) && !\query('SELECT 1 FROM remember_tokens WHERE selector=? AND expires_at>now()',[$_SESSION['selector']])->fetchColumn()) { $_SESSION=[]; }
        $_SESSION['csrf'] ??= bin2hex(random_bytes(24));
    }
    public static function loggedIn(): bool { self::start(); return !empty($_SESSION['authenticated']); }
    public static function login(string $password,bool $remember): bool {
        self::start();
        // REMOTE_ADDR is set by the trusted web server, not arbitrary X-Forwarded-For.
        $ip=hash('sha256',($_SERVER['REMOTE_ADDR'] ?? 'cli').\envv('APP_KEY'));
        \query('INSERT INTO login_limits(ip_hash) VALUES(?) ON CONFLICT DO NOTHING',[$ip]);
        \query("UPDATE login_limits SET failures=0,window_start=now() WHERE ip_hash=? AND window_start<now()-interval '15 minutes'",[$ip]);
        $n=\query('SELECT failures FROM login_limits WHERE ip_hash=?',[$ip])->fetchColumn();
        if ((int)$n>=10) throw new \InvalidArgumentException('尝试次数过多，请在 15 分钟后重试');
        if (!password_verify($password,\envv('ADMIN_PASSWORD_HASH'))) { \query('UPDATE login_limits SET failures=failures+1 WHERE ip_hash=?',[$ip]); return false; }
        \query('UPDATE login_limits SET failures=0 WHERE ip_hash=?',[$ip]);
        session_regenerate_id(true); $_SESSION['authenticated']=true; $_SESSION['csrf']=bin2hex(random_bytes(24));
        // Session-bound token for WS revocation; persistent cookie is optional.
        $selector=bin2hex(random_bytes(12)); $validator=bin2hex(random_bytes(32));
        $days=$remember ? max(1,min(365,(int)\envv('REMEMBER_DAYS','30'))) : 1;
        \query("INSERT INTO remember_tokens VALUES(?,?,now()+make_interval(days=>?))",[$selector,hash('sha256',$validator),$days]);
        $_SESSION['selector']=$selector;
        if ($remember) setcookie('sensor_remember',$selector.':'.$validator,['expires'=>time()+$days*86400,'path'=>'/','secure'=>\envv('COOKIE_SECURE','1')==='1','httponly'=>true,'samesite'=>'Strict']);
        return true;
    }
    public static function logout(): void {
        self::start();
        if (!empty($_SESSION['selector'])) \query('DELETE FROM remember_tokens WHERE selector=?',[$_SESSION['selector']]);
        $_SESSION=[]; session_destroy();
        foreach(['sensor_remember','sensor_session'] as $name) setcookie($name,'',['expires'=>1,'path'=>'/','secure'=>\envv('COOKIE_SECURE','1')==='1','httponly'=>true,'samesite'=>'Strict']);
    }
    public static function csrf(): void {
        self::start(); $supplied=$_SERVER['HTTP_X_CSRF_TOKEN'] ?? $_POST['csrf'] ?? '';
        if (!is_string($supplied) || !hash_equals($_SESSION['csrf'],$supplied)) throw new \InvalidArgumentException('CSRF 校验失败');
        $origin=$_SERVER['HTTP_ORIGIN'] ?? '';
        if ($origin!=='' && rtrim($origin,'/')!==rtrim(\envv('APP_URL'),'/')) throw new \InvalidArgumentException('来源不匹配');
    }
}
