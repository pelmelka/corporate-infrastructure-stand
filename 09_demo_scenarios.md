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
cd /opt/app
sudo docker compose stop supportdesk-api

# web/admin
curl http://192.168.85.131/api/v1/health

# monitor / Prometheus UI
# открыть /targets и /alerts

# app
cd /opt/app
sudo docker compose start supportdesk-api
sudo docker compose ps
curl http://localhost:8080/v1/health
```

Ожидаемый итог:

```text
supportdesk-api target -> DOWN
SupportDeskApiDown -> PENDING -> FIRING
после восстановления Docker container alert исчезает
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


## Сценарий 15a. HTTP/API observability

Цель: показать, что проект мониторит не только наличие backend-а, но и качество HTTP/API-слоя.

Шаги:

1. Сгенерировать нормальный и ошибочный трафик:

```bash
for i in {1..20}; do
  curl -s -o /dev/null http://192.168.85.131/api/v1/health
  curl -s -o /dev/null http://192.168.85.131/api/v1/tickets
  curl -s -o /dev/null http://192.168.85.131/api/bad-endpoint
done
```

2. Проверить Prometheus query:

```promql
sum by(method, route) (
  rate(supportdesk_http_requests_total{job="supportdesk-api"}[5m])
)
```

3. Проверить status code query:

```promql
sum by(status_code) (
  rate(supportdesk_http_requests_total{job="supportdesk-api"}[5m])
)
```

4. Проверить p95 latency:

```promql
histogram_quantile(
  0.95,
  sum by(le) (
    rate(supportdesk_http_request_duration_seconds_bucket{job="supportdesk-api"}[5m])
  )
)
```

5. Открыть Grafana dashboard `Infrastructure Overview`, блок `HTTP/API Observability`.

Ожидаемый итог:

```text
HTTP/API Health Overview показывает 4xx rate, 5xx rate, p95 latency, Nginx 502 / 5m и HTTP alerts firing.
API Request Rate by Route показывает GET /v1/health, GET /v1/tickets и GET unmatched.
API Responses by Status Code показывает HTTP 200 и HTTP 404.
API p95 Latency by Route показывает p95 latency по routes в milliseconds.
```

## Сценарий 15b. Nginx502Spike proxy-level alert

Цель: показать разницу между backend scrape failure и пользовательской ошибкой reverse proxy.

Шаги:

```bash
# app
cd /opt/app
sudo docker compose stop supportdesk-api

# admin/web
for i in {1..5}; do
  curl -s -o /dev/null http://192.168.85.131/api/v1/health
done
```

Проверить Prometheus Alerts:

```text
SupportDeskApiDown -> FIRING
Nginx502Spike -> FIRING
```

Смысл:

```text
SupportDeskApiDown = Prometheus не может scrape-ить app:8080/metrics.
Nginx502Spike = пользовательский путь Browser -> web/Nginx -> app сломан, Nginx возвращает 502.
```

Восстановление:

```bash
# app
cd /opt/app
sudo docker compose start supportdesk-api
sudo docker compose ps
curl -s http://localhost:8080/v1/health | python3 -m json.tool
```

Ожидаемый итог: после восстановления backend-а и выхода 502 из окна `[5m]` оба alert-а гаснут.

## Сценарий 16. Dockerized app runtime

Цель: показать, что backend теперь доставляется и запускается через Docker, но внешний пользовательский и observability flow не изменился.

Шаги на `app`:

```bash
cd /opt/app
sudo docker compose ps
ss -tulpn | grep :8080
curl -s http://localhost:8080/v1/health | python3 -m json.tool
curl -s http://localhost:8080/metrics | head
systemctl status app.service --no-pager
systemctl is-enabled app.service || true
```

Ожидаемый итог:

```text
container misis-digital-student-support-api -> Up
порт 8080 слушает docker-proxy
/v1/health -> status ok
/metrics -> supportdesk_* metrics
app.service -> inactive/dead, disabled
```

Проверка через пользовательский путь:

```bash
curl -s http://192.168.85.131/api/v1/health | python3 -m json.tool
curl -s -X POST http://192.168.85.131/api/v1/tickets   -H "Content-Type: application/json"   -d '{"category":"newlms-misis","resource":"login","description":"docker demo ticket","priority":"normal","source":"api"}'   | python3 -m json.tool
```

Проверка Prometheus:

```bash
curl -s 'http://192.168.85.137:9090/api/v1/query?query=up%7Bjob%3D%22supportdesk-api%22%7D' | python3 -m json.tool
```

Ожидаемый итог:

```text
web/Nginx -> app:8080 -> Docker container работает
Prometheus -> app:8080/metrics возвращает up=1
Promtail продолжает читать /var/log/app/app.log
Loki/Grafana показывают app logs
```

Rollback-сценарий:

```bash
cd /opt/app
sudo docker compose down
sudo systemctl start app.service
```

Смысл: Dockerization изменила runtime backend-а, но не изменила внешний контракт сервиса.

## Сценарий 17. PostgreSQL-backed storage demo

Цель: показать, что backend больше не пишет в `tickets.json`, а использует PostgreSQL на отдельном сервере `db`.

Практический backup/restore proof после этапа 17 вынесен ниже в сценарий `Backup and restore proof`.

## Сценарий 18. Telegram support bot end-to-end

Цель: показать, что Telegram стал вторым клиентом продукта, но не обходит backend API и БД напрямую.

Поток:

```text
Telegram user -> Telegram API -> support-bot -> supportdesk-api -> PostgreSQL
```

Шаги demo:

1. Открыть `@misis_digital_support_bot` в Telegram.
2. Нажать `/start` и показать кнопочное меню.
3. Создать заявку через `➕ Создать заявку`:
   - выбрать digital service;
   - выбрать resource;
   - выбрать priority;
   - ввести description;
   - подтвердить создание.
4. Показать, что бот вернул номер заявки и `Создана через: telegram`.
5. В web UI открыть active tickets и показать ту же заявку.
6. Проверить PostgreSQL audit trail:

```sql
SELECT id, ticket_id, event, old_status, new_status, source, created_at
FROM ticket_events
WHERE ticket_id = <ticket_id>
ORDER BY id;
```

Ожидание:

```text
ticket_created source=telegram
```

7. Закрыть заявку через Telegram `✅ Закрыть заявку`.
8. Проверить, что бот показывает:

```text
Создана через: telegram
Закрыта через: telegram
```

9. Проверить DB audit trail:

```text
ticket_status_changed old_status=open new_status=resolved source=telegram
```

## Сценарий 19. Telegram bot observability

Цель: показать, что новый bot-container наблюдается через Prometheus, Grafana, Alertmanager и Loki.

Проверки normal state:

```promql
up{job="support-bot"}
```

```logql
{host="app", job="support-bot", service="misis-digital-support-bot"}
```

Grafana row:

```text
Telegram Bot Alerts
Telegram Bot Runtime
Bot -> API dependency / 30m
Bot -> API latency by endpoint / 30m
Bot API requests by endpoint/status / 30m
Bot actions / 30m
Bot recent logs
Bot error logs
```

Demo bot down:

```bash
cd /opt/app
sudo docker compose stop support-bot
```

Ожидание:

```text
Prometheus target support-bot DOWN
SupportBotDown Pending/Firing
Telegram Bot Alerts показывает SupportBotDown
```

Recovery:

```bash
sudo docker compose up -d support-bot
```

Demo backend dependency error:

```bash
cd /opt/app
sudo docker compose stop supportdesk-api
```

Далее нажать в Telegram действие, которое требует backend API, например `📋 Активные заявки`.

Ожидание:

```text
SupportBotBackendErrors Pending/Firing
Bot API requests by endpoint/status показывает endpoint=/v1/tickets status_code=error
Bot -> API latency by endpoint показывает всплеск latency для /v1/tickets
Bot error logs показывает ошибочное событие
```

Recovery:

```bash
sudo docker compose up -d supportdesk-api
```

Важно: `SupportBotBackendErrors` срабатывает только после реального bot -> backend запроса. Это не замена `SupportDeskApiDown`, а наблюдение за ошибками backend-зависимости глазами Telegram-клиента.
## Сценарий 17a. PostgreSQL-backed storage и SQL-native backend

Цель: показать, что backend больше не пишет в `tickets.json`, а использует PostgreSQL на отдельном сервере `db`.

1. Проверить health через app:

```bash
curl -s http://localhost:8080/v1/health | python3 -m json.tool
```

2. Проверить список заявок через полный web path:

```bash
curl -s http://192.168.85.131/api/v1/tickets | python3 -m json.tool | head -n 30
```

3. Создать заявку через web/Nginx:

```bash
curl -s -X POST http://192.168.85.131/api/v1/tickets \
  -H "Content-Type: application/json" \
  -d '{"category":"lk-misis","resource":"service-requests","description":"DB demo ticket","priority":"normal","source":"web"}' \
  | python3 -m json.tool
```

4. Проверить последнюю запись в PostgreSQL:

```bash
PGPASSWORD='<redacted>' psql -h 192.168.85.139 -U supportdesk_user -d supportdesk -P pager=off -c "SELECT id, category, resource, status, source FROM tickets ORDER BY id DESC LIMIT 1;"
```

5. Проверить audit event:

```bash
PGPASSWORD='<redacted>' psql -h 192.168.85.139 -U supportdesk_user -d supportdesk -P pager=off -c "SELECT event, old_status, new_status, source, metadata_json FROM ticket_events ORDER BY id DESC LIMIT 1;"
```

Ожидаемый признак успеха:

```text
metadata_json содержит {"write_path": "sql_native", "storage_backend": "postgresql"}
```

6. Проверить, что product metrics продолжают работать:

```bash
curl -s http://localhost:8080/metrics | grep supportdesk_tickets_total
```


## Сценарий 19. DB observability dashboard

Цель: показать, что БД наблюдается как отдельный слой, а не только как Linux-нода.

Шаги:

1. Открыть Grafana dashboard `Infrastructure Overview`.
2. Перейти к блоку `PostgreSQL / Supportdesk DB`.
3. Проверить панели:

```text
DB Health
DB Connections
DB Activity
PostgreSQL Important Logs
```

4. Проверить Prometheus queries:

```promql
up{job="postgres", host="db"}
pg_up{job="postgres", host="db"}
pg_database_size_bytes{job="postgres", datname="supportdesk"}
rate(pg_stat_database_xact_commit{job="postgres", datname="supportdesk"}[5m])
rate(pg_stat_database_xact_rollback{job="postgres", datname="supportdesk"}[5m])
```

Ожидаемый итог:

```text
postgres_exporter UP = UP
PostgreSQL UP = UP
supportdesk DB size около нескольких MB
DB alerts firing = 0
DB Activity показывает commits/sec, rollbacks/sec обычно 0
```

Важно: `DB Connections` может показывать `0%`, даже если app ходит в БД. Это нормально, потому что метрика показывает текущие открытые подключения в момент scrape-а, а backend использует короткоживущие подключения.

## Сценарий 20. PostgreSQL Important Logs

Цель: показать поток PostgreSQL logs в Loki/Grafana.

Сгенерировать безопасную ошибку на `db`:

```bash
sudo -u postgres psql -d supportdesk -c "SELECT * FROM promtail_db_log_test_table;" || true
```

Проверить Grafana logs panel или Explore:

```logql
{host="db", job="postgresql"}
|~ "(ERROR|FATAL|PANIC|shutting down|ready to accept connections|starting PostgreSQL|terminating connection|deadlock)"
```

Ожидаемый итог:

```text
ERROR: relation "promtail_db_log_test_table" does not exist
STATEMENT: SELECT * FROM promtail_db_log_test_table;
```

## Сценарий 21. PostgreSQLExporterDown alert

Цель: показать разницу между exporter down и PostgreSQL down.

На `db`:

```bash
sudo systemctl stop prometheus-postgres-exporter.service
```

На `monitor` / Prometheus UI:

```promql
up{job="postgres", host="db"}
```

Ожидаемый итог:

```text
postgres target DOWN
PostgreSQLExporterDown -> PENDING/FIRING
PostgreSQLDown не обязан сработать, потому что сама БД может быть жива, но exporter недоступен
```

Восстановление:

```bash
sudo systemctl start prometheus-postgres-exporter.service
```

## Сценарий 22. PostgreSQLDown alert

Цель: показать alert по недоступности самой PostgreSQL.

На `db`:

```bash
sudo pg_ctlcluster 17 main stop
```

Проверить:

```promql
pg_up{job="postgres", host="db"}
```

Ожидаемый итог:

```text
pg_up = 0
PostgreSQLDown -> PENDING/FIRING
```

Восстановление:

```bash
sudo pg_ctlcluster 17 main start
pg_lsclusters
```

## Сценарий 23. Backup and restore proof

Цель: показать не просто наличие backup-файла, а доказанную восстановимость.

На `db`:

```bash
sudo systemctl start backup-supportdesk.service
sudo journalctl -u backup-supportdesk.service -n 50 --no-pager
sudo ls -lh /var/backups/postgresql/supportdesk/
sudo -u postgres bash -c 'sha256sum -c /var/backups/postgresql/supportdesk/*.sha256'
sudo -u postgres bash -c 'pg_restore -l /var/backups/postgresql/supportdesk/latest.dump | head -n 40'
```

Restore test в отдельную БД:

```bash
sudo -u postgres dropdb --if-exists supportdesk_restore_test
sudo -u postgres createdb supportdesk_restore_test
sudo -u postgres pg_restore --clean --if-exists -d supportdesk_restore_test /var/backups/postgresql/supportdesk/latest.dump
sudo -u postgres psql -d supportdesk_restore_test -P pager=off -c "SELECT 'tickets' AS table_name, count(*) FROM tickets UNION ALL SELECT 'ticket_events' AS table_name, count(*) FROM ticket_events;"
sudo -u postgres dropdb supportdesk_restore_test
```

Ожидаемый итог:

```text
checksum OK
pg_restore -l показывает TABLE public tickets и TABLE public ticket_events
counts восстановленной БД совпадают с рабочей БД
supportdesk_restore_test удалена после проверки
```

## Сценарий 24. Ansible service checks after DB stage

Цель: показать, что `admin` проверяет текущую реальную архитектуру.

На `admin`:

```bash
cd ~/control-node
ansible-inventory --graph
ansible-playbook playbooks/check_services.yml
```

Ожидаемый итог:

```text
app:     ok=5 failed=0  # Docker/API endpoints, не старый app.service
db:      ok=5 failed=0  # PostgreSQL cluster, exporters, Promtail, backup timer
log:     ok=2 failed=0
monitor: ok=4 failed=0
web:     ok=3 failed=0
```

## Сценарий 19. Security/network hardening access checks

Цель: показать, что после hardening внутренние сервисы доступны только нужным источникам, а нормальный пользовательский путь не сломан.

Проверки с `admin`:

```bash
cd ~/control-node

# allowed: web -> app backend
ansible web_nodes -m shell -a "nc -vzn 192.168.85.133 8080"

# allowed: monitor -> app metrics
ansible monitor_nodes -m shell -a "nc -vzn 192.168.85.133 8080; nc -vzn 192.168.85.133 8090; nc -vzn 192.168.85.133 9100"

# denied: db -> app direct backend/bot metrics
ansible db_nodes -m shell -a "nc -vzn -w 3 192.168.85.133 8080 || true; nc -vzn -w 3 192.168.85.133 8090 || true"

# denied: web -> db PostgreSQL
ansible web_nodes -m shell -a "nc -vzn -w 3 192.168.85.139 5432 || true"

# denied: web -> monitor UI ports
ansible web_nodes -m shell -a "nc -vzn -w 3 192.168.85.137 3000 || true; nc -vzn -w 3 192.168.85.137 9090 || true; nc -vzn -w 3 192.168.85.137 9093 || true"
```

Expected:

```text
web -> app:8080 open;
monitor -> app:8080/8090/9100 open;
db -> app:8080/8090 timeout;
web -> db:5432 timeout;
web -> monitor:3000/9090/9093 timeout.
```

User-facing path must still work:

```bash
curl -s http://192.168.85.131/api/v1/health | python3 -m json.tool
curl -s http://192.168.85.131/api/v1/tickets | python3 -m json.tool | head
```

Expected:

```text
Browser -> web -> app -> db works;
direct Windows/browser access to app:8080 and app:8090 does not work;
Windows/browser access to web:80 still works;
Grafana/Prometheus/Alertmanager remain accessible from Windows 192.168.85.1.
```

## Сценарий 20. DOCKER-USER persistence after app reboot

Цель: показать, что Docker firewall rules на `app` переживают reboot.

Проверка:

```bash
cd ~/control-node

ansible app_nodes -b -K -m shell -a '
systemctl is-enabled app-docker-user-firewall.service
systemctl is-active app-docker-user-firewall.service
iptables -S DOCKER-USER
'
```

Expected:

```text
app-docker-user-firewall.service -> enabled
app-docker-user-firewall.service -> active
DOCKER-USER contains allow rules for web/monitor/admin and DROP rules for other ens18 traffic to 8080/8090.
```

