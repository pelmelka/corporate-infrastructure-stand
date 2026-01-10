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
        +-- web     192.168.85.131  Nginx frontend
        +-- app     192.168.85.133  Python backend service
        +-- log     192.168.85.135  Loki logging server
        +-- monitor TBD             Prometheus + Grafana + Alertmanager
```

Планируемые потоки:

```text
Browser -> web:80 -> app:8080                 # пользовательский поток, позже через reverse proxy
web/app -> Promtail -> log:3100 Loki          # централизованные логи
web/app/log/monitor -> node_exporter -> monitor:9090 Prometheus -> Grafana:3000  # метрики
```

## Роли серверов

### admin

Управляющий сервер. На нем SSH-ключи, Ansible, inventory, будущие playbook'и, шаблоны конфигов, документация, возможно Git. С него выполняются SSH-подключения, curl-проверки, Ansible-команды и диагностика.

### web

Frontend / Nginx server. Сейчас отдает простую HTML-страницу. В финале должен отдавать осмысленный frontend и проксировать `/api/*` на `app:8080`. Будет источником nginx access/error логов и системных метрик.

### app

Backend/application node. Сейчас Python-приложение на стандартной библиотеке, запущенное через `app.service`. В финале желательно сделать более осмысленный backend: `/`, `/health`, `/info`, `/api/time`, `/api/status`, возможно `/metrics`, структурированные логи, интеграция с `web`.

### log

Централизованный сервер логирования. На нем Loki. В финале принимает логи от Promtail с `web` и `app`, хранит их и отдает Grafana.

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

### web — минимально готов

- Debian 13 установлен.
- Hostname: `web`.
- IP: `192.168.85.131`.
- SSH работает.
- sudo работает.
- Nginx установлен и запущен.
- Порт 80 слушается.
- Создан `/var/www/html/index.html`.
- Доступ с `admin` к `http://192.168.85.131` проверен.

### app — минимально готов

- Debian 13 установлен.
- Hostname: `app`.
- IP: `192.168.85.133`.
- SSH работает.
- sudo работает.
- Создано Python-приложение в `/opt/app/app.py`.
- Приложение слушает 8080.
- `/` и `/health` работают.
- Создан `app.service`.
- `app.service` enabled + active.
- Проверено, что процесс идет от `pelmel`.
- Доступ с `admin` к `http://192.168.85.133:8080` и `/health` проверен.

### log — база готова, Loki почти доведен

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
- Loki вручную запускался от пользователя `loki`.
- `curl http://localhost:3100/ready` возвращал `ready`.
- Ручной процесс Loki был остановлен, порт 3100 освобожден.
- Осталось оформить Loki как systemd service.

## Оставшиеся этапы и ожидаемые итоги

### Этап 1. Завершить Loki на `log`

Итог: создан `loki.service`, выполнен `daemon-reload`, сервис `enabled` и `active`, порт 3100 слушается, `/ready` возвращает `ready`, процесс идет от пользователя `loki`, доступ с `admin` к `http://192.168.85.135:3100/ready` работает.

### Этап 2. Promtail на `web` и `app`

Итог: Promtail установлен на `web` и `app`; nginx access/error logs уходят в Loki; app logs уходят в Loki; labels согласованы: `host`, `job`, `service`, `env`.

### Этап 3. Поднять `monitor`

Итог: создана VM `monitor`; Debian, SSH, sudo; установлены Prometheus, Grafana, Alertmanager; сервисы active/enabled; доступны порты 3000, 9090, 9093.

### Этап 4. Метрики

Итог: node_exporter установлен на `web`, `app`, `log`, возможно `monitor`; Prometheus видит targets как UP; Grafana видит Prometheus datasource; доступны CPU/RAM/disk/network/uptime метрики.

### Этап 5. Интеграция `web` и `app`

Итог: Nginx на `web` проксирует `/api/*` на `app:8080`; сайт на `web` может получать данные от `app`; пользовательский поток Browser -> web -> app работает.

### Этап 6. Grafana + Loki + Prometheus

Итог: в Grafana добавлены datasources Loki и Prometheus; видны логи `web` и `app`, метрики узлов, dashboard'ы.

### Этап 7. Полировка logging

Итог: labels логов стабильны; app пишет полезные логи, возможно JSON; в Grafana/Loki удобно фильтровать по `host`, `job`, `service`, `level`, `endpoint`.

### Этап 8. Полировка monitoring

Итог: есть dashboard'ы Infrastructure Overview, Web, App, Logs/Observability; есть базовые alerts: target down, app health fail, disk usage warning.

### Этап 9. Полировка Ansible/admin

Итог: inventory содержит все реальные узлы; SSH-ключи раскатаны; Ansible подключается к `web`, `app`, `log`, `monitor`; есть первые playbook'и для базовой настройки, установки nginx/app/promtail/node_exporter и рестарта сервисов.

### Этап 10. Демонстрационный сценарий

Итог: можно показать полный сценарий: открыть сайт, проверить backend, увидеть логи, увидеть метрики, уронить `app.service`, увидеть проблему в логах/метриках/alerts, поднять сервис обратно и подтвердить восстановление.

## Текущий прогресс

Оценка текущего прогресса: **45–55% проекта**.

Оценка остатка:

- текущий темп: 5–9 дней;
- ускоренный темп: 3–5 дней;
- вдумчивая полировка и документация: 7–12 дней.
