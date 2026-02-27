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

### Ansible

Установлен на `admin`. Сейчас inventory минимальный, будущие playbook'и запланированы.

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
- product logs: `event=...` в key=value формате;
- product metrics: текущие tickets counts на `/metrics`.

### systemd

Используется для `app.service`, `loki.service`, `promtail.service`, Prometheus, Grafana, Alertmanager, node_exporter.

## Logging

### Loki

Установлен на `log`, принимает nginx logs и app product logs.

### Promtail

Установлен на `web` и `app`.

- `web`: читает `/var/log/nginx/*.log`;
- `app`: читает `/var/log/app/*.log`.

## Monitoring

### Prometheus

Установлен на `monitor`, собирает node_exporter metrics с `web`, `app`, `log`, `monitor`. App `/metrics` scrape пока не добавлен.

### Grafana

Установлена на `monitor`, подключены datasources Prometheus и Loki, создан dashboard `Infrastructure Overview`.

### Alertmanager

Установлен на `monitor`, связан с Prometheus. Alert rules пока не создавались.

### node_exporter

Установлен на `monitor`, `web`, `app`, `log`; Prometheus показывает `node (4/4 up)`.

## Future components

### Telegram bot

Пока не реализован. Архитектурно выбран будущий вариант:

```text
Browser -> web -> app
Telegram -> support-bot.service -> app
```

Для текущей NAT-инфраструктуры выбран подход:

```text
long polling + outbound HTTP proxy
```

Проверенный proxy path:

```text
app VM -> 192.168.85.1:10802 -> Windows portproxy -> 127.0.0.1:10801 -> Invisible Man XRay -> Telegram API
```

### Database / PostgreSQL

Пока не реализована. Сейчас tickets хранятся в `/opt/app/tickets.json`. Замена на PostgreSQL вынесена в future backlog.

## Future improvements

Все будущие улучшения по logging, monitoring, product alerts, storage, Telegram bot и security собраны в:

```text
12_future_improvements_backlog.md
```
