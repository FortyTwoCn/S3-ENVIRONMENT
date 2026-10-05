<?php
declare(strict_types=1);
namespace Monitor;
use PHPMailer\PHPMailer\PHPMailer;
final class Worker {
    public static function cleanup(): array {
        $days=(int)(\settings()['retention_days']??60);
        $n=0;
        do { $deleted=\query('DELETE FROM samples WHERE id IN (SELECT id FROM samples WHERE observed_at<now()-make_interval(days=>?) LIMIT 5000)',[$days])->rowCount(); $n+=$deleted; } while($deleted===5000);
        \query('DELETE FROM alerts WHERE started_at<now()-make_interval(days=>?)',[$days]);
        \query("DELETE FROM mail_queue WHERE created_at<now()-make_interval(days=>?)",[$days]);
        \query("DELETE FROM commands WHERE created_at<now()-interval '7 days'");
        \query('DELETE FROM remember_tokens WHERE expires_at<now()'); \query('DELETE FROM ws_tickets WHERE expires_at<now()');
        \query("DELETE FROM login_limits WHERE window_start<now()-interval '1 day'");
        return ['samples_deleted'=>$n,'retention_days'=>$days];
    }
    public static function mailOne(): bool {
        \query("UPDATE mail_queue SET state='pending',claimed_at=NULL WHERE state='sending' AND claimed_at<now()-interval '5 minutes'");
        \db()->beginTransaction();
        $job=\query("SELECT * FROM mail_queue WHERE state='pending' AND next_attempt<=now() ORDER BY id FOR UPDATE SKIP LOCKED LIMIT 1")->fetch(\PDO::FETCH_ASSOC);
        if (!$job) { \db()->commit(); return false; }
        \query("UPDATE mail_queue SET state='sending',claimed_at=now(),attempts=attempts+1 WHERE id=?",[$job['id']]); \db()->commit();
        try {
            $s=\settings();
            if ($job['kind']==='smoke' && !($s['mail_enabled']??false)) { \query("UPDATE mail_queue SET state='cancelled',last_error='邮件告警已关闭' WHERE id=?",[$job['id']]); return true; }
            $smtp=$s['smtp']; $p=json_decode($job['payload'],true);
            $mail=new PHPMailer(true); $mail->CharSet='UTF-8'; $mail->isSMTP();
            $mail->Host=$smtp['host']; $mail->Port=(int)$smtp['port']; $mail->Timeout=15;
            $mode=$smtp['encryption'];
            if ($mode==='none' && \envv('SMTP_ALLOW_PLAIN','0')!=='1') throw new \RuntimeException('无加密 SMTP 未启用');
            $mail->SMTPSecure=$mode==='ssl'?PHPMailer::ENCRYPTION_SMTPS:($mode==='tls'?PHPMailer::ENCRYPTION_STARTTLS:'');
            $mail->SMTPAutoTLS=$mode!=='none'; $mail->SMTPAuth=$smtp['username']!=='';
            $mail->Username=$smtp['username']; $mail->Password=\decryptSecret($smtp['password_enc']??'');
            $mail->setFrom($smtp['from_address'],$smtp['from_name']);
            foreach($smtp['recipients'] as $address) $mail->addAddress($address);
            $mail->Subject=$job['kind']==='test'?'传感器监测：SMTP 测试邮件':'烟雾告警：'.$p['name'];
            $mail->Body=$job['kind']==='test'?'SMTP 测试成功。网站已能够发送通知。':"设备：{$p['name']}\n事件时间（UTC）：{$p['time']}\nMQ 检测到持续告警信号。\nADC：".($p['data']['mq_adc_mv']??'--')." mV\n请打开监测网站查看最新读数：".\envv('APP_URL');
            // Stable Message-ID helps mail providers deduplicate crash/retry delivery.
            $domain=parse_url(\envv('APP_URL'),PHP_URL_HOST)?:'sensor.local';
            $mail->MessageID='<sensor-mail-'.$job['id'].'@'.$domain.'>';
            $mail->send();
            \query("UPDATE mail_queue SET state='sent',sent_at=now(),last_error=NULL WHERE id=?",[$job['id']]);
        } catch(\Throwable $e) {
            $attempts=(int)$job['attempts']+1; $delay=min(3600,30*(2**min(7,$attempts-1)));
            // Avoid returning SMTP errors which may contain credentials to browsers/logs.
            $error='SMTP 发送失败，请检查主机、端口、TLS、授权码和发件人设置';
            \query('UPDATE mail_queue SET state=?,next_attempt=now()+make_interval(secs=>?),last_error=? WHERE id=?',[$attempts>=6?'failed':'pending',$delay,$error,$job['id']]);
        }
        return true;
    }
}
