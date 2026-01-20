# Текущее состояние сервера log

## Назначение

`log` — сервер централизованного логирования.

Роль: запускать Loki, принимать логи от Promtail с `web` и `app`, хранить логи, отдавать логи Grafana на `monitor`.

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

Права:

```bash
sudo chown loki:loki /etc/loki/config.yml
```

## Ручной запуск Loki

Команда:

```bash
sudo -u loki /opt/loki/loki -config.file=/etc/loki/config.yml
```

Loki успешно стартовал и слушал:

```text
http=[::]:3100
grpc=[::]:9095
```

Проверка:

```bash
curl http://localhost:3100/ready
```

Результат:

```text
ready
```

## 404 на корне

`http://192.168.85.135:3100` возвращал `404 page not found`. Это нормально: Loki — API-сервис, а не веб-сайт. Проверять нужно `/ready`, `/metrics` и API endpoints.

## Ingester not ready

С Windows один раз был ответ:

```text
Ingester not ready: waiting for 15s after being ready
```

Это нормально сразу после старта Loki.

## Остановка ручного процесса

При повторном запуске возникло:

```text
listen tcp :3100: bind: address already in use
```

Причина: ручной Loki уже занимал порт 3100. Через `ps -ef | grep loki` был найден процесс. Он был остановлен через `kill -9`. После этого `ss -tulpn | grep :3100` не показывал слушателей.

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

## Проверки после запуска через systemd

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

Проверка labels:

```bash
curl -s "http://192.168.85.135:3100/loki/api/v1/labels"
```

Результат включал:

```text
env
filename
host
job
service
service_name
```

Проверка логов через `query_range`:

```bash
START=$(date -d '15 minutes ago' +%s%N)
END=$(date +%s%N)

curl -G -s "http://192.168.85.135:3100/loki/api/v1/query_range"   --data-urlencode 'query={host="web",job="nginx"}'   --data-urlencode "start=$START"   --data-urlencode "end=$END"   --data-urlencode 'limit=10'   --data-urlencode 'direction=backward' | python3 -m json.tool
```

Результат:

- `"status": "success"`;
- `resultType`: `streams`;
- найден stream с `filename="/var/log/nginx/access.log"`;
- присутствовали строки `GET / HTTP/1.1` и `GET /not-found-promtail-test HTTP/1.1`.

Важно: `/loki/api/v1/push` не является страницей для браузера. При открытии через браузер может быть `HTTP ERROR 405`, потому что endpoint принимает POST-запросы от Promtail, а браузер делает GET.

Важно: для обычных log queries нужно использовать `/loki/api/v1/query_range`. Endpoint `/loki/api/v1/query` для такого запроса может вернуть ошибку `log queries are not supported as an instant query type`.

## Текущий статус

`log`: **готов как Loki logging server и уже принимает nginx logs от web**.

Loki 3.5.0 установлен, настроен, запущен через `loki.service`, включен в автозапуск, слушает порт `3100`, локальный `/ready` отвечает `ready`, проверка с `admin` тоже возвращает `ready`.

Дополнительно подтверждено: после настройки Promtail на `web` Loki возвращает nginx access logs по запросу `{host="web",job="nginx"}`.

## Следующий шаг

Перейти к этапу **Promtail на app**:

- решить, как собирать app logs: через файл или через journald;
- установить Promtail на `app`;
- настроить labels `host=app`, `job=app`, `service=python-backend`, `env=lab`;
- отправлять логи в Loki по адресу `http://192.168.85.135:3100/loki/api/v1/push`;
- запустить Promtail как `systemd` service;
- сгенерировать запросы к `app` и убедиться, что app logs дошли в Loki.
