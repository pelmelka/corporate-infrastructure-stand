# Матрица сетевых доступов

Этот файл фиксирует основные разрешенные потоки стенда. Детальные снимки состояния firewall и критических TCP/HTTP-проверок находятся в `network-audit-latest/`.

| Источник | Назначение | Порт | Назначение потока |
|---|---:|---:|---|
| operator/admin | `web` | 80/tcp | пользовательский HTTP-вход в стенд |
| `web` | `app` | 8080/tcp | reverse proxy к backend API |
| `support-bot` | `supportdesk-api` | 8080/tcp | внутренний Docker Compose flow Telegram-клиента к backend API |
| `app` | `db` | 5432/tcp | подключение backend API к PostgreSQL |
| `web` | `log` | 3100/tcp | отправка nginx logs через Promtail в Loki |
| `app` | `log` | 3100/tcp | отправка app/bot logs через Promtail в Loki |
| `db` | `log` | 3100/tcp | отправка PostgreSQL logs через Promtail в Loki |
| `monitor` | `web`, `app`, `db`, `log`, `monitor` | 9100/tcp | scrape node_exporter |
| `monitor` | `app` | 8080/tcp | scrape backend API metrics |
| `monitor` | `app` | 8090/tcp | scrape Telegram-клиента metrics |
| `monitor` | `web` | 9080/tcp | scrape Promtail/nginx-derived metrics |
| `monitor` | `db` | 9187/tcp | scrape postgres_exporter |
| `monitor` | `localhost` | 9093/tcp | Prometheus -> Alertmanager |
| Grafana | Prometheus | 9090/tcp | datasource Prometheus |
| Grafana | Loki | 3100/tcp | datasource Loki |
| `admin` | managed nodes | 22/tcp | SSH/Ansible управление |
| `admin` | service endpoints | service-specific | диагностика и проверка состояния |

Правила входящего доступа строятся по allowlist-подходу: открыты только потоки, которые нужны для работы или диагностики стенда.
