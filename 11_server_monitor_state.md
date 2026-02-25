# Текущее состояние сервера monitor

## Назначение

`monitor` — сервер мониторинга, визуализации и алертов.

Роль:

- Prometheus — сбор и хранение метрик;
- Grafana — визуализация метрик и логов;
- Alertmanager — прием alerts от Prometheus;
- node_exporter — системные метрики самого `monitor`;
- сбор системных метрик с `web`, `app`, `log`.

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
- Prometheus видит `node (4/4 up)`.

Текущие node targets:

```text
monitor: localhost:9100, host="monitor"
web:     192.168.85.131:9100, host="web"
app:     192.168.85.133:9100, host="app"
log:     192.168.85.135:9100, host="log"
```

App `/metrics` scrape пока не добавлен. Это задача этапа Полировка monitoring.

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
- Prometheus видит Alertmanager.

Файл параметров:

```text
/etc/default/prometheus-alertmanager
```

Текущая строка:

```bash
ARGS="--cluster.listen-address="
```

Alert rules пока не создавались.

## Dashboard Infrastructure Overview

Dashboard создан через Grafana UI.

Panels:

```text
Targets UP
Disk Usage by host
CPU Usage by host
RAM Usage by host
Web nginx logs
App logs
```

App logs panel была создана до перехода на `support-desk-api` и рассчитана на старый формат logs. Обновление LogQL под новый `event=...` формат относится к этапу Полировка logging.

## Product logs после Web/App integration

После перехода приложения на Mini Support Desk API Grafana Explore/Loki подтверждает прием новых app product logs.

Проверенный запрос:

```logql
{host="app", job="app"} |= "support-desk-api"
```

Видны события:

```text
event=ticket_created
event=ticket_status_changed
event=ticket_list_requested
event=health_check
```

Пример строки:

```text
service=support-desk-api event=ticket_status_changed method=PATCH path=/tickets/6/status status=200 client_ip=192.168.85.131 ticket_id=6 old_status=in_progress new_status=resolved source=web
```

## Текущий статус

`monitor` готов как observability node:

- Prometheus active/enabled;
- Grafana active/enabled;
- Alertmanager active/enabled;
- node_exporter targets `4/4 up`;
- Grafana datasources подключены;
- Infrastructure Overview создан;
- Loki/Grafana видит новые product logs от Mini Support Desk.
