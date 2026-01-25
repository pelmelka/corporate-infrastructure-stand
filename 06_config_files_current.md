# Важные текущие конфигурационные файлы проекта

## 1. Ansible inventory

Файл:

```text
admin: ~/control-node/inventory/hosts.ini
```

Текущее минимальное состояние:

```ini
[control]
admin ansible_connection=local

[all:vars]
ansible_user=pelmel
```

Будущий вариант:

```ini
[control]
admin ansible_connection=local

[web]
web ansible_host=192.168.85.131

[app]
app ansible_host=192.168.85.133

[log]
log ansible_host=192.168.85.135

[monitor]
monitor ansible_host=<IP_MONITOR>

[all:vars]
ansible_user=pelmel
```

## 2. Nginx default site

Файл:

```text
web: /etc/nginx/sites-available/default
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

## 3. Web HTML page

Файл:

```text
web: /var/www/html/index.html
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

## 4. Python app

Файл:

```text
app: /opt/app/app.py
```

Текущий код:

```python
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import logging

HOST = "0.0.0.0"
PORT = 8080
LOG_FILE = "/var/log/app/app.log"

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s service=python-backend %(message)s",
)


class AppHandler(BaseHTTPRequestHandler):
    def write_response(self, status_code, content_type, body):
        self.send_response(status_code)
        self.send_header("Content-Type", content_type)
        self.end_headers()
        self.wfile.write(body)

        level = logging.WARNING if status_code >= 400 else logging.INFO
        logging.log(
            level,
            "method=GET path=%s status=%s client_ip=%s",
            self.path,
            status_code,
            self.client_address[0],
        )

    def do_GET(self):
        if self.path == "/":
            self.write_response(
                200,
                "text/plain; charset=utf-8",
                b"app server is working\n",
            )
        elif self.path == "/health":
            self.write_response(
                200,
                "application/json",
                json.dumps({"status": "ok"}).encode(),
            )
        else:
            self.write_response(
                404,
                "text/plain; charset=utf-8",
                b"not found\n",
            )

    def log_message(self, format, *args):
        return


if __name__ == "__main__":
    server = HTTPServer((HOST, PORT), AppHandler)
    server.serve_forever()
```

Backup перед добавлением логирования:

```text
app: /opt/app/app.py.bak-before-logging
```

## 5. app log file

Файлы:

```text
app: /var/log/app
app: /var/log/app/app.log
```

Права:

```text
drwxr-x--- 2 pelmel adm ... /var/log/app
-rw-r----- 1 pelmel adm ... /var/log/app/app.log
```

Команды создания:

```bash
sudo mkdir -p /var/log/app
sudo touch /var/log/app/app.log
sudo chown -R pelmel:adm /var/log/app
sudo chmod 750 /var/log/app
sudo chmod 640 /var/log/app/app.log
```

Примеры логов:

```text
2026-04-27 02:06:36,931 INFO service=python-backend method=GET path=/ status=200 client_ip=127.0.0.1
2026-04-27 02:06:45,581 INFO service=python-backend method=GET path=/health status=200 client_ip=127.0.0.1
2026-04-27 02:06:56,160 WARNING service=python-backend method=GET path=/bad-endpoint status=404 client_ip=127.0.0.1
```

## 6. app systemd unit

Файл:

```text
app: /etc/systemd/system/app.service
```

Содержимое:

```ini
[Unit]
Description=Simple Python App Service
After=network.target

[Service]
User=pelmel
WorkingDirectory=/opt/app
ExecStart=/usr/bin/python3 /opt/app/app.py
Restart=always

[Install]
WantedBy=multi-user.target
```

## 7. Loki config

Файл:

```text
log: /etc/loki/config.yml
```

Содержимое:

```yaml
auth_enabled: false

server:
  http_listen_port: 3100

common:
  path_prefix: /var/lib/loki
  storage:
    filesystem:
      chunks_directory: /var/lib/loki/chunks
      rules_directory: /var/lib/loki/rules
  replication_factor: 1
  ring:
    kvstore:
      store: inmemory

schema_config:
  configs:
    - from: 2024-01-01
      store: tsdb
      object_store: filesystem
      schema: v13
      index:
        prefix: index_
        period: 24h

limits_config:
  allow_structured_metadata: true
  volume_enabled: true

ruler:
  alertmanager_url: http://localhost:9093
```

## 8. Loki systemd unit

Файл:

```text
log: /etc/systemd/system/loki.service
```

Содержимое:

```ini
[Unit]
Description=Loki Log Aggregation System
After=network.target

[Service]
User=loki
Group=loki
ExecStart=/opt/loki/loki -config.file=/etc/loki/config.yml
WorkingDirectory=/opt/loki
Restart=always

[Install]
WantedBy=multi-user.target
```

Команды применения:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now loki.service
```

Команды проверки:

```bash
systemctl status loki.service --no-pager
ss -tulpn | grep :3100
curl http://localhost:3100/ready
ps -o user,group,pid,cmd -C loki
```

Ожидаемое/полученное состояние:

```text
loki.service active (running)
autostart enabled
порт 3100 LISTEN
/ready -> ready
процесс работает от loki:loki
```

## 9. Promtail config для web

Файл:

```text
web: /etc/promtail/config.yml
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

Назначение:

- `server.http_listen_port: 9080` — служебный HTTP-порт Promtail;
- `grpc_listen_port: 0` — gRPC в нашем стенде не используем;
- `positions.filename` — файл, где Promtail запоминает, до какого места дочитал логи;
- `clients.url` — адрес Loki, куда отправлять логи;
- `__path__` — какие файлы читать;
- labels `host`, `job`, `service`, `env` — удобные фильтры для поиска логов в Loki/Grafana.

Права:

```bash
sudo chown promtail:promtail /etc/promtail/config.yml
sudo chmod 640 /etc/promtail/config.yml
```

## 10. Promtail systemd unit для web

Файл:

```text
web: /etc/systemd/system/promtail.service
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

Команды проверки:

```bash
systemctl status promtail.service --no-pager
ss -tulpn | grep :9080
sudo journalctl -u promtail.service -n 30 --no-pager
systemctl is-enabled promtail.service
systemctl is-active promtail.service
```

Полученное состояние:

```text
promtail.service active (running)
promtail.service enabled
порт 9080 LISTEN
Promtail читает /var/log/nginx/access.log
Promtail читает /var/log/nginx/error.log
```

## 11. Promtail config для app

Файл:

```text
app: /etc/promtail/config.yml
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
  - job_name: app
    static_configs:
      - targets:
          - localhost
        labels:
          host: app
          job: app
          service: python-backend
          env: lab
          __path__: /var/log/app/*.log
```

Права:

```bash
sudo chown promtail:promtail /etc/promtail/config.yml
sudo chmod 640 /etc/promtail/config.yml
```

Проверка синтаксиса:

```bash
sudo -u promtail /opt/promtail/promtail -config.file=/etc/promtail/config.yml -check-syntax
```

Полученное состояние:

```text
Valid config file! No syntax issues found
```

## 12. Promtail systemd unit для app

Файл:

```text
app: /etc/systemd/system/promtail.service
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

Команды проверки:

```bash
systemctl status promtail.service --no-pager
ss -tulpn | grep :9080
sudo journalctl -u promtail.service -n 30 --no-pager
```

Полученное состояние:

```text
promtail.service active (running)
promtail.service enabled
порт 9080 LISTEN
Promtail добавил target /var/log/app/*.log
Promtail начал читать /var/log/app/app.log
```

Важные строки из `journalctl`:

```text
Adding target key="/var/log/app/*.log:{env=\"lab\", host=\"app\", job=\"app\", service=\"python-backend\"}"
watching new directory directory=/var/log/app
tail routine: started path=/var/log/app/app.log
```

## 13. Проверка nginx logs в Loki

Сгенерировать запросы на `web`:

```bash
curl http://localhost/
curl http://localhost/not-found-promtail-test
curl http://localhost/
```

Проверить локальный nginx access log:

```bash
sudo tail -n 10 /var/log/nginx/access.log
```

Проверить в Loki через `query_range`:

```bash
START=$(date -d '15 minutes ago' +%s%N)
END=$(date +%s%N)

curl -G -s "http://192.168.85.135:3100/loki/api/v1/query_range" \
  --data-urlencode 'query={host="web",job="nginx"}' \
  --data-urlencode "start=$START" \
  --data-urlencode "end=$END" \
  --data-urlencode 'limit=10' \
  --data-urlencode 'direction=backward' | python3 -m json.tool
```

Ожидаемый/полученный результат:

```text
"status": "success"
labels: host=web, job=nginx, service=frontend, env=lab
values содержат nginx access log строки
```

## 14. Проверка app logs в Loki

Сгенерировать запросы на `app`:

```bash
curl http://localhost:8080/
curl http://localhost:8080/health
curl http://localhost:8080/bad-endpoint
```

Проверить локальный app log:

```bash
tail -n 20 /var/log/app/app.log
```

Проверить в Loki через `query_range`:

```bash
START=$(date -d '15 minutes ago' +%s%N)
END=$(date +%s%N)

curl -G -s "http://192.168.85.135:3100/loki/api/v1/query_range" \
  --data-urlencode 'query={host="app",job="app"}' \
  --data-urlencode "start=$START" \
  --data-urlencode "end=$END" \
  --data-urlencode 'limit=20' \
  --data-urlencode 'direction=backward' | python3 -m json.tool
```

Ожидаемый/полученный результат:

```text
"status": "success"
labels: host=app, job=app, service=python-backend, env=lab
filename=/var/log/app/app.log
values содержат path=/, path=/health, path=/bad-endpoint, status=200, status=404
```

## 15. Важное про Loki endpoints

- `/loki/api/v1/push` — endpoint для POST-запросов от Promtail, не страница для браузера.
- `HTTP ERROR 405` в браузере на `/push` — нормально.
- Обычные log queries нужно проверять через `/loki/api/v1/query_range`, а не через `/loki/api/v1/query`.
