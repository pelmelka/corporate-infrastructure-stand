# Текущее состояние сервера web

## Назначение

`web` — frontend / Nginx server.

Роль: отдавать веб-страницу, позже проксировать запросы к `app`, писать access/error логи, отправлять логи в Loki через Promtail, отдавать системные метрики через node_exporter.

## Основная информация

- Hostname: `web`
- OS: Debian GNU/Linux 13 (trixie)
- Kernel: Linux 6.12.74+deb13+1-amd64
- Virtualization: KVM
- IP: `192.168.85.131/24`
- Interface: `ens18`
- User: `pelmel`
- sudo: работает
- SSH: работает
- Nginx: работает
- Promtail: установлен и работает как `systemd` service
- node_exporter: установлен и работает как `systemd` service

## SSH и sudo

`ssh.service` работает, включен в автозапуск, порт 22 слушается. `sudo whoami` возвращает `root`.

## Nginx

Nginx установлен и запущен.

Проверки:

```bash
systemctl status nginx --no-pager
ss -tulpn | grep :80
curl http://localhost
```

Состояние:

- `nginx.service`: `active (running)`
- `nginx.service`: `enabled`
- порт `80`: слушается
- порт `9100`: слушается node_exporter
- `curl http://localhost`: возвращает пользовательский HTML

## Конфигурация Nginx

Файл:

```text
/etc/nginx/sites-available/default
```

Важные строки:

```nginx
root /var/www/html;
index index.html index.htm index.nginx-debian.html;
server_name _;
location / {
    try_files $uri $uri/ =404;
}
```

Nginx берет сайт из `/var/www/html` и первым ищет `index.html`.

## HTML-страница

Файл:

```text
/var/www/html/index.html
```

Текущее содержимое:

```html
<!doctype html>
<html>
<head>
    <meta charset="utf-8">
    <title>Web node</title>
</head>
<body>
    <h1>web server is working</h1>
    <p>Mini Corporate Infrastructure Lab</p>
</body>
</html>
```

Файл `/var/www/html/index.nginx-debian.html` остался, но не мешает, потому что `index.html` имеет приоритет.

## Nginx logs

Файлы:

```text
/var/log/nginx/access.log
/var/log/nginx/error.log
```

Права на момент настройки:

```text
-rw-r----- 1 www-data adm ... access.log
-rw-r----- 1 www-data adm ... error.log
```

Пользователь `promtail` добавлен в группу `adm`, поэтому может читать nginx-логи.

Проверка:

```bash
sudo -u promtail test -r /var/log/nginx/access.log && echo "access.log readable"
sudo -u promtail test -r /var/log/nginx/error.log && echo "error.log readable"
```

Результат:

```text
access.log readable
error.log readable
```

## Promtail

Promtail установлен вручную как бинарник.

Версия:

```bash
/opt/promtail/promtail --version
```

Результат:

```text
promtail, version 3.5.0
branch: k248
revision: 4b16bc4f
go version: go1.24.1
platform: linux/amd64
tags: promtail_journal_enabled
```

Пользователь:

```bash
id promtail
```

Результат:

```text
uid=988(promtail) gid=988(promtail) groups=988(promtail),4(adm)
```

Директории:

```text
/opt/promtail
/etc/promtail
/var/lib/promtail
```

Назначение:

- `/opt/promtail` — бинарник;
- `/etc/promtail` — конфиг;
- `/var/lib/promtail` — positions-файл, то есть служебное состояние чтения логов.

## Promtail config

Файл:

```text
/etc/promtail/config.yml
```

Содержимое:

```yaml
server:
  http_listen_port: 9080
  grpc_listen_port: 0

positions:
  filename: /var/lib/promtail/positions.yaml

clients:
  - url: http://192.168.85.135:3100/loki/api/v1/push

scrape_configs:
  - job_name: nginx
    static_configs:
      - targets:
          - localhost
        labels:
          host: web
          job: nginx
          service: frontend
          env: lab
          __path__: /var/log/nginx/*.log
```

Права:

```bash
sudo chown promtail:promtail /etc/promtail/config.yml
sudo chmod 640 /etc/promtail/config.yml
```

## Promtail systemd service

Файл:

```text
/etc/systemd/system/promtail.service
```

Содержимое:

```ini
[Unit]
Description=Promtail Log Shipping Agent
After=network.target

[Service]
User=promtail
Group=promtail
ExecStart=/opt/promtail/promtail -config.file=/etc/promtail/config.yml
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Команды применения:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now promtail.service
```

Проверки:

```bash
systemctl status promtail.service --no-pager
ss -tulpn | grep :9080
sudo journalctl -u promtail.service -n 30 --no-pager
systemctl is-enabled promtail.service
systemctl is-active promtail.service
```

Подтверждено:

```text
promtail.service active (running)
promtail.service enabled
порт 9080 LISTEN
Promtail начал читать /var/log/nginx/access.log
Promtail начал читать /var/log/nginx/error.log
```

В `journalctl` были важные строки:

```text
tail routine: started path=/var/log/nginx/access.log
tail routine: started path=/var/log/nginx/error.log
```


## node_exporter

`node_exporter` установлен из Debian-пакета:

```text
prometheus-node-exporter
```

Сервис:

```text
prometheus-node-exporter.service
```

Проверки на `web`:

```bash
systemctl status prometheus-node-exporter --no-pager
systemctl is-enabled prometheus-node-exporter
systemctl is-active prometheus-node-exporter
ss -tulpn | grep :9100
curl -s http://localhost:9100/metrics | head
```

Подтверждено:

```text
prometheus-node-exporter.service active (running)
prometheus-node-exporter.service enabled
порт 9100 LISTEN
/metrics возвращает системные метрики
```

Проверка с `monitor`:

```bash
curl -s http://192.168.85.131:9100/metrics | head
```

Результат: `monitor` получает метрики с `web`.

В Prometheus target добавлен как:

```text
instance="192.168.85.131:9100"
host="web"
job="node"
```

## Проверка доставки nginx logs в Loki

Сгенерированы запросы на `web`:

```bash
curl http://localhost/
curl http://localhost/not-found-promtail-test
curl http://localhost/
```

Локально они появились в:

```bash
sudo tail -n 10 /var/log/nginx/access.log
```

Примеры строк:

```text
::1 - - [26/Apr/2026:20:47:00 +0300] "GET / HTTP/1.1" 200 188 "-" "curl/8.14.1"
::1 - - [26/Apr/2026:20:47:17 +0300] "GET /not-found-promtail-test HTTP/1.1" 404 146 "-" "curl/8.14.1"
::1 - - [26/Apr/2026:20:47:33 +0300] "GET / HTTP/1.1" 200 188 "-" "curl/8.14.1"
```

Проверка Loki через `query_range`:

```bash
START=$(date -d '15 minutes ago' +%s%N)
END=$(date +%s%N)

curl -G -s "http://192.168.85.135:3100/loki/api/v1/query_range"   --data-urlencode 'query={host="web",job="nginx"}'   --data-urlencode "start=$START"   --data-urlencode "end=$END"   --data-urlencode 'limit=10'   --data-urlencode 'direction=backward' | python3 -m json.tool
```

Результат:

- Loki вернул `"status": "success"`;
- найден stream с labels `host="web"`, `job="nginx"`, `service="frontend"`, `env="lab"`;
- в `values` были строки `GET / HTTP/1.1` и `GET /not-found-promtail-test HTTP/1.1`.

## Важное замечание про `/loki/api/v1/push`

Адрес:

```text
http://192.168.85.135:3100/loki/api/v1/push
```

не является веб-страницей для браузера. Это API endpoint для POST-запросов от Promtail. При открытии в браузере может быть `HTTP ERROR 405`, и это нормально: браузер делает GET-запрос, а endpoint `/push` предназначен для отправки логов методом POST.

Для проверки доступности Loki использовать:

```bash
curl http://192.168.85.135:3100/ready
```

Для чтения логов использовать:

```text
/loki/api/v1/query_range
```

а не `/loki/api/v1/query`, потому что обычные log queries должны выполняться как range query.

## Проверка с admin

```bash
curl http://192.168.85.131
```

Результат: пользовательская страница `web server is working`.

## Статус

`web` считается **готовым frontend node с отправкой nginx logs в Loki**.

Готово:

- Nginx работает;
- HTML-страница отдается;
- nginx access/error logs существуют;
- Promtail установлен;
- node_exporter установлен;
- `promtail.service` active/enabled;
- `prometheus-node-exporter.service` active/enabled;
- Promtail читает `/var/log/nginx/*.log`;
- Promtail отправляет nginx logs в Loki на `log`;
- Loki query_range возвращает nginx access logs с labels `host=web`, `job=nginx`, `service=frontend`, `env=lab`;
- Prometheus видит системные метрики `web` через `192.168.85.131:9100` с label `host="web"`.

Осталось: более осмысленная страница, reverse proxy к `app`, подключение datasource/dashboard в Grafana.
