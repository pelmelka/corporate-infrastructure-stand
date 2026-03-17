# Демонстрационные сценарии проекта

## Сценарий 1. Нормальная работа системы

Цель: показать, что frontend, backend, логирование, мониторинг и alerts работают вместе на примере продукта `MISIS_Digital Student Support`.

Шаги:

1. Открыть `http://192.168.85.131`.
2. Проверить, что Backend status показывает `OK`.
3. Создать заявку через форму `MISIS_Digital Student Support`.
4. Изменить статус заявки.
5. Проверить backend через web reverse proxy:

```bash
curl http://192.168.85.131/api/v1/health
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
{host="app", job="app", service="misis-digital-student-support-api"}
```

9. Проверить Grafana dashboard:

```text
SupportDesk API UP = UP
SupportDesk Tickets / Student Support Tickets меняется после создания/изменения заявки
App logs показывает category/resource
Active Alerts = OK
```

Ожидаемый итог: Browser -> web -> app работает; пользовательские действия создают product logs; nginx logs и app logs видны в Loki/Grafana; product metrics меняются в Prometheus/Grafana.

## Сценарий 2. MISIS_Digital Student Support product flow

Цель: показать продуктовый сценарий, а не просто infrastructure healthcheck.

Шаги:

1. Открыть `http://192.168.85.131`.
2. Создать заявку:
   - Digital service: `newlms.misis.ru`
   - Service section: `Schedule`
   - Description: `В расписании отображается неправильная аудитория`
   - Priority: `high`
3. Проверить, что заявка появилась во вкладке `Active`.
4. Изменить статус заявки на `in_progress`.
5. Изменить статус заявки на `resolved`.
6. Проверить, что заявка исчезла из `Active`.
7. Проверить, что заявка появилась во вкладке `Resolved`.
8. Проверить web logs:

```text
POST /api/v1/tickets HTTP/1.1 201
PATCH /api/v1/tickets/<id>/status HTTP/1.1 200
GET /api/v1/tickets?status=resolved HTTP/1.1 200
```

9. Проверить app logs:

```text
event=ticket_created category=newlms-misis resource=schedule
event=ticket_status_changed old_status=open new_status=in_progress category=newlms-misis resource=schedule
event=ticket_status_changed old_status=in_progress new_status=resolved category=newlms-misis resource=schedule
```

10. Проверить Loki/Grafana:

```logql
{host="app", job="app", service="misis-digital-student-support-api", category="newlms-misis"}
```

Ожидаемый итог: UI action -> web access log -> app product log -> Loki/Grafana -> product metrics.

## Сценарий 3. Category/resource validation

Цель: показать, что backend понимает предметную модель и не принимает неверные пары.

Проверка через API:

```bash
curl -s -X POST http://192.168.85.131/api/v1/tickets   -H "Content-Type: application/json"   -d '{"category":"newlms-misis","resource":"plumber-request","description":"bad pair","priority":"normal","source":"api"}'   | python3 -m json.tool
```

Ожидаемый ответ:

```text
invalid_resource_for_category:newlms-misis:plumber-request
```

Смысл: `plumber-request` относится к `gornyak-misis`, но не к `newlms-misis`.

## Сценарий 4. Status unchanged behavior

Цель: показать, что backend отличает реальное изменение статуса от повторного выбора текущего статуса.

Шаги:

1. Создать или выбрать заявку.
2. Нажать текущий статус повторно.
3. Изменить статус на другой.
4. Проверить app logs:

```text
event=ticket_status_unchanged old_status=in_progress new_status=in_progress
event=ticket_status_changed old_status=in_progress new_status=resolved
```

Ожидаемый итог: повторное нажатие текущего статуса не называется изменением.

## Сценарий 5. Reopen resolved ticket

Цель: показать, что resolved-заявка хранится в истории и может быть открыта заново.

Шаги:

1. Перевести заявку в `resolved`.
2. Убедиться, что она исчезла из `Active`.
3. Открыть вкладку `Resolved`.
4. Нажать `Reopen`.
5. Убедиться, что заявка снова появилась в `Active`.
6. Проверить API:

```bash
curl -s http://192.168.85.131/api/v1/tickets | python3 -m json.tool --no-ensure-ascii
curl -s 'http://192.168.85.131/api/v1/tickets?status=resolved' | python3 -m json.tool --no-ensure-ascii
```

Ожидаемый итог: при reopen статус становится `open`, а `resolved_at` сбрасывается в `null`.

## Сценарий 6. Proxy metadata in app logs

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

## Сценарий 7. App service down + SupportDeskApiDown alert

Цель: показать troubleshooting backend-сервиса через пользовательский путь и alerting.

Шаги:

```bash
# app
sudo systemctl stop app.service

# web/admin
curl http://192.168.85.131/api/v1/health

# monitor / Prometheus UI
# открыть /targets и /alerts

# app
sudo systemctl start app.service
systemctl status app.service --no-pager
curl http://localhost:8080/v1/health
```

Ожидаемый итог:

```text
supportdesk-api target -> DOWN
SupportDeskApiDown -> PENDING -> FIRING
после восстановления app.service alert исчезает
```

## Сценарий 8. Deprecated TooManyOpenTickets product alert

Старый общий alert `TooManyOpenTickets` удален после Product observability v2 cleanup.

Причина:

```text
supportdesk_tickets_open >= 3
```

показывал только общее количество open-заявок и не отвечал на вопрос, где именно проблема. Его заменил более точный сценарий `SupportDeskTooManyTicketsForResource` по `category/resource`.

## Сценарий 9. Product observability v2: resource incident by category/resource

Цель: показать Product observability v2 — концентрацию заявок вокруг конкретного цифрового сервиса и ресурса.

Шаги:

1. Создать несколько active-заявок на один resource, например:

```text
category=lk-misis
resource=gradebook
priority=high/normal
```

или:

```text
category=newlms-misis
resource=schedule
priority=high/normal
```

2. Проверить Prometheus query:

```promql
sum by(category, resource) (
  supportdesk_tickets_current{job="supportdesk-api",status=~"open|in_progress"}
)
```

3. Проверить Grafana panels:

```text
Open tickets by category
Active tickets by category/resource
```

4. Открыть Prometheus `/alerts`.

Ожидаемый итог:

```text
SupportDeskTooManyTicketsForResource -> PENDING -> FIRING
```

5. Проверить Alertmanager:

```bash
amtool --alertmanager.url=http://localhost:9093 alert
```

Ожидаемый итог: Alertmanager показывает active alert с конкретными `category/resource`.

## Сценарий 9a. Critical ticket and old critical ticket alerts

Цель: показать critical product alerts и SLA-like сигнал по возрасту active-заявки.

Шаги:

1. Создать active-заявку с priority `critical`, например:

```text
category=vector-misis
resource=resume-upload
priority=critical
```

2. Проверить Prometheus query:

```promql
sum by(category, resource) (
  supportdesk_tickets_current{job="supportdesk-api",status=~"open|in_progress",priority="critical"}
)
```

3. Проверить age query:

```promql
max by(category, resource) (
  supportdesk_active_ticket_age_seconds_max{job="supportdesk-api",priority="critical"}
)
```

Ожидаемый итог:

```text
SupportDeskCriticalTicketsOpen -> PENDING -> FIRING
SupportDeskOldCriticalTicket -> FIRING после превышения 600 секунд
```

Смысл: первый alert говорит, что critical-заявка есть; второй — что она уже слишком долго остается active.

## Сценарий 10. Loki category label filtering

Цель: показать, что логи можно фильтровать по цифровому сервису университета.

Запросы в Grafana Explore:

```logql
{host="app", job="app", category="gornyak-misis"}
```

```logql
{host="app", job="app", category="lk-misis"}
```

```logql
{host="app", job="app", service="misis-digital-student-support-api", category="pay-misis"}
|= "resource=dorm-payment"
```

Ожидаемый итог: Loki показывает только события выбранной категории или ресурса.

## Сценарий 11. HighDiskUsage alert test

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

## Сценарий 12. NodeTargetDown alert

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

## Сценарий 13. Active Alerts panel

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

## Сценарий 14. Infrastructure overview

Цель: показать Grafana dashboard `Infrastructure Overview`.

Должно быть видно:

- `web` UP;
- `app` UP;
- `log` UP;
- `monitor` UP;
- `supportdesk-api` UP;
- CPU/RAM/Disk по каждому узлу;
- SupportDesk Tickets / Student Support Tickets;
- Active Alerts;
- web nginx logs;
- app logs с `category/resource`.

## Сценарий 15. Admin/Ansible operational control

Цель: показать, что `admin` работает как Ansible control node и может управлять/проверять инфраструктуру из одного места.

Шаги на `admin`:

```bash
cd ~/control-node
ansible-inventory --graph
ansible managed -m ping
ansible-playbook playbooks/ping_all.yml
ansible-playbook playbooks/check_services.yml
ansible-playbook playbooks/deploy_prometheus_rules.yml
```

Для controlled restart backend-а:

```bash
ansible-playbook playbooks/restart_app.yml
```

Ожидаемый итог:

```text
inventory показывает control + managed groups
managed nodes отвечают ping=pong
check_services.yml возвращает failed=0
Prometheus rules deploy проходит promtool validation и readiness check
restart_app.yml перезапускает app.service и проверяет /health
```

Смысл демонстрации: инфраструктура уже частично управляется как code — через Git-tracked Ansible inventory/playbook'и на `admin`, а не только ручными командами на каждом сервере.

## Сценарий 16. Future Dockerized app

Цель: будущая демонстрация Docker как способа доставки backend-а.

Идея:

```text
app.service или docker compose запускает misis-digital-student-support-api container
web/Nginx продолжает ходить на app:8080
Prometheus продолжает scrape app:8080/metrics
Promtail продолжает читать /var/log/app/app.log через volume
```

## Сценарий 17. Future DB backup/restore

Цель: будущая демонстрация stateful service recovery.

Идея:

1. Заявки хранятся в PostgreSQL.
2. Выполнить `pg_dump`.
3. Удалить или изменить тестовые данные.
4. Восстановить backup.
5. Показать, что tickets вернулись.

## Сценарий 18. Future Telegram ticket

Цель: будущая демонстрация второго клиента к тому же API.

Идея:

1. Создать заявку из Telegram.
2. Увидеть ее в web UI.
3. Увидеть `source=telegram` в logs.
4. Увидеть изменение product metrics.
5. Закрыть заявку из web или Telegram.
