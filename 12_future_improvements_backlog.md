# Future improvements backlog

Этот файл хранит идеи будущих улучшений. Он нужен, чтобы не дублировать backlog по разным state/config sources. Текущие фактические состояния серверов фиксируются в server state files, а будущие улучшения — здесь.

## Полировка logging

### 1. Structured JSON logs

Перевести app product logs с текущего учебного `key=value` формата на structured JSON logs.

Текущий формат:

```text
event=ticket_created method=POST path=/tickets status=201 ticket_id=6 source=web
```

Будущий формат:

```json
{"level":"INFO","service":"support-desk-api","event":"ticket_created","method":"POST","path":"/tickets","status":201,"ticket_id":6,"source":"web"}
```

Плюсы:

- проще парсить в Loki/ELK/Splunk;
- меньше зависимости от regexp;
- удобнее фильтровать по `event`, `status`, `source`, `resource`, `category`;
- лучше подходит для dashboards и alerts.

### 2. Proxy headers in app logs

Улучшить `app.py` logging:

- оставить `client_ip` как TCP peer address;
- добавить `x_real_ip` из header `X-Real-IP`;
- добавить `x_forwarded_for` из header `X-Forwarded-For`;
- не заменять `client_ip` на `X-Real-IP` / `X-Forwarded-For`, чтобы не терять факт, что backend реально получил соединение от `web/Nginx`;
- использовать `X-Real-IP` и `X-Forwarded-For` как proxy metadata, а не как безусловно доверенный источник истины.

Security note:

```text
X-Real-IP и X-Forwarded-For можно подделать, если backend доступен напрямую.
В production backend должен принимать трафик только от доверенного reverse proxy/load balancer, а proxy должен перезаписывать эти headers.
Безопаснее логировать client_ip + x_real_ip + x_forwarded_for как разные поля и доверять proxy headers только при сетевом ограничении доступа к backend.
```

### 3. Status unchanged behavior

Сейчас backend пишет `event=ticket_status_changed`, даже если `old_status == new_status`. Это не ломает flow, но продуктовую логику можно улучшить:

- на frontend отключать кнопку текущего статуса;
- на backend логировать отдельное событие `ticket_status_unchanged`;
- или не обновлять `updated_at` и не писать `ticket_status_changed`, если статус фактически не изменился.

### 4. Resource/category fields in tickets

Добавить в ticket model поля:

```text
resource
category
```

Примеры:

```text
resource=grafana, category=observability
resource=prometheus, category=observability
resource=loki, category=observability
resource=vpn, category=access
resource=ssh, category=access
resource=web, category=application
resource=app, category=application
```

Использование:

- писать `resource` и `category` в product logs;
- фильтровать tickets в Loki по resource/category;
- подготовить product metrics и alerts по resource/category.

### 5. Promtail label cleanup

Сейчас Promtail label для app содержит `service=python-backend`, а внутри новой log line приложение пишет `service=support-desk-api`. Можно обновить label в `/etc/promtail/config.yml` на `service=support-desk-api`, если это не ломает существующие Grafana panels.

## Полировка monitoring

### 1. Add app /metrics scrape to Prometheus

Добавить отдельный Prometheus scrape job для app product metrics:

```text
app: 192.168.85.133:8080/metrics
```

### 2. Product metrics panels

Добавить panels в Grafana:

```text
supportdesk_tickets_total
supportdesk_tickets_open
supportdesk_tickets_in_progress
supportdesk_tickets_resolved
```

После добавления resource/category:

```text
supportdesk_tickets_by_resource{resource="..."}
supportdesk_tickets_by_category{category="..."}
```

### 3. Prometheus client library

Сейчас app `/metrics` реализован вручную: приложение само формирует Prometheus text response. Это нормально для lab-этапа.

Для production-like реализации позже перейти на Prometheus client library и добавить стандартные application metrics:

- `supportdesk_requests_total` — количество HTTP-запросов к app;
- `supportdesk_request_duration_seconds` — длительность обработки запросов;
- `supportdesk_errors_total` — количество ошибок;
- `supportdesk_tickets_created_total` — сколько заявок создано;
- `supportdesk_tickets_open` — текущее количество open-заявок;
- `supportdesk_tickets_by_status{status="open|in_progress|resolved"}`;
- `supportdesk_tickets_by_resource{resource="grafana|vpn|web|app|..."}`;
- `supportdesk_tickets_by_category{category="observability|access|application|..."}`.

Плюсы:

- меньше ручного формирования `/metrics`;
- стандартные типы Counter/Gauge/Histogram;
- проще считать error rate, latency, request rate;
- проще строить Grafana panels;
- проще делать alerts.

### 4. Product alerts

Будущие product alerts для Mini Support Desk:

1. `SupportDeskTooManyOpenTickets` — слишком много открытых заявок вообще.
2. `SupportDeskTicketSpike` — за короткий период создано слишком много заявок.
3. `SupportDeskTooManyTicketsForResource` — много открытых заявок на один ресурс.
4. `SupportDeskCategoryIncident` — много заявок по группе смежных ресурсов.
5. `SupportDeskCriticalTicketsOpen` — есть открытые critical-заявки дольше N минут.

### 5. HTTP status / error-rate alerts

Добавить error-rate alerts по HTTP-статусам:

- если доля 5xx ответов выше 5% за 5 минут — warning/critical alert;
- если Nginx часто возвращает 502 — вероятно backend app недоступен;
- если растет количество 500 от app — вероятно ошибка внутри backend-кода;
- если растет количество 400/404 — возможно frontend вызывает неправильный API, пользователи отправляют некорректные данные или есть лишний/мусорный трафик.

Для реализации желательно добавить application/request metrics:

```text
requests_total by status/method/path
errors_total by status
request_duration_seconds
```

На первом этапе можно демонстрировать это через Loki/LogQL по nginx/app logs.

## Product/data improvements

### 1. PostgreSQL instead of tickets.json

Сейчас Mini Support Desk хранит заявки в:

```text
/opt/app/tickets.json
```

Это подходит для lab/pet-project этапа, потому что просто и наглядно.

Для более production-like реализации позже вынести данные в отдельную БД:

- PostgreSQL как основной вариант для tickets;
- MySQL как альтернативная relational DB;
- Redis не как основное хранилище заявок, а скорее для cache/queues/rate limits/session-like временных данных.

Причины:

- JSON-файл неудобен при параллельных запросах;
- сложнее делать фильтрацию, поиск, аналитику и историю изменений;
- нет нормальных транзакций;
- хуже масштабируется;
- при нескольких app instances общий файл уже не подходит.

Предпочтительный future path:

```text
app -> PostgreSQL
```

### 2. API versioning

Позже можно перейти с:

```text
/api/tickets
```

на:

```text
/api/v1/tickets
```

Это нужно, если API будет развиваться и потребуется сохранить совместимость frontend/bot с разными версиями backend.

## Telegram bot

Будущий компонент:

```text
support-bot.service
```

Архитектура:

```text
Browser -> web -> app
Telegram -> support-bot.service -> app
```

Решение по сети уже проверено:

```text
app VM -> 192.168.85.1:10802 -> Windows portproxy -> 127.0.0.1:10801 -> Invisible Man XRay -> Telegram API
```

Подход:

- long polling;
- outbound HTTP proxy;
- bot token хранить в env-файле, не в коде;
- bot logs отправлять в Loki отдельным job/service;
- позже добавить bot metrics.

## Security/network improvements

### 1. Restrict direct backend access

Сейчас `app:8080` доступен внутри lab-сети. Для более production-like схемы позже ограничить доступ к backend так, чтобы `app:8080` принимал запросы только от `web` / trusted proxy.

Это важно для безопасного использования proxy headers `X-Real-IP` и `X-Forwarded-For`.

### 2. HTTPS

Позже добавить HTTPS termination на `web`:

- self-signed certificate для lab;
- или локальный CA;
- или production-like cert workflow в финальном README.

### 3. Nginx hardening

Будущие настройки:

- security headers;
- request body size limit;
- proxy timeouts;
- rate limiting;
- access control для admin/debug endpoints.
