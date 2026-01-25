# Текущее состояние сервера app

## Назначение

`app` — backend/application server.

Роль: запускать Python-приложение, отвечать на HTTP-запросы, работать как `systemd` service, быть backend'ом для будущего reverse proxy на `web`, писать application logs и отправлять их в Loki через Promtail.

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
- Promtail: установлен и работает как `systemd` service

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

Текущая логика:

- слушает `0.0.0.0:8080`;
- `/` возвращает `app server is working`;
- `/health` возвращает `{"status": "ok"}`;
- остальные пути возвращают `404 not found`;
- пишет application logs в `/var/log/app/app.log`.

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

Перед изменением приложения был создан backup:

```text
/opt/app/app.py.bak-before-logging
```

## App logs

Созданы:

```text
/var/log/app
/var/log/app/app.log
```

Права:

```text
drwxr-x--- 2 pelmel adm ... /var/log/app
-rw-r----- 1 pelmel adm ... /var/log/app/app.log
```

Назначение:

- `pelmel` может писать в `app.log`, потому что `app.service` запускается от пользователя `pelmel`;
- группа `adm` может читать `app.log`, поэтому пользователь `promtail`, добавленный в `adm`, может читать application logs;
- остальные пользователи доступа не имеют.

Примеры строк в `/var/log/app/app.log`:

```text
2026-04-27 02:06:36,931 INFO service=python-backend method=GET path=/ status=200 client_ip=127.0.0.1
2026-04-27 02:06:45,581 INFO service=python-backend method=GET path=/health status=200 client_ip=127.0.0.1
2026-04-27 02:06:56,160 WARNING service=python-backend method=GET path=/bad-endpoint status=404 client_ip=127.0.0.1
```

## systemd unit приложения

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

## Проверки приложения

На `app`:

```bash
systemctl status app.service --no-pager
curl http://localhost:8080/
curl http://localhost:8080/health
curl http://localhost:8080/bad-endpoint
tail -n 20 /var/log/app/app.log
```

Получено:

```text
app.service active (running)
/ -> app server is working
/health -> {"status": "ok"}
/bad-endpoint -> not found
```

В `app.log` появились строки с `INFO` для `200` и `WARNING` для `404`.

С `admin` ранее проверялось:

```bash
curl http://192.168.85.133:8080
curl http://192.168.85.133:8080/health
```

Результаты успешные.

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

Проверка чтения app log:

```bash
sudo -u promtail test -r /var/log/app/app.log && echo "app.log readable"
```

Результат:

```text
app.log readable
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

Результат:

```text
Valid config file! No syntax issues found
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
```

Подтверждено:

```text
promtail.service active (running)
promtail.service enabled
порт 9080 LISTEN
Promtail добавил target /var/log/app/*.log
Promtail начал следить за /var/log/app
Promtail начал читать /var/log/app/app.log
```

В `journalctl` были важные строки:

```text
Adding target key="/var/log/app/*.log:{env=\"lab\", host=\"app\", job=\"app\", service=\"python-backend\"}"
watching new directory directory=/var/log/app
tail routine: started path=/var/log/app/app.log
```

Предупреждение `enable watchConfig` было замечено, но не критично: сервис работает.

## Проверка доставки app logs в Loki

Сгенерированы запросы на `app`:

```bash
curl http://localhost:8080/
curl http://localhost:8080/health
curl http://localhost:8080/bad-endpoint
```

Локально они появились в:

```bash
tail -n 20 /var/log/app/app.log
```

Проверка Loki через `query_range`:

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

Результат:

- Loki вернул `"status": "success"`;
- `resultType`: `streams`;
- найдены stream'ы с labels `host="app"`, `job="app"`, `service="python-backend"`, `env="lab"`;
- `filename="/var/log/app/app.log"`;
- в `values` есть строки `path=/`, `path=/health`, `path=/bad-endpoint`, `status=200`, `status=404`.

Дополнительно Loki/Promtail добавил `detected_level`:

```text
detected_level="info"
detected_level="warn"
```

Это нормально: строки `INFO` и `WARNING` попали в разные stream'ы по обнаруженному уровню.

## Текущий статус

`app` считается **готовым backend node с отправкой app logs в Loki**.

Готово:

- Python-приложение работает;
- `app.service` active/enabled;
- приложение пишет полезные логи в `/var/log/app/app.log`;
- Promtail 3.5.0 установлен;
- пользователь `promtail` создан и добавлен в `adm`;
- `promtail.service` active/enabled;
- Promtail читает `/var/log/app/*.log`;
- Promtail отправляет app logs в Loki на `http://192.168.85.135:3100/loki/api/v1/push`;
- Loki query_range возвращает app logs с labels `host=app`, `job=app`, `service=python-backend`, `env=lab`.

## Следующий шаг

Перейти к этапу **monitor / Prometheus / Grafana**:

- создать VM `monitor`;
- установить Debian 13;
- настроить SSH и sudo;
- установить Prometheus, Grafana, Alertmanager;
- затем добавить node_exporter на `web`, `app`, `log`, `monitor`;
- подключить Loki и Prometheus в Grafana.
