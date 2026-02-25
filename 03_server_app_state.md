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

Это простое файловое хранилище для учебного этапа. Замена на PostgreSQL вынесена в `12_future_improvements_backlog.md`.

## Product logs

Файл:

```text
/var/log/app/app.log
```

Текущий формат: `key=value`.

Примеры новых product logs:

```text
service=support-desk-api event=ticket_created method=POST path=/tickets status=201 client_ip=192.168.85.131 ticket_id=6 priority=high source=web
service=support-desk-api event=ticket_status_changed method=PATCH path=/tickets/6/status status=200 client_ip=192.168.85.131 ticket_id=6 old_status=in_progress new_status=resolved source=web
service=support-desk-api event=ticket_list_requested method=GET path=/tickets status=200 client_ip=192.168.85.131 count=6
service=support-desk-api event=health_check method=GET path=/health status=200 client_ip=192.168.85.131
```

Важно: `client_ip=192.168.85.131` нормально после reverse proxy, потому что для backend TCP-клиентом является Nginx на `web`. Future improvement: добавить отдельные поля `x_real_ip` и `x_forwarded_for`, не заменяя `client_ip`.

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

Сейчас `/metrics` реализован вручную в `app.py`. Переход на Prometheus client library и расширенные метрики вынесен в `12_future_improvements_backlog.md`.

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
- `/opt/app/tickets.json` существует и хранит заявки.

## Promtail

Promtail читает:

```text
/var/log/app/*.log
```

и отправляет logs в Loki:

```text
http://192.168.85.135:3100/loki/api/v1/push
```

Promtail labels сейчас:

```text
host=app
job=app
service=python-backend
env=lab
```

Примечание: внутри log line приложение уже пишет `service=support-desk-api`. Обновление Promtail label `service` можно рассмотреть на этапе Полировка logging.

## node_exporter

`prometheus-node-exporter.service` active/enabled, порт `9100` слушается. Prometheus видит target `host="app"`.

## Текущий статус

`app` считается готовым backend node для Mini Support Desk:

- `support-desk-api` работает;
- tickets create/list/status flow подтвержден;
- product logs пишутся;
- product metrics доступны на `/metrics`;
- app logs доходят в Loki/Grafana;
- системные метрики доступны Prometheus через node_exporter.
