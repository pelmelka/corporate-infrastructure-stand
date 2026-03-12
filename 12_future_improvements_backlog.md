# Future improvements backlog

Этот файл хранит идеи будущих улучшений. Он нужен, чтобы не дублировать backlog по разным state/config sources. Текущие фактические состояния серверов фиксируются в server state files, а будущие улучшения — здесь.

## Product observability v2 для MISIS_Digital Student Support

Следующий приоритетный блок после Product model v2.

### Metrics by category/resource

Добавить в `/metrics`:

```text
supportdesk_tickets_by_status{status="open"}
supportdesk_tickets_by_category{category="newlms-misis",status="open"}
supportdesk_tickets_by_resource{category="newlms-misis",resource="schedule",status="open"}
supportdesk_tickets_by_priority{priority="critical",status="open"}
supportdesk_tickets_created_total{category,resource,priority,source}
supportdesk_tickets_resolved_total{category,resource}
```

Примеры продуктовых вопросов:

```text
Сколько открытых заявок по newlms.misis.ru?
Сколько проблем с schedule внутри newlms.misis.ru?
Какие resources чаще всего получают заявки?
Сколько critical-заявок сейчас открыто?
Сколько заявок пришло из web, а сколько потом из Telegram?
```

### Grafana panels

Идеи panels:

```text
Tickets by category
Open tickets by category
Top resources by open tickets
Critical tickets by category
Created tickets by source
Resolved tickets by category
```

### Product alerts

Идеи alerts:

```text
SupportDeskTooManyTicketsForCategory
SupportDeskTooManyTicketsForResource
SupportDeskCriticalTicketsOpen
SupportDeskTicketSpike
```

Примеры:

```text
category=newlms-misis resource=schedule >= 3 open tickets
→ Possible newlms.misis.ru schedule incident

category=gornyak-misis resource=plumber-request >= 3 open tickets
→ Possible gornyak.misis.ru service request issue

priority=critical status=open > 0 for 5m
→ Critical student support ticket is open
```

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

Добавить request-level метрики API:

```text
supportdesk_requests_total{method,path,status}
supportdesk_errors_total{status}
supportdesk_request_duration_seconds_bucket
supportdesk_request_duration_seconds_sum
supportdesk_request_duration_seconds_count
```

Возможные alerts:

```text
SupportDeskHigh5xxRate
SupportDeskHigh4xxRate
SupportDeskHighLatency
Nginx502Spike
```

Желательно перейти с ручного `/metrics` на Prometheus client library.

## Dockerization

Экологичный scope:

```text
Dockerize misis-digital-student-support-api
Dockerize support-bot позже
```

Не переносить в Docker на текущем этапе:

```text
Prometheus
Grafana
Loki
Alertmanager
Nginx
node_exporter
admin
```

Требования:

```text
внешний порт app остается 8080
Nginx продолжает ходить на app:8080
Prometheus продолжает scrape app:8080/metrics
Promtail продолжает читать /var/log/app/app.log через volume
```

## PostgreSQL / storage

Текущий storage: `/opt/app/tickets.json`.

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

Возможная таблица `ticket_events`:

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

После добавления PostgreSQL:

```text
postgres_exporter
PostgreSQL UP panel
connections panel
DB size panel
transaction rate panel
PostgreSQLDown alert
TooManyConnections alert
pg_dump backup
restore test
```

## Telegram support bot

Будущий второй клиент к тому же API v1.

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
bot token хранить вне Git
bot logs отправлять в Loki
```

## Security / hardening

Идеи:

```text
ограничить прямой доступ к app:8080
ограничить db:5432 после появления DB
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
