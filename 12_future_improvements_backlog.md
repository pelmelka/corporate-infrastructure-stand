# Future improvements backlog

Этот файл хранит идеи будущих улучшений. Он нужен, чтобы не дублировать backlog по разным state/config sources. Текущие фактические состояния серверов фиксируются в server state files, а будущие улучшения — здесь.

## Product observability после этапа 13

Этап 13 завершен в минимальном production-like scope.

Реализовано сейчас:

```text
supportdesk_tickets_current{status,category,resource,priority}
supportdesk_active_ticket_age_seconds_max{category,resource,priority}
```

Реализованные Grafana panels:

```text
Open tickets by category
Active tickets by category/resource
Critical active tickets
Oldest active ticket age
```

Итоговые product alerts:

```text
SupportDeskApiDown
SupportDeskTooManyTicketsForResource
SupportDeskCriticalTicketsOpen
SupportDeskOldCriticalTicket
```

Старый `TooManyOpenTickets` удален как слишком общий и заменен более точным alert-ом по `category/resource`.

### Source dimension после Telegram bot / API-client

Пока `source` не добавлялся в базовую метрику, потому что сейчас почти все заявки приходят из `web`. После появления Telegram bot или отдельного API-клиента добавить source dimension:

```text
source=web
source=telegram
source=api
```

Возможная метрика:

```text
supportdesk_tickets_current_by_source{status,category,resource,priority,source}
```

Возможные вопросы:

```text
Сколько active-заявок пришло из web?
Сколько active-заявок пришло из Telegram?
Есть ли critical-заявки из Telegram?
```

### Event-based counters после PostgreSQL / ticket_events

Не добавлять честные counters поверх одного только `tickets.json`: при reopen и отсутствии event history они будут неоднозначны.

После появления PostgreSQL и таблицы `ticket_events` добавить:

```text
supportdesk_tickets_created_total{category,resource,priority,source}
supportdesk_tickets_resolved_total{category,resource,priority,source}
```

Возможные alerts:

```text
SupportDeskTicketSpike
SupportDeskCreatedOutpacesResolved
SupportDeskNoResolutionsForActiveBacklog
```

### Duration/SLA metrics после полноценной event observability

После event storage можно корректно считать время от создания до закрытия:

```text
supportdesk_ticket_resolution_duration_seconds_bucket{category,resource,priority,source,le}
supportdesk_ticket_resolution_duration_seconds_sum{category,resource,priority,source}
supportdesk_ticket_resolution_duration_seconds_count{category,resource,priority,source}
```

Возможные alerts:

```text
SupportDeskSlowResolution
SupportDeskSlaViolationRisk
```

Причина отложить: на этапе 13 уже добавлена простая и полезная метрика возраста active-заявки `supportdesk_active_ticket_age_seconds_max`; полноценная SLA-аналитика требует event-based storage.

## Logging improvements

### Оставить category как Loki label

Уже реализовано: Promtail на `app` добавляет `category` как dynamic Loki label.

Текущий подход считается правильным:

```text
хорошие labels: env, host, job, service, category
оставить в log fields: resource, ticket_id, client_ip, path, description
```

`resource` пока не выносить в Loki label, чтобы не увеличивать cardinality без необходимости. Для фильтрации достаточно:

```logql
{host="app", job="app", service="misis-digital-student-support-api", category="pay-misis"}
|= "resource=dorm-payment"
```

### Возможное улучшение App logs panel

Пока `ticket_list_requested` оставлен в dashboard, потому что он показывает активность UI/API. Если dashboard станет слишком шумным, можно создать две панели:

```text
App activity logs     -> включает ticket_list_requested
Ticket change events  -> только ticket_created/ticket_status_changed/ticket_status_unchanged
```

### Dashboard JSON export

Экспортировать Grafana dashboard JSON и хранить его в проектных источниках или в `~/control-node/files/grafana/`.

Плюсы:

```text
можно восстановить dashboard после переустановки Grafana
можно отслеживать изменения dashboard в Git
```

## HTTP/request observability

Этап 14 завершен в минимальном production-like scope.

Реализовано:

```text
supportdesk_http_requests_total{method,route,status_code}
supportdesk_http_request_duration_seconds_bucket/sum/count{method,route,status_code}
promtail_custom_nginx_http_responses_total{status_code}
```

Реализованные alerts:

```text
SupportDeskHigh5xxRate
SupportDeskHigh4xxRate
SupportDeskHighLatency
Nginx502Spike
```

Реализованные Grafana panels:

```text
HTTP/API Health Overview
API Request Rate by Route
API Responses by Status Code
API p95 Latency by Route
```

Сознательно не добавлялось:

```text
supportdesk_errors_total
supportdesk_4xx_total
supportdesk_5xx_total
```

Причина: эти сигналы уже считаются через `supportdesk_http_requests_total{status_code=...}`, а дублирующие counters усложняют dashboard и alerts.

Возможные будущие улучшения HTTP/API observability:

```text
экспортировать Grafana dashboard JSON в Git;
добавить отдельную Nginx Responses by Status Code panel, если понадобится подробный reverse proxy traffic view;
после Docker/DB проверить latency thresholds на более реалистичной нагрузке;
после появления DB добавить latency breakdown для DB-зависимых endpoints.
```

## Dockerization

Этап 15 завершен в экологичном scope.

Реализовано:

```text
Dockerize misis-digital-student-support-api на app
Docker Engine 29.4.3
Docker Compose v5.1.3
image misis-digital-student-support-api:local
container misis-digital-student-support-api
host 8080 -> container 8080
```

Не переносилось в Docker на текущем этапе:

```text
Prometheus
Grafana
Loki
Alertmanager
Nginx
node_exporter
admin
```

Сохраненные внешние контракты:

```text
внешний порт app остается 8080
Nginx продолжает ходить на app:8080
Prometheus продолжает scrape app:8080/metrics
Promtail продолжает читать /var/log/app/app.log через volume
```

Осознанный временный компромисс:

```text
/opt/app:/opt/app
```

Причина: текущий файловый storage использует `/opt/app/tickets.json`, временный файл и `os.replace()`. Mount одного файла `tickets.json` ломал POST/PATCH, потому что временный файл и итоговый файл оказывались на разных mount/filesystem слоях. До PostgreSQL этот workaround допустим. После перехода на PostgreSQL volume `/opt/app:/opt/app` нужно убрать.

Будущие Docker improvements:

```text
Dockerize support-bot позже
добавить registry/image tags после появления CI/CD или Ansible deploy v2
перейти с file logs на stdout/stderr + collector после стабилизации Docker/DB
```

## PostgreSQL / storage

Текущий storage: `/opt/app/tickets.json`.

PostgreSQL нужен не только как более надежное хранилище заявок, но и как основа для будущих event-based counters и SLA/duration metrics.

Будущая таблица `tickets`:

```text
id
schema_version
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

Рекомендуемая таблица `ticket_events` для counters, duration metrics и audit trail:

```text
id
ticket_id
event
old_status
new_status
source
created_at
metadata_json
```

## DB observability и backups

Этап DB observability и backups реализован.

Сделано:

```text
node_exporter на db
postgres_exporter на db
Prometheus job postgres
Grafana DB Health / DB Connections / DB Activity / PostgreSQL Important Logs
alerts PostgreSQLExporterDown / PostgreSQLDown / PostgreSQLTooManyConnections
PostgreSQL logs -> Promtail -> Loki
pg_dump -Fc backup
sha256 checksum
latest.dump symlink
restore test в supportdesk_restore_test
systemd service + timer
retention 7 days
```

Будущие улучшения для backup/DB observability:

```text
экспортировать Grafana dashboard JSON в Git;
добавить отдельный backup freshness alert после появления метрики/текстового collector-а;
добавить backup size / last successful backup panel;
перенести backups на отдельный storage или remote location;
добавить weekly/monthly tiered retention;
автоматизировать restore test отдельным playbook-ом;
добавить более глубокие PostgreSQL panels: locks, slow queries, cache hit ratio, WAL/checkpoints.
```

## Telegram support bot

Будущий второй клиент к тому же API v1. После его появления появится практический смысл добавлять `source` в product metrics.

Команды:

```text
/start
/new
/tickets
/resolve
```

Требования:

```text
создавать заявки через app API v1
писать source=telegram
использовать те же category/resource values
после стабилизации добавить source dimension в product metrics
bot token хранить вне Git
bot logs отправлять в Loki
```

## Security / hardening

Идеи:

```text
ограничить прямой доступ к app:8080
ограничить db:5432 только для app/admin-maintenance
добавить Nginx security headers
добавить body size limit
добавить proxy timeouts
добавить rate limiting
добавить HTTPS/self-signed cert или local CA
секреты хранить вне Git
права 600 на env-файлы
DHCP reservation или static IP
```

## Ansible automation v2

После ручной стабилизации Product model v2 стоит автоматизировать новую архитектуру.

Идеи playbook/roles:

```text
app.yml                 deploy /opt/app/app.py
frontend.yml            deploy /var/www/html/index.html
promtail.yml            deploy promtail config with category label
prometheus.yml          deploy prometheus config/rules
grafana.yml             provision dashboard/datasources later
docker_app.yml          deploy Dockerized app
postgres.yml            deploy DB
bot.yml                 deploy Telegram bot
backup.yml              run DB backup
```

## Final README/demo packaging

Что собрать к финалу:

```text
архитектура
IP/порты/сервисы
data flows
команды проверки
LogQL examples
PromQL examples
alerts list
dashboard screenshots
demo scripts
troubleshooting scenarios
backup/restore scenario
Proxmox snapshots checklist
```


## Реализовано на этапе 16: PostgreSQL-backed storage

Идея переноса storage с `/opt/app/tickets.json` на отдельный PostgreSQL server реализована.

Сделано:

```text
server db 192.168.85.139;
PostgreSQL 17;
database supportdesk;
tables tickets/ticket_events;
JSON -> PostgreSQL migration;
SQL-native GET/POST/PATCH/metrics;
legacy Python-list helpers removed from app.py.
```

Остается как future/backlog:

```text
DB observability: node_exporter/postgres_exporter, Prometheus, Grafana, alerts;
backup/restore: pg_dump, restore test;
source-based counters после Telegram/API-client;
SLA/resolution duration metrics на базе ticket_events;
секреты БД вне plain .env;
connection pooling при усложнении backend runtime.
```
