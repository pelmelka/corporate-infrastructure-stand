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
- nginx logs отправляются в Loki через Promtail.

## Application слой

### Python

Используется на `app`. Сейчас стандартная библиотека `http.server`; позже возможен Flask.

Текущее состояние:

- приложение находится в `/opt/app/app.py`;
- сервис: `app.service`;
- порт: `8080`;
- endpoints: `/`, `/health`, остальные пути дают `404`;
- application logs пишутся в `/var/log/app/app.log`;
- app logs отправляются в Loki через Promtail.

### systemd

Используется для:

- `app.service` на `app`;
- `loki.service` на `log`;
- `promtail.service` на `web`;
- `promtail.service` на `app`;
- позже для Prometheus, Grafana, Alertmanager, node_exporter.

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
- принимает app logs от `app` через Promtail;
- запрос `{host="web",job="nginx"}` через `/loki/api/v1/query_range` возвращает nginx access logs;
- запрос `{host="app",job="app"}` через `/loki/api/v1/query_range` возвращает app logs.

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

### Promtail на app

Установлен на `app`.

Текущее состояние:

- версия: `3.5.0`;
- binary: `/opt/promtail/promtail`;
- config: `/etc/promtail/config.yml`;
- positions: `/var/lib/promtail/positions.yaml`;
- user/group: `promtail:promtail`;
- дополнительная группа: `adm` для чтения `/var/log/app/app.log`;
- service: `promtail.service`;
- status: `active (running)`;
- autostart: `enabled`;
- служебный порт: `9080`;
- читает: `/var/log/app/app.log` через паттерн `/var/log/app/*.log`;
- отправляет в Loki: `http://192.168.85.135:3100/loki/api/v1/push`;
- labels: `host=app`, `job=app`, `service=python-backend`, `env=lab`.

Роль: чтение app logs, добавление labels, отправка в Loki.

Важно: `/loki/api/v1/push` — API endpoint для POST-запросов от Promtail, а не страница для браузера. `HTTP ERROR 405` при открытии в браузере не означает поломку.

Важно: обычные log queries нужно проверять через `/loki/api/v1/query_range`, а не через `/loki/api/v1/query`.

## Monitoring

### Prometheus

Установлен на `monitor` из стандартных Debian-репозиториев.

Текущее состояние:

- service: `prometheus.service`;
- status: `active (running)`;
- autostart: `enabled`;
- порт: `9090`;
- UI: `http://192.168.85.137:9090`;
- readiness: `curl http://localhost:9090/-/ready -> Prometheus Server is Ready.`;
- API-запрос `query=up` возвращает `job="prometheus", instance="localhost:9090", value="1"`;
- видит local node_exporter на `localhost:9100`;
- видит node_exporter на `web`, `app`, `log`;
- Prometheus UI показывает `node (4/4 up)`;
- у node targets добавлены labels `host="monitor"`, `host="web"`, `host="app"`, `host="log"`.

Роль: сбор и хранение метрик. Сейчас собирает метрики самого `monitor` и системные метрики `web`, `app`, `log` через node_exporter.

### Grafana

Установлена на `monitor` как Grafana 13.0.1 через локальный `.deb` файл.

Текущее состояние:

- service: `grafana-server.service`;
- status: `active (running)`;
- autostart: `enabled`;
- порт: `3000`;
- UI: `http://192.168.85.137:3000`;
- `curl -I http://localhost:3000` возвращает `HTTP/1.1 302 Found` и `Location: /login`.

Роль: UI для dashboard'ов, логов и метрик. В Grafana нужно будет подключить datasources:

- Loki: `http://192.168.85.135:3100`;
- Prometheus: `http://localhost:9090` или `http://192.168.85.137:9090`.

Особенность установки: официальный Grafana APT/download был недоступен из текущей сети/маршрута:

```text
apt.grafana.com/gpg.key -> HTTP 403 Access Denied
apt.grafana.com/gpg-full.key -> HTTP 403
ответ содержал: Sorry, the provided token is not valid
dl.grafana.com/...deb -> HTTP 451
```

Практическое решение: скачать `.deb` на Windows через доступный маршрут, передать на `monitor` через `scp`, установить локально через `sudo apt install ./grafana_...deb`. После установки следы неудачных попыток были очищены. Директории `/etc/apt/keyrings` и `/etc/apt/sources.list.d` не удалялись.

### Alertmanager

Установлен на `monitor` из стандартных Debian-репозиториев как пакет `prometheus-alertmanager`.

Текущее состояние:

- service: `prometheus-alertmanager.service`;
- status: `active (running)`;
- autostart: `enabled`;
- порт: `9093`;
- readiness: `curl http://localhost:9093/-/ready -> OK`;
- Prometheus уже знает Alertmanager через `localhost:9093`.

Проверка Prometheus API:

```bash
curl -s http://localhost:9090/api/v1/alertmanagers | python3 -m json.tool
```

Подтверждено:

```json
{
    "status": "success",
    "data": {
        "activeAlertmanagers": [
            {
                "url": "http://localhost:9093/api/v2/alerts"
            }
        ],
        "droppedAlertmanagers": []
    }
}
```

Важно: Debian-пакет Alertmanager не включает полноценный web UI. По `http://192.168.85.137:9093` открывается простая HTML-страница с пояснением и ссылками на `/metrics`, `/-/healthy`, `/-/ready`. Это нормально, API и health endpoints работают.

### node_exporter

`node_exporter` установлен как пакет `prometheus-node-exporter` на всех monitored nodes:

```text
monitor: localhost:9100
web:     192.168.85.131:9100
app:     192.168.85.133:9100
log:     192.168.85.135:9100
```

Текущее состояние:

- service: `prometheus-node-exporter.service`;
- status: `active (running)` на `monitor`, `web`, `app`, `log`;
- autostart: `enabled` на `monitor`, `web`, `app`, `log`;
- порт: `9100`;
- `/metrics` возвращает системные метрики;
- `monitor` успешно получает `/metrics` с `web`, `app`, `log`;
- Prometheus UI показывает `node (4/4 up)`.

Prometheus labels:

```text
instance="localhost:9100", host="monitor", job="node"
instance="192.168.85.131:9100", host="web", job="node"
instance="192.168.85.133:9100", host="app", job="node"
instance="192.168.85.135:9100", host="log", job="node"
```

Концептуально:

```text
node_exporter + Prometheus = pull-модель метрик.
node_exporter отдает endpoint :9100/metrics, Prometheus сам приходит и забирает метрики.
Promtail + Loki = push-модель логов: Promtail сам отправляет логи в Loki.
```

## Планируемые dashboard'ы

- Infrastructure Overview
- Web Node Dashboard
- App Node Dashboard
- Logs / Observability
- Loki dashboard
- Prometheus targets dashboard

## Планируемые alerts

- TargetDown: один из targets Prometheus недоступен;
- HighDiskUsage: высокий процент использования диска;
- AppDown или AppHealthFail: backend health endpoint недоступен;
- LokiDown: Loki `/ready` недоступен;
- PromtailDown: Promtail не отвечает на служебном порту или нет новых логов.

## Планируемые демонстрационные сценарии

1. Нормальная работа: открыть сайт, дернуть backend, увидеть логи и метрики.
2. App down: остановить `app.service`, увидеть ошибку, поднять обратно.
3. Web logs: сгенерировать HTTP-запросы и увидеть nginx logs в Loki.
4. App logs: сгенерировать HTTP-запросы и увидеть app logs в Loki.
5. Infrastructure overview: показать состояние всех узлов. База для этого готова: Prometheus видит node targets `4/4 up`.
