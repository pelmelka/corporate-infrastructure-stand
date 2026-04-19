# Стек инструментов проекта

## Виртуализация

### VMware

Среда, внутри которой запущен Proxmox VE. Дает NAT-сеть `192.168.85.0/24`.

### Proxmox VE

Роль: создание VM, управление ресурсами, snapshots, web UI, bridge `vmbr0`.

## OS

### Debian 13

Используется на VM: `admin`, `web`, `app`, `log`, `monitor`, `db`.

## Управление и автоматизация

### SSH / sudo

SSH работает на узлах. Пользователь `pelmel` имеет sudo. Для `web/app/log/monitor` раскатаны SSH-ключи с `admin`. `db` добавлен в Ansible inventory и управляется с `admin` по SSH/Ansible.

### Ansible

Ansible используется на `admin` как основной automation/control слой.

```text
Ansible core: 2.19.4
config: /home/pelmel/control-node/ansible.cfg
inventory: inventory/hosts.ini
roles_path: ./roles
```

Stage 20 Ansible automation v2 добавил:

```text
inventory/group_vars for all role groups;
roles for common baseline, node_exporter, app compose project, compose service deploy, nginx frontend, promtail, prometheus, postgres_exporter, postgres_backup;
playbooks for baseline, deploy app/bot/nginx/promtail/prometheus/postgres_exporter/postgres_backup, manual DB backup, network audit, full check.
```

Firewall changes are intentionally not managed by Ansible. `network_audit.yml` is audit-only and creates reports under `docs/network-audit/latest/`.

### Git

Git установлен на `admin`; используется для истории Ansible/control-node файлов. Product/app changes пока в основном фиксируются в project sources и server backups.

## Web слой

### Nginx

Установлен на `web`.

Текущая роль:

- frontend server для `MISIS_Digital Student Support`;
- reverse proxy `/api/* -> app:8080`;
- access/error logs;
- будущая точка для HTTPS, rate limiting, security headers.

## Application слой

### Python backend

Текущий backend: `MISIS_Digital Student Support API`.

Runtime:

```text
app: Docker container misis-digital-student-support-api
port: 8080
code: /opt/app/app.py, copied into Docker image
data: PostgreSQL on db, not tickets.json
logs: /var/log/app/app.log
metrics: /metrics
```

Ключевые библиотеки:

```text
http.server стандартной библиотеки
psycopg2-binary
prometheus_client
```

Текущая модель кода:

```text
GET /tickets        -> db_list_tickets()
GET /tickets/<id>   -> db_get_ticket()
GET /metrics        -> build_product_metrics_body_from_db()
POST /tickets       -> create_ticket_in_db()
PATCH /status       -> update_ticket_status_in_db()
```

Старый storage layer на `tickets.json` удален из runtime-логики.


### Python Telegram bot

Новый компонент после этапа 18: `MISIS_Digital Student Support` Telegram bot.

```text
Bot username: @misis_digital_support_bot
Runtime host: app
Compose service: support-bot
Container: misis-digital-support-bot
Library: python-telegram-bot==22.7
HTTP client: httpx
Metrics: prometheus_client
Logs: /var/log/bot/support-bot.log
Metrics endpoint: 8090/metrics
```

Работает через long polling и outbound proxy, не требует входящего публичного webhook endpoint-а.

### Docker

Docker Engine и Docker Compose установлены на `app`.

Текущий состав:

```text
Docker Engine: 29.4.3
Docker Compose: v5.1.3
image: misis-digital-student-support-api:local
container: misis-digital-student-support-api
compose service: supportdesk-api

image: misis-digital-support-bot:local
container: misis-digital-support-bot
compose service: support-bot
```

Compose сохраняет внешний контракт:

```text
host app:8080 -> supportdesk-api container:8080
host app:8090 -> support-bot container:8090
```

Текущий volume:

```text
/var/log/app:/var/log/app
/var/log/bot:/var/log/bot
```

Старый `/opt/app:/opt/app` volume удален после перехода на PostgreSQL.

## Data слой

### PostgreSQL

Установлен на отдельной VM `db`.

```text
host: 192.168.85.139
version: PostgreSQL 17
cluster: 17/main
port: 5432
database: supportdesk
role: supportdesk_user
schema: public
```

Таблицы:

```text
tickets        текущее состояние заявок
ticket_events  история событий и audit trail
```

Индексы:

```text
tickets_pkey
idx_tickets_status
idx_tickets_category_resource
idx_tickets_priority
idx_ticket_events_ticket_id
idx_ticket_events_event
idx_ticket_events_created_at
```

`app -> db` доступ разрешен через `pg_hba.conf` для `192.168.85.133/32`.

## Logging

### Loki

Установлен на `log`, принимает nginx logs и app product logs.

### Promtail

Установлен на `web`, `app` и `db`.

- `web`: читает `/var/log/nginx/*.log`, label `service=frontend`, дополнительно строит custom metric `promtail_custom_nginx_http_responses_total{status_code}` на `:9080/metrics`;
- `app`: читает `/var/log/app/*.log`, static label `service=misis-digital-student-support-api`;
- `app`: через pipeline извлекает `category` из app log line и добавляет dynamic Loki label;
- `db`: читает `/var/log/postgresql/*.log` и отправляет PostgreSQL logs в Loki с labels `host=db`, `job=postgresql`, `service=postgresql`, `env=lab`.

## Monitoring

### Prometheus

Установлен на `monitor`.

Собирает:

- node_exporter metrics с `web`, `app`, `log`, `monitor`;
- product metrics и HTTP/API metrics с `app:8080/metrics` через job `supportdesk-api`;
- Promtail metrics с `web:9080/metrics` через job `promtail-web`;
- node_exporter metrics с `db:9100`;
- PostgreSQL metrics с `db:9187/metrics` через job `postgres`.

DB-specific scrape targets добавлены.

Текущие product metrics:

```text
supportdesk_tickets_total
supportdesk_tickets_open
supportdesk_tickets_in_progress
supportdesk_tickets_resolved
supportdesk_tickets_active
supportdesk_tickets_current{status,category,resource,priority}
supportdesk_active_ticket_age_seconds_max{category,resource,priority}
```

Текущие HTTP/API metrics:

```text
supportdesk_http_requests_total{method,route,status_code}
supportdesk_http_request_duration_seconds_bucket{method,route,status_code,le}
supportdesk_http_request_duration_seconds_sum{method,route,status_code}
supportdesk_http_request_duration_seconds_count{method,route,status_code}
promtail_custom_nginx_http_responses_total{status_code}
```

### Grafana

Установлена на `monitor`, подключены datasources Prometheus и Loki, создан dashboard `Infrastructure Overview`.

### Alertmanager

Установлен на `monitor`, связан с Prometheus.

### node_exporter

Установлен на `monitor`, `web`, `app`, `log`, `db`; Prometheus показывает `node (5/5 up)`.

## Alert rules

Файл:

```text
monitor: /etc/prometheus/supportdesk.rules.yml
```

Текущие alerts:

```text
SupportDeskApiDown
SupportDeskTooManyTicketsForResource
SupportDeskCriticalTicketsOpen
SupportDeskOldCriticalTicket
SupportDeskHigh4xxRate
SupportDeskHigh5xxRate
SupportDeskHighLatency
Nginx502Spike
HighDiskUsage
NodeTargetDown
PostgreSQLExporterDown
PostgreSQLDown
PostgreSQLTooManyConnections
```

DB alerts добавлены после DB observability stage.


## Backup/restore

### pg_dump / pg_restore

Для `supportdesk` настроены daily logical backups PostgreSQL:

```text
backup script: /usr/local/sbin/backup_supportdesk.sh
backup dir:    /var/backups/postgresql/supportdesk
format:        pg_dump -Fc
checksum:      sha256sum per dump
latest link:   latest.dump -> latest supportdesk_*.dump
retention:     7 days
```

Automation:

```text
backup-supportdesk.service  Type=oneshot
backup-supportdesk.timer    OnCalendar=*-*-* 03:15:00, Persistent=true
```

Restore test выполнен в отдельную БД `supportdesk_restore_test`; counts `tickets=15`, `ticket_events=18` совпали с рабочей БД, затем test DB удалена.

## Firewall / network access control

### UFW

Used after Stage 19 as the main host firewall on Debian nodes:

```text
web
app
log
monitor
db
```

Baseline policy:

```text
default deny incoming
default allow outgoing
routed disabled
```

### iptables / DOCKER-USER

Used on `app` to restrict Docker-published ports:

```text
app:8080 supportdesk-api
app:8090 support-bot metrics
```

Reason: Docker published ports are handled through Docker NAT/FORWARD rules, so host UFW alone is not enough for reliable access control. Rules are installed into `DOCKER-USER` and restored after reboot by `app-docker-user-firewall.service`.



## Ansible automation v2 tooling notes

Ключевые production-like приемы, закрепленные в Stage 20:

```text
validate: promtool check config/rules для Prometheus;
nginx -t перед reload Nginx;
handlers для restart/reload только при changed;
no_log для env/secrets checks;
delegate_to: localhost для проверки source-файлов на control node;
stat follow=true для latest.dump symlink;
JSON parsing targets API вместо поиска строки в Prometheus response;
network_audit.yml как audit-only playbook без firewall auto-apply.
```
