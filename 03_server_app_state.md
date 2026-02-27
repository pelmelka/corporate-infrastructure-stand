# Текущее состояние сервера app

## Назначение

`app` — backend/application server.

Роль:

- запускать Python backend `support-desk-api`;
- обрабатывать API Mini Support Desk;
- хранить заявки в lab storage `/opt/app/tickets.json`;
- писать product logs в `/var/log/app/app.log`;
- отдавать product metrics на `/metrics`;
- работать как `systemd` service;
- отправлять app logs в Loki через Promtail;
- отдавать системные метрики через node_exporter.

## Основная информация

- Hostname: `app`
- OS: Debian GNU/Linux 13 (trixie)
- IP: `192.168.85.133/24`
- Interface: `ens18`
- User: `pelmel`
- SSH/sudo: работают
- App service: `active/enabled`
- Promtail: `active/enabled`
- node_exporter: `active/enabled`

## Директория приложения

```text
/opt/app
```

Важные файлы:

```text
/opt/app/app.py
/opt/app/app.py.bak-before-supportdesk
/opt/app/app.py.bak-before-logging
/opt/app/app.py.bak-before-logging-polish
/opt/app/tickets.json
```

Полный текущий код `app.py` фиксируется в `06_config_files_current.md`, а не дублируется здесь.

## Python-приложение

Текущая роль приложения: backend API продукта Mini Support Desk.

Приложение:

- слушает `0.0.0.0:8080`;
- работает через `app.service`;
- возвращает API-ответы преимущественно в JSON;
- хранит заявки в `/opt/app/tickets.json`;
- пишет product logs в `/var/log/app/app.log`;
- отдает product metrics на `/metrics` в Prometheus text format.

Endpoints:

```text
GET    /health
GET    /tickets
POST   /tickets
GET    /tickets/<id>
PATCH  /tickets/<id>/status
GET    /metrics
```

## Data storage

Текущий lab storage:

```text
/opt/app/tickets.json
```

Это простое файловое хранилище для учебного этапа. Замена на PostgreSQL вынесена в roadmap/future improvements.

## Product logs

Файл:

```text
/var/log/app/app.log
```

Текущий формат: `key=value`, совместимый с LogQL `logfmt`.

Текущие поля product logs:

```text
service=support-desk-api
level через стандартный logging format
event
method
path
status
client_ip
x_forwarded_for
x_forwarded_proto
ticket_id / priority / source / old_status / new_status / reason / count при необходимости
```

Логика IP-полей:

```text
client_ip        = TCP peer для backend-а; обычно web/Nginx: 192.168.85.131
x_forwarded_for  = исходный клиент до Nginx; обычно Windows/Browser: 192.168.85.1
x_forwarded_proto = схема исходного запроса; сейчас http
```

`x_real_ip` сознательно не логируется, потому что в текущей single-proxy схеме он дублирует `x_forwarded_for`. Nginx может продолжать передавать `X-Real-IP`, но app logs используют только `x_forwarded_for` как более полезное proxy metadata.

Примеры product logs:

```text
service=support-desk-api event=ticket_created method=POST path=/tickets status=201 client_ip=192.168.85.131 x_forwarded_for=192.168.85.1 x_forwarded_proto=http ticket_id=8 priority=high source=web
service=support-desk-api event=ticket_status_changed method=PATCH path=/tickets/8/status status=200 client_ip=192.168.85.131 x_forwarded_for=192.168.85.1 x_forwarded_proto=http ticket_id=8 old_status=open new_status=in_progress source=web
service=support-desk-api event=ticket_status_unchanged method=PATCH path=/tickets/8/status status=200 client_ip=192.168.85.131 x_forwarded_for=192.168.85.1 x_forwarded_proto=http ticket_id=8 old_status=in_progress new_status=in_progress source=web
service=support-desk-api event=ticket_validation_failed method=POST path=/tickets status=400 client_ip=192.168.85.131 x_forwarded_for=192.168.85.1 x_forwarded_proto=http reason=missing_title source=web
service=support-desk-api event=ticket_not_found method=GET path=/tickets/999999 status=404 client_ip=192.168.85.131 x_forwarded_for=192.168.85.1 x_forwarded_proto=http ticket_id=999999
service=support-desk-api event=endpoint_not_found method=GET path=/bad-endpoint status=404 client_ip=192.168.85.131 x_forwarded_for=192.168.85.1 x_forwarded_proto=http
```

Подтвержденные события:

```text
event=health_check
event=ticket_list_requested
event=ticket_detail_requested
event=ticket_created
event=ticket_status_changed
event=ticket_status_unchanged
event=ticket_validation_failed
event=ticket_not_found
event=endpoint_not_found
event=metrics_requested
event=internal_error
```

Примечание: после подключения Prometheus scrape для app `/metrics` в logs регулярно появляются `event=metrics_requested` от `monitor` (`client_ip=192.168.85.137`). Это ожидаемо и пока оставлено как есть.

## Product metrics

Endpoint:

```text
GET /metrics
```

Текущие метрики:

```text
supportdesk_tickets_total
supportdesk_tickets_open
supportdesk_tickets_in_progress
supportdesk_tickets_resolved
```

Prometheus на `monitor` собирает эти метрики отдельным scrape job:

```text
job="supportdesk-api"
instance="192.168.85.133:8080"
host="app"
service="support-desk-api"
env="lab"
```

Сейчас `/metrics` реализован вручную в `app.py`. Переход на Prometheus client library и расширенные request/error/latency metrics вынесен в roadmap/future improvements.

## systemd unit приложения

Файл:

```text
/etc/systemd/system/app.service
```

Сервис работает как:

```text
User=pelmel
WorkingDirectory=/opt/app
ExecStart=/usr/bin/python3 /opt/app/app.py
Restart=always
```

Проверки:

```bash
systemctl status app.service --no-pager
curl http://localhost:8080/health
curl http://localhost:8080/tickets
curl http://localhost:8080/metrics
```

Подтверждено:

- `app.service active (running)`;
- `/health` возвращает `support-desk-api` JSON;
- `/tickets` возвращает список заявок;
- `/metrics` возвращает product metrics;
- `/opt/app/tickets.json` существует и хранит заявки;
- при остановке `app.service` alert `SupportDeskApiDown` переходит в `FIRING`.

## Promtail

Promtail читает:

```text
/var/log/app/*.log
```

и отправляет logs в Loki:

```text
http://192.168.85.135:3100/loki/api/v1/push
```

Текущие Promtail labels:

```text
host=app
job=app
service=support-desk-api
env=lab
```

Старые logs в Loki могут оставаться с label `service=python-backend`; новые logs после logging polish идут с `service=support-desk-api`.

## node_exporter

`prometheus-node-exporter.service` active/enabled, порт `9100` слушается. Prometheus видит target `host="app"`.

При остановке node_exporter на `app` должен срабатывать alert `NodeTargetDown`.

## Текущий статус

`app` считается готовым backend node для Mini Support Desk:

- `support-desk-api` работает;
- tickets create/list/status flow подтвержден;
- product logs пишутся и доходят в Loki/Grafana;
- product metrics доступны на `/metrics` и собираются Prometheus;
- alerts по app/API проверены;
- системные метрики доступны Prometheus через node_exporter.
