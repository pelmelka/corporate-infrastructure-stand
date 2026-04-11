# Текущее состояние сервера log

## Назначение

`log` — централизованный сервер логирования.

Роль:

- запускать Loki;
- принимать nginx logs от `web`;
- принимать app product logs от `app`;
- принимать Telegram bot logs от `app`;
- принимать PostgreSQL logs от `db`;
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
- web/app/db logs принимаются;
- support-bot logs принимаются отдельным Loki stream-ом.

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
| path != "/metrics"
| line_format "{{.event}}{{ if .method }} | {{.method}}{{ end }}{{ if .path }} {{.path}}{{ end }}{{ if .status }} | status={{.status}}{{ end }}{{ if .ticket_id }} | ticket={{.ticket_id}}{{ end }}{{ if .old_status }} | {{.old_status}}{{ end }}{{ if .new_status }} -> {{.new_status}}{{ end }}{{ if .category }} | category={{.category}}{{ end }}{{ if .resource }} | resource={{.resource}}{{ end }}{{ if .priority }} | priority={{.priority}}{{ end }}{{ if .source }} | source={{.source}}{{ end }}{{ if .filter }} | filter={{.filter}}{{ end }}{{ if .count }} | count={{.count}}{{ end }}{{ if .reason }} | reason={{.reason}}{{ end }}{{ if and .x_forwarded_for (ne .x_forwarded_for "-") }} | client={{.x_forwarded_for}}{{ end }}{{ if .client_ip }} | via={{.client_ip}}{{ end }}{{ if .error }} | error={{.error}}{{ end }}"
```

`path != "/metrics"` скрывает шумные Prometheus scrape-запросы от `monitor` (`192.168.85.137`) к backend `/metrics`.

В отображении `via` означает direct client IP: IP узла, который физически подключился к backend API. Для web-flow это обычно Nginx (`192.168.85.131`), для Telegram-flow это внутренний Docker IP контейнера `support-bot` (`172.18.0.x`).

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


## Telegram bot logs

После этапа 18 Loki принимает bot logs от `app` через Promtail.

Stream:

```logql
{host="app", job="support-bot", service="misis-digital-support-bot"}
```

Файл на app:

```text
/var/log/bot/support-bot.log
```

Базовая панель `Bot recent logs`:

```logql
{host="app", job="support-bot", service="misis-digital-support-bot"}
| logfmt
| line_format "{{.event}}{{ if .normalized_action }} | action={{.normalized_action}}{{ end }}{{ if .ticket_id }} | ticket={{.ticket_id}}{{ end }}{{ if .new_status }} | status={{.new_status}}{{ end }}{{ if .category }} | category={{.category}}{{ end }}{{ if .resource }} | resource={{.resource}}{{ end }}{{ if .count }} | count={{.count}}{{ end }}{{ if .page }} | page={{.page}}{{ end }}{{ if .telegram_user_id }} | user={{.telegram_user_id}}{{ end }}"
```

Панель `Bot error logs`:

```logql
{host="app", job="support-bot", service="misis-digital-support-bot"}
| logfmt
| event=~"handler_error|backend_health_failed|ticket_create_failed|ticket_resolve_failed|support_model_load_failed|active_tickets_request_failed|resolve_menu_failed|handler_error_notify_failed"
| line_format "{{.event}}{{ if .error_type }} | type={{.error_type}}{{ end }}{{ if .ticket_id }} | ticket={{.ticket_id}}{{ end }}{{ if .normalized_action }} | action={{.normalized_action}}{{ end }}{{ if .category }} | category={{.category}}{{ end }}{{ if .resource }} | resource={{.resource}}{{ end }}{{ if .error }} | error={{.error}}{{ end }}{{ if .telegram_user_id }} | user={{.telegram_user_id}}{{ end }}"
```

Подтвержденные bot events:

```text
bot_starting
metrics_server_started
bot_started
start_command
button_pressed
new_ticket_started
ticket_category_selected
ticket_resource_selected
ticket_priority_selected
ticket_description_received
ticket_created_via_bot
active_tickets_requested
resolve_menu_requested
ticket_resolved_via_bot
backend_health_ok
handler_error
```

Токен Telegram bot не должен попадать в логи. После обнаружения leak старый token был перевыпущен, log file очищен, а `bot.py` получил suppression сторонних HTTP-логов и SecretRedactingFilter.

## DB PostgreSQL logs

После этапа 17 Loki принимает PostgreSQL logs от `db` через Promtail.

Stream:

```logql
{host="db", job="postgresql"}
```

Important logs filter для dashboard:

```logql
{host="db", job="postgresql"}
|~ "(ERROR|FATAL|PANIC|shutting down|ready to accept connections|starting PostgreSQL|terminating connection|deadlock)"
```

Проверено тестовой безопасной ошибкой PostgreSQL:

```text
ERROR: relation "promtail_db_log_test_table" does not exist
STATEMENT: SELECT * FROM promtail_db_log_test_table;
```

Подтвержденный поток:

```text
db PostgreSQL log file -> db Promtail -> log/Loki -> Grafana PostgreSQL Important Logs panel
```

## node_exporter

`prometheus-node-exporter.service` active/enabled, порт `9100` слушается. Prometheus видит target `host="log"`.

## Текущий статус

`log` готов как Loki logging server: принимает nginx logs, app product logs, Telegram bot logs и PostgreSQL logs, отдает logs в Grafana, поддерживает фильтрацию app logs по dynamic label `category`, а также отдает системные метрики через node_exporter.

## Security/network hardening

UFW installed and active after Stage 19.

Current policy:

```text
default incoming: deny
default outgoing: allow
routed: disabled
```

Allowed inbound:

```text
192.168.85.129 -> 22/tcp     admin SSH/Ansible
192.168.85.131 -> 3100/tcp   web Promtail -> Loki
192.168.85.133 -> 3100/tcp   app Promtail -> Loki
192.168.85.139 -> 3100/tcp   db Promtail -> Loki
192.168.85.137 -> 3100/tcp   monitor/Grafana Loki datasource
192.168.85.129 -> 3100/tcp   admin Loki diagnostics
192.168.85.137 -> 9100/tcp   monitor node_exporter scrape
192.168.85.129 -> 9100/tcp   admin node_exporter diagnostics
```

`9095/tcp` Loki gRPC is intentionally not opened to external nodes because current project flows use Loki HTTP API on `3100/tcp`.

Confirmed:

```text
admin -> log:3100 /ready works;
web/app/db -> log:3100 works;
monitor -> log:3100 and log:9100 works;
external/non-allowed access to log:9095 is blocked;
Grafana/Loki logs remain available.
```

