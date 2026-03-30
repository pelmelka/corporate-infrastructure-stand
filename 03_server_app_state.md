# Текущее состояние сервера app

## Назначение

`app` — backend/application server.

Роль:

- запускать Dockerized Python backend `misis-digital-student-support-api`;
- обрабатывать API продукта `MISIS_Digital Student Support`;
- хранить заявки в lab storage `/opt/app/tickets.json`;
- писать product logs в `/var/log/app/app.log`;
- отдавать product metrics и HTTP/API request metrics на `/metrics`;
- работать как Docker container через `docker compose`;
- отправлять app logs в Loki через Promtail;
- отдавать системные метрики через node_exporter.

## Основная информация

- Hostname: `app`
- OS: Debian GNU/Linux 13 (trixie)
- IP: `192.168.85.133/24`
- Interface: `ens18`
- User: `pelmel`
- SSH/sudo: работают
- App runtime: Docker container `misis-digital-student-support-api` `Up` через `docker compose`
- Legacy app.service: `inactive/dead`, `disabled`, сохранен как rollback-вариант
- Docker Engine: `active/enabled`
- Promtail: `active/enabled`
- node_exporter: `active/enabled`

## Директория приложения

```text
/opt/app
```

Важные файлы:

```text
/opt/app/app.py
/opt/app/tickets.json
/opt/app/Dockerfile
/opt/app/docker-compose.yml
/opt/app/requirements.txt
/opt/app/.dockerignore
/opt/app/.env
/opt/app/backups/
```

Backup-и старых версий `app.py`, `tickets.json` и промежуточных Docker/compose правок перенесены в:

```text
/opt/app/backups/
```

Старые заявки из Mini Support Desk v1 сохранены в backup `tickets.json.bak-before-product-model-v2-*` внутри `backups/`. Рабочий `/opt/app/tickets.json` используется текущей моделью v2. Категория `legacy` сознательно не используется.

Полный текущий код `app.py`, а также Dockerfile, docker-compose.yml и .dockerignore фиксируются в `06_config_files_current.md`, а не дублируются здесь.

## Python-приложение

Текущая роль приложения: backend API продукта `MISIS_Digital Student Support`.

Приложение:

- слушает `0.0.0.0:8080` внутри Docker container;
- работает через Docker Compose service `supportdesk-api` / container `misis-digital-student-support-api`;
- возвращает API-ответы в JSON;
- хранит заявки в `/opt/app/tickets.json`;
- пишет product logs в `/var/log/app/app.log`;
- отдает product metrics и HTTP/API request metrics на `/metrics` в Prometheus text format;
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

## Docker runtime после этапа 15

Docker установлен на `app` как server-side Docker Engine.

Проверенное состояние:

```text
Docker Engine: 29.4.3
Docker Compose: v5.1.3
docker.service: active/enabled
image: misis-digital-student-support-api:local
container: misis-digital-student-support-api
compose service: supportdesk-api
external port: 8080 -> container 8080
```

Файлы Docker runtime:

```text
/opt/app/Dockerfile
/opt/app/docker-compose.yml
/opt/app/requirements.txt
/opt/app/.dockerignore
/opt/app/.env
```

Текущий compose-запуск:

```bash
cd /opt/app
sudo docker compose ps
sudo docker compose up -d
sudo docker compose restart
sudo docker compose down
```

Текущие volume mounts:

```text
/opt/app:/opt/app
/var/log/app:/var/log/app
```

Примечание: `/opt/app:/opt/app` — осознанный временный workaround до PostgreSQL stage. Первичная попытка монтировать только `/opt/app/tickets.json:/opt/app/tickets.json` ломала `POST/PATCH`, потому что приложение сохраняет данные через временный файл и `os.replace()`. Для такого способа записи `tickets.json` и `tickets.json.tmp` должны быть в одной mounted директории. После миграции на PostgreSQL этот volume должен быть убран: код будет жить в image, данные — в БД.

`/var/log/app:/var/log/app` сохранен, чтобы Promtail продолжал читать `/var/log/app/app.log` без изменения текущего Loki/Grafana flow. Позже app logs можно перенести в stdout/stderr и собирать контейнерные логи через отдельный collector.

Проверенные команды после Dockerization:

```bash
curl -s http://localhost:8080/v1/health | python3 -m json.tool
curl -s http://localhost:8080/metrics | head
curl -s http://192.168.85.131/api/v1/health | python3 -m json.tool
curl -s -X POST http://192.168.85.131/api/v1/tickets -H "Content-Type: application/json" -d '{...}'
curl -s -X PATCH http://192.168.85.131/api/v1/tickets/<id>/status -H "Content-Type: application/json" -d '{...}'
```

Подтверждено:

```text
health -> ok
metrics -> supportdesk_* and supportdesk_http_* доступны
POST ticket -> создает заявку
PATCH status -> меняет статус
Prometheus up{job="supportdesk-api"} -> 1
Nginx reverse proxy flow работает без изменения config
Loki/Grafana получают app logs через Promtail
```

## Legacy app.service после Dockerization

Файл systemd unit остался:

```text
/etc/systemd/system/app.service
```

Текущее состояние:

```text
app.service inactive/dead
app.service disabled
```

Сервис сохранен как rollback-вариант, но не должен автоматически стартовать после reboot, чтобы не конфликтовать с Docker container за порт `8080`.

Rollback на старый systemd runtime:

```bash
cd /opt/app
sudo docker compose down
sudo systemctl start app.service
```

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

Compatibility metrics:

```text
supportdesk_tickets_total
supportdesk_tickets_open
supportdesk_tickets_in_progress
supportdesk_tickets_resolved
supportdesk_tickets_active
```

Product observability v2 metrics:

```text
supportdesk_tickets_current{status,category,resource,priority}
supportdesk_active_ticket_age_seconds_max{category,resource,priority}
```

HTTP/API request observability metrics:

```text
supportdesk_http_requests_total{method,route,status_code}
supportdesk_http_request_duration_seconds_bucket{method,route,status_code,le}
supportdesk_http_request_duration_seconds_sum{method,route,status_code}
supportdesk_http_request_duration_seconds_count{method,route,status_code}
```

HTTP metrics реализованы через `prometheus_client` с отдельным `CollectorRegistry`, чтобы не засорять `/metrics` лишними runtime/process metrics. Старые product metrics остались ручными и совместимыми с существующими panels/alerts.

Принципы:

```text
/metrics не учитывается как пользовательский API request;
route label нормализуется: /v1/tickets/123/status -> /v1/tickets/{id}/status;
raw ticket_id и query string не попадают в labels;
ошибки считаются через status_code, отдельный supportdesk_errors_total не добавлялся как дублирующий.
```

`supportdesk_tickets_current` показывает текущее распределение заявок по статусу, цифровому сервису, ресурсу и приоритету.

`supportdesk_active_ticket_age_seconds_max` считает максимальный возраст активной заявки (`open` или `in_progress`) по `category/resource/priority`. Значение считается как `now - created_at`, поэтому для незакрытой заявки оно растет от scrape к scrape.

Prometheus на `monitor` собирает product и HTTP/API metrics отдельным scrape job:

```text
job="supportdesk-api"
instance="192.168.85.133:8080"
host="app"
service="support-desk-api"
env="lab"
```

Примечание: Prometheus job/metric names сохранены как `supportdesk-*`, чтобы не ломать существующие dashboard panels и alert rules. На этапе Product observability v2 добавлены только две минимальные product metrics; counters/source/duration отложены до PostgreSQL, `ticket_events` и Telegram/API-client stages.

## systemd unit приложения

Файл legacy unit:

```text
/etc/systemd/system/app.service
```

После Dockerization `app.service` больше не является основным runtime. Он отключен из автозапуска и находится в состоянии `inactive/dead`, но сохранен для rollback.

Старый способ запуска:

```text
User=pelmel
WorkingDirectory=/opt/app
ExecStart=/usr/bin/python3 /opt/app/app.py
Restart=always
```

Текущий основной способ запуска:

```bash
cd /opt/app
sudo docker compose up -d
```

Проверки текущего Docker runtime:

```bash
sudo docker compose ps
ss -tulpn | grep :8080
curl -s http://localhost:8080/v1/health | python3 -m json.tool
curl -s http://localhost:8080/metrics | head
```

Подтверждено:

- container `misis-digital-student-support-api` `Up`;
- порт `8080` слушает `docker-proxy`;
- `/v1/health` возвращает `MISIS_Digital Student Support` JSON;
- `/metrics` возвращает product metrics, Product observability v2 metrics и HTTP/API request metrics;
- `POST /v1/tickets` и `PATCH /v1/tickets/<id>/status` работают после volume fix;
- Prometheus `up{job="supportdesk-api"}` возвращает `1`.

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
- Product observability v2 metrics `supportdesk_tickets_current` и `supportdesk_active_ticket_age_seconds_max` работают и видны в Prometheus/Grafana;
- HTTP request counter и latency histogram работают, видны в Prometheus и используются в Grafana/alerts;
- системные метрики доступны Prometheus через node_exporter.


## Dockerization stage result

Этап 15 завершен: backend `MISIS_Digital Student Support API` перенесен из systemd-managed Python process в Docker container. Внешний контракт сохранен: `app:8080`, `/metrics`, Nginx reverse proxy, Prometheus scrape и Promtail/Loki flow работают без изменения внешних адресов и портов.
