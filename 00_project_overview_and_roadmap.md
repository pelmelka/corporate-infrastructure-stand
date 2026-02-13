# Mini Corporate Infrastructure Lab — план и roadmap

## Цель проекта

Собрать учебный pet-project в формате мини-инфраструктуры корпоративного типа на базе Proxmox VE внутри VMware. Это не набор отдельных VM, а связанный стенд с frontend, backend, централизованным логированием, мониторингом, базовой автоматизацией и демонстрационными сценариями troubleshooting.

Итоговая ценность проекта: показать навыки Linux administration, DevOps-подхода, systemd, SSH, Ansible, Nginx, Python-сервисов, Loki/Promtail, Prometheus/Grafana/Alertmanager, node_exporter и диагностики.

## Итоговая архитектура

```text
Windows host / Browser / SSH client
        |
        | VMware NAT / local access
        v
Proxmox VE node: 192.168.85.128:8006
        |
        +-- admin    192.168.85.129  control node / Ansible
        +-- web      192.168.85.131  Nginx frontend + Promtail
        +-- app      192.168.85.133  Python backend service + Promtail
        +-- log      192.168.85.135  Loki logging server
        +-- monitor  192.168.85.137  Prometheus + Grafana + Alertmanager + node_exporter
```

Реализованные и планируемые потоки:

```text
Browser -> web:80                                      # реализовано: статический nginx frontend
admin/browser -> app:8080                              # реализовано: Python backend отвечает на / и /health
web -> Promtail -> log:3100 Loki                       # реализовано: nginx logs уходят в Loki
app -> Promtail -> log:3100 Loki                       # реализовано: app logs уходят в Loki
monitor:9090 Prometheus -> monitor:9100 node_exporter  # реализовано: метрики monitor
Prometheus -> Alertmanager:9093                        # реализовано: Prometheus видит Alertmanager
Browser -> monitor:9090 Prometheus UI                  # реализовано
Browser -> monitor:3000 Grafana UI                     # реализовано
web/app/log -> node_exporter:9100 -> Prometheus         # реализовано: node (4/4 up)
Grafana -> Prometheus:9090                             # текущий следующий этап: datasource
Grafana -> Loki:3100                                   # текущий следующий этап: datasource
web:80 -> app:8080 через reverse proxy                 # план
```

## Важное замечание про IP

На текущем этапе все VM получают IP через DHCP VMware NAT. В lab-режиме адреса держатся стабильно, потому что VMware NAT обычно выдает адрес “липко” по MAC-адресу VM.

Но для более правильной и воспроизводимой инфраструктуры позже нужно сделать одно из двух:

```text
1. DHCP reservation по MAC-адресам всех VM;
2. статические IP внутри Debian на всех серверах.
```

Это важно, потому что в проекте уже есть зависимости от IP: Promtail отправляет данные в Loki на `192.168.85.135:3100`, Prometheus будет опрашивать targets по IP, Grafana будет подключаться к Loki/Prometheus, Ansible inventory тоже будет завязан на адреса узлов.

## Роли серверов

### admin

Управляющий сервер. На нем SSH-ключи, Ansible, inventory, будущие playbook'и, шаблоны конфигов, документация, возможно Git. С него выполняются SSH-подключения, curl-проверки, Ansible-команды и диагностика.

### web

Frontend / Nginx server. Сейчас отдает простую HTML-страницу. Promtail установлен и отправляет nginx access/error logs в Loki. В финале должен отдавать более осмысленный frontend и проксировать `/api/*` на `app:8080`. Также является источником системных метрик через node_exporter.

### app

Backend/application node. Сейчас Python-приложение на стандартной библиотеке запущено через `app.service`, отвечает на `/` и `/health`, пишет app logs в `/var/log/app/app.log`. Promtail установлен и отправляет app logs в Loki. В финале желательно добавить более осмысленные endpoints: `/info`, `/api/time`, `/api/status`, возможно `/metrics`, JSON logs и интеграцию с `web`.

### log

Централизованный сервер логирования. На нем Loki. Loki установлен и запущен как `systemd` service. Принимает nginx logs от `web` и app logs от `app`. Позже Grafana будет подключаться к Loki как datasource. На `log` также работает node_exporter для системных метрик.

### monitor

Сервер мониторинга, визуализации и алертов. На нем уже установлены Prometheus, Grafana, Alertmanager и node_exporter. Сейчас Prometheus собирает метрики самого `monitor` и метрики `web`, `app`, `log` через node_exporter. Prometheus показывает `node (4/4 up)`; следующий шаг — подключить Prometheus и Loki как datasources в Grafana.

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
- После проблемы с автозапуском Loki после reboot добавлены `common.ring.instance_addr: 127.0.0.1` и `memberlist.advertise_addr: 127.0.0.1`; после этого `loki.service` корректно поднимается после reboot.

### monitor — базовый observability stack готов

- Debian 13 установлен.
- Hostname: `monitor`.
- IP: `192.168.85.137`.
- SSH работает.
- sudo работает.
- Связность с `admin`, `web`, `app`, `log` проверена.
- Loki доступен с `monitor`: `curl http://192.168.85.135:3100/ready -> ready`.
- Prometheus установлен из стандартных Debian-репозиториев.
- `prometheus.service` active/enabled.
- Prometheus слушает порт `9090`.
- Prometheus UI доступен: `http://192.168.85.137:9090`.
- Grafana 13.0.1 установлена через локальный `.deb` файл.
- `grafana-server.service` active/enabled.
- Grafana слушает порт `3000`.
- Grafana UI доступен: `http://192.168.85.137:3000`.
- Alertmanager установлен как пакет `prometheus-alertmanager`.
- `prometheus-alertmanager.service` active/enabled.
- Alertmanager слушает порт `9093`.
- `curl http://localhost:9093/-/ready -> OK`.
- Prometheus уже знает Alertmanager: `localhost:9093` отображается в `/api/v1/alertmanagers`.
- `prometheus-node-exporter.service` на `monitor` active/enabled.
- node_exporter на `monitor` слушает порт `9100`.
- node_exporter установлен и active/enabled на `web`, `app`, `log`.
- Prometheus видит targets `prometheus (1/1 up)` и `node (4/4 up)`.
- У node targets добавлены labels `host="monitor"`, `host="web"`, `host="app"`, `host="log"`.

#### Особенность установки Grafana

Официальные домены Grafana были недоступны из текущей сети/маршрута:

```text
apt.grafana.com/gpg.key -> HTTP 403 Access Denied
apt.grafana.com/gpg-full.key -> HTTP 403
ответ содержал: Sorry, the provided token is not valid
dl.grafana.com/...deb -> HTTP 451
```

DNS, ping и TLS handshake при этом работали. Это означает, что проблема была не в Debian, curl/wget, DNS или сертификатах, а в отказе Grafana CDN выдать файлы. Практическое решение: скачать `.deb` на Windows через доступный маршрут, передать файл на `monitor` через `scp`, установить локально через `sudo apt install ./grafana_...deb`. После успешной установки следы неудачных попыток были очищены; директории `/etc/apt/keyrings` и `/etc/apt/sources.list.d` не удалялись.

## Оставшиеся этапы и ожидаемые итоги

### Этап 1. Loki на `log` — завершено

Итог: создан `loki.service`, сервис `enabled` и `active`, порт 3100 слушается, `/ready` возвращает `ready`, процесс идет от пользователя `loki`, доступ с `admin` к `http://192.168.85.135:3100/ready` работает, web/app logs доходят в Loki.

### Этап 2. Promtail на `web` — завершено

Итог: Promtail установлен на `web`; nginx access/error logs уходят в Loki; labels согласованы: `host=web`, `job=nginx`, `service=frontend`, `env=lab`; запрос `{host="web",job="nginx"}` через `query_range` возвращает логи.

### Этап 3. Promtail на `app` — завершено

Итог: app logs уходят в Loki; labels согласованы: `host=app`, `job=app`, `service=python-backend`, `env=lab`; запрос `{host="app",job="app"}` через `query_range` возвращает логи.

### Этап 4. Поднять `monitor` — завершено

Итог: создана VM `monitor`; Debian, SSH, sudo и сеть работают; установлены Prometheus, Grafana, Alertmanager; сервисы active/enabled; доступны порты 3000, 9090, 9093; node_exporter на `monitor` работает на 9100.

### Этап 5. Метрики — завершено

Итог: node_exporter установлен на `web`, `app`, `log`, `monitor`; Prometheus видит targets как `node (4/4 up)`; добавлены labels `host="monitor"`, `host="web"`, `host="app"`, `host="log"`; доступны CPU/RAM/disk/network/uptime метрики по всем узлам.

Концептуально зафиксировано:

```text
node_exporter + Prometheus = pull-модель метрик.
Prometheus сам приходит на :9100/metrics и забирает метрики.
Promtail + Loki = push-модель логов.
Promtail сам отправляет logs в Loki на /loki/api/v1/push.
```

### Этап 6. Grafana + Loki + Prometheus — текущий следующий этап

Итог: в Grafana должны быть добавлены datasources Loki и Prometheus; должны быть видны логи `web` и `app`, метрики узлов, dashboard'ы.

### Этап 7. Интеграция `web` и `app`

Итог: Nginx на `web` проксирует `/api/*` на `app:8080`; сайт на `web` может получать данные от `app`; пользовательский поток Browser -> web -> app работает.

### Этап 8. Полировка logging

Итог: labels логов стабильны; app пишет полезные логи, возможно JSON; в Grafana/Loki удобно фильтровать по `host`, `job`, `service`, `level`, `endpoint`.

### Этап 9. Полировка monitoring

Итог: есть dashboard'ы Infrastructure Overview, Web, App, Logs/Observability; есть базовые alerts: target down, app health fail, disk usage warning.

### Этап 10. Полировка Ansible/admin

Итог: inventory содержит все реальные узлы; SSH-ключи раскатаны; Ansible подключается к `web`, `app`, `log`, `monitor`; есть первые playbook'и для базовой настройки, установки nginx/app/promtail/node_exporter и рестарта сервисов.

### Этап 11. Демонстрационный сценарий

Итог: можно показать полный сценарий: открыть сайт, проверить backend, увидеть логи, увидеть метрики, уронить `app.service`, увидеть проблему в логах/метриках/alerts, поднять сервис обратно и подтвердить восстановление.

## Текущий прогресс

Оценка текущего прогресса после завершения node_exporter и Prometheus targets: **80–85% проекта**.

Текущий ближайший следующий шаг: **подключить Prometheus и Loki как datasources в Grafana**.

Оценка остатка:

- текущий темп: 3–6 дней;
- ускоренный темп: 2–4 дня;
- вдумчивая полировка и документация: 6–10 дней.
