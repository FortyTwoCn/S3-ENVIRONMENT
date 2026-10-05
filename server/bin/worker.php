<?php
declare(strict_types=1);
require dirname(__DIR__).'/src/bootstrap.php';
if (in_array('--cleanup',$argv,true)) { echo jsonv(Monitor\Worker::cleanup()).PHP_EOL; exit; }
if (in_array('--once',$argv,true)) { Monitor\Worker::mailOne(); exit; }
$cleanupAt=0;
while(true) {
    try {
        if (time()>=$cleanupAt) { echo jsonv(Monitor\Worker::cleanup()).PHP_EOL; $cleanupAt=time()+3600; }
        if (!Monitor\Worker::mailOne()) sleep(3);
    } catch(Throwable $e) { error_log('Worker operation failed; retrying'); sleep(5); }
}
