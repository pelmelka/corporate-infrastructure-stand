# Текущее состояние сервера app

## Назначение

`app` — backend/application server продукта `MISIS_Digital Student Support`.

Текущая роль:

- запускать Dockerized Python backend `misis-digital-student-support-api`;
- запускать Dockerized Telegram bot `misis-digital-support-bot`;
- принимать API-запросы от `web`/Nginx на `8080`;
- принимать API-запросы от `support-bot` внутри Docker Compose network;
- работать с PostgreSQL на отдельном сервере `db` (`192.168.85.139:5432`);
- хранить заявки не в локальном `tickets.json`, а в БД `supportdesk`;
- писать product logs в `/var/log/app/app.log`;
- отдавать product metrics и HTTP/API request metrics backend-а на `8080/metrics`;
- отдавать native bot metrics на `8090/metrics`;
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
- support-bot container: `misis-digital-support-bot`
- support-bot metrics: `8090/tcp`
- support-bot logs: `/var/log/bot/support-bot.log`

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


## Telegram support bot runtime

После этапа 18 на `app` запущен второй Docker Compose service:

```text
Compose service: support-bot
Container: misis-digital-support-bot
Image: misis-digital-support-bot:local
Runtime: python-telegram-bot long polling
Metrics endpoint: 8090/tcp -> container 8090
Logs: /var/log/bot/support-bot.log
```

Файлы:

```text
/opt/app/bot.py
/opt/app/Dockerfile.bot
/opt/app/requirements-bot.txt
/opt/app/.env.bot
/var/log/bot/support-bot.log
```

`.env.bot` содержит Telegram token и proxy-настройки, поэтому не фиксируется в Git/sources. В sources хранится только redacted template.

Текущий логический поток:

```text
Telegram user -> Telegram API -> support-bot container -> supportdesk-api container -> PostgreSQL
```

Бот не пишет в БД напрямую. Он вызывает backend API v1:

```text
GET  /v1/health
GET  /v1/support-model
GET  /v1/tickets
POST /v1/tickets
PATCH /v1/tickets/<id>/status
```

Создание/закрытие из Telegram передает `source=telegram`, что фиксируется в `tickets.source` и `ticket_events.source`.

Поддержанные команды и сценарии:

```text
/start     главное меню
/help      справка
/new       создание заявки кнопками
/tickets   active-заявки с пагинацией
/resolve   закрытие active-заявки с пагинацией
```

Поддержан whitelist через `ALLOWED_TELEGRAM_USER_IDS`, но сейчас он оставлен пустым для открытого lab/demo-доступа.

## Telegram bot observability on app

Bot logs пишутся отдельно от backend logs:

```text
/var/log/app/app.log             backend API
/var/log/bot/support-bot.log     Telegram bot
```

Promtail на app читает `/var/log/bot/*.log` отдельным stream-ом:

```logql
{host="app", job="support-bot", service="misis-digital-support-bot"}
```

Bot metrics отдаются на `8090/metrics`:

```text
support_bot_info{service,version}
support_bot_start_time_seconds
support_bot_actions_total{action}
support_bot_api_requests_total{method,endpoint,status_code}
support_bot_api_request_duration_seconds_bucket{method,endpoint,status_code,le}
support_bot_errors_total{type}
```

Нормализованные labels:

```text
action=category_selected/resource_selected/priority_selected/resolve_ticket/...;
endpoint=/v1/tickets, /v1/support-model, /v1/health, /v1/tickets/{id}/status;
status_code=200/201/error/4xx/5xx.
```

Проверенные команды:

```bash
cd /opt/app
sudo docker compose ps
curl -s http://localhost:8090/metrics | grep support_bot
sudo tail -n 50 /var/log/bot/support-bot.log
```

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


## Ansible operational check after DB stage

После этапа 17 `check_services.yml` больше не проверяет старый `app.service` как основной runtime.

Актуальная проверка `app` через Ansible:

```text
docker.service active
http://localhost:8080/v1/health -> 200
http://localhost:8080/metrics -> 200
promtail.service active
prometheus-node-exporter.service active
```

Это соответствует текущей архитектуре: backend работает в Docker container, а не как systemd `app.service`.

## Security/network hardening

UFW installed and active after Stage 19. Docker published ports are additionally restricted through `DOCKER-USER`.

Current UFW policy:

```text
default incoming: deny
default outgoing: allow
routed: disabled
```

Allowed inbound through UFW:

```text
192.168.85.129 -> 22/tcp     admin SSH/Ansible
192.168.85.131 -> 8080/tcp   web/Nginx to supportdesk-api
192.168.85.137 -> 8080/tcp   Prometheus supportdesk-api metrics
192.168.85.129 -> 8080/tcp   admin backend diagnostics
192.168.85.137 -> 8090/tcp   Prometheus support-bot metrics
192.168.85.129 -> 8090/tcp   admin bot metrics diagnostics
192.168.85.137 -> 9100/tcp   monitor node_exporter
192.168.85.129 -> 9100/tcp   admin node_exporter diagnostics
192.168.85.129 -> 9080/tcp   admin Promtail metrics diagnostics
```

Docker-specific hardening:

```text
DOCKER-USER allows web/admin/monitor to app:8080;
DOCKER-USER allows monitor/admin to app:8090;
DOCKER-USER drops all other ens18 traffic to 8080/8090;
Docker-internal support-bot -> supportdesk-api traffic is not blocked because rules match -i ens18.
```

Persistence:

```text
/usr/local/sbin/app-docker-user-firewall.sh
/etc/systemd/system/app-docker-user-firewall.service
```

Service state after reboot:

```text
systemctl is-enabled app-docker-user-firewall.service -> enabled
systemctl is-active app-docker-user-firewall.service  -> active
```

Confirmed after reboot:

```text
web -> app:8080 open;
monitor -> app:8080/8090/9100 open;
admin -> app:8080/8090 works;
db -> app:8080/8090 timed out;
Windows/browser direct access to app:8080/8090 is blocked;
Browser -> web -> app -> db still works.
```



## Ansible automation v2 management

После Stage 20 `app` управляется следующими Ansible ролями/playbook-ами:

```text
common
node_exporter
app_compose_project
docker_compose_service через deploy_app.yml/deploy_bot.yml
promtail
check.yml
network_audit.yml
```

`app_compose_project` закрепляет runtime contract:

```text
/opt/app code/config files -> root:root 0644
.env/.env.bot -> root:root 0600
/var/log/app, /var/log/bot -> pelmel:adm 2750
app.log/support-bot.log -> pelmel:adm 0640
```

`docker_compose_service` переиспользуется для `supportdesk-api` и `support-bot`; rebuild выполняется handler-ом `docker compose up -d --build <service>` только при изменении source files.

`promtail` деплоит `files/promtail/app-promtail.yml` в `/etc/promtail/config.yml` с правами `root:promtail 0640`.

Финальный `check.yml` после этапа: `app failed=0 changed=0`.
