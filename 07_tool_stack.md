# Стек инструментов проекта

## Виртуализация

### VMware

Используется как среда, внутри которой запущен Proxmox VE. Дает NAT-сеть `192.168.85.0/24`.

### Proxmox VE

Версия по скриншотам: `Proxmox VE 9.1.1`.

Роль: создание VM, управление ресурсами, snapshots, web UI, bridge `vmbr0` и потенциально `vmbr1`.

## OS

### Debian 13

Используется на всех VM. Минимальная установка без GUI.

## Управление и автоматизация

### SSH

Подключения с Windows к `admin`, с `admin` к узлам, будущая база для Ansible.

### sudo

Пользователь `pelmel` добавляется в группу `sudo` на всех узлах.

### Ansible

Установлен на `admin`. Роль: inventory, ad-hoc команды, будущие playbook'и, автоматизация установки и настройки сервисов.

### Git, план

Пока пропущен. В будущем нужен для хранения структуры проекта, README, playbook'ов, шаблонов и истории изменений.

## Web слой

### Nginx

Установлен на `web`. Роль: статический frontend, позже reverse proxy, access/error logs.

Текущее состояние:

- `nginx.service`: `active (running)`;
- порт `80`: слушается;
- сайт отдается из `/var/www/html/index.html`;
- access/error логи пишутся в `/var/log/nginx/`;
- nginx logs уже отправляются в Loki через Promtail.

## Application слой

### Python

Используется на `app`. Сейчас стандартная библиотека `http.server`; позже возможен Flask.

### systemd

Используется для `app.service`, `loki.service`, `promtail.service` на `web`; позже для Promtail на `app`, Prometheus, Grafana, Alertmanager, node_exporter.

## Logging

### Loki

Установлен на `log`.

Текущее состояние:

- версия: `3.5.0`;
- binary: `/opt/loki/loki`;
- config: `/etc/loki/config.yml`;
- data dir: `/var/lib/loki`;
- user/group: `loki:loki`;
- service: `loki.service`;
- status: `active (running)`;
- autostart: `enabled`;
- HTTP API: `192.168.85.135:3100`;
- `/ready` локально и с `admin` возвращает `ready`;
- принимает nginx logs от `web` через Promtail;
- запрос `{host="web",job="nginx"}` через `/loki/api/v1/query_range` возвращает nginx access logs.

Роль: хранение логов и API для Grafana.

### Promtail на web

Установлен на `web`.

Текущее состояние:

- версия: `3.5.0`;
- binary: `/opt/promtail/promtail`;
- config: `/etc/promtail/config.yml`;
- positions: `/var/lib/promtail/positions.yaml`;
- user/group: `promtail:promtail`;
- дополнительная группа: `adm` для чтения `/var/log/nginx/*.log`;
- service: `promtail.service`;
- status: `active (running)`;
- autostart: `enabled`;
- служебный порт: `9080`;
- читает: `/var/log/nginx/access.log`, `/var/log/nginx/error.log`;
- отправляет в Loki: `http://192.168.85.135:3100/loki/api/v1/push`;
- labels: `host=web`, `job=nginx`, `service=frontend`, `env=lab`.

Роль: чтение nginx logs, добавление labels, отправка в Loki.

Важно: `/loki/api/v1/push` — API endpoint для POST-запросов от Promtail, а не страница для браузера. `HTTP ERROR 405` при открытии в браузере не означает поломку.

### Promtail на app, план

Будет установлен на `app`. Роль: чтение app logs, добавление labels, отправка в Loki на `http://192.168.85.135:3100/loki/api/v1/push`.

Планируемые labels:

```text
host=app
job=app
service=python-backend
env=lab
```

Открытый вопрос: собирать app logs из файла или из journald.

## Monitoring

### Prometheus, план

Будет установлен на `monitor`. Роль: сбор метрик.

### Grafana, план

Будет установлена на `monitor`. Роль: UI для dashboard'ов, логов и метрик.

### Alertmanager, план

Будет установлен на `monitor`. Роль: alerts.

### node_exporter, план

Будет установлен на `web`, `app`, `log`, возможно `monitor`. Роль: системные метрики.

## Планируемые dashboard'ы

- Infrastructure Overview
- Web Node Dashboard
- App Node Dashboard
- Logs / Observability
- Loki dashboard
- Prometheus targets dashboard

## Планируемые демонстрационные сценарии

1. Нормальная работа: открыть сайт, дернуть backend, увидеть логи и метрики.
2. App down: остановить `app.service`, увидеть ошибку, поднять обратно.
3. Web logs: сгенерировать HTTP-запросы и увидеть nginx logs в Loki.
4. Infrastructure overview: показать состояние всех узлов.
