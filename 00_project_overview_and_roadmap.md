# Mini Corporate Infrastructure Lab — план и roadmap

## Цель проекта

Собрать учебный pet-project в формате мини-инфраструктуры корпоративного типа на базе Proxmox VE внутри VMware. Это не набор отдельных VM, а связанный стенд с frontend, backend, централизованным логированием, мониторингом, базовой автоматизацией и демонстрационными сценариями troubleshooting.

Итоговая ценность проекта: показать навыки Linux administration, DevOps-подхода, systemd, SSH, Ansible, Nginx, Python-сервисов, Loki/Promtail, Prometheus/Grafana/Alertmanager и диагностики.

## Итоговая архитектура

```text
Windows host / Browser / SSH client
        |
        | VMware NAT / local access
        v
Proxmox VE node: 192.168.85.128:8006
        |
        +-- admin   192.168.85.129  control node / Ansible
        +-- web     192.168.85.131  Nginx frontend + Promtail
        +-- app     192.168.85.133  Python backend service + Promtail
        +-- log     192.168.85.135  Loki logging server
        +-- monitor TBD             Prometheus + Grafana + Alertmanager
```

Реализованные и планируемые потоки:

```text
Browser -> web:80                              # реализовано: статический nginx frontend
admin/browser -> app:8080                      # реализовано: Python backend отвечает на / и /health
web -> Promtail -> log:3100 Loki               # реализовано: nginx logs уходят в Loki
app -> Promtail -> log:3100 Loki               # реализовано: app logs уходят в Loki
web/app/log/monitor -> node_exporter -> monitor:9090 Prometheus -> Grafana:3000  # план
web:80 -> app:8080 через reverse proxy         # план
```

## Роли серверов

### admin

Управляющий сервер. На нем SSH-ключи, Ansible, inventory, будущие playbook'и, шаблоны конфигов, документация, возможно Git. С него выполняются SSH-подключения, curl-проверки, Ansible-команды и диагностика.

### web

Frontend / Nginx server. Сейчас отдает простую HTML-страницу. Promtail установлен и отправляет nginx access/error logs в Loki. В финале должен отдавать более осмысленный frontend и проксировать `/api/*` на `app:8080`. Также будет источником системных метрик.

### app

Backend/application node. Сейчас Python-приложение на стандартной библиотеке запущено через `app.service`, отвечает на `/` и `/health`, пишет app logs в `/var/log/app/app.log`. Promtail установлен и отправляет app logs в Loki. В финале желательно добавить более осмысленные endpoints: `/info`, `/api/time`, `/api/status`, возможно `/metrics`, JSON logs и интеграцию с `web`.

### log

Централизованный сервер логирования. На нем Loki. Loki установлен и запущен как `systemd` service. Уже принимает nginx logs от `web` и app logs от `app`.

### monitor

Сервер мониторинга и визуализации. На нем будут Prometheus, Grafana, Alertmanager, возможно blackbox_exporter. В финале показывает метрики, логи, алерты и dashboard'ы.

## Что уже сделано

### Архитектура — готово

- Определены серверы: `admin`, `web`, `app`, `log`, `monitor`.
- Все узлы на Debian.
- LXC пока не используется.
- `web` и `app` пока отдельные VM.
- Logging и monitoring остаются на отдельных серверах.
- `admin` — control node с Ansible.

### Proxmox — базово готов

- Proxmox установлен и доступен по `https://192.168.85.128:8006`.
- Используется bridge `vmbr0` через VMware NAT.
- DNS на Proxmox был исправлен, после чего заработала загрузка ISO и доступ в интернет.

### admin — минимально готов

- Debian 13 установлен.
- Hostname: `admin`.
- IP: `192.168.85.129`.
- SSH работает.
- sudo работает.
- Ansible установлен.
- Inventory создан.
- `ansible all -i ./hosts.ini -m ping` дал `pong`.
- SSH-ключ ed25519 создан.
- Структура `~/control-node` начата.

### web — Nginx и Promtail готовы

- Debian 13 установлен.
- Hostname: `web`.
- IP: `192.168.85.131`.
- SSH работает.
- sudo работает.
- Nginx установлен и запущен.
- Порт 80 слушается.
- Создан `/var/www/html/index.html`.
- Доступ с `admin` к `http://192.168.85.131` проверен.
- Nginx пишет логи в `/var/log/nginx/access.log` и `/var/log/nginx/error.log`.
- Promtail 3.5.0 установлен в `/opt/promtail/promtail`.
- Создан пользователь `promtail`, добавлен в группу `adm`.
- Создан `/etc/promtail/config.yml`.
- Создан `/etc/systemd/system/promtail.service`.
- `promtail.service` находится в состоянии `active (running)`.
- `promtail.service` включен в автозапуск.
- Promtail читает `/var/log/nginx/*.log`.
- Promtail отправляет nginx logs в Loki на `http://192.168.85.135:3100/loki/api/v1/push`.
- Loki `query_range` возвращает nginx logs по `{host="web",job="nginx"}`.

### app — backend и Promtail готовы

- Debian 13 установлен.
- Hostname: `app`.
- IP: `192.168.85.133`.
- SSH работает.
- sudo работает.
- Создано Python-приложение в `/opt/app/app.py`.
- Приложение слушает `0.0.0.0:8080`.
- `/` и `/health` работают.
- Создан `app.service`.
- `app.service` enabled + active.
- Процесс идет от пользователя `pelmel`.
- Создан `/var/log/app/app.log`.
- Приложение пишет строки логов в `/var/log/app/app.log`.
- Promtail 3.5.0 установлен в `/opt/promtail/promtail`.
- Создан пользователь `promtail`, добавлен в группу `adm`.
- Создан `/etc/promtail/config.yml`.
- Создан `/etc/systemd/system/promtail.service`.
- `promtail.service` active/enabled.
- Promtail читает `/var/log/app/*.log`.
- Promtail отправляет app logs в Loki на `http://192.168.85.135:3100/loki/api/v1/push`.
- Loki `query_range` возвращает app logs по `{host="app",job="app"}`.

### log — Loki завершен и принимает web/app logs

- Debian 13 установлен.
- Hostname: `log`.
- IP: `192.168.85.135`.
- SSH работает.
- sudo работает.
- Создан пользователь `loki`.
- Созданы `/opt/loki`, `/etc/loki`, `/var/lib/loki`.
- Скачан Loki 3.5.0.
- Проверен `/opt/loki/loki --version`.
- Создан `/etc/loki/config.yml`.
- Создан `/etc/systemd/system/loki.service`.
- `loki.service` находится в состоянии `active (running)`.
- `loki.service` включен в автозапуск.
- Порт `3100` слушается.
- Процесс Loki работает от пользователя `loki` и группы `loki`.
- На `log`: `curl http://localhost:3100/ready` возвращает `ready`.
- С `admin`: `curl http://192.168.85.135:3100/ready` возвращает `ready`.
- `http://192.168.85.135:3100` может возвращать `404 page not found`; это нормально, потому что Loki — API-сервис, а не веб-сайт.
- Loki принимает nginx logs от `web`.
- Loki принимает app logs от `app`.
- Проверка через `/loki/api/v1/query_range` возвращает `status=success` для `{host="web",job="nginx"}` и `{host="app",job="app"}`.

## Оставшиеся этапы и ожидаемые итоги

### Этап 1. Loki на `log` — завершено

Итог: создан `loki.service`, выполнен `daemon-reload`, сервис `enabled` и `active`, порт 3100 слушается, `/ready` возвращает `ready`, процесс идет от пользователя `loki`, доступ с `admin` к `http://192.168.85.135:3100/ready` работает.

### Этап 2. Promtail на `web` — завершено

Итог: Promtail установлен на `web`; nginx access/error logs уходят в Loki; labels согласованы: `host=web`, `job=nginx`, `service=frontend`, `env=lab`; запрос `{host="web",job="nginx"}` через `query_range` возвращает логи.

### Этап 3. Promtail на `app` — завершено

Итог: app logs уходят в Loki; labels согласованы: `host=app`, `job=app`, `service=python-backend`, `env=lab`; запрос `{host="app",job="app"}` через `query_range` возвращает логи.

### Этап 4. Поднять `monitor` — текущий следующий этап

Итог: создана VM `monitor`; Debian, SSH, sudo; установлены Prometheus, Grafana, Alertmanager; сервисы active/enabled; доступны порты 3000, 9090, 9093.

### Этап 5. Метрики

Итог: node_exporter установлен на `web`, `app`, `log`, возможно `monitor`; Prometheus видит targets как UP; Grafana видит Prometheus datasource; доступны CPU/RAM/disk/network/uptime метрики.

### Этап 6. Интеграция `web` и `app`

Итог: Nginx на `web` проксирует `/api/*` на `app:8080`; сайт на `web` может получать данные от `app`; пользовательский поток Browser -> web -> app работает.

### Этап 7. Grafana + Loki + Prometheus

Итог: в Grafana добавлены datasources Loki и Prometheus; видны логи `web` и `app`, метрики узлов, dashboard'ы.

### Этап 8. Полировка logging

Итог: labels логов стабильны; app пишет полезные логи, возможно JSON; в Grafana/Loki удобно фильтровать по `host`, `job`, `service`, `level`, `endpoint`.

### Этап 9. Полировка monitoring

Итог: есть dashboard'ы Infrastructure Overview, Web, App, Logs/Observability; есть базовые alerts: target down, app health fail, disk usage warning.

### Этап 10. Полировка Ansible/admin

Итог: inventory содержит все реальные узлы; SSH-ключи раскатаны; Ansible подключается к `web`, `app`, `log`, `monitor`; есть первые playbook'и для базовой настройки, установки nginx/app/promtail/node_exporter и рестарта сервисов.

### Этап 11. Демонстрационный сценарий

Итог: можно показать полный сценарий: открыть сайт, проверить backend, увидеть логи, увидеть метрики, уронить `app.service`, увидеть проблему в логах/метриках/alerts, поднять сервис обратно и подтвердить восстановление.

## Текущий прогресс

Оценка текущего прогресса после завершения Promtail на `app`: **65–75% проекта**.

Текущий ближайший следующий шаг: **создать `monitor` и начать этап Prometheus/Grafana/Alertmanager**.

Оценка остатка:

- текущий темп: 4–7 дней;
- ускоренный темп: 3–5 дней;
- вдумчивая полировка и документация: 7–12 дней.
