# LogQL examples

## App logs

```logql
{host="app", job="app", service="misis-digital-student-support-api"}
```

## App logs без Prometheus scrape-запросов

```logql
{host="app", job="app", service="misis-digital-student-support-api"}
| logfmt
| path != "/metrics"
```

## Фильтр по цифровому сервису

```logql
{host="app", job="app", category="lk-misis"}
```

## События создания заявок

```logql
{host="app", job="app", service="misis-digital-student-support-api"}
| logfmt
| event="ticket_created"
```

## Nginx logs

```logql
{host="web", job="nginx"}
```

## Telegram-клиент logs

```logql
{host="app", job="support-bot", service="misis-digital-support-bot"}
```

## Ошибки Telegram-клиента

```logql
{host="app", job="support-bot", service="misis-digital-support-bot"}
|~ "handler_error|backend_health_failed|ticket_create_failed|ticket_resolve_failed|support_model_load_failed|active_tickets_request_failed|resolve_menu_failed"
```

## Важные PostgreSQL logs

```logql
{host="db", job="postgresql"}
|~ "(ERROR|FATAL|PANIC|shutting down|ready to accept connections|starting PostgreSQL|terminating connection|deadlock)"
```
