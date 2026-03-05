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

Установлен на `admin`; `admin` теперь является полноценным базовым control node.

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

Git используется как история и источник правды для Ansible control-node файлов.

## Web слой

### Nginx

Установлен на `web`.

Текущая роль:

- frontend server для Mini Support Desk;
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

Используется на `app`. Сейчас стандартная библиотека `http.server`; приложение реализовано как Mini Support Desk API.

Текущее состояние:

- код: `/opt/app/app.py`;
- сервис: `app.service`;
- порт: `8080`;
- данные: `/opt/app/tickets.json`;
- logs: `/var/log/app/app.log`;
- endpoints: `/health`, `/tickets`, `/tickets/<id>`, `/tickets/<id>/status`, `/metrics`;
- product logs: `event=...` в key=value/logfmt-friendly формате;
- product metrics: текущие tickets counts на `/metrics`;
- Prometheus scrape job: `supportdesk-api`.

### systemd

Используется для `app.service`, `loki.service`, `promtail.service`, Prometheus, Grafana, Alertmanager, node_exporter.

## Logging

### Loki

Установлен на `log`, принимает nginx logs и app product logs.

### Promtail

Установлен на `web` и `app`.

- `web`: читает `/var/log/nginx/*.log`, label `service=frontend`;
- `app`: читает `/var/log/app/*.log`, label `service=support-desk-api`.

## Monitoring

### Prometheus

Установлен на `monitor`.

Собирает:

- node_exporter metrics с `web`, `app`, `log`, `monitor`;
- product metrics с `app:8080/metrics` через job `supportdesk-api`.

Текущие product metrics:

```text
supportdesk_tickets_total
supportdesk_tickets_open
supportdesk_tickets_in_progress
supportdesk_tickets_resolved
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
SupportDesk Tickets
Active Alerts
Web nginx logs
App logs
```

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
SupportDeskApiDown      critical   app API /metrics недоступен
TooManyOpenTickets      warning    слишком много open-заявок
HighDiskUsage           warning    root filesystem >80%
NodeTargetDown          critical   node_exporter target недоступен
```

## Future components

### Docker

Планируется как отдельный production-like этап после Admin/Ansible foundation и Product model v2.

Экологичный scope:

```text
Dockerize support-desk-api
Dockerize support-bot позже
```

Пока не планируется переносить в Docker:

```text
Prometheus
Grafana
Loki
Alertmanager
Nginx
node_exporter
admin
```

Смысл: добавить Docker как способ доставки приложения, не ломая уже работающую observability-инфраструктуру.

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
