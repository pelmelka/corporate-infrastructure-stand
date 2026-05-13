# Карта визуальных материалов

Этот файл фиксирует, какие схемы и скриншоты добавлены в финальную документацию и где они используются.

## Схемы

| Файл | Где вставлен | Что показывает |
|---|---|---|
| `assets/diagrams/architecture.png` | `README.md`, `SPECIFICATION.md`, `docs/architecture.md` | общая архитектура: пользователи, web/app/db/log/monitor/admin, app traffic, logs, metrics, Ansible/SSH |
| `assets/diagrams/application-flow.png` | `README.md`, `docs/architecture.md`, `docs/runtime-and-deployment.md` | web-flow и Telegram-flow через общий backend API и PostgreSQL |
| `assets/diagrams/network-flow.png` | `README.md`, `SPECIFICATION.md`, `docs/network-and-security.md` | сеть, управление, allowlist, ports, Telegram outbound и operator access |
| `assets/diagrams/observability-flow.png` | `README.md`, `docs/observability.md` | Promtail/Loki logging flow и Prometheus/Grafana/Alertmanager metrics/alerts flow |

## Скриншоты

| Файл | Где вставлен | Что показывает |
|---|---|---|
| `assets/screenshots/web-ui-ticket-form-filled.png` | `docs/demo-guide.md` | заполненная форма создания заявки через web UI |
| `assets/screenshots/web-ui-service-dropdown.png` | `docs/runtime-and-deployment.md` | выбор цифрового сервиса в frontend |
| `assets/screenshots/web-ui-resource-dropdown.png` | `docs/runtime-and-deployment.md` | выбор раздела после выбора сервиса |
| `assets/screenshots/web-ui-ticket-list-active.png` | `README.md`, `docs/runtime-and-deployment.md` | список заявок, статусы, source/category/resource |
| `assets/screenshots/web-ui-loki-ticket-created.png` | `docs/observability.md`, `docs/demo-guide.md` | созданная заявка и соответствующий Loki/app log |
| `assets/screenshots/web-ui-loki-ticket-sources.png` | `docs/demo-guide.md` | разные источники заявок: `web` и `telegram` |
| `assets/screenshots/grafana-app-log-post.png` | `docs/observability.md`, `docs/demo-guide.md` | app logs после POST/validation events с category/resource/source |
| `assets/screenshots/dashboard-infrastructure-normal.png` | `README.md`, `docs/observability.md` | общий нормальный вид dashboard Infrastructure Overview |
| `assets/screenshots/dashboard-tickets-normal.png` | `README.md`, `docs/observability.md`, `docs/demo-guide.md` | product observability по tickets/category/resource/age |
| `assets/screenshots/dashboard-http-api-normal.png` | `README.md`, `docs/observability.md`, `docs/demo-guide.md` | HTTP/API request rate, status codes и p95 latency |
| `assets/screenshots/dashboard-db-normal.png` | `docs/observability.md`, `docs/database-and-backups.md` | DB Health, DB Connections, DB Activity, PostgreSQL logs |
| `assets/screenshots/dashboard-bot-normal.png` | `docs/observability.md`, `docs/demo-guide.md` | Telegram bot observability: runtime, actions, API calls, logs, latency |
| `assets/screenshots/prometheus-targets-main.png` | `README.md`, `docs/observability.md` | Prometheus targets: node/postgres/prometheus UP |
| `assets/screenshots/prometheus-targets-app-bot-promtail.png` | `README.md`, `docs/observability.md` | Prometheus targets: supportdesk-api/support-bot/promtail-web UP |
| `assets/screenshots/ansible-check-web-app-start.png` | `docs/automation.md`, `docs/demo-guide.md` | начало `ansible-playbook playbooks/check.yml`: web/app checks |
| `assets/screenshots/ansible-check-log-monitor.png` | `docs/automation.md`, `docs/demo-guide.md` | продолжение `check.yml`: log/monitor checks |
| `assets/screenshots/ansible-check-prometheus-jobs.png` | `docs/automation.md`, `docs/demo-guide.md` | проверка expected Prometheus jobs через API |
| `assets/screenshots/ansible-check-recap.png` | `README.md`, `docs/automation.md`, `docs/demo-guide.md` | итоговый recap: `failed=0`, `unreachable=0` |
| `assets/screenshots/network-audit-critical-connectivity.png` | `docs/network-and-security.md`, `docs/automation.md`, `docs/demo-guide.md` | critical connectivity audit из admin |
| `assets/screenshots/db-backup-restore-test.png` | `README.md`, `docs/database-and-backups.md`, `docs/demo-guide.md` | backup timer, dump/checksum files, latest.dump и restore test count |
| `assets/screenshots/tickets-alert-too-many-resource.png` | `docs/observability.md`, `docs/demo-guide.md` | product alert `SupportDeskTooManyTicketsForResource` в FIRING |
| `assets/screenshots/app-api-down-grafana-view.png` | `docs/demo-guide.md`, `docs/troubleshooting.md` | controlled backend/proxy degradation на dashboard |
| `assets/screenshots/app-api-down-prometheus-alerts.png` | `README.md`, `docs/observability.md`, `docs/demo-guide.md`, `docs/troubleshooting.md` | Prometheus alerts при app/proxy failure |
| `assets/screenshots/db-down-dashboard.png` | `docs/demo-guide.md`, `docs/troubleshooting.md` | DB dashboard при `PostgreSQLDown` |
| `assets/screenshots/db-down-alerts-and-user-impact.png` | `docs/observability.md`, `docs/demo-guide.md`, `docs/troubleshooting.md` | DB degradation, Prometheus/Grafana, app/bot impact |
| `assets/screenshots/db-down-bot-errors-panel.png` | `docs/demo-guide.md`, `docs/troubleshooting.md` | bot error logs/API responses при backend/storage issue |
| `assets/screenshots/node-exporter-down-demo.png` | `docs/demo-guide.md`, `docs/troubleshooting.md` | observability degradation: node_exporter target DOWN |
| `assets/screenshots/http-api-4xx-alert-demo.png` | `docs/demo-guide.md` | controlled 4xx traffic и `SupportDeskHigh4xxRate` |
