<?php
declare(strict_types=1);
namespace Monitor;
use Ratchet\ConnectionInterface;
use Ratchet\MessageComponentInterface;
final class Hub implements MessageComponentInterface {
    private \SplObjectStorage $clients;
    private array $devices=[];
    public function __construct() { $this->clients=new \SplObjectStorage(); \query('UPDATE devices SET connected=false'); }
    public function onOpen(ConnectionInterface $conn): void { $this->clients[$conn]=['role'=>null,'opened'=>time(),'last'=>time(),'rate_at'=>time(),'count'=>0]; }
    private function send(ConnectionInterface $c,array $m): void { $c->send(\jsonv($m)); }
    private function broadcast(array $m): void { foreach($this->clients as $c) if ($this->clients[$c]['role']==='browser') $this->send($c,$m); }
    public function onMessage(ConnectionInterface $conn,$msg): void {
        try {
            if (strlen($msg)>8192) throw new \InvalidArgumentException('message_too_large');
            $m=json_decode($msg,true,32,JSON_THROW_ON_ERROR); if (!is_array($m)) throw new \InvalidArgumentException('json_object_required');
            $meta=$this->clients[$conn];
            if (time()-$meta['rate_at']>=60) { $meta['rate_at']=time(); $meta['count']=0; }
            if (++$meta['count']>180) throw new \InvalidArgumentException('rate_limit');
            $meta['last']=time(); $this->clients[$conn]=$meta;
            if (!$meta['role']) { $this->authenticate($conn,$m); return; }
            if (($m['type']??'')==='ping') {
                if ($meta['role']==='device') \query('UPDATE devices SET last_seen=now() WHERE id=?',[$meta['id']]);
                $this->send($conn,['type'=>'pong','server_time'=>time()]); return;
            }
            if ($meta['role']!=='device') throw new \InvalidArgumentException('read_only_browser');
            if (($m['type']??'')==='telemetry') {
                $result=Telemetry::save($meta['id'],$m);
                \query('UPDATE devices SET last_seen=now() WHERE id=?',[$meta['id']]);
                $this->send($conn,['type'=>'telemetry_ack','boot_id'=>$result['boot_id'],'seq'=>$result['seq'],'dropped'=>$result['dropped']??null]);
                if (isset($result['sample'])) { $this->broadcast(['type'=>'sample','device_id'=>$meta['id'],'sample'=>$result['sample']]); $this->broadcast(['type'=>'refresh_commands']); }
            } elseif (($m['type']??'')==='command_ack') {
                $id=(string)($m['request_id']??''); if (!preg_match('/^[a-f0-9-]{36}$/',$id)) throw new \InvalidArgumentException('request_id');
                \query("UPDATE commands SET state='acked' WHERE id=? AND device_id=? AND state='sent' AND deadline>now()",[$id,$meta['id']]);
            } elseif (($m['type']??'')==='config_ack') {
                $this->broadcast(['type'=>'config_ack','device_id'=>$meta['id'],'version'=>$m['version']??null]);
            } else throw new \InvalidArgumentException('unknown_type');
        } catch(\InvalidArgumentException|\JsonException $e) { $this->send($conn,['type'=>'error','error'=>$e->getMessage()]); if ($e->getMessage()==='rate_limit') $conn->close(); }
        catch(\Throwable $e) { error_log('WS message failure: '.$e->getMessage()); $this->send($conn,['type'=>'error','error'=>'server_error']); }
    }
    private function authenticate(ConnectionInterface $conn,array $m): void {
        if (($m['type']??'')!=='hello' || ($m['v']??0)!==1) { $conn->close(); return; }
        $meta=$this->clients[$conn];
        if (($m['role']??'')==='device') {
            $token=$m['token']??''; if (!is_string($token) || strlen($token)!==64) { $conn->close(); return; }
            $d=\query('SELECT * FROM devices WHERE token_hash=? AND enabled=true',[hash('sha256',$token)])->fetch(\PDO::FETCH_ASSOC);
            if (!$d) { $conn->close(); return; }
            if (isset($this->devices[$d['id']])) $this->devices[$d['id']]->close();
            $meta['role']='device'; $meta['id']=$d['id']; $meta['version']=(int)$d['config_version']; $meta['token_hash']=$d['token_hash'];
            $this->devices[$d['id']]=$conn; $this->clients[$conn]=$meta;
            $fw=substr((string)($m['firmware']??''),0,80);
            \query('UPDATE devices SET connected=true,last_seen=now(),firmware=? WHERE id=?',[$fw,$d['id']]);
            $this->send($conn,['type'=>'welcome','device_id'=>$d['id'],'server_time'=>time(),'config_version'=>$meta['version'],'config'=>json_decode($d['config'],true)]);
            $this->broadcast(['type'=>'device_status','device_id'=>$d['id'],'online'=>true]);
        } elseif (($m['role']??'')==='browser') {
            $origin=$conn->httpRequest->getHeaderLine('Origin');
            if (rtrim($origin,'/')!==rtrim(\envv('APP_URL'),'/')) { $conn->close(); return; }
            $ticket=(string)($m['ticket']??''); if (strlen($ticket)!==64) { $conn->close(); return; }
            $t=\query('DELETE FROM ws_tickets WHERE token_hash=? AND expires_at>now() RETURNING remember_selector',[hash('sha256',$ticket)])->fetch(\PDO::FETCH_ASSOC);
            if (!$t || !\query('SELECT 1 FROM remember_tokens WHERE selector=? AND expires_at>now()',[$t['remember_selector']])->fetchColumn()) { $conn->close(); return; }
            $meta['role']='browser'; $meta['selector']=$t['remember_selector']; $this->clients[$conn]=$meta;
            $this->send($conn,['type'=>'welcome','server_time'=>time()]);
        } else $conn->close();
    }
    public function tick(): void {
        try {
            foreach($this->clients as $c) {
                $meta=$this->clients[$c];
                if ((!$meta['role'] && time()-$meta['opened']>10) || time()-$meta['last']>90) { $c->close(); continue; }
                if ($meta['role']==='browser' && !\query('SELECT 1 FROM remember_tokens WHERE selector=? AND expires_at>now()',[$meta['selector']])->fetchColumn()) { $c->close(); continue; }
                if ($meta['role']==='device') {
                    $d=\query('SELECT enabled,config_version,config,token_hash FROM devices WHERE id=?',[$meta['id']])->fetch(\PDO::FETCH_ASSOC);
                    if (!$d || !\boolv($d['enabled']) || !hash_equals($meta['token_hash'],$d['token_hash'])) { $c->close(); continue; }
                    if ((int)$d['config_version']!==$meta['version']) {
                        $meta['version']=(int)$d['config_version']; $this->clients[$c]=$meta;
                        $this->send($c,['type'=>'config','config_version'=>$meta['version'],'config'=>json_decode($d['config'],true)]);
                    }
                }
            }
            $expired=\query("UPDATE commands SET state='timeout' WHERE state IN ('queued','sent','acked') AND deadline<=now() RETURNING id")->fetchAll();
            if ($expired) $this->broadcast(['type'=>'refresh_commands']);
            foreach(\query("SELECT * FROM commands WHERE state='queued' AND deadline>now() ORDER BY created_at LIMIT 100")->fetchAll(\PDO::FETCH_ASSOC) as $cmd) {
                if (!isset($this->devices[$cmd['device_id']])) {
                    \query("UPDATE commands SET state='offline' WHERE id=? AND state='queued'",[$cmd['id']]); $this->broadcast(['type'=>'refresh_commands']); continue;
                }
                \query("UPDATE commands SET state='sent',sent_at=now() WHERE id=?",[$cmd['id']]);
                $this->send($this->devices[$cmd['device_id']],['type'=>'command','command'=>'sample_now','request_id'=>$cmd['id']]);
            }
        } catch(\Throwable $e) { error_log('WS tick failure: '.$e->getMessage()); }
    }
    public function onClose(ConnectionInterface $conn): void {
        if (!$this->clients->contains($conn)) return;
        $meta=$this->clients[$conn]; $this->clients->detach($conn);
        if (($meta['role']??'')==='device' && ($this->devices[$meta['id']]??null)===$conn) {
            unset($this->devices[$meta['id']]);
            try { \query('UPDATE devices SET connected=false WHERE id=?',[$meta['id']]); $this->broadcast(['type'=>'device_status','device_id'=>$meta['id'],'online'=>false]); } catch(\Throwable $e) { error_log('WS close DB failed'); }
        }
    }
    public function onError(ConnectionInterface $conn,\Exception $e): void { error_log('WS connection error'); $conn->close(); }
}
