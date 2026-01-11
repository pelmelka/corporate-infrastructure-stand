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

HOST = "0.0.0.0"
PORT = 8080

class AppHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"app server is working\n")
        elif self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok"}).encode())
        else:
            self.send_response(404)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"not found\n")

    def log_message(self, format, *args):
        return

if __name__ == "__main__":
    server = HTTPServer((HOST, PORT), AppHandler)
    server.serve_forever()
```

## 5. app systemd unit

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

## 6. Loki config

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

## 7. Loki systemd unit, планируемый

Файл:

```text
log: /etc/systemd/system/loki.service
```

Планируемое содержимое:

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

## 8. Будущий Promtail config для web, концепт

```yaml
server:
  http_listen_port: 9080

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

## 9. Будущий Promtail config для app, концепт

```yaml
server:
  http_listen_port: 9080

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

Финальный вариант для `app` может быть через journald или через файл логов.
