# Текущее состояние сервера app

## Назначение

`app` — backend/application server продукта `MISIS_Digital Student Support`.

Текущая роль:

- запускать Dockerized Python backend `misis-digital-student-support-api`;
- принимать API-запросы от `web`/Nginx на `8080`;
- работать с PostgreSQL на отдельном сервере `db` (`192.168.85.139:5432`);
- хранить заявки не в локальном `tickets.json`, а в БД `supportdesk`;
- писать product logs в `/var/log/app/app.log`;
- отдавать product metrics и HTTP/API request metrics на `/metrics`;
- отправлять app logs в Loki через Promtail;
- отдавать системные метрики через node_exporter.

## Основная информация

- Hostname: `app`
- OS: Debian GNU/Linux 13 (trixie)
- IP: `192.168.85.133/24`
- Interface: `ens18`
- User: `pelmel`
- Runtime: Docker Compose
- Container: `misis-digital-student-support-api`
- Compose service: `supportdesk-api`
- Image: `misis-digital-student-support-api:local`
- External port: `8080 -> container 8080`
- Legacy `app.service`: `inactive/dead`, `disabled`, сохранен только как rollback-вариант
- Promtail: `active/enabled`
- node_exporter: `active/enabled`

## Директория приложения

```text
/opt/app
```

Важные файлы:

```text
/opt/app/app.py
/opt/app/Dockerfile
/opt/app/docker-compose.yml
/opt/app/requirements.txt
/opt/app/.dockerignore
/opt/app/.env
/opt/app/backups/
```

`/opt/app/tickets.json` больше не является рабочим storage. Он может оставаться на диске как legacy/migration artifact, но текущий backend после этапа 16 читает и пишет заявки через PostgreSQL.

Полный текущий код `app.py`, Dockerfile, Compose config, `.env` template, PostgreSQL DDL и важные команды фиксируются в `06_config_files_current.md`.

## Docker runtime

Текущий compose-запуск:

```bash
cd /opt/app
sudo docker compose build
sudo docker compose up -d
sudo docker compose ps
sudo docker compose restart
sudo docker compose down
```

Текущие volume mounts:

```text
/var/log/app:/var/log/app
```

Важно: старый transitional mount `/opt/app:/opt/app` удален после перехода на PostgreSQL. Теперь код живет внутри Docker image, а состояние приложения живет в PostgreSQL на `db`.

`/var/log/app:/var/log/app` сохранен, чтобы текущий Promtail продолжал читать `/var/log/app/app.log` без перестройки logging flow. Позже возможен переход на stdout/stderr container logs.

## DB connectivity

Backend получает параметры PostgreSQL из `/opt/app/.env`, который передается в container через `env_file`.

Текущие переменные окружения приложения:

```text
DB_HOST=192.168.85.139
DB_PORT=5432
DB_NAME=supportdesk
DB_USER=supportdesk_user
DB_PASSWORD=<хранится в /opt/app/.env, не фиксируется в sources>
```

Проверенные DB-связности:

```bash
PGPASSWORD='<redacted>' psql -h 192.168.85.139 -U supportdesk_user -d supportdesk -P pager=off -c "SELECT current_user, current_database(), inet_server_addr(), inet_client_addr();"
```

Подтверждено:

```text
current_user = supportdesk_user
current_database = supportdesk
inet_server_addr = 192.168.85.139
inet_client_addr = 192.168.85.133
```

## Python-приложение

Текущая роль приложения: backend API продукта `MISIS_Digital Student Support`.

Приложение:

- слушает `0.0.0.0:8080` внутри Docker container;
- возвращает API-ответы в JSON;
- использует PostgreSQL через `psycopg2`;
- читает заявки через SQL `SELECT`;
- создает заявки через SQL `INSERT ... RETURNING`;
- меняет статусы через `SELECT ... FOR UPDATE` + `UPDATE ... RETURNING`;
- пишет audit/event history в таблицу `ticket_events`;
- строит product metrics через SQL `COUNT`, `GROUP BY`, `MIN(created_at)`;
- пишет product logs в `/var/log/app/app.log`;
- поддерживает legacy endpoints и `/v1/*` endpoints.

Актуальная модель кода:

```text
GET /tickets        -> db_list_tickets()
GET /tickets/<id>   -> db_get_ticket()
GET /metrics        -> build_product_metrics_body_from_db()
POST /tickets       -> create_ticket_in_db()
PATCH /status       -> update_ticket_status_in_db()
```

Старый Python-list storage layer удален из кода:

```text
load_tickets()
save_tickets()
next_ticket_id()
active_tickets()
count_by_status()
ticket_age_seconds()
make_list_payload()
```

## Endpoints

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

## PostgreSQL-backed storage

Текущая БД:

```text
host: 192.168.85.139
port: 5432
database: supportdesk
role: supportdesk_user
schema: public
```

Основные таблицы:

```text
tickets        текущее состояние заявок
ticket_events  история событий и audit trail
```

Проверенный результат после миграции и финальной чистки:

```text
POST через web/Nginx создает новую строку в tickets.
ticket_events получает event=ticket_created.
metadata_json содержит write_path=sql_native и storage_backend=postgresql.
/opt/app/tickets.json больше не меняется как рабочее хранилище.
```

## Product logs

Файл:

```text
/var/log/app/app.log
```

Формат: `key=value`, совместимый с LogQL `logfmt`.

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
client_ip         = TCP peer backend-а; обычно web/Nginx: 192.168.85.131
x_forwarded_for   = исходный клиент до Nginx; обычно Windows/Browser: 192.168.85.1
x_forwarded_proto = схема исходного запроса; сейчас http
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

## Product metrics

Endpoint:

```text
GET /metrics
```

Product metrics теперь считаются из PostgreSQL SQL-запросами:

```text
supportdesk_tickets_total
supportdesk_tickets_open
supportdesk_tickets_in_progress
supportdesk_tickets_resolved
supportdesk_tickets_active
supportdesk_tickets_current{status,category,resource,priority}
supportdesk_active_ticket_age_seconds_max{category,resource,priority}
```

HTTP/API metrics реализованы через `prometheus_client`:

```text
supportdesk_http_requests_total{method,route,status_code}
supportdesk_http_request_duration_seconds_bucket{method,route,status_code,le}
supportdesk_http_request_duration_seconds_sum{method,route,status_code}
supportdesk_http_request_duration_seconds_count{method,route,status_code}
```

Принципы:

```text
/metrics не учитывается как пользовательский API request;
route label нормализуется: /v1/tickets/123/status -> /v1/tickets/{id}/status;
raw ticket_id и query string не попадают в labels;
product metrics берутся из PostgreSQL, а HTTP runtime metrics из in-memory prometheus_client registry.
```

Prometheus на `monitor` собирает metrics scrape job:

```text
job="supportdesk-api"
instance="192.168.85.133:8080"
host="app"
service="support-desk-api"
env="lab"
```

Примечание: Prometheus job/metric names сохранены как `supportdesk-*`, чтобы не ломать существующие dashboard panels и alert rules.

## Promtail

Promtail читает:

```text
/var/log/app/*.log
```

и отправляет logs в Loki:

```text
http://192.168.85.135:3100/loki/api/v1/push
```

Static labels:

```text
host=app
job=app
service=misis-digital-student-support-api
env=lab
```

Dynamic Loki label:

```text
category=<category из app log line>
```

## Текущий статус

`app` считается готовым backend node для PostgreSQL-backed `MISIS_Digital Student Support`:

- Docker container `misis-digital-student-support-api` `Up`;
- `/v1/health` возвращает `status=ok`;
- `/metrics` возвращает product и HTTP/API metrics;
- `GET /api/v1/tickets` идет через web/Nginx и возвращает заявки из PostgreSQL;
- `POST /api/v1/tickets` пишет в PostgreSQL через `INSERT ... RETURNING`;
- `PATCH /api/v1/tickets/<id>/status` пишет в PostgreSQL через `SELECT ... FOR UPDATE` + `UPDATE ... RETURNING`;
- `ticket_events` фиксирует `ticket_created` и `ticket_status_changed`;
- Prometheus `supportdesk-api` target `UP`;
- Loki/Grafana получают app logs через Promtail;
- старый `tickets.json` больше не является source of truth.
