# Текущее состояние сервера app

## Назначение

`app` — backend/application server.

Роль:

- запускать Python backend `misis-digital-student-support-api`;
- обрабатывать API продукта `MISIS_Digital Student Support`;
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
/opt/app/app.py.bak-before-product-model-v2
/opt/app/tickets.json
/opt/app/tickets.json.bak-before-product-model-v2-...
```

Старые заявки из Mini Support Desk v1 сохранены в backup `tickets.json.bak-before-product-model-v2-*`. Рабочий `/opt/app/tickets.json` очищен и используется только под новую модель v2. Категория `legacy` сознательно не используется.

Полный текущий код `app.py` фиксируется в `06_config_files_current.md`, а не дублируется здесь.

## Python-приложение

Текущая роль приложения: backend API продукта `MISIS_Digital Student Support`.

Приложение:

- слушает `0.0.0.0:8080`;
- работает через `app.service`;
- возвращает API-ответы в JSON;
- хранит заявки в `/opt/app/tickets.json`;
- пишет product logs в `/var/log/app/app.log`;
- отдает product metrics на `/metrics` в Prometheus text format;
- поддерживает legacy endpoints и новые `/v1/*` endpoints.

Product model v2:

```text
category = цифровой сервис университета
resource = раздел/функция внутри выбранного сервиса
```

Текущие category values:

```text
newlms-misis
lk-misis
gornyak-misis
folio-misis
pulse-misis
vector-misis
pay-misis
```

UI labels:

```text
newlms.misis.ru
lk.misis.ru
gornyak.misis.ru
folio.misis.ru
pulse.misis.ru
vector.misis.ru
pay.misis.ru
```

`category` и `resource` обязательны для новых заявок. Backend проверяет, что выбранный `resource` разрешен именно для выбранной `category`. Неправильная пара возвращает ошибку вида:

```text
invalid_resource_for_category:newlms-misis:plumber-request
```

Endpoints:

```text
GET    /health
GET    /v1/health
GET    /v1/support-model
GET    /tickets
GET    /v1/tickets
GET    /tickets/all
GET    /v1/tickets/all
GET    /tickets?status=resolved
GET    /v1/tickets?status=resolved
POST   /tickets
POST   /v1/tickets
GET    /tickets/<id>
GET    /v1/tickets/<id>
PATCH  /tickets/<id>/status
PATCH  /v1/tickets/<id>/status
GET    /metrics
```

Active/resolved logic:

```text
/tickets                    -> active tickets: open + in_progress
/tickets?status=resolved    -> resolved history
/tickets/all                -> all tickets
```

При переводе заявки в `resolved` заполняется `resolved_at`. При reopen обратно в `open`/`in_progress` поле `resolved_at` сбрасывается в `null`.

## Data storage

Текущий lab storage:

```text
/opt/app/tickets.json
```

Текущая schema для заявки:

```text
id
schema_version
title
category
category_label
resource
resource_label
description
priority
status
source
created_at
updated_at
resolved_at
```

Это простое файловое хранилище для учебного этапа. Запись выполняется через временный файл и `os.replace()`, чтобы снизить риск повреждения файла при перезаписи. Замена на PostgreSQL вынесена в roadmap/future improvements.

## Product logs

Файл:

```text
/var/log/app/app.log
```

Текущий формат: `key=value`, совместимый с LogQL `logfmt`.

Текущие поля product logs:

```text
service=misis-digital-student-support-api
event
method
path
status
client_ip
x_forwarded_for
x_forwarded_proto
api_version
ticket_id
category
resource
priority
source
old_status
new_status
resolved_at
reason / count при необходимости
```

Логика IP-полей:

```text
client_ip        = TCP peer для backend-а; обычно web/Nginx: 192.168.85.131
x_forwarded_for  = исходный клиент до Nginx; обычно Windows/Browser: 192.168.85.1
x_forwarded_proto = схема исходного запроса; сейчас http
```

Примеры product logs:

```text
service=misis-digital-student-support-api event=ticket_created method=POST path=/v1/tickets status=201 client_ip=192.168.85.131 x_forwarded_for=192.168.85.1 x_forwarded_proto=http api_version=v1 ticket_id=4 category=gornyak-misis resource=plumber-request priority=normal source=web
service=misis-digital-student-support-api event=ticket_status_changed method=PATCH path=/v1/tickets/2/status status=200 client_ip=192.168.85.131 x_forwarded_for=192.168.85.1 x_forwarded_proto=http api_version=v1 ticket_id=2 old_status=open new_status=in_progress category=pay-misis resource=dorm-payment source=web resolved_at=-
service=misis-digital-student-support-api event=ticket_status_unchanged method=PATCH path=/v1/tickets/2/status status=200 client_ip=192.168.85.131 x_forwarded_for=192.168.85.1 x_forwarded_proto=http api_version=v1 ticket_id=2 old_status=in_progress new_status=in_progress category=pay-misis resource=dorm-payment source=web
service=misis-digital-student-support-api event=ticket_list_requested method=GET path=/v1/tickets status=200 client_ip=192.168.85.131 x_forwarded_for=192.168.85.1 x_forwarded_proto=http api_version=v1 filter=active count=4
service=misis-digital-student-support-api event=metrics_requested method=GET path=/metrics status=200 client_ip=192.168.85.137 x_forwarded_for=- x_forwarded_proto=- api_version=legacy
```

Подтвержденные события:

```text
event=health_check
event=support_model_requested
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

Примечание: `ticket_list_requested` сознательно оставлен в dashboard/logs, потому что он показывает активность UI/API и подтверждает пользовательский путь `Browser -> web -> app`.

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
supportdesk_tickets_active
```

Prometheus на `monitor` собирает эти метрики отдельным scrape job:

```text
job="supportdesk-api"
instance="192.168.85.133:8080"
host="app"
service="support-desk-api"
env="lab"
```

Примечание: Prometheus job/metric names пока сохранены как `supportdesk-*`, чтобы не ломать существующие dashboard panels и alert rules. Переименование или добавление новых category/resource metrics запланировано на этап `Product observability v2`.

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
curl -s http://localhost:8080/v1/health | python3 -m json.tool
curl -s http://localhost:8080/v1/support-model | python3 -m json.tool
curl -s http://localhost:8080/v1/tickets | python3 -m json.tool
curl -s http://localhost:8080/metrics
```

Подтверждено:

- `app.service active (running)`;
- `/v1/health` возвращает `MISIS_Digital Student Support` JSON;
- `/v1/support-model` возвращает список цифровых сервисов и ресурсов;
- `/v1/tickets` возвращает active tickets;
- `/metrics` возвращает product metrics;
- неверная пара `category/resource` возвращает validation error;
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

Текущие static Promtail labels:

```text
host=app
job=app
service=misis-digital-student-support-api
env=lab
```

Текущий dynamic Loki label:

```text
category=<category из app log line>
```

`category` извлекается pipeline stage из log line вида `category=pay-misis`. Подтверждено, что Grafana Explore находит streams:

```logql
{host="app", job="app", category="gornyak-misis"}
{host="app", job="app", category="lk-misis"}
{host="app", job="app", service="misis-digital-student-support-api", category="pay-misis"}
```

`resource` пока не вынесен в Loki label и фильтруется как поле строки:

```logql
{host="app", job="app", service="misis-digital-student-support-api", category="pay-misis"}
|= "resource=dorm-payment"
```

Старые logs в Loki остаются в stream `service="support-desk-api"`; новые logs после обновления Promtail идут в stream `service="misis-digital-student-support-api"`.

## node_exporter

`prometheus-node-exporter.service` active/enabled, порт `9100` слушается. Prometheus видит target `host="app"`.

При остановке node_exporter на `app` должен срабатывать alert `NodeTargetDown`.

## Текущий статус

`app` считается готовым backend node для `MISIS_Digital Student Support`:

- API v1 работает;
- category/resource validation подтверждена;
- active/resolved разделение подтверждено;
- `resolved_at` работает;
- UI create/status/reopen flow подтвержден;
- product logs пишутся и доходят в Loki/Grafana;
- Loki category label работает;
- product metrics доступны на `/metrics` и собираются Prometheus;
- системные метрики доступны Prometheus через node_exporter.
