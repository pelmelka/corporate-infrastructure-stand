# Future improvements backlog

Этот файл хранит идеи будущих улучшений. Он нужен, чтобы не дублировать backlog по разным state/config sources. Текущие фактические состояния серверов фиксируются в server state files, а будущие улучшения — здесь.

## Logging improvements

### 1. Structured JSON logs

Перевести app product logs с текущего учебного `key=value` формата на structured JSON logs.

Текущий формат:

```text
event=ticket_created method=POST path=/tickets status=201 ticket_id=6 source=web
```

Будущий формат:

```json
{"level":"INFO","service":"support-desk-api","event":"ticket_created","method":"POST","path":"/tickets","status":201,"ticket_id":6,"source":"web"}
```

Плюсы:

- проще парсить в Loki/ELK/Splunk;
- меньше зависимости от regexp;
- удобнее фильтровать по `event`, `status`, `source`, `resource`, `category`;
- лучше подходит для dashboards и alerts.

Статус: не срочно. Текущий `key=value` формат нормально работает через LogQL `logfmt`.

### 2. logrotate для `/var/log/app/app.log`

Добавить ротацию app logs:

```text
/var/log/app/app.log
/var/log/app/app.log.1
/var/log/app/app.log.2.gz
```

Причина: без logrotate файл будет расти бесконечно.

Статус: полезное небольшое улучшение, но не блокирует текущий проект.

### 3. `metrics_requested` noise после Prometheus scrape

После подключения Prometheus scrape `app:/metrics` в app logs регулярно появляются:

```text
event=metrics_requested method=GET path=/metrics
```

Варианты:

- оставить как есть — видно, что Prometheus реально ходит за метриками;
- убрать `/metrics` из dashboard App logs query;
- не логировать успешные `/metrics`, а логировать только ошибки;
- писать технические events отдельно от product events.

Статус: пока оставлено как есть.

### 4. Request ID для связки Nginx log и app log

Добавить `request_id`, чтобы связать один пользовательский запрос между слоями:

```text
nginx: request_id=abc123 PATCH /api/tickets/7/status -> 200
app:   request_id=abc123 event=ticket_status_changed ticket_id=7
```

Потребуется:

- добавить/использовать request id в Nginx;
- передавать header в app;
- логировать `request_id` в app logs;
- обновить Nginx log_format.

### 5. duration_ms / request_time / upstream_response_time

Добавить время обработки запросов:

```text
app log: duration_ms=12
nginx log: request_time=0.013 upstream_response_time=0.011
```

Это позволит различать:

- сколько запрос занял на Nginx;
- сколько реально обрабатывал backend;
- где появилась задержка.

## Product/data improvements

### 1. Resource/category fields in tickets

Добавить в ticket model поля:

```text
resource
category
```

Примеры:

```text
resource=grafana, category=observability
resource=prometheus, category=observability
resource=loki, category=observability
resource=vpn, category=access
resource=ssh, category=access
resource=web, category=application
resource=app, category=application
resource=database, category=database
resource=telegram-bot, category=application
```

Использование:

- заменить/дополнить свободный `Title` dropdown-ами `Resource` и `Category`;
- писать `resource` и `category` в product logs;
- фильтровать tickets в Loki по resource/category;
- строить product metrics и alerts по resource/category.

### 2. Active/resolved tickets

Сделать так, чтобы при переходе в `resolved` заявка исчезала из активного списка, но сохранялась в истории.

Возможная API-логика:

```text
GET /tickets                  -> open + in_progress
GET /tickets?status=resolved  -> resolved
GET /tickets/all              -> all tickets
GET /tickets/<id>             -> конкретная заявка независимо от статуса
```

Добавить поле:

```text
resolved_at
```

### 3. API versioning

Позже перейти с:

```text
/api/tickets
```

на:

```text
/api/v1/tickets
```

Это нужно, если API будет развиваться и потребуется сохранить совместимость frontend/bot с разными версиями backend.

### 4. Ticket events/history

Добавить таблицу/модель истории:

```text
ticket_events:
- ticket_created
- status_changed
- comment_added
- ticket_resolved
```

Польза:

- аудит изменений;
- история заявки;
- richer product logs;
- метрики resolution time.

## Monitoring improvements

### 1. Product metrics by resource/category

После появления `resource` и `category` добавить:

```text
supportdesk_tickets_by_resource{resource="grafana",status="open"}
supportdesk_tickets_by_category{category="observability",status="open"}
supportdesk_tickets_by_priority{priority="critical",status="open"}
supportdesk_tickets_created_total{resource,category,priority,source}
supportdesk_tickets_resolved_total{resource,category}
```

### 2. Product alerts

Будущие product alerts для Mini Support Desk:

1. `SupportDeskTooManyOpenTickets` — слишком много открытых заявок вообще. Текущий вариант уже реализован как `TooManyOpenTickets`.
2. `SupportDeskTicketSpike` — за короткий период создано слишком много заявок.
3. `SupportDeskTooManyTicketsForResource` — много открытых заявок на один ресурс.
4. `SupportDeskCategoryIncident` — много заявок по группе смежных ресурсов.
5. `SupportDeskCriticalTicketsOpen` — есть открытые critical-заявки дольше N минут.

### 3. HTTP status / error-rate alerts

Добавить error-rate alerts по HTTP-статусам:

- если доля 5xx ответов выше 5% за 5 минут — warning/critical alert;
- если Nginx часто возвращает 502 — вероятно backend app недоступен;
- если растет количество 500 от app — вероятно ошибка внутри backend-кода;
- если растет количество 400/404 — возможно frontend вызывает неправильный API, пользователи отправляют некорректные данные или есть лишний/мусорный трафик.

Для реализации желательно добавить application/request metrics:

```text
supportdesk_requests_total{method,path,status}
supportdesk_errors_total{status}
supportdesk_request_duration_seconds
```

### 4. Prometheus client library

Сейчас app `/metrics` реализован вручную. Это нормально для lab-этапа.

Для production-like реализации позже перейти на Prometheus client library и добавить стандартные application metrics:

- `supportdesk_requests_total`;
- `supportdesk_request_duration_seconds`;
- `supportdesk_errors_total`;
- `supportdesk_tickets_created_total`;
- `supportdesk_tickets_open`;
- `supportdesk_tickets_by_status{status="open|in_progress|resolved"}`;
- `supportdesk_tickets_by_resource{resource="grafana|vpn|web|app|..."}`;
- `supportdesk_tickets_by_category{category="observability|access|application|..."}`.

### 5. Monitoring of monitoring

Текущая lab-схема single-node monitoring:

```text
monitor = Prometheus + Grafana + Alertmanager
```

Ограничение: если весь `monitor` VM упадет, сам Prometheus не сможет отправить alert о собственном полном падении.

Future improvement:

```text
admin или внешний watchdog -> monitor health endpoints
```

Проверки:

```text
monitor:9090/-/ready
monitor:3000/api/health
monitor:9093/-/ready
```

Варианты реализации:

- lightweight cron/systemd timer на `admin`;
- blackbox exporter;
- второй Prometheus;
- внешний uptime check.

## Dockerization

Docker стоит добавить экологично как способ доставки приложения, а не как замена всей уже работающей инфраструктуры.

Контейнеризировать:

```text
support-desk-api
support-bot позже
```

Пока не переносить:

```text
Prometheus
Grafana
Loki
Alertmanager
Nginx
node_exporter
admin
```

План Docker stage:

```text
1. Dockerfile для support-desk-api.
2. docker-compose.yml на app.
3. ports: "8080:8080".
4. env_file для конфигурации.
5. volume для /var/log/app/app.log, чтобы Promtail продолжал читать host-file.
6. Проверить Nginx -> app:8080.
7. Проверить Prometheus -> app:8080/metrics.
8. Проверить Promtail -> Loki.
9. Добавить Ansible deploy для docker compose.
```

Плюсы:

- воспроизводимая доставка backend-а;
- легче развивать bot;
- шаг к CI/CD;
- хороший production-like элемент.

Риски/усложнения:

- нужно аккуратно сохранить logs/metrics;
- нужно не потерять systemd-level управление;
- не стоит сразу контейнеризировать весь observability stack.

## PostgreSQL instead of tickets.json

Сейчас Mini Support Desk хранит заявки в:

```text
/opt/app/tickets.json
```

Это подходит для lab/pet-project этапа, потому что просто и наглядно.

Для production-like реализации позже вынести данные в отдельную БД:

- PostgreSQL как основной вариант для tickets;
- MySQL как альтернативная relational DB;
- Redis не как основное хранилище заявок, а скорее для cache/queues/rate limits/session-like временных данных.

Причины:

- JSON-файл неудобен при параллельных запросах;
- сложнее делать фильтрацию, поиск, аналитику и историю изменений;
- нет нормальных транзакций;
- хуже масштабируется;
- при нескольких app instances общий файл уже не подходит.

Предпочтительный future path:

```text
app -> PostgreSQL на отдельной VM db
```

## DB observability + backups

После PostgreSQL добавить:

```text
node_exporter на db
postgres_exporter
Prometheus scrape для db
Grafana panels по DB
PostgreSQLDown alert
TooManyConnections alert
DatabaseDiskUsageHigh alert
pg_dump backup
restore demo
```

Ценность: появится полноценный stateful service и recovery story.

## Telegram bot

Будущий компонент:

```text
support-bot.service или support-bot container
```

Архитектура:

```text
Browser -> web -> app
Telegram -> support-bot -> app
```

Решение по сети уже проверено:

```text
app VM -> 192.168.85.1:10802 -> Windows portproxy -> 127.0.0.1:10801 -> Invisible Man XRay -> Telegram API
```

Подход:

- long polling;
- outbound HTTP proxy;
- bot token хранить в env-файле, не в коде;
- bot создает/читает/закрывает tickets через тот же app API;
- в tickets/logs писать `source=telegram`;
- bot logs отправлять в Loki отдельным job/service;
- позже добавить bot metrics.

## Security/network improvements

### 1. Restrict direct backend access

Сейчас `app:8080` доступен внутри lab-сети. Для более production-like схемы позже ограничить доступ к backend так, чтобы `app:8080` принимал запросы только от `web` / trusted proxy / admin / bot.

Это важно для безопасного использования proxy headers `X-Forwarded-For`.

### 2. Restrict DB access

После появления PostgreSQL:

```text
db:5432 принимает подключения только от app и admin
```

### 3. HTTPS

Позже добавить HTTPS termination на `web`:

- self-signed certificate для lab;
- или локальный CA;
- или production-like cert workflow в финальном README.

### 4. Nginx hardening

Будущие настройки:

- security headers;
- request body size limit;
- proxy timeouts;
- rate limiting;
- access control для admin/debug endpoints.

### 5. Secrets management

Минимально:

- DB password в env-файле;
- bot token в env-файле;
- env-файлы не хранить в Git;
- права `600`.

## Ansible automation improvements

После Admin/Ansible foundation добавить playbook-и/roles:

```text
common.yml
nginx.yml
app.yml
docker_app.yml
promtail.yml
prometheus.yml
postgres.yml
bot.yml
backup.yml
```

Цель: сделать проект воспроизводимым, а не только вручную настроенным.
