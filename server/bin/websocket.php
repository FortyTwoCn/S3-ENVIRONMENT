<?php
declare(strict_types=1);
require dirname(__DIR__).'/src/bootstrap.php';
$loop=React\EventLoop\Loop::get();
$hub=new Monitor\Hub();
$loop->addPeriodicTimer(1.0,fn()=>$hub->tick());
$socket=new React\Socket\SocketServer(envv('WS_BIND','0.0.0.0').':'.envv('WS_PORT','8081'),[],$loop);
$server=new Ratchet\Server\IoServer(new Ratchet\Http\HttpServer(new Monitor\BoundedWsServer($hub)),$socket,$loop);
echo 'WebSocket listening on '.envv('WS_BIND','0.0.0.0').':'.envv('WS_PORT','8081').PHP_EOL;
$loop->run();
