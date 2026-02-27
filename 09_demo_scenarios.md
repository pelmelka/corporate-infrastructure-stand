# Демонстрационные сценарии проекта

## Сценарий 1. Нормальная работа системы

Цель: показать, что frontend, backend, логирование и мониторинг работают вместе на примере продукта Mini Support Desk.

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
{host="app", job="app"} |= "support-desk-api"
```

Ожидаемый итог: Browser -> web -> app работает; пользовательские действия создают product logs; nginx logs и app logs видны в Loki/Grafana.

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
{host="app", job="app"} |= "support-desk-api"
```

Ожидаемый итог: UI action -> web access log -> app product log -> Loki/Grafana.

## Сценарий 3. App service down

Цель: показать troubleshooting backend-сервиса через пользовательский путь.

Шаги:

```bash
# app
sudo systemctl stop app.service

# web или admin
curl http://192.168.85.131/api/health

# app
systemctl status app.service --no-pager
journalctl -u app.service -n 50 --no-pager
sudo systemctl start app.service
curl http://localhost:8080/health

# web или admin
curl http://192.168.85.131/api/health
```

Ожидаемый итог: при остановленном backend Nginx возвращает ошибку upstream/reverse proxy уровня; после восстановления `app.service` API снова отвечает.

## Сценарий 4. Web access logs

Цель: показать централизованный сбор nginx logs.

Шаги:

```bash
curl http://192.168.85.131/
curl http://192.168.85.131/api/health
curl http://192.168.85.131/api/tickets
curl http://192.168.85.131/not-found-grafana-test
```

В Grafana/Loki искать:

```logql
{host="web", job="nginx"}
```

Ожидаемый итог: видны HTTP-запросы к frontend и API route.

## Сценарий 5. App product logs

Цель: показать централизованный сбор backend product logs.

Шаги:

1. Создать заявку через UI.
2. Изменить ее статус.
3. Проверить Loki/Grafana:

```logql
{host="app", job="app"} |= "support-desk-api"
```

Ожидаемые события:

```text
event=ticket_created
event=ticket_status_changed
event=ticket_list_requested
event=health_check
```

## Сценарий 6. Infrastructure overview

Цель: показать Grafana dashboard `Infrastructure Overview`.

Должно быть видно:

- `web` UP;
- `app` UP;
- `log` UP;
- `monitor` UP;
- CPU/RAM/Disk по каждому узлу;
- web nginx logs;
- app logs.

Важно: текущая App logs panel была создана под старый формат. Красивое отображение product logs под `event=...` будет обновляться на этапе Полировка logging.

## Сценарий 7. Product incident from support tickets — будущий

Цель: будущая демонстрация product-level alerting.

Идея:

1. Создать несколько заявок на один ресурс, например `grafana`.
2. Создать несколько заявок по категории `observability`.
3. Prometheus product metrics фиксируют рост open tickets by resource/category.
4. Alertmanager показывает alert вида `SupportDeskTooManyTicketsForResource` или `SupportDeskCategoryIncident`.

Этот сценарий пока не реализован. Детали — в `12_future_improvements_backlog.md`.
