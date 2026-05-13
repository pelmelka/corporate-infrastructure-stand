# PromQL examples

## Состояние scrape target-ов

```promql
up
```

```promql
up{job="node"}
```

## Доступность backend API

```promql
up{job="supportdesk-api"}
```

## Активные заявки по цифровому сервису и разделу

```promql
sum by(category, resource) (
  supportdesk_tickets_current{job="supportdesk-api",status=~"open|in_progress"}
)
```

## Critical-заявки

```promql
sum by(category, resource) (
  supportdesk_tickets_current{job="supportdesk-api",status=~"open|in_progress",priority="critical"}
)
```

## p95 latency backend API

```promql
1000 * histogram_quantile(
  0.95,
  sum by(le) (
    rate(supportdesk_http_request_duration_seconds_bucket{job="supportdesk-api"}[15m])
  )
)
```

## 5xx rate backend API

```promql
sum(rate(supportdesk_http_requests_total{job="supportdesk-api",status_code=~"5.."}[5m]))
/
clamp_min(sum(rate(supportdesk_http_requests_total{job="supportdesk-api"}[5m])), 0.001)
```

## PostgreSQL connections usage

```promql
100 * max(pg_stat_database_numbackends{job="postgres",datname="supportdesk"})
/
max(pg_settings_max_connections{job="postgres"})
```

## Telegram-клиент: ошибки backend-зависимости

```promql
sum by(endpoint, method, status_code) (
  increase(support_bot_api_requests_total{job="support-bot",status_code!~"2.."}[10m])
)
```
