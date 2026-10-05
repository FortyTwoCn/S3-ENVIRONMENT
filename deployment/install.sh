#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
if [ -f server/.env ]; then
    echo 'server/.env 已存在；保留原密钥与数据库配置。'
else
    echo '输入网站完整地址，例如 https://sensors.example.com 或本机测试 http://localhost:8080：'
    read -r site_url
    case "$site_url" in
        https://*) local_flag='' ;;
        http://*) local_flag='--local' ;;
        *) echo '地址格式无效'; exit 1 ;;
    esac
    # Initialization does not need Composer, DB or running services.
    docker run --rm -i --user "$(id -u):$(id -g)" -v "$PWD/server:/app" -w /app php:8.5-cli php bin/setup.php --url="$site_url" $local_flag
fi
echo '配置生成完成。局域网启动：'
echo 'docker compose --env-file server/.env up -d --build'
echo '公网部署请按 README 设置 SITE_ADDRESS，使用 compose.production.yaml。'
