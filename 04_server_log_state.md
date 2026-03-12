# Текущее состояние сервера log

## Назначение

`log` — централизованный сервер логирования.

Роль:

- запускать Loki;
- принимать nginx logs от `web`;
- принимать app product logs от `app`;
- отдавать logs в Grafana через Loki datasource;
- отдавать системные метрики через node_exporter.

## Основная информация

- Hostname: `log`
- IP: `192.168.85.135/24`
- Loki HTTP: `3100/tcp`
- Loki gRPC: `9095/tcp`
- node_exporter: `9100/tcp`

## Loki

Сервис:

```text
loki.service
```

Подтверждено:

- `loki.service active (running)`;
- `enabled`;
- `/ready -> ready`;
- web/app logs принимаются.

Важные paths:

```text
/opt/loki/loki
/etc/loki/config.yml
/var/lib/loki
```

## Loki config autostart fix

В `/etc/loki/config.yml` добавлены параметры для корректного autostart после reboot в VM:

```yaml
common:
  ring:
    instance_addr: 127.0.0.1
    kvstore:
      store: inmemory

memberlist:
  advertise_addr: 127.0.0.1
```

## Web logs

Loki принимает nginx logs от `web`.

Базовый LogQL:

```logql
{host="web", job="nginx"}
```

После Product model v2 flow ожидаемые строки:

```text
GET /api/v1/health HTTP/1.1 200
GET /api/v1/support-model HTTP/1.1 200
GET /api/v1/tickets HTTP/1.1 200
POST /api/v1/tickets HTTP/1.1 201
PATCH /api/v1/tickets/<id>/status HTTP/1.1 200
```

## App product logs

Loki принимает product logs от `MISIS_Digital Student Support`.

Старый stream до Product model v2:

```logql
{host="app", job="app", service="support-desk-api"}
```

Новый stream после обновления Promtail:

```logql
{host="app", job="app", service="misis-digital-student-support-api"}
```

Дополнительный dynamic label:

```text
category=<newlms-misis|lk-misis|gornyak-misis|folio-misis|pulse-misis|vector-misis|pay-misis>
```

Проверенные запросы:

```logql
{host="app", job="app", service="misis-digital-student-support-api"}
```

```logql
{host="app", job="app", service="misis-digital-student-support-api", category="pay-misis"}
```

```logql
{host="app", job="app", category="gornyak-misis"}
```

```logql
{host="app", job="app", category="lk-misis"}
```

Для `resource` пока используется фильтр по строке:

```logql
{host="app", job="app", service="misis-digital-student-support-api", category="pay-misis"}
|= "resource=dorm-payment"
```

Текущий формат для Grafana App logs panel:

```logql
{host="app", job="app", service="misis-digital-student-support-api"}
| logfmt
| line_format "{{.event}} | {{.method}} {{.path}} | status={{.status}} | category={{.category}} | resource={{.resource}} | ticket={{.ticket_id}} | {{.old_status}} -> {{.new_status}} | client={{.x_forwarded_for}} | proxy={{.client_ip}}"
```

Подтвержденные события:

```text
event=ticket_created
event=ticket_status_changed
event=ticket_status_unchanged
event=ticket_list_requested
event=health_check
event=support_model_requested
event=ticket_validation_failed
event=ticket_not_found
event=endpoint_not_found
event=metrics_requested
```

Подтвержденный поток:

```text
Browser -> web/Nginx -> app/misis-digital-student-support-api -> app.log -> Promtail -> Loki -> Grafana
```

Пример новых строк:

```text
service=misis-digital-student-support-api event=ticket_created method=POST path=/v1/tickets status=201 client_ip=192.168.85.131 x_forwarded_for=192.168.85.1 x_forwarded_proto=http api_version=v1 ticket_id=4 category=gornyak-misis resource=plumber-request priority=normal source=web
service=misis-digital-student-support-api event=ticket_status_changed method=PATCH path=/v1/tickets/2/status status=200 client_ip=192.168.85.131 x_forwarded_for=192.168.85.1 x_forwarded_proto=http api_version=v1 ticket_id=2 old_status=open new_status=in_progress category=pay-misis resource=dorm-payment source=web resolved_at=-
```

## node_exporter

`prometheus-node-exporter.service` active/enabled, порт `9100` слушается. Prometheus видит target `host="log"`.

## Текущий статус

`log` готов как Loki logging server: принимает nginx logs и app product logs, отдает logs в Grafana, поддерживает фильтрацию app logs по dynamic label `category`, а также отдает системные метрики через node_exporter.
