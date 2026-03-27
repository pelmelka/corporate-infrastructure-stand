# Текущее состояние сервера monitor

## Назначение

`monitor` — сервер мониторинга, визуализации и алертов.

Роль:

- Prometheus — сбор и хранение метрик;
- Grafana — визуализация метрик и логов;
- Alertmanager — прием alerts от Prometheus;
- node_exporter — системные метрики самого `monitor`;
- сбор системных метрик с `web`, `app`, `log`;
- сбор product metrics и HTTP/API request metrics с `supportdesk-api`;
- сбор nginx-derived custom metrics с `web` Promtail (`promtail-web`).

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
- Prometheus видит `node (4/4 up)`;
- Prometheus видит `supportdesk-api (1/1 up)`;
- Prometheus видит `promtail-web (1/1 up)`.

Текущие node targets:

```text
monitor: localhost:9100, host="monitor"
web:     192.168.85.131:9100, host="web"
app:     192.168.85.133:9100, host="app"
log:     192.168.85.135:9100, host="log"
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
```

Старый общий alert `TooManyOpenTickets` удален, потому что его заменил более точный product alert `SupportDeskTooManyTicketsForResource`.

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
- при stop `app.service` одновременно ожидаемо срабатывает `SupportDeskApiDown`, потому что Prometheus теряет scrape target `supportdesk-api`.

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

- Prometheus собирает system metrics, product metrics, HTTP/API request metrics и Promtail nginx-derived metrics;
- Grafana показывает dashboard `Infrastructure Overview` с новым блоком HTTP/API Observability;
- Loki datasource показывает web/app logs;
- App logs panel обновлена под `MISIS_Digital Student Support`;
- Alertmanager принимает alerts;
- текущий следующий крупный этап проекта — Dockerization backend-а; HTTP/API observability завершена.
