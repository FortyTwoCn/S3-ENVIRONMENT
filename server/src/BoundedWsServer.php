<?php
declare(strict_types=1);
namespace Monitor;
use Ratchet\ConnectionInterface;
use Ratchet\RFC6455\Messaging\CloseFrameChecker;
use Ratchet\RFC6455\Messaging\MessageBuffer;
use Ratchet\RFC6455\Messaging\MessageInterface;
use Ratchet\RFC6455\Messaging\FrameInterface;
use Psr\Http\Message\RequestInterface;
final class BoundedWsServer extends \Ratchet\WebSocket\WsServer {
    public function __construct(private Hub $hub) { parent::__construct($hub); }
    public function onOpen(ConnectionInterface $conn,?RequestInterface $request=null): void {
        parent::onOpen($conn,$request);
        if (!$this->connections->contains($conn)) return;
        $context=$this->connections[$conn]; $wsConn=$context->connection;
        // Bound the protocol buffer before accepting payload, not only after JSON decode.
        $context->buffer=new MessageBuffer(new CloseFrameChecker(),
            fn(MessageInterface $msg)=>$this->hub->onMessage($wsConn,$msg->getPayload()),
            fn(FrameInterface $frame)=>$this->onControlFrame($frame,$wsConn),true,null,8192,8192);
    }
}
