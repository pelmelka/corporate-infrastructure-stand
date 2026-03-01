# Демонстрационные сценарии проекта

## Сценарий 1. Нормальная работа системы

Цель: показать, что frontend, backend, логирование, мониторинг и alerts работают вместе на примере продукта Mini Support Desk.

Шаги:

1. Открыть `http://192.168.85.131`.
2. Проверить, что Backend status показывает `OK`.
3. Создать заявку через форму Mini Support Desk.
4. Изменить статус заявки.
5. Проверить backend через web reverse proxy:

```bash
curl http://192.168.85.131/api/health
```

6. Проверить nginx logs на `web`:

```bash
sudo tail -n 30 /var/log/nginx/access.log
```

7. Проверить app product logs на `app`:

```bash
sudo tail -n 30 /var/log/app/app.log
```

8. Проверить Loki/Grafana:

```logql
{host="app", job="app", service="support-desk-api"}
```

9. Проверить Grafana dashboard:

```text
SupportDesk API UP = UP
SupportDesk Tickets меняется после создания/изменения заявки
Active Alerts = OK
```

Ожидаемый итог: Browser -> web -> app работает; пользовательские действия создают product logs; nginx logs и app logs видны в Loki/Grafana; product metrics меняются в Prometheus/Grafana.

## Сценарий 2. Mini Support Desk product flow

Цель: показать продуктовый сценарий, а не просто infrastructure healthcheck.

Шаги:

1. Открыть `http://192.168.85.131`.
2. Создать заявку:
   - Title: `Browser test ticket`
   - Description: `Created from Mini Support Desk web UI`
   - Priority: `high`
3. Изменить статус заявки на `in_progress`.
4. Изменить статус заявки на `resolved`.
5. Проверить web logs:

```text
POST /api/tickets HTTP/1.1 201
PATCH /api/tickets/<id>/status HTTP/1.1 200
```

6. Проверить app logs:

```text
event=ticket_created
event=ticket_status_changed
```

7. Проверить Loki/Grafana:

```logql
{host="app", job="app", service="support-desk-api"}
| logfmt
```

Ожидаемый итог: UI action -> web access log -> app product log -> Loki/Grafana -> product metrics.

## Сценарий 3. Status unchanged behavior

Цель: показать, что backend отличает реальное изменение статуса от повторного выбора текущего статуса.

Шаги:

1. Создать или выбрать заявку.
2. Нажать текущий статус повторно.
3. Изменить статус на другой.
4. Проверить app logs:

```text
event=ticket_status_unchanged old_status=open new_status=open
event=ticket_status_changed old_status=open new_status=in_progress
```

Ожидаемый итог: повторное нажатие текущего статуса не называется изменением.

## Сценарий 4. Proxy metadata in app logs

Цель: показать различие между TCP peer и исходным клиентом до reverse proxy.

Ожидаемые app log поля:

```text
client_ip=192.168.85.131
x_forwarded_for=192.168.85.1
x_forwarded_proto=http
```

Смысл:

```text
client_ip        = web/Nginx, который реально подключился к app
x_forwarded_for  = Windows/Browser как исходный клиент
```

## Сценарий 5. App service down + SupportDeskApiDown alert

Цель: показать troubleshooting backend-сервиса через пользовательский путь и alerting.

Шаги:

```bash
# app
sudo systemctl stop app.service

# web/admin
curl http://192.168.85.131/api/health

# monitor / Prometheus UI
# открыть /targets и /alerts

# app
sudo systemctl start app.service
systemctl status app.service --no-pager
curl http://localhost:8080/health
```

Ожидаемый итог:

```text
supportdesk-api target -> DOWN
SupportDeskApiDown -> PENDING -> FIRING
после восстановления app.service alert исчезает
```

## Сценарий 6. TooManyOpenTickets product alert

Цель: показать product-level alerting.

Шаги:

1. Создать несколько open-заявок, чтобы `supportdesk_tickets_open >= 3`.
2. Проверить Prometheus query:

```promql
supportdesk_tickets_open{job="supportdesk-api"}
```

3. Открыть Prometheus `/alerts`.

Ожидаемый итог:

```text
TooManyOpenTickets -> PENDING -> FIRING
```

После проверки перевести часть заявок в `in_progress` или `resolved`, чтобы open стало меньше 3.

## Сценарий 7. HighDiskUsage alert test

Цель: проверить disk alert без реального забивания диска.

Шаги:

1. Временно изменить порог в `/etc/prometheus/supportdesk.rules.yml` с `> 80` на `> 20`.
2. Проверить rules/config через `promtool`.
3. Перезапустить Prometheus.
4. Дождаться `HighDiskUsage PENDING/FIRING` для хостов, где disk usage больше 20%.
5. Вернуть порог `> 80`.
6. Перезапустить Prometheus.

Ожидаемый итог:

```text
HighDiskUsage срабатывает при тестовом пороге и становится inactive после возврата >80.
```

## Сценарий 8. NodeTargetDown alert

Цель: показать alert по недоступности node_exporter target.

Шаги:

```bash
# на web/app/log, например web
sudo systemctl stop prometheus-node-exporter.service

# monitor / Prometheus UI
# проверить /targets и /alerts

# восстановить
sudo systemctl start prometheus-node-exporter.service
systemctl status prometheus-node-exporter.service --no-pager
```

Ожидаемый итог:

```text
node target для host -> DOWN
NodeTargetDown -> PENDING -> FIRING
после восстановления node_exporter alert исчезает
```

## Сценарий 9. Active Alerts panel

Цель: показать, что состояние alert-ов видно прямо на dashboard.

Панель использует:

```promql
sum(ALERTS{alertstate="firing"}) or vector(0)
```

Ожидаемый итог:

```text
без firing alerts -> OK
при firing alert -> показывает проблему
```

## Сценарий 10. App validation and not_found logs

Цель: показать диагностические WARN-события backend-а.

Шаги:

```bash
curl -s -X POST http://192.168.85.131/api/tickets \
  -H "Content-Type: application/json" \
  -d '{"title":"","description":"test validation","priority":"high","source":"web"}'

curl -s -X PATCH http://192.168.85.131/api/tickets/1/status \
  -H "Content-Type: application/json" \
  -d '{"status":"bad_status","source":"web"}'

curl -s http://192.168.85.131/api/tickets/999999
curl -s http://192.168.85.131/api/bad-endpoint
```

Проверить:

```logql
{host="app", job="app", service="support-desk-api"} |= "ticket_validation_failed"
{host="app", job="app", service="support-desk-api"} |= "ticket_not_found"
{host="app", job="app", service="support-desk-api"} |= "endpoint_not_found"
```

Ожидаемый итог: backend validation и diagnostic logs работают. Если пустой Title вводится через UI, frontend блокирует запрос до отправки, поэтому backend log не появляется — это нормальное поведение.

## Сценарий 11. Infrastructure overview

Цель: показать Grafana dashboard `Infrastructure Overview`.

Должно быть видно:

- `web` UP;
- `app` UP;
- `log` UP;
- `monitor` UP;
- `supportdesk-api` UP;
- CPU/RAM/Disk по каждому узлу;
- SupportDesk Tickets;
- Active Alerts;
- web nginx logs;
- app logs.

## Сценарий 12. Future Product incident from resource/category

Цель: будущая демонстрация product-level alerting по resource/category.

Идея:

1. Создать несколько заявок на один ресурс, например `grafana`.
2. Создать несколько заявок по категории `observability`.
3. Prometheus product metrics фиксируют рост open tickets by resource/category.
4. Alertmanager показывает alert вида `SupportDeskTooManyTicketsForResource` или `SupportDeskCategoryIncident`.

Этот сценарий пока не реализован. Детали — в roadmap и `12_future_improvements_backlog.md`.

## Сценарий 13. Future Dockerized app

Цель: будущая демонстрация Docker как способа доставки backend-а.

Идея:

```text
app.service или docker compose запускает support-desk-api container
web/Nginx продолжает ходить на app:8080
Prometheus продолжает scrape app:8080/metrics
Promtail продолжает читать /var/log/app/app.log через volume
```

Ожидаемый итог: меняется способ запуска приложения, но внешний flow и observability остаются стабильными.

## Сценарий 14. Future DB backup/restore

Цель: будущая демонстрация stateful service recovery.

Идея:

1. Заявки хранятся в PostgreSQL.
2. Выполнить `pg_dump`.
3. Удалить или изменить тестовые данные.
4. Восстановить backup.
5. Показать, что tickets вернулись.

## Сценарий 15. Future Telegram ticket

Цель: будущая демонстрация второго клиента к тому же API.

Идея:

1. Создать заявку из Telegram.
2. Увидеть ее в web UI.
3. Увидеть `source=telegram` в logs.
4. Увидеть изменение product metrics.
5. Закрыть заявку из web или Telegram.
