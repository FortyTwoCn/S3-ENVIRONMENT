<?php
declare(strict_types=1);
require dirname(__DIR__).'/src/bootstrap.php';
db()->exec(file_get_contents(dirname(__DIR__).'/database/schema.sql'));
echo "Database schema ready.\n";
