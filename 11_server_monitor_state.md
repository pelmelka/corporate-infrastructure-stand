# Текущее состояние сервера monitor

## Назначение

`monitor` — сервер мониторинга, визуализации и алертов.

Роль:

- Prometheus — сбор и хранение метрик;
- Grafana — визуализация метрик и логов;
- Alertmanager — прием alerts от Prometheus;
- node_exporter — системные метрики самого `monitor`;
- сбор системных метрик с `web`, `app`, `log`, `db`;
- сбор product metrics и HTTP/API request metrics с `supportdesk-api`;
- сбор native metrics с Telegram bot `support-bot`;
- сбор nginx-derived custom metrics с `web` Promtail (`promtail-web`);
- сбор PostgreSQL metrics с `db` postgres_exporter (`postgres`).

## Основная информация

- Hostname: `monitor`
- IP: `192.168.85.137/24`
- Interface: `ens18`
- Gateway: `192.168.85.2`
- User: `pelmel`
- SSH/sudo: работают

## Prometheus

Сервис:

```text
prometheus.service
```

Подтверждено:

- active/enabled;
- порт `9090`;
- UI доступен: `http://192.168.85.137:9090`;
- Prometheus видит Alertmanager;
- Prometheus видит `node (5/5 up)`;
- Prometheus видит `supportdesk-api (1/1 up)`;
- Prometheus видит `promtail-web (1/1 up)`;
- Prometheus видит `postgres (1/1 up)`;
- Prometheus видит `support-bot (1/1 up)`.

Текущие node targets:

```text
monitor: localhost:9100, host="monitor"
web:     192.168.85.131:9100, host="web"
app:     192.168.85.133:9100, host="app"
log:     192.168.85.135:9100, host="log"
db:      192.168.85.139:9100, host="db"
```

Текущий app product + HTTP metrics target:

```text
job="supportdesk-api"
instance="192.168.85.133:8080"
metrics_path="/metrics"
host="app"
service="support-desk-api"
env="lab"
```

Примечание: Prometheus job/label `supportdesk-api` пока сохранен для совместимости с текущими panels и alert rules. Само приложение теперь называется `misis-digital-student-support-api`.


Текущий Promtail metrics target для nginx-derived metrics:

```text
job="promtail-web"
instance="192.168.85.131:9080"
metrics_path="/metrics"
host="web"
service="promtail"
env="lab"
```

Проверенная custom metric:

```text
promtail_custom_nginx_http_responses_total{job="promtail-web",host="web",status_code="..."}
```

Prometheus при label conflict сохраняет исходные labels из Promtail stream как `exported_host`, `exported_job`, `exported_service`, а target labels оставляет как `host="web"`, `job="promtail-web"`, `service="promtail"`.


Текущий PostgreSQL metrics target:

```text
job="postgres"
instance="192.168.85.139:9187"
metrics_path="/metrics"
host="db"
service="postgresql"
env="lab"
```

Проверенные PostgreSQL metrics:

```text
pg_up{job="postgres",host="db"} = 1
pg_database_size_bytes{job="postgres",datname="supportdesk"}
pg_stat_database_numbackends{job="postgres",datname="supportdesk"}
pg_settings_max_connections{job="postgres"}
pg_stat_database_xact_commit{job="postgres",datname="supportdesk"}
pg_stat_database_xact_rollback{job="postgres",datname="supportdesk"}
```

Проверенные product metrics:

```text
supportdesk_tickets_total
supportdesk_tickets_open
supportdesk_tickets_in_progress
supportdesk_tickets_resolved
supportdesk_tickets_active
supportdesk_tickets_current{status,category,resource,priority}
supportdesk_active_ticket_age_seconds_max{category,resource,priority}
```


Проверенные HTTP/API metrics:

```text
supportdesk_http_requests_total{method,route,status_code}
supportdesk_http_request_duration_seconds_bucket{method,route,status_code,le}
supportdesk_http_request_duration_seconds_sum{method,route,status_code}
supportdesk_http_request_duration_seconds_count{method,route,status_code}
```



Текущий Telegram bot metrics target:

```text
job="support-bot"
instance="192.168.85.133:8090"
metrics_path="/metrics"
host="app"
service="misis-digital-support-bot"
env="lab"
```

Проверенные support-bot metrics:

```text
support_bot_info{service="misis-digital-support-bot",version="1.0.0"}
support_bot_start_time_seconds
support_bot_actions_total{action}
support_bot_api_requests_total{method,endpoint,status_code}
support_bot_api_request_duration_seconds_bucket{method,endpoint,status_code,le}
support_bot_api_request_duration_seconds_sum{method,endpoint,status_code}
support_bot_api_request_duration_seconds_count{method,endpoint,status_code}
support_bot_errors_total{type}
```

## Prometheus alert rules

Rules file:

```text
/etc/prometheus/supportdesk.rules.yml
```

В `prometheus.yml` подключен:

```yaml
rule_files:
  - /etc/prometheus/supportdesk.rules.yml
```

Текущие alerts после HTTP/API observability:

```text
SupportDeskApiDown                    critical   up{job="supportdesk-api"} == 0
SupportDeskTooManyTicketsForResource  warning    active tickets by category/resource >= 3
SupportDeskCriticalTicketsOpen        critical   active critical tickets > 0
SupportDeskOldCriticalTicket          critical   critical active ticket age > 600s
SupportDeskHigh4xxRate                warning    app-level 4xx rate >30% with enough traffic
SupportDeskHigh5xxRate                critical   app-level 5xx rate >5% with enough traffic
SupportDeskHighLatency                warning    app p95 latency >0.5s with enough traffic
Nginx502Spike                         critical   nginx 502 responses >=3 in 5m
HighDiskUsage                         warning    root filesystem usage >80%
NodeTargetDown                        critical   up{job="node"} == 0
PostgreSQLExporterDown                warning    up{job="postgres",host="db"} == 0
PostgreSQLDown                        critical   pg_up{job="postgres",host="db"} == 0
PostgreSQLTooManyConnections          warning    supportdesk connections >80% max_connections
SupportBotDown                        critical   up{job="support-bot"} == 0
SupportBotBackendErrors               warning    bot -> backend API non-2xx/error in 10m, grouped by endpoint/method/status_code
SupportBotErrorsDetected              warning    non-backend bot errors in 10m (type!=backend_error)
```

Старый общий alert `TooManyOpenTickets` удален, потому что его заменил более точный product alert `SupportDeskTooManyTicketsForResource`.

Все alert summaries в `supportdesk.rules.yml` приведены к статичному виду без шаблонов `{{ }}`; динамические значения оставлены в descriptions.

Проверено ранее:

- `SupportDeskApiDown` переходит в FIRING при остановке `app.service`;
- `SupportDeskTooManyTicketsForResource` переходит в FIRING при >=3 active tickets на одной паре `category/resource`;
- `SupportDeskCriticalTicketsOpen` переходит в FIRING при active critical-заявке;
- `SupportDeskOldCriticalTicket` переходит в FIRING, если active critical-заявка старше 600 секунд;
- alert доходит до Alertmanager, проверено через `amtool`;
- `HighDiskUsage` проверен через временный тестовый порог `>20`, затем возвращен на `>80`;
- `NodeTargetDown` переходит в FIRING при остановке node_exporter на target node;
- `SupportDeskHigh4xxRate` переходит в FIRING при генерации 4xx-трафика через `/api/bad-endpoint`;
- `Nginx502Spike` переходит в FIRING при остановке `app.service` и запросах через `web/Nginx`;
- при stop/down Dockerized backend одновременно ожидаемо срабатывает `SupportDeskApiDown`, потому что Prometheus теряет scrape target `supportdesk-api`;
- `PostgreSQLExporterDown` протестирован остановкой `prometheus-postgres-exporter.service`;
- `PostgreSQLDown` протестирован остановкой PostgreSQL cluster/exporter visibility через `pg_up`;
- `PostgreSQLTooManyConnections` добавлен как warning при высокой доле used connections;
- `SupportBotDown` протестирован остановкой `support-bot` container;
- `SupportBotBackendErrors` протестирован остановкой `supportdesk-api` и нажатием Telegram-действия, которое требует backend API;
- `SupportBotErrorsDetected` исключает `backend_error`, чтобы не дублировать `SupportBotBackendErrors`, и предназначен для Telegram/handler/unexpected errors.

## Grafana

Сервис:

```text
grafana-server.service
```

Подтверждено:

- active/enabled;
- порт `3000`;
- UI доступен: `http://192.168.85.137:3000`.

Datasources:

```text
Prometheus: http://localhost:9090
Loki:       http://192.168.85.135:3100
```

## Alertmanager

Сервис:

```text
prometheus-alertmanager.service
```

Подтверждено:

- active/enabled;
- порт `9093`;
- `/ready -> OK`;
- Prometheus видит Alertmanager;
- alerts доходят до Alertmanager, проверено через `amtool`.

Файл параметров:

```text
/etc/default/prometheus-alertmanager
```

Текущая строка:

```bash
ARGS="--cluster.listen-address="
```

Примечание: Debian package Alertmanager не включает полноценный web UI. На `:9093` доступны endpoints/API (`/-/ready`, `/-/healthy`, `/api/v2/alerts`, `/metrics`) и CLI `amtool`.

## Dashboard Infrastructure Overview

Dashboard создан через Grafana UI.

Panels:

```text
Targets UP
Disk Usage by host
CPU Usage by host
RAM Usage by host
SupportDesk API UP
SupportDesk Tickets / Student Support Tickets
Active Alerts
Web nginx logs
App logs
```

Product panels:

```text
SupportDesk API UP:
  up{job="supportdesk-api"}

SupportDesk Tickets / Student Support Tickets:
  supportdesk_tickets_total{job="supportdesk-api"}
  supportdesk_tickets_open{job="supportdesk-api"}
  supportdesk_tickets_in_progress{job="supportdesk-api"}
  supportdesk_tickets_resolved{job="supportdesk-api"}
  supportdesk_tickets_active{job="supportdesk-api"}

Active Alerts:
  sum(ALERTS{alertstate="firing"}) or vector(0)
```


HTTP/API Observability panels:

```text
HTTP/API Health Overview:
  4xx error rate %
  5xx error rate %
  API p95 latency ms
  Nginx 502 / 5m
  HTTP alerts firing

API Request Rate by Route:
  sum by(method, route) (rate(supportdesk_http_requests_total{job="supportdesk-api"}[5m]))

API Responses by Status Code:
  sum by(status_code) (rate(supportdesk_http_requests_total{job="supportdesk-api"}[5m]))

API p95 Latency by Route:
  topk(8, 1000 * histogram_quantile(0.95, sum by(le, route) (rate(supportdesk_http_request_duration_seconds_bucket{job="supportdesk-api"}[15m]))))
```

Примечание: Nginx 502 включен в summary panel через `promtail_custom_nginx_http_responses_total`; отдельная детальная панель Nginx status codes сознательно не добавлялась, чтобы сохранить минимальный dashboard scope.

App logs panel использует новый Loki stream:

```logql
{host="app", job="app", service="misis-digital-student-support-api"}
| logfmt
| line_format "{{.event}} | {{.method}} {{.path}} | status={{.status}} | category={{.category}} | resource={{.resource}} | ticket={{.ticket_id}} | {{.old_status}} -> {{.new_status}} | client={{.x_forwarded_for}} | proxy={{.client_ip}}"
```

`ticket_list_requested` оставлен в panel сознательно: он показывает активность UI/API, а не только изменения заявок.

## PostgreSQL / Supportdesk DB dashboard block

В dashboard `Infrastructure Overview` добавлен DB-блок:

```text
DB Health
DB Connections
DB Activity
PostgreSQL Important Logs
```

`DB Health` показывает:

```promql
up{job="postgres", host="db"}
pg_up{job="postgres", host="db"}
pg_database_size_bytes{job="postgres", datname="supportdesk"}
sum(ALERTS{alertstate="firing",alertname=~"PostgreSQLExporterDown|PostgreSQLDown|PostgreSQLTooManyConnections"}) or vector(0)
pg_stat_database_numbackends{job="postgres", datname="supportdesk"}
```

`DB Connections` показывает долю занятых connections:

```promql
100 *
max(pg_stat_database_numbackends{job="postgres", datname="supportdesk"})
/
max(pg_settings_max_connections{job="postgres"})
```

`DB Activity` показывает transaction rate:

```promql
rate(pg_stat_database_xact_commit{job="postgres", datname="supportdesk"}[5m])
rate(pg_stat_database_xact_rollback{job="postgres", datname="supportdesk"}[5m])
```

`PostgreSQL Important Logs` использует Loki:

```logql
{host="db", job="postgresql"}
|~ "(ERROR|FATAL|PANIC|shutting down|ready to accept connections|starting PostgreSQL|terminating connection|deadlock)"
```

Нормальное состояние logs-панели может быть `No data`, если за выбранный период не было важных DB events.

## Product logs после Product model v2

Grafana/Loki подтверждает прием новых app product logs.

Проверенные запросы:

```logql
{host="app", job="app", service="misis-digital-student-support-api"}
```

```logql
{host="app", job="app", category="gornyak-misis"}
```

```logql
{host="app", job="app", category="lk-misis"}
```

Видны события:

```text
event=ticket_created category=gornyak-misis resource=plumber-request
event=ticket_created category=lk-misis resource=gradebook
event=ticket_status_changed
event=ticket_status_unchanged
event=ticket_list_requested
event=metrics_requested
```

## Текущий статус

`monitor` готов как observability node:

- Prometheus собирает system metrics, product metrics, HTTP/API request metrics, Promtail nginx-derived metrics, PostgreSQL metrics и support-bot metrics;
- Grafana показывает dashboard `Infrastructure Overview` с блоками HTTP/API Observability, PostgreSQL / Supportdesk DB и Telegram Bot Observability;
- Loki datasource показывает web/app/db/support-bot logs;
- App logs panel обновлена под `MISIS_Digital Student Support`;
- Alertmanager принимает alerts;
- последний завершенный крупный этап проекта — Telegram support bot + bot observability.


## PostgreSQL-backed app metrics after stage 16

После этапа 16 Prometheus target `supportdesk-api` остался прежним:

```text
job="supportdesk-api"
instance="192.168.85.133:8080"
host="app"
```

Но источник product metrics изменился: backend теперь считает `supportdesk_tickets_total`, `supportdesk_tickets_current` и `supportdesk_active_ticket_age_seconds_max` SQL-запросами к PostgreSQL, а не Python-агрегацией поверх `tickets.json`.

Проверено после чистки `app.py`:

```bash
curl -s http://localhost:8080/metrics | grep supportdesk_tickets_total
```

DB-specific metrics добавлены на этапе 17: node_exporter на `db`, postgres_exporter на `db`, Prometheus job `postgres`, DB Grafana panels и DB alerts.


## Grafana row: Telegram Bot Observability

Добавлен отдельный блок на dashboard `Infrastructure Overview`.

Панели:

```text
Telegram Bot Alerts
Telegram Bot Runtime
Bot -> API dependency / 30m
Bot -> API latency by endpoint / 30m
Bot API requests by endpoint/status / 30m
Bot actions / 30m
Bot recent logs
Bot error logs
```

Назначение блока:

```text
не дублировать product observability по заявкам;
показывать состояние самого bot-container;
показывать зависимость support-bot -> supportdesk-api;
показывать действия пользователя в Telegram UI;
давать быстрый drill-down в Loki logs при bot alert.
```

Ключевые PromQL/LogQL запросы зафиксированы в `06_config_files_current.md`.

## Security/network hardening

UFW installed and active after Stage 19.

Current policy:

```text
default incoming: deny
default outgoing: allow
routed: disabled
```

Allowed inbound:

```text
192.168.85.129 -> 22/tcp     admin SSH/Ansible
192.168.85.1   -> 3000/tcp   Windows Grafana UI
192.168.85.129 -> 3000/tcp   admin Grafana diagnostics
192.168.85.1   -> 9090/tcp   Windows Prometheus UI
192.168.85.129 -> 9090/tcp   admin Prometheus diagnostics
192.168.85.1   -> 9093/tcp   Windows Alertmanager endpoints/API
192.168.85.129 -> 9093/tcp   admin Alertmanager diagnostics
192.168.85.129 -> 9100/tcp   admin node_exporter diagnostics
```

Prometheus local scrape of monitor node_exporter continues through localhost/loopback. Outgoing scrapes from monitor to web/app/log/db remain allowed by `default allow outgoing`.

Confirmed:

```text
Grafana/Prometheus/Alertmanager are accessible from Windows 192.168.85.1;
admin diagnostics works;
web -> monitor:3000/9090/9093 times out;
Prometheus /-/ready works;
Prometheus targets remain UP.
```

