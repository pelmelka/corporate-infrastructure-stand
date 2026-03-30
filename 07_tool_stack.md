# Стек инструментов проекта

## Виртуализация

### VMware

Среда, внутри которой запущен Proxmox VE. Дает NAT-сеть `192.168.85.0/24`.

### Proxmox VE

Роль: создание VM, управление ресурсами, snapshots, web UI, bridge `vmbr0`.

## OS

### Debian 13

Используется на всех VM. Минимальная установка без GUI.

## Управление и автоматизация

### SSH / sudo

SSH работает на всех узлах. Пользователь `pelmel` имеет sudo.

Реализовано для Ansible foundation:

- на `admin` хранится private key `/home/pelmel/.ssh/id_ed25519`;
- public key раскатан на `web`, `app`, `log`, `monitor`;
- SSH login с `admin` на managed nodes работает без пароля пользователя;
- sudo/root-действия через Ansible по-прежнему требуют sudo-пароль, если playbook использует `become: true` и не настроен `NOPASSWD`.

### Ansible

Установлен на `admin`; `admin` является полноценным базовым control node.

Текущая структура:

```text
~/control-node/
├── ansible.cfg
├── inventory/hosts.ini
├── playbooks/
├── files/
├── roles/
├── templates/
└── docs/
```

Реализовано:

- inventory с `control`, `web_nodes`, `app_nodes`, `log_nodes`, `monitor_nodes`, `managed`;
- `ansible.cfg` с project inventory, `remote_user=pelmel`, Python interpreter и выключенным `become` по умолчанию;
- `ansible all -m ping` и `ansible managed -m ping` проходят успешно;
- `ping_all.yml` — проверка Ansible-связности;
- `check_services.yml` — проверка ключевых сервисов на `web/app/log/monitor`;
- `restart_app.yml` — controlled restart `app.service` + healthcheck;
- `deploy_prometheus_rules.yml` — деплой Prometheus alert rules с `promtool` validation, handler restart Prometheus и readiness check.

Позже планируются roles/playbook'и для app/web/promtail/prometheus/db/bot/docker.

### Git

Git установлен на `admin`; в `~/control-node` инициализирован локальный Git repository.

Текущая ветка:

```text
master
```

Зафиксированы commit'ы:

```text
cb5794d Add Ansible project directory placeholders
b98b8f9 initial Ansible control node setup
```

Git используется как история и источник правды для Ansible control-node файлов. Product model v2 пока реализован вручную на серверах, без Ansible deploy automation.

## Web слой

### Nginx

Установлен на `web`.

Текущая роль:

- frontend server для `MISIS_Digital Student Support`;
- reverse proxy `/api/* -> app:8080`;
- access/error logs;
- будущая точка для HTTPS, rate limiting, security headers.

Текущее состояние:

- `nginx.service active/running`;
- порт `80` слушается;
- сайт отдается из `/var/www/html/index.html`;
- proxy block находится в `/etc/nginx/sites-available/default`;
- nginx logs отправляются в Loki через Promtail.

## Application слой

### Python

Используется на `app`. Сейчас стандартная библиотека `http.server` + `prometheus_client` для HTTP request metrics; приложение реализовано как `MISIS_Digital Student Support API`.

Текущее состояние:

- продукт: `MISIS_Digital Student Support`;
- service name в app logs: `misis-digital-student-support-api`;
- код: `/opt/app/app.py`;
- сервис: `app.service`;
- порт: `8080`;
- данные: `/opt/app/tickets.json`;
- logs: `/var/log/app/app.log`;
- endpoints: `/health`, `/v1/health`, `/v1/support-model`, `/v1/tickets`, `/v1/tickets/all`, `/v1/tickets/<id>`, `/v1/tickets/<id>/status`, `/metrics`;
- product logs: `event=... category=... resource=...` в key=value/logfmt-friendly формате;
- product metrics: tickets counts на `/metrics`;
- HTTP/API metrics: request counter and latency histogram на `/metrics`;
- Prometheus scrape job: `supportdesk-api`.

Модель заявки:

```text
category = цифровой сервис университета
resource = раздел/функция внутри выбранного сервиса
status   = open / in_progress / resolved
```

Поддерживаются сервисы:

```text
newlms-misis, lk-misis, gornyak-misis, folio-misis, pulse-misis, vector-misis, pay-misis
```

### systemd

Используется для `app.service`, `loki.service`, `promtail.service`, Prometheus, Grafana, Alertmanager, node_exporter.

## Logging

### Loki

Установлен на `log`, принимает nginx logs и app product logs.

### Promtail

Установлен на `web` и `app`.

- `web`: читает `/var/log/nginx/*.log`, label `service=frontend`; дополнительно строит custom metric `promtail_custom_nginx_http_responses_total{status_code}` на `:9080/metrics`;
- `app`: читает `/var/log/app/*.log`, static label `service=misis-digital-student-support-api`;
- `app`: через pipeline извлекает `category` из app log line и добавляет его как dynamic Loki label.

Примеры LogQL:

```logql
{host="app", job="app", service="misis-digital-student-support-api"}
```

```logql
{host="app", job="app", service="misis-digital-student-support-api", category="newlms-misis"}
```

```logql
{host="app", job="app", service="misis-digital-student-support-api", category="gornyak-misis"}
|= "resource=plumber-request"
```

## Monitoring

### Prometheus

Установлен на `monitor`.

Собирает:

- node_exporter metrics с `web`, `app`, `log`, `monitor`;
- product metrics и HTTP/API metrics с `app:8080/metrics` через job `supportdesk-api`;
- Promtail metrics с `web:9080/metrics` через job `promtail-web` для nginx-derived status metrics.

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

Dashboard содержит:

```text
Targets UP
Disk Usage by host
CPU Usage by host
RAM Usage by host
SupportDesk API UP
SupportDesk Tickets / Student Support Tickets
Product Observability v2 panels
Active Alerts
Web nginx logs
App logs
```

App logs panel обновлен под новый service label и показывает v1-events с `category/resource`.

### Alertmanager

Установлен на `monitor`, связан с Prometheus. Debian package не включает полноценный web UI, но доступны endpoints/API и `amtool`.

Проверки:

```bash
curl http://localhost:9093/-/ready
curl http://localhost:9093/-/healthy
amtool --alertmanager.url=http://localhost:9093 alert
```

### node_exporter

Установлен на `monitor`, `web`, `app`, `log`; Prometheus показывает `node (4/4 up)`.

## Alert rules

Файл:

```text
monitor: /etc/prometheus/supportdesk.rules.yml
```

Текущие alerts:

```text
SupportDeskApiDown                    critical   app API /metrics недоступен
SupportDeskTooManyTicketsForResource  warning    много active-заявок на одном category/resource
SupportDeskCriticalTicketsOpen        critical   есть active critical-заявка
SupportDeskOldCriticalTicket          critical   critical-заявка висит дольше 600 секунд
SupportDeskHigh4xxRate                warning    высокая доля app-level 4xx
SupportDeskHigh5xxRate                critical   высокая доля app-level 5xx
SupportDeskHighLatency                warning    высокая p95 latency API
Nginx502Spike                         critical   nginx вернул >=3 HTTP 502 за 5 минут
HighDiskUsage                         warning    root filesystem >80%
NodeTargetDown                        critical   node_exporter target недоступен
```

Старый `TooManyOpenTickets` удален после Product observability v2 cleanup.

Имена alert-ов пока сохранены, чтобы не ломать существующие rules/dashboard. Переименование и расширение alert-ов под category/resource запланировано на Product observability v2.

## Future components

### Product observability v2

Реализовано как минимальный production-like слой: current tickets by status/category/resource/priority, max age active ticket, Grafana panels и product alerts. Source/counters/duration metrics отложены до Telegram, PostgreSQL и event storage.

### HTTP/API observability

Реализовано на этапе 14: app-level request counter, latency histogram, error-rate alerts, Promtail nginx status metric, Prometheus target `promtail-web`, `Nginx502Spike` и компактный блок Grafana panels.

### Docker

Реализован на `app` как production-like способ доставки backend-а `misis-digital-student-support-api` без переноса всей инфраструктуры в контейнеры.

Установлено на `app`:

```text
Docker Engine 29.4.3
Docker Compose v5.1.3
docker.service active/enabled
```

Dockerized component:

```text
misis-digital-student-support-api на app
```

Текущий Docker runtime:

```text
image: misis-digital-student-support-api:local
container: misis-digital-student-support-api
compose service: supportdesk-api
host port: 8080 -> container port 8080
```

Файлы:

```text
app: /opt/app/Dockerfile
app: /opt/app/docker-compose.yml
app: /opt/app/requirements.txt
app: /opt/app/.dockerignore
app: /opt/app/.env
```

Текущие mounts:

```text
/opt/app:/opt/app
/var/log/app:/var/log/app
```

Примечание: `/opt/app:/opt/app` — временный workaround до PostgreSQL. Он нужен, пока storage работает через `/opt/app/tickets.json` и `os.replace()`. После PostgreSQL код должен жить только в image, а данные — в DB.

Пока не переносится в Docker:

```text
Prometheus
Grafana
Loki
Alertmanager
Nginx
node_exporter
admin
```

Позже планируется:

```text
Dockerize support-bot
перевести app logs на stdout/stderr и современный log collector
```

### PostgreSQL

Пока не реализована. Сейчас tickets хранятся в `/opt/app/tickets.json`. Замена на PostgreSQL вынесена в production-like roadmap.

План:

```text
app -> PostgreSQL на отдельной VM db
```

### Telegram bot

Пока не реализован. Архитектурно выбран будущий вариант:

```text
Browser -> web -> app
Telegram -> support-bot.service/container -> app
```

Для текущей NAT-инфраструктуры выбран подход:

```text
long polling + outbound HTTP proxy
```

Проверенный proxy path:

```text
app VM -> 192.168.85.1:10802 -> Windows portproxy -> 127.0.0.1:10801 -> Invisible Man XRay -> Telegram API
```

## Future improvements

Все будущие улучшения по logging, monitoring, product alerts, Docker, storage, Telegram bot и security собраны в:

```text
12_future_improvements_backlog.md
```
