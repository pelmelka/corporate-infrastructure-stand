# Текущее состояние сервера app

## Назначение

`app` — backend/application server.

Роль: запускать Python-приложение, отвечать на HTTP-запросы, работать как systemd service, позже быть backend'ом для `web`, писать app logs, отдавать `/metrics`, отправлять логи в Loki через Promtail.

## Основная информация

- Hostname: `app`
- OS: Debian GNU/Linux 13 (trixie)
- Kernel: Linux 6.12.74+deb13+1-amd64
- Virtualization: KVM
- IP: `192.168.85.133/24`
- Interface: `ens18`
- Default gateway: `192.168.85.2`
- User: `pelmel`
- sudo: работает
- SSH: работает
- App service: работает

## Сеть

```text
interface: ens18
inet: 192.168.85.133/24
default via 192.168.85.2 dev ens18
```

DNS работает, `ping deb.debian.org` проходит.

## SSH и sudo

SSH работает и включен. `sudo whoami` возвращает `root`.

## Директория приложения

```text
/opt/app
```

Владелец должен быть `pelmel:pelmel`. `/opt` остается `root:root`.

## Python-приложение

Файл:

```text
/opt/app/app.py
```

Текущая логика: слушает `0.0.0.0:8080`; `/` возвращает `app server is working`; `/health` возвращает `{"status": "ok"}`; остальные пути возвращают 404.

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

## systemd unit

Файл:

```text
/etc/systemd/system/app.service
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

Сервис: `enabled`, `active (running)`, порт `8080` слушается, процесс идет от пользователя `pelmel`.

## Проверки

На `app`:

```bash
curl http://localhost:8080
curl http://localhost:8080/health
```

С `admin`:

```bash
curl http://192.168.85.133:8080
curl http://192.168.85.133:8080/health
```

Результаты успешные.

## Статус

`app` считается **минимально готовым application node**.

Осталось: возможно перейти на Flask, добавить `/info`, `/api/time`, `/api/status`, `/metrics`, осмысленные логи, JSON logs, Promtail, node_exporter, reverse proxy с `web`.
