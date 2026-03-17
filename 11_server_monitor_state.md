# Текущее состояние сервера monitor

## Назначение

`monitor` — сервер мониторинга, визуализации и алертов.

Роль:

- Prometheus — сбор и хранение метрик;
- Grafana — визуализация метрик и логов;
- Alertmanager — прием alerts от Prometheus;
- node_exporter — системные метрики самого `monitor`;
- сбор системных метрик с `web`, `app`, `log`;
- сбор product metrics с `supportdesk-api`.

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
- Prometheus видит `supportdesk-api (1/1 up)`.

Текущие node targets:

```text
monitor: localhost:9100, host="monitor"
web:     192.168.85.131:9100, host="web"
app:     192.168.85.133:9100, host="app"
log:     192.168.85.135:9100, host="log"
```

Текущий app product metrics target:

```text
job="supportdesk-api"
instance="192.168.85.133:8080"
metrics_path="/metrics"
host="app"
service="support-desk-api"
env="lab"
```

Примечание: Prometheus job/label `supportdesk-api` пока сохранен для совместимости с текущими panels и alert rules. Само приложение теперь называется `misis-digital-student-support-api`.

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

Текущие alerts после Product observability v2 cleanup:

```text
SupportDeskApiDown                    critical   up{job="supportdesk-api"} == 0
SupportDeskTooManyTicketsForResource  warning    active tickets by category/resource >= 3
SupportDeskCriticalTicketsOpen        critical   active critical tickets > 0
SupportDeskOldCriticalTicket          critical   critical active ticket age > 600s
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
- `NodeTargetDown` переходит в FIRING при остановке node_exporter на target node.

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

- Prometheus собирает system metrics и product metrics;
- Grafana показывает dashboard `Infrastructure Overview`;
- Loki datasource показывает web/app logs;
- App logs panel обновлена под `MISIS_Digital Student Support`;
- Alertmanager принимает alerts;
- текущий следующий monitoring/product шаг — `Product observability v2`: metrics и alerts по `category/resource/priority/source`.
