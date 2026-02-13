# Текущее состояние сервера log

## Назначение

`log` — сервер централизованного логирования.

Роль: запускать Loki, принимать логи от Promtail с `web` и `app`, хранить логи, отдавать логи Grafana на будущем сервере `monitor`.

## Основная информация

- Hostname: `log`
- OS: Debian GNU/Linux 13 (trixie)
- Kernel: Linux 6.12.74+deb13+1-amd64
- Virtualization: KVM
- IP: `192.168.85.135/24`
- Interface: `ens18`
- Default gateway: `192.168.85.2`
- User: `pelmel`
- sudo: работает
- SSH: работает
- Loki: установлен и работает как `systemd` service
- Принимает logs от `web` и `app`
- node_exporter: установлен и работает как `systemd` service

## Сеть

```text
interface: ens18
inet: 192.168.85.135/24
default via 192.168.85.2 dev ens18
```

DNS и интернет работают, `ping deb.debian.org` проходит.

## SSH и sudo

SSH работает и включен. `sudo whoami` возвращает `root`.

## Loki: пользователь и директории

Создан системный пользователь:

```bash
sudo useradd --system --no-create-home --shell /usr/sbin/nologin loki
```

Директории:

```text
/opt/loki
/etc/loki
/var/lib/loki
```

Права: `loki:loki`.

Назначение:

- `/opt/loki` — бинарник;
- `/etc/loki` — конфиг;
- `/var/lib/loki` — данные.

## Loki: версия

```bash
/opt/loki/loki --version
```

Вывод:

```text
loki, version 3.5.0
branch: k248
revision: 4b16bc4f
go version: go1.24.1
platform: linux/amd64
```

## Loki config

Файл:

```text
/etc/loki/config.yml
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
    instance_addr: 127.0.0.1
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

memberlist:
  advertise_addr: 127.0.0.1
```

Права:

```bash
sudo chown loki:loki /etc/loki/config.yml
```

## Loki systemd service

Файл:

```text
/etc/systemd/system/loki.service
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

После создания unit-файла выполнено:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now loki.service
```

Проверка статуса показала:

```text
Loaded: loaded (...; enabled; ...)
Active: active (running)
Main PID: loki
```

## Проверки Loki

На `log` выполнено:

```bash
ss -tulpn | grep :3100
curl http://localhost:3100/ready
ps -o user,group,pid,cmd -C loki
```

Подтверждено:

```text
порт 3100 слушается
/ready -> ready
процесс работает от пользователя loki и группы loki
```

С `admin` выполнено:

```bash
curl http://192.168.85.135:3100/ready
```

Результат:

```text
ready
```

## 404 на корне

`http://192.168.85.135:3100` может возвращать `404 page not found`. Это нормально: Loki — API-сервис, а не веб-сайт. Проверять нужно `/ready`, `/metrics` и API endpoints.

## Ingester not ready

Сразу после старта Loki может быть ответ:

```text
Ingester not ready: waiting for 15s after being ready
```

Это нормально сразу после запуска Loki.

## Исправление автозапуска Loki после reboot

После выключения и повторного включения VM была обнаружена проблема: `loki.service` был `enabled`, но переходил в состояние `failed` сразу после старта.

Симптомы:

```text
Active: failed (Result: exit-code)
no usable address found for interfaces [eth0 en0]
error initialising module: memberlist-kv
Start request repeated too quickly
```

Причина: Loki при старте пытался найти интерфейсы `eth0` или `en0`, но на Debian VM сетевой интерфейс называется `ens18`. Для single-node Loki не нужно завязываться на имя внешнего интерфейса, поэтому для внутреннего ring/memberlist-механизма явно указан `127.0.0.1`.

В `/etc/loki/config.yml` добавлены параметры:

```yaml
common:
  ring:
    instance_addr: 127.0.0.1
    kvstore:
      store: inmemory

memberlist:
  advertise_addr: 127.0.0.1
```

Проверка конфига:

```bash
sudo -u loki /opt/loki/loki -config.file=/etc/loki/config.yml -verify-config
```

Результат:

```text
config is valid
```

После исправления выполнено:

```bash
sudo systemctl reset-failed loki.service
sudo systemctl restart loki.service
systemctl status loki.service --no-pager
curl http://localhost:3100/ready
sudo reboot
```

После reboot `loki.service` снова поднялся в состоянии `active (running)`, `/ready` после короткого периода `Ingester not ready...` вернул `ready`.

## Проверка приема логов от web

После настройки Promtail на `web` Loki успешно принимает nginx logs.

Источник логов:

```text
web: /var/log/nginx/access.log
web: /var/log/nginx/error.log
```

Promtail на `web` отправляет данные в Loki по адресу:

```text
http://192.168.85.135:3100/loki/api/v1/push
```

Labels для nginx logs:

```text
host=web
job=nginx
service=frontend
env=lab
```

Проверка логов через `query_range`:

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

Результат:

- `"status": "success"`;
- `resultType`: `streams`;
- найден stream с `filename="/var/log/nginx/access.log"`;
- присутствовали строки `GET / HTTP/1.1` и `GET /not-found-promtail-test HTTP/1.1`.

## Проверка приема логов от app

После настройки Promtail на `app` Loki успешно принимает app logs.

Источник логов:

```text
app: /var/log/app/app.log
```

Promtail на `app` отправляет данные в Loki по адресу:

```text
http://192.168.85.135:3100/loki/api/v1/push
```

Labels для app logs:

```text
host=app
job=app
service=python-backend
env=lab
```

Проверка логов через `query_range`:

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

- `"status": "success"`;
- `resultType`: `streams`;
- найдены stream'ы с `filename="/var/log/app/app.log"`;
- labels включают `host="app"`, `job="app"`, `service="python-backend"`, `env="lab"`;
- в `values` были строки `path=/`, `path=/health`, `path=/bad-endpoint`, `status=200`, `status=404`.

Дополнительно Loki/Promtail добавил `detected_level="info"` и `detected_level="warn"`. Это нормально: строки `INFO` и `WARNING` попали в разные stream'ы по обнаруженному уровню.


## node_exporter

`node_exporter` установлен из Debian-пакета:

```text
prometheus-node-exporter
```

Сервис:

```text
prometheus-node-exporter.service
```

Проверки на `log`:

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
curl -s http://192.168.85.135:9100/metrics | head
```

Результат: `monitor` получает метрики с `log`.

В Prometheus target добавлен как:

```text
instance="192.168.85.135:9100"
host="log"
job="node"
```

## Важные замечания про Loki endpoints

Адрес:

```text
http://192.168.85.135:3100/loki/api/v1/push
```

не является страницей для браузера. Это API endpoint для POST-запросов от Promtail. При открытии через браузер может быть `HTTP ERROR 405`, потому что endpoint принимает POST-запросы от Promtail, а браузер делает GET.

Для обычных log queries нужно использовать:

```text
/loki/api/v1/query_range
```

Endpoint `/loki/api/v1/query` для обычного log query может вернуть ошибку `log queries are not supported as an instant query type`.

## Текущий статус

`log`: **готов как Loki logging server, принимает nginx/app logs и отдает системные метрики через node_exporter**.

Loki 3.5.0 установлен, настроен, запущен через `loki.service`, включен в автозапуск, слушает порт `3100`, локальный `/ready` отвечает `ready`, проверка с `admin` тоже возвращает `ready`. После дополнительного исправления `common.ring.instance_addr` и `memberlist.advertise_addr` сервис также успешно поднимается после reboot VM.

Дополнительно подтверждено:

- запрос `{host="web",job="nginx"}` через `/loki/api/v1/query_range` возвращает nginx access logs;
- запрос `{host="app",job="app"}` через `/loki/api/v1/query_range` возвращает app logs;
- Prometheus видит системные метрики `log` через `192.168.85.135:9100` с label `host="log"`.

## Следующий шаг

Следующий этап: **Grafana datasources и dashboard**:

- подключить Prometheus datasource в Grafana;
- подключить Loki datasource в Grafana;
- проверить Loki-запросы в Grafana;
- начать dashboard Infrastructure Overview.
