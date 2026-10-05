FROM composer:2 AS vendor
WORKDIR /app
COPY composer.json composer.lock ./
RUN composer install --no-dev --no-interaction --prefer-dist --no-scripts --ignore-platform-req=ext-pdo_pgsql --ignore-platform-req=ext-sodium --ignore-platform-req=ext-mbstring
FROM php:8.5-fpm-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends libpq-dev ca-certificates \
    && docker-php-ext-install pdo_pgsql \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY . .
COPY --from=vendor /app/vendor /app/vendor
RUN mkdir -p /tmp/sensor-sessions && chown www-data:www-data /tmp/sensor-sessions \
    && printf '[www]\nclear_env = no\n' > /usr/local/etc/php-fpm.d/zz-env.conf \
    && printf 'expose_php=Off\ndisplay_errors=Off\nlog_errors=On\nerror_reporting=E_ALL\n' > /usr/local/etc/php/conf.d/sensor.ini
CMD ["php-fpm"]
