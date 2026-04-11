# Mini Corporate Infrastructure Lab — план и roadmap

## Цель проекта

Собрать учебный, но production-like pet-project в формате мини-инфраструктуры корпоративного типа на базе Proxmox VE внутри VMware: frontend, backend, централизованное логирование, мониторинг, alerting, базовая автоматизация, дальнейшая контейнеризация, БД, Telegram-клиент и демонстрационные сценарии troubleshooting.

Итоговая ценность проекта: показать Linux administration, DevOps-подход, systemd, SSH, Ansible, Nginx, Python-сервис, Loki/Promtail, Prometheus/Grafana/Alertmanager, node_exporter, reverse proxy, product metrics, alerts, Docker, PostgreSQL, backup/restore и диагностику end-to-end.

---

## Текущий продуктовый концепт

Текущий учебный продукт проекта — `MISIS_Digital Student Support`.

Это сервис поддержки студентов по цифровым сервисам университета. Пользователь выбирает цифровой сервис, затем конкретный раздел/функцию внутри сервиса, описывает проблему и создает заявку.

Модель:

```text
category = цифровой сервис университета
resource = раздел/функция внутри выбранного сервиса
```

Категории в API/logs/metrics:

```text
newlms-misis
lk-misis
gornyak-misis
folio-misis
pulse-misis
vector-misis
pay-misis
```

Человекочитаемые labels в UI:

```text
newlms.misis.ru
lk.misis.ru
gornyak.misis.ru
folio.misis.ru
pulse.misis.ru
vector.misis.ru
pay.misis.ru
```

Пример заявки:

```text
category=lk-misis
resource=gradebook
priority=high
description="В электронной зачетке не отображается оценка"
```

Смысл observability: видеть не только техническое состояние серверов, но и продуктовые сигналы — по каким цифровым сервисам и разделам студенты создают больше всего заявок.

---

## Итоговая архитектура текущего состояния

```text
Windows host / Browser / SSH client
        |
        | VMware NAT / local access
        v
Proxmox VE node: 192.168.85.128:8006
        |
        +-- admin    192.168.85.129  control node / Ansible foundation
        +-- web      192.168.85.131  Nginx frontend + reverse proxy + Promtail + node_exporter
        +-- app      192.168.85.133  Dockerized MISIS_Digital Student Support API + app logs + app metrics + Promtail + node_exporter
        +-- log      192.168.85.135  Loki logging server + node_exporter
        +-- monitor  192.168.85.137  Prometheus + Grafana + Alertmanager + node_exporter
        +-- db       192.168.85.139  PostgreSQL 17 storage for supportdesk
```

## Реализованные потоки

```text
Browser -> web:80                                              # реализовано: MISIS_Digital Student Support frontend
Browser -> web:80/api/v1/* -> app:8080/v1/*                    # реализовано: Nginx reverse proxy /api/* -> app
web -> Promtail -> log:3100 Loki                               # реализовано: nginx access/error logs
app -> db:5432 PostgreSQL                                      # реализовано: tickets + ticket_events storage
app -> Promtail -> log:3100 Loki                               # реализовано: product logs with category label
monitor:9090 Prometheus -> node_exporter targets               # реализовано: node (5/5 up), включая db
monitor:9090 Prometheus -> app:8080/metrics                    # реализовано: product metrics + HTTP/API request metrics from Dockerized app
monitor:9090 Prometheus -> web:9080/metrics                    # реализовано: Promtail custom metric по nginx status_code
monitor:9090 Prometheus -> db:9187/metrics                     # реализовано: PostgreSQL metrics через postgres_exporter
db Promtail -> log:3100 Loki                                  # реализовано: PostgreSQL logs в Loki
db backup-supportdesk.timer -> pg_dump -Fc                    # реализовано: daily backup + restore test
Grafana -> Prometheus:9090                                     # реализовано: datasource подключен
Grafana -> Loki:3100                                           # реализовано: datasource подключен
Prometheus -> Alertmanager:9093                                # реализовано: alerts отправляются в Alertmanager
admin -> SSH/Ansible -> web/app/log/monitor                    # реализовано: базовый control node
admin -> SSH/Ansible -> db                                      # реализовано: db добавлен в inventory и service checks
```

## Важное замечание про IP

Все VM сейчас получают IP через DHCP VMware NAT. В lab-режиме адреса держатся стабильно, но позже нужно сделать одно из двух:

```text
1. DHCP reservation по MAC-адресам всех VM;
2. статические IP внутри Debian на всех серверах.
```

Это важно для Promtail, Prometheus targets, Grafana datasources, Ansible inventory, Nginx reverse proxy, будущей БД, Docker deployment и Telegram-бота.

---

# Роли серверов

## admin

Управляющий сервер. На нем SSH-ключи, Ansible, inventory, playbook'и, шаблоны, документация и Git.

## web

Frontend / Nginx server. Сейчас отдает страницу `MISIS_Digital Student Support`, проксирует `/api/*` на `app:8080`, пишет nginx access/error logs, отправляет их в Loki через Promtail, отдает системные метрики через node_exporter и экспортирует nginx-derived HTTP response metrics через Promtail `:9080/metrics`.

## app

Backend/application node. Сейчас Python-приложение работает как Docker container `misis-digital-student-support-api`: `/v1/health`, `/v1/support-model`, `/v1/tickets`, `/v1/tickets/all`, `/v1/tickets/<id>`, `/v1/tickets/<id>/status`, `/metrics`. Заявки хранятся в PostgreSQL на `db`; product logs пишутся в `/var/log/app/app.log`; app logs отправляются в Loki через Promtail; product metrics и HTTP/API request metrics собираются Prometheus.

## db

Database node. На нем работает PostgreSQL 17 cluster `17/main`, база `supportdesk`, роль `supportdesk_user`, таблицы `tickets` и `ticket_events`. `app` подключается к `db:5432`; доступ ограничен правилом `pg_hba.conf` для `192.168.85.133/32`. После этапа 17 на `db` также работают node_exporter, postgres_exporter, Promtail для PostgreSQL logs и daily pg_dump backup timer.

## log

Централизованный сервер логирования. На нем Loki. Принимает nginx logs от `web` и app product logs от `app`. Для app logs добавлен dynamic Loki label `category`.

## monitor

Сервер мониторинга, визуализации и алертов. На нем Prometheus, Grafana, Alertmanager и node_exporter. Dashboard `Infrastructure Overview` показывает infrastructure metrics, app/product metrics, HTTP/API observability, active alerts, web nginx logs и app product logs.

---

# Завершенные этапы

## Этап 1. Loki на log — завершено

Loki 3.5.0 установлен как `loki.service`, `active/enabled`, `/ready -> ready`, принимает web/app logs.

## Этап 2. Promtail на web — завершено

Promtail читает `/var/log/nginx/*.log` и отправляет nginx logs в Loki с labels `host=web`, `job=nginx`, `service=frontend`, `env=lab`.

## Этап 3. Promtail на app — завершено

Promtail читает `/var/log/app/*.log` и отправляет app logs в Loki. После Product model v2 static label приведен к `service=misis-digital-student-support-api`, а `category` извлекается из app log line как dynamic Loki label.

Что теперь можно делать:

```logql
{host="app", job="app", service="misis-digital-student-support-api"}
{host="app", job="app", category="lk-misis"}
```

## Этап 4. Monitor base stack — завершено

На `monitor` установлены Prometheus, Grafana, Alertmanager и node_exporter. Сервисы active/enabled.

## Этап 5. Метрики node_exporter — завершено

node_exporter установлен на `web`, `app`, `log`, `monitor`, `db`; Prometheus видит `node (5/5 up)` с host labels.

## Этап 6. Grafana datasources — завершено

В Grafana подключены Prometheus datasource (`http://localhost:9090`) и Loki datasource (`http://192.168.85.135:3100`).

## Этап 7. Grafana dashboard Infrastructure Overview — завершено

Dashboard показывает Targets UP, CPU/RAM/Disk по host, Web nginx logs, App logs, product ticket metrics, Product Observability v2 panels, HTTP/API Observability panels и Active Alerts.

## Этап 8. Web/App integration — завершено

Первоначально был реализован продукт `Mini Support Desk` через поток:

```text
Browser -> web/Nginx -> app/support-desk-api
```

Позже на этапе Product model v2 продукт был переосмыслен и заменен на `MISIS_Digital Student Support`, сохранив тот же infrastructure flow.

## Этап 9. Полировка logging — завершено

Финализирован формат product logs: `key=value`, proxy metadata, корректное различение `ticket_status_changed` и `ticket_status_unchanged`, validation/not_found события, LogQL/panel.

## Этап 10. Полировка monitoring — завершено

Добавлены product metrics, dashboard panels и базовые alert rules.

Текущие product metrics:

```text
supportdesk_tickets_total
supportdesk_tickets_open
supportdesk_tickets_in_progress
supportdesk_tickets_resolved
supportdesk_tickets_active
```

Текущие базовые alerts после cleanup на этапе 13:

```text
SupportDeskApiDown
HighDiskUsage
NodeTargetDown
```

Примечание: старый общий `TooManyOpenTickets` был удален на этапе 13, потому что его заменил более точный product alert по `category/resource`.

## Этап 11. Admin/Ansible foundation — завершено

Сделано:

```text
1. Раскатан SSH-ключ admin -> web/app/log/monitor.
2. Проверен SSH-вход с admin на managed nodes без пароля пользователя.
3. Расширен inventory.
4. Проверены ansible all -m ping и ansible managed -m ping.
5. Создана структура ~/control-node.
6. Добавлен ansible.cfg.
7. Созданы playbook'и: ping_all.yml, check_services.yml, restart_app.yml, deploy_prometheus_rules.yml.
8. Инициализирован Git repo.
9. Сделаны первые commit'ы.
```

## Этап 12. Product model v2 — завершено

Цель этапа: превратить простую форму заявок в самостоятельный продукт `MISIS_Digital Student Support` с моделью `category/resource`, active/resolved разделением и API v1.

Сделано:

```text
1. Новый продуктовый концепт: MISIS_Digital Student Support.
2. category = цифровой сервис университета.
3. resource = раздел/функция внутри выбранного сервиса.
4. category/resource обязательны.
5. Backend валидирует, что resource разрешен для выбранной category.
6. Старые заявки v1 сохранены в backup tickets.json; рабочий tickets.json очищен.
7. legacy-категория не используется.
8. Добавлены schema_version=2, category_label, resource_label, resolved_at.
9. Реализовано active/resolved разделение:
   /tickets -> active
   /tickets?status=resolved -> history
   /tickets/all -> all
10. Добавлены /v1/* endpoints.
11. Frontend переведен на category-first dropdown: сначала digital service, потом service section.
12. Исправлен статусный баг: in_progress корректно нормализуется через normalize_status.
13. Promtail app label обновлен на service=misis-digital-student-support-api.
14. Promtail pipeline добавляет Loki label category.
15. Grafana App logs panel обновлен под новую модель.
16. Prometheus метрики сохранены совместимыми; добавлена supportdesk_tickets_active.
```

Что теперь можно делать:

```text
Создать заявку:
category=lk-misis
resource=gradebook
priority=high

Увидеть:
- заявку в UI Active;
- POST /api/v1/tickets в nginx logs;
- event=ticket_created category=lk-misis resource=gradebook в app logs;
- stream category="lk-misis" в Loki;
- изменение supportdesk_tickets_* metrics в Prometheus/Grafana.
```

---

# Новый production-like roadmap от текущей точки до финала

## Этап 13. Product observability v2 — завершено

Цель этапа: добавить минимальную, но содержательную product observability поверх модели `MISIS_Digital Student Support` без избыточной сложности.

Итоговый production-like scope был сознательно сужен: не добавлялись counters/исторические duration-метрики без event storage, потому что их корректная реализация будет уместнее после PostgreSQL / `ticket_events`.

Добавлено в `/metrics` на `app`:

```text
supportdesk_tickets_current{status,category,resource,priority}
supportdesk_active_ticket_age_seconds_max{category,resource,priority}
```

Старые compatibility metrics сохранены:

```text
supportdesk_tickets_total
supportdesk_tickets_open
supportdesk_tickets_in_progress
supportdesk_tickets_resolved
supportdesk_tickets_active
```

Добавлены/обновлены Grafana panels в dashboard `Infrastructure Overview`:

```text
Open tickets by category
Active tickets by category/resource
Critical active tickets
Oldest active ticket age
```

Итоговый alert-набор после cleanup:

```text
Product/API:
- SupportDeskApiDown
- SupportDeskTooManyTicketsForResource
- SupportDeskCriticalTicketsOpen
- SupportDeskOldCriticalTicket

Infrastructure:
- HighDiskUsage
- NodeTargetDown
```

Что убрано/отложено:

```text
TooManyOpenTickets удален как слишком общий alert.
supportdesk_tickets_created_total отложен до event storage.
supportdesk_tickets_resolved_total отложен до event storage.
source dimension отложен до Telegram/API-client stage.
resolution duration/SLA metrics отложены до ticket_events/PostgreSQL.
SupportDeskTicketSpike и created-vs-resolved alerts отложены до counters.
```

Дополнительно улучшено:

```text
Ansible playbook deploy_prometheus_rules.yml теперь проверяет Prometheus /-/ready с retries/delay, чтобы не падать на кратковременный 503 сразу после restart Prometheus.
Prometheus rules deployment и cleanup зафиксированы в Git на admin.
```

Что теперь можно делать:

```text
Создать несколько заявок по одному resource:
category=lk-misis
resource=gradebook

Увидеть:
- рост supportdesk_tickets_current по lk-misis / gradebook;
- концентрацию проблемы в Grafana panel Active tickets by category/resource;
- SupportDeskTooManyTicketsForResource в Prometheus/Alertmanager;
- critical-заявки отдельно в Critical active tickets;
- старые critical-заявки через SupportDeskOldCriticalTicket.
```

## Этап 14. HTTP request metrics, error-rate alerts и latency — завершено

Цель этапа: добавить production-like HTTP/API observability без дублирующих метрик: request rate, status codes, error-rate, latency и proxy-level 502.

Итоговый scope был сознательно минимальным: отдельный `supportdesk_errors_total` не добавлялся, потому что ошибки считаются через `status_code` в общей request counter.

Добавлено на `app` в `/opt/app/app.py` через `prometheus_client`:

```text
supportdesk_http_requests_total{method,route,status_code}
supportdesk_http_request_duration_seconds_bucket{method,route,status_code,le}
supportdesk_http_request_duration_seconds_sum{method,route,status_code}
supportdesk_http_request_duration_seconds_count{method,route,status_code}
```

Принципы реализации:

```text
route label хранит нормализованный route, а не raw URL;
/v1/tickets/123/status -> /v1/tickets/{id}/status;
query string не попадает в label;
/metrics исключен из пользовательских HTTP request metrics;
старые product metrics сохранены;
HTTP metrics отдаются на том же /metrics через отдельный CollectorRegistry.
```

Добавлено на `web` в Promtail:

```text
promtail_custom_nginx_http_responses_total{status_code}
```

Эта метрика строится из `/var/log/nginx/access.log` через Promtail `pipeline_stages` и нужна для proxy-level alert-а `Nginx502Spike`, потому что 502 формирует Nginx, когда backend недоступен.

Добавлено в Prometheus:

```text
job="promtail-web"
target="192.168.85.131:9080"
```

Добавлены alerts:

```text
SupportDeskHigh4xxRate   warning   доля 4xx > 30% при >=5 запросах за 5m
SupportDeskHigh5xxRate   critical  доля 5xx > 5% при >=5 запросах за 5m
SupportDeskHighLatency   warning   p95 API latency > 0.5s при >=5 запросах за 5m
Nginx502Spike            critical  >=3 nginx 502 за 5m
```

Проверено:

```text
supportdesk_http_requests_total виден на app /metrics и в Prometheus;
supportdesk_http_request_duration_seconds_* виден в Prometheus;
404-запросы дают route="unmatched", status_code="404";
SupportDeskHigh4xxRate переходит в FIRING при генерации 4xx-трафика;
promtail_custom_nginx_http_responses_total виден в Prometheus через job="promtail-web";
Nginx502Spike переходит в FIRING при остановке app.service и запросах через web/Nginx;
SupportDeskApiDown одновременно показывает backend scrape failure при stop app.service.
```

Добавлен минимальный блок Grafana `HTTP/API Observability` в dashboard `Infrastructure Overview`:

```text
HTTP/API Health Overview
API Request Rate by Route
API Responses by Status Code
API p95 Latency by Route
```

Что теперь можно делать:

```text
видеть, какие API routes используются;
видеть распределение backend response status codes;
видеть 4xx/5xx error-rate;
видеть p95 latency по API и по routes;
видеть proxy-level nginx 502;
отличать backend down от пользовательских 502 на reverse proxy path.
```

## Этап 15. Dockerization — завершено

Цель этапа: добавить Docker как production-like способ доставки backend-приложения, не ломая текущую инфраструктурную модель.

Сделано на `app`:

```text
Docker Engine 29.4.3 установлен и active/enabled
Docker Compose v5.1.3 установлен
Dockerfile создан
requirements.txt создан
.env создан
.dockerignore создан
image misis-digital-student-support-api:local собран
container misis-digital-student-support-api запущен через docker compose
host 8080 -> container 8080
```

Что контейнеризировано:

```text
misis-digital-student-support-api на app
```

Что пока не переносилось в Docker:

```text
Prometheus
Grafana
Loki
Alertmanager
Nginx
node_exporter
admin
```

Сохраненные внешние контракты:

```text
Browser -> web/Nginx -> app:8080
Prometheus -> app:8080/metrics
Promtail -> /var/log/app/app.log -> Loki
```

Проверено:

```text
localhost:8080/v1/health -> ok
localhost:8080/metrics -> product и HTTP/API metrics
web/Nginx -> app:8080 -> Docker container работает
POST /api/v1/tickets работает
PATCH /api/v1/tickets/<id>/status работает
Prometheus up{job="supportdesk-api"} -> 1
app logs доходят до Loki/Grafana
```

Старый runtime:

```text
app.service inactive/dead
autostart disabled
unit сохранен как rollback-вариант
```

Rollback:

```bash
cd /opt/app
sudo docker compose down
sudo systemctl start app.service
```

Осознанный временный компромисс:

```text
/opt/app:/opt/app
```

Причина: текущий `tickets.json` storage пишет через временный файл и `os.replace()`. Mount только одного файла `tickets.json` ломал `POST/PATCH`. До PostgreSQL этот workaround допустим; после DB migration code должен жить в image, а состояние — в PostgreSQL.

Что теперь можно делать:

```text
демонстрировать migration от systemd-managed Python backend к Dockerized backend;
пересобирать image через Dockerfile;
перезапускать backend через docker compose;
проверять rollback на app.service;
переходить к PostgreSQL, сохраняя Dockerized app как runtime.
```

## Этап 16. PostgreSQL вместо tickets.json — завершено

Цель: заменить учебное файловое хранилище на нормальную БД и подготовить основу для event-based product observability.

Сделано:

```text
создан сервер db 192.168.85.139;
установлен PostgreSQL 17;
созданы role/database/schema для supportdesk;
созданы таблицы tickets и ticket_events;
созданы индексы для status/category-resource/priority/events/time;
app получил DB_* env-переменные;
requirements.txt дополнен psycopg2-binary;
13 заявок мигрированы из tickets.json;
для мигрированных заявок созданы events imported_from_json;
read-path переведен на SQL SELECT;
metrics переведены на SQL COUNT/GROUP BY/MIN;
write-path переведен на SQL-native INSERT/UPDATE RETURNING;
app.py почищен от legacy Python-list storage helpers;
Docker image пересобран;
/opt/app:/opt/app volume удален;
код живет в image, данные живут в PostgreSQL.
```

Новая архитектура:

```text
Browser -> web/Nginx -> app/Docker container -> db/PostgreSQL
```

Текущие таблицы:

```text
tickets        текущее состояние заявок
ticket_events  история событий: imported_from_json, ticket_created, ticket_status_changed
```

Проверено:

```text
/v1/health -> ok;
/metrics -> supportdesk_tickets_total;
GET /api/v1/tickets возвращает данные из PostgreSQL;
POST /api/v1/tickets создает запись в tickets и ticket_events;
ticket_events.metadata_json содержит write_path=sql_native и storage_backend=postgresql;
Prometheus supportdesk-api target остается UP;
Grafana/Loki app logs продолжают работать через /var/log/app/app.log.
```

Что теперь можно делать:

```text
демонстрировать настоящий stateful backend с отдельной БД;
показывать SQL-запросы к tickets/ticket_events;
показывать audit trail по заявкам;
строить будущие counters/SLA-метрики из ticket_events;
переходить к DB observability и backup/restore.
```

## Этап 17. DB observability и backups — завершено

Цель: сделать БД наблюдаемой и восстановимой: видеть состояние PostgreSQL, получать DB logs, иметь проверенный backup и доказанный restore.

Сделано на `db`:

```text
node_exporter установлен и добавлен в общий Prometheus job="node";
postgres_exporter установлен и слушает :9187;
postgres_exporter подключается к PostgreSQL ролью postgres_exporter через DATA_SOURCE_NAME;
Promtail установлен на db и читает /var/log/postgresql/*.log;
PostgreSQL logs уходят в Loki с labels host=db, job=postgresql, service=postgresql, env=lab;
pg_dump backup script создан: /usr/local/sbin/backup_supportdesk.sh;
backup-supportdesk.service Type=oneshot;
backup-supportdesk.timer daily 03:15 MSK, Persistent=true;
retention policy: 7 дней;
backup формат: pg_dump -Fc;
для каждого dump создается .sha256;
latest.dump symlink указывает на последний dump;
restore test выполнен в отдельную БД supportdesk_restore_test;
после проверки supportdesk_restore_test удалена.
```

Сделано на `monitor`:

```text
Prometheus node target теперь 5/5 up, включая db;
добавлен Prometheus job="postgres" target 192.168.85.139:9187;
postgres target 1/1 up;
проверены метрики pg_up, pg_database_size_bytes, pg_stat_database_numbackends, pg_settings_max_connections;
добавлены alerts PostgreSQLExporterDown, PostgreSQLDown, PostgreSQLTooManyConnections;
alerts PostgreSQLExporterDown и PostgreSQLDown протестированы;
Grafana dashboard Infrastructure Overview получил блок PostgreSQL / Supportdesk DB.
```

Grafana DB panels:

```text
DB Health: postgres_exporter UP, PostgreSQL UP, supportdesk DB size, DB alerts firing, DB Connections;
DB Connections: % used connections for supportdesk relative to max_connections;
DB Activity: commits/sec и rollbacks/sec по базе supportdesk;
PostgreSQL Important Logs: ERROR/FATAL/PANIC/startup/shutdown/deadlock/termination события из Loki.
```

Сделано на `admin`:

```text
inventory/hosts.ini дополнен группой db_nodes и db включен в managed;
check_services.yml обновлен под Dockerized app: docker.service + /v1/health + /metrics вместо старого app.service;
check_services.yml дополнен db checks: pg_lsclusters, node_exporter, postgres_exporter, promtail, backup timer;
ansible-playbook playbooks/check_services.yml проходит: app ok=5, db ok=5, log ok=2, monitor ok=4, web ok=3;
изменения зафиксированы commit 23771ba Add DB observability checks and PostgreSQL alerts.
```

Что теперь можно делать:

```text
видеть, что db как Linux-нода доступна;
видеть, что PostgreSQL как процесс/кластер доступен;
отличать down postgres_exporter от down самой PostgreSQL;
смотреть PostgreSQL logs в Grafana/Loki;
видеть размер supportdesk DB, активность транзакций и текущую загрузку connections;
получать DB alerts;
создавать ежедневные backup-и;
проверять checksum dump-файлов;
доказывать восстановимость через restore test в отдельную БД.
```

## Этап 18. Telegram support bot + bot observability

Статус: завершено.

Цель: добавить Telegram как второго клиента к тому же backend API и построить минимальную observability вокруг нового bot-container без дублирования уже существующей product observability.

Итоговая архитектура клиентских потоков:

```text
Browser -> web/Nginx -> supportdesk-api -> PostgreSQL
Telegram user -> Telegram API -> support-bot container -> supportdesk-api -> PostgreSQL
```

Ключевое решение: Telegram bot не пишет напрямую в PostgreSQL. Он работает как отдельный клиент backend API v1, поэтому вся бизнес-логика остается в `misis-digital-student-support-api`: валидация category/resource/priority/status, запись `tickets`, запись `ticket_events`, product logs и product metrics.

Реализовано на `app`:

```text
Docker Compose service: support-bot
Container: misis-digital-support-bot
Bot username: @misis_digital_support_bot
Bot token: хранится только в /opt/app/.env.bot, в sources не фиксируется
Runtime: long polling через outbound HTTP(S) proxy
Metrics endpoint: app:8090/metrics
Logs: /var/log/bot/support-bot.log
```

Функциональность бота:

```text
/start      главное меню
/help       справка
/new        создание заявки через кнопочный wizard
/tickets    просмотр active-заявок с пагинацией
/resolve    закрытие active-заявки с пагинацией
```

UI-решения:

```text
кнопочный интерфейс вместо ручного ввода slug-ов;
category/resource/priority выбираются кнопками;
описание вводится текстом;
HTML-разметка + html.escape для безопасного отображения спецсимволов;
после закрытия заявки бот отдельно показывает: "Создана через" и "Закрыта через";
active tickets и resolve menu имеют пагинацию;
whitelist через ALLOWED_TELEGRAM_USER_IDS поддержан, но сейчас сознательно оставлен пустым для demo/lab.
```

Observability вокруг бота:

```text
Promtail на app читает /var/log/bot/*.log отдельным job="support-bot";
Loki stream: {host="app", job="support-bot", service="misis-digital-support-bot"};
Prometheus scrape job: support-bot -> 192.168.85.133:8090/metrics;
Grafana row: Telegram Bot Observability;
Prometheus alerts: SupportBotDown, SupportBotBackendErrors, SupportBotErrorsDetected.
```

Bot metrics:

```text
support_bot_info{service,version}
support_bot_start_time_seconds
support_bot_actions_total{action}
support_bot_api_requests_total{method,endpoint,status_code}
support_bot_api_request_duration_seconds_bucket{method,endpoint,status_code,le}
support_bot_api_request_duration_seconds_sum{method,endpoint,status_code}
support_bot_api_request_duration_seconds_count{method,endpoint,status_code}
support_bot_errors_total{type}
```

Принцип scope: на этом этапе не добавлялась новая product source-metric вроде `supportdesk_tickets_current_by_source`, потому что продуктовые вопросы уже покрыты существующими panels/alerts по category/resource/priority/age/status. Новый observability-слой отвечает именно на вопросы bot-runtime и bot-as-client:

```text
бот жив?
бот используется?
бот может ходить в backend API?
какие bot->API endpoint-ы дают ошибки?
где bot->API latency становится высокой?
какие действия выполнялись в Telegram UI?
что видно в bot logs и bot error logs?
```

Проверено:

```text
/start, /help, /new, /tickets, /resolve работают;
созданные из Telegram заявки получают source=telegram;
ticket_events фиксирует ticket_created/ticket_status_changed с source=telegram;
бот создает и закрывает заявки через API v1;
Promtail/Loki получают bot logs отдельным stream-ом;
token не попадает в bot logs;
Prometheus видит support-bot target UP;
SupportBotDown срабатывает при остановке support-bot container;
SupportBotBackendErrors срабатывает, когда backend выключен и бот получает ошибку при реальном Telegram-действии;
SupportBotErrorsDetected отделен от backend_error и предназначен для non-backend ошибок бота;
Grafana показывает Telegram Bot Alerts, Runtime, API dependency/latency, actions, recent logs и error logs.
```

## Этап 19. Security/network hardening

Цель: приблизить сетевую модель к production-like варианту.

Что сделать:

```text
ограничить прямой доступ к app:8080
ограничить db:5432
Nginx hardening
HTTPS/self-signed cert или local CA
секреты вне Git
DHCP reservation или static IP
```

## Этап 20. Ansible automation v2

Цель: автоматизировать уже новую архитектуру: app, Docker, DB, bot, monitoring rules.

Playbooks/roles:

```text
common.yml
nginx.yml
app.yml
docker_app.yml
promtail.yml
prometheus.yml
postgres.yml
bot.yml
backup.yml
```

## Этап 21. Финальная документация, README и demo packaging

Цель: упаковать проект как законченный pet-project.

Что подготовить:

```text
README с архитектурой
IP/порты/сервисы
Data flows
Команды проверки
Dashboard screenshots
Alerts list
Demo сценарии
Troubleshooting scenarios
Backup/restore scenario
Snapshots/контрольные точки в Proxmox
```

---

# Текущий маркер прогресса

```text
Последний завершенный этап: Этап 18. Telegram support bot + bot observability.
Текущий следующий этап: Этап 19. Security/network hardening.
Далее: hardening, Ansible automation v2, final README/demo.
```

## Текущий прогресс проекта

Важно: прогресс считается относительно расширенного production-like roadmap.

```text
Формальная готовность по расширенному roadmap: 18/21 основных этапов завершены ≈ 86%.
Готовность core infrastructure lab: 100% по этапам 1–10.
Admin/Ansible foundation: 100%.
Product model v2: 100%.
DB observability и backups: 100%.
Инженерная готовность по новому production-like scope: 90–93%.
Демонстрационная готовность текущего core-проекта: 98–99%.
Финальная демонстрационная готовность с DB/Bot/Ansible v2: 76–82%.
```

Разбивка по этапам:

| Этап | Статус | Готовность | Комментарий |
|---|---:|---:|---|
| 1. Loki на log | завершено | 100% | Loki работает как systemd service и принимает logs. |
| 2. Promtail на web | завершено | 100% | nginx logs уходят в Loki. |
| 3. Promtail на app | завершено | 100% | app logs уходят в Loki, category label добавлен. |
| 4. Monitor base stack | завершено | 100% | Prometheus, Grafana, Alertmanager, node_exporter active/enabled. |
| 5. Метрики node_exporter | завершено | 100% | Prometheus видит node targets `4/4 up`. |
| 6. Grafana datasources | завершено | 100% | Prometheus и Loki подключены к Grafana. |
| 7. Grafana dashboard Infrastructure Overview | завершено | 100% | Есть рабочий обзорный dashboard. |
| 8. Web/App integration | завершено | 100% | Browser -> web -> app flow работает. |
| 9. Полировка logging | завершено | 100% | Product logs, proxy metadata, LogQL/panel. |
| 10. Полировка monitoring | завершено | 100% | App metrics, product panels, active alerts, alert rules. |
| 11. Admin/Ansible foundation | завершено | 100% | SSH keys, inventory, ansible.cfg, playbook-и и Git repo готовы. |
| 12. Product model v2 | завершено | 100% | MISIS_Digital Student Support, category/resource, active/resolved, API v1, UI, Loki category label. |
| 13. Product observability v2 | завершено | 100% | Добавлены current/age metrics, Grafana panels, product alerts по category/resource/critical age; старый TooManyOpenTickets удален. |
| 14. HTTP request/error-rate observability | завершено | 100% | Добавлены HTTP request counter, latency histogram, app-level 4xx/5xx/latency alerts, Promtail nginx status metric, promtail-web target, Nginx502Spike и HTTP/API Grafana panels. |
| 15. Dockerization | завершено | 100% | Backend перенесен в Docker container, порт 8080 и observability flow сохранены, app.service disabled как rollback-вариант. |
| 16. PostgreSQL migration | завершено | 100% | Создан db, PostgreSQL 17, tickets/ticket_events, миграция из JSON, SQL-native read/write path, app.py cleanup, `/opt/app:/opt/app` volume удален. |
| 17. DB observability + backups | завершено | 100% | db добавлен в Ansible/Prometheus/Grafana/Loki; postgres_exporter, DB alerts, PostgreSQL logs, pg_dump backup, checksum, restore test и systemd timer готовы. |
| 18. Telegram support bot + bot observability | завершено | 100% | Telegram bot реализован как Docker Compose service, работает через long polling/proxy, создает/показывает/закрывает заявки через API v1, пишет source=telegram, логи идут в Loki, native /metrics подключены к Prometheus, bot alerts и Grafana row готовы. |
| 19. Security/network hardening | следующий этап | 5–10% | Есть proxy headers и понимание сетевых потоков, но ограничения доступа/HTTPS еще впереди. |
| 20. Ansible automation v2 | план | 0–10% | Зависит от дальнейшей формализации deploy. |
| 21. Final README/demo packaging | план | 25–35% | Sources ведутся, но финальный README/demo/snapshots еще не собраны. |

Короткая интерпретация:

```text
Проект уже можно демонстрировать как работающий infrastructure lab с web/app/logging/monitoring/alerts, базовым Ansible control node и самостоятельным продуктовым сценарием MISIS_Digital Student Support.
```

---

# Future improvements

Подробный backlog будущих улучшений вынесен отдельно в файл:

```text
12_future_improvements_backlog.md
```
