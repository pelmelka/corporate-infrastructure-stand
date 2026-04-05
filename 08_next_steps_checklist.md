# Чек-лист следующих шагов

## Завершено: logging base

- [x] Loki 3.5.0 установлен на `log`.
- [x] `loki.service` active/enabled.
- [x] Loki принимает nginx logs от `web`.
- [x] Loki принимает app logs от `app`.
- [x] Promtail установлен на `web`.
- [x] Promtail на `web` читает `/var/log/nginx/*.log`.
- [x] Promtail установлен на `app`.
- [x] Promtail на `app` читает `/var/log/app/*.log`.

## Завершено: monitor base stack

- [x] Создана VM `monitor`.
- [x] Prometheus active/enabled.
- [x] Grafana active/enabled.
- [x] Alertmanager active/enabled.
- [x] Prometheus видит Alertmanager.
- [x] node_exporter работает на `monitor`.

## Завершено: node_exporter + Prometheus targets

- [x] node_exporter установлен на `web`.
- [x] node_exporter установлен на `app`.
- [x] node_exporter установлен на `log`.
- [x] node_exporter работает на `monitor`.
- [x] Prometheus показывает `node (4/4 up)`.

## Завершено: Grafana datasources

- [x] Prometheus datasource подключен.
- [x] Loki datasource подключен.
- [x] `up{job="node"}` показывает `web`, `app`, `log`, `monitor`.
- [x] Loki показывает nginx logs и app logs.

## Завершено: Grafana dashboard Infrastructure Overview

- [x] Создан dashboard `Infrastructure Overview`.
- [x] Добавлены panels Targets UP, CPU, RAM, Disk.
- [x] Добавлены panels Web nginx logs и App logs.

## Завершено: Web/App integration

- [x] Выбрана первичная продуктовая реализация: Mini Support Desk.
- [x] На `app` создан backup `/opt/app/app.py.bak-before-supportdesk`.
- [x] Backend заменен на support-desk API.
- [x] `app.service` перезапущен и active/running.
- [x] Проверены `/health`, `/tickets`, `POST /tickets`, `PATCH /tickets/<id>/status`, `/metrics`.
- [x] Создан `/opt/app/tickets.json`.
- [x] App пишет product logs `event=...`.
- [x] На `web` настроен Nginx reverse proxy `/api/* -> http://192.168.85.133:8080/`.
- [x] На `web` заменен frontend.
- [x] Browser -> web -> app flow подтвержден.

## Завершено: Полировка logging

- [x] Финализирован формат product logs в `key=value` формате.
- [x] Добавлен `clean_log_value()`.
- [x] `client_ip` оставлен как TCP peer backend-а.
- [x] Добавлены `x_forwarded_for` и `x_forwarded_proto`.
- [x] `x_real_ip` сознательно не логируется, чтобы не дублировать `x_forwarded_for` в текущей схеме.
- [x] `old_status == new_status` пишет `event=ticket_status_unchanged`.
- [x] Реальные изменения статуса пишут `event=ticket_status_changed`.
- [x] Подтверждены `ticket_validation_failed`, `ticket_not_found`, `endpoint_not_found`.
- [x] App logs panel в Grafana обновлена под `event=...` формат.
- [x] Promtail label на `app` изменен с `service=python-backend` на `service=support-desk-api`.

## Завершено: Полировка monitoring

- [x] Проверен доступ `monitor -> app:8080/metrics`.
- [x] В Prometheus добавлен scrape job `supportdesk-api`.
- [x] Target `supportdesk-api` показывает `1/1 up`.
- [x] Prometheus видит `supportdesk_tickets_total`, `supportdesk_tickets_open`, `supportdesk_tickets_in_progress`, `supportdesk_tickets_resolved`.
- [x] В Grafana добавлена panel `SupportDesk Tickets`.
- [x] В Grafana добавлена panel `SupportDesk API UP`.
- [x] В Grafana добавлена panel `Active Alerts`.
- [x] Создан `/etc/prometheus/supportdesk.rules.yml`.
- [x] В `prometheus.yml` подключен `rule_files` для `supportdesk.rules.yml`.
- [x] Alert `SupportDeskApiDown` добавлен и протестирован.
- [x] Alert `TooManyOpenTickets` добавлен и протестирован.
- [x] Alert `HighDiskUsage` добавлен и протестирован через временный порог.
- [x] Alert `NodeTargetDown` добавлен и протестирован.
- [x] Проверено, что Alertmanager получает alert через `amtool`.

## Завершено: Admin/Ansible foundation

- [x] Раскатаны SSH-ключи с `admin` на `web`, `app`, `log`, `monitor`.
- [x] Проверен SSH-вход с `admin` на managed nodes без пароля пользователя.
- [x] Расширен Ansible inventory всеми узлами.
- [x] Группы inventory приведены к виду `web_nodes`, `app_nodes`, `log_nodes`, `monitor_nodes`, чтобы не было конфликтов имени host/group.
- [x] Добавлена группа `managed` как children-группа для `web/app/log/monitor`.
- [x] Проверены `ansible all -m ping` и `ansible managed -m ping`.
- [x] Создана структура `~/control-node`: `inventory/`, `playbooks/`, `roles/`, `templates/`, `files/`, `docs/`.
- [x] Добавлен `ansible.cfg`; подтверждено, что Ansible использует `/home/pelmel/control-node/ansible.cfg`.
- [x] Создан `playbooks/ping_all.yml`.
- [x] Создан и проверен `playbooks/check_services.yml`.
- [x] Создан и проверен `playbooks/restart_app.yml`.
- [x] Создан и проверен `playbooks/deploy_prometheus_rules.yml`.
- [x] Локальный source-файл Prometheus rules сохранен в `files/prometheus/supportdesk.rules.yml`.
- [x] Инициализирован Git repo в `~/control-node`.
- [x] Настроены локальные Git user.name/user.email.
- [x] Сделан первый commit `initial Ansible control node setup`.
- [x] Добавлены `.gitkeep` для пустых директорий `roles/`, `templates/`, `docs/` и сделан commit `Add Ansible project directory placeholders`.

## Завершено: Product model v2 — MISIS_Digital Student Support

- [x] Концепция продукта переосмыслена: `MISIS_Digital Student Support`.
- [x] `category` теперь означает цифровой сервис университета.
- [x] `resource` теперь означает раздел/функцию внутри выбранного сервиса.
- [x] Утверждены категории: `newlms-misis`, `lk-misis`, `gornyak-misis`, `folio-misis`, `pulse-misis`, `vector-misis`, `pay-misis`.
- [x] В UI показываются labels с `.ru`: `newlms.misis.ru`, `lk.misis.ru`, `gornyak.misis.ru`, `folio.misis.ru`, `pulse.misis.ru`, `vector.misis.ru`, `pay.misis.ru`.
- [x] В API/logs/metrics используются короткие slug-и без `-ru` для читаемости.
- [x] Старые v1-заявки сохранены в backup `tickets.json.bak-before-product-model-v2-*`.
- [x] Рабочий `/opt/app/tickets.json` очищен под новую модель.
- [x] Категория `legacy` не используется.
- [x] Backend заменен на `misis-digital-student-support-api`.
- [x] Добавлены поля `schema_version`, `category`, `category_label`, `resource`, `resource_label`, `resolved_at`.
- [x] `category/resource` обязательны для новых заявок.
- [x] Backend валидирует, что `resource` разрешен для выбранной `category`.
- [x] Неверная пара `category/resource` возвращает validation error.
- [x] Исправлена нормализация статуса `in_progress` через отдельную `normalize_status()`.
- [x] Реализованы `/v1/health`, `/v1/support-model`, `/v1/tickets`, `/v1/tickets/all`, `/v1/tickets/<id>`, `/v1/tickets/<id>/status`.
- [x] Legacy endpoints без `/v1` сохранены для совместимости.
- [x] `/tickets` и `/v1/tickets` показывают active tickets: `open + in_progress`.
- [x] `/tickets?status=resolved` и `/v1/tickets?status=resolved` показывают resolved history.
- [x] `/tickets/all` и `/v1/tickets/all` показывают все заявки.
- [x] При `resolved` заполняется `resolved_at`.
- [x] При reopen в `open`/`in_progress` `resolved_at` сбрасывается в `null`.
- [x] Frontend заменен на форму `Digital service -> Service section`.
- [x] Resource dropdown динамически меняется по выбранной category.
- [x] В UI работают вкладки `Active`, `Resolved`, `All`.
- [x] UI flow подтвержден: create, open, in_progress, resolved, reopen.
- [x] App logs пишут `service=misis-digital-student-support-api`.
- [x] Promtail static label обновлен на `service=misis-digital-student-support-api`.
- [x] Promtail pipeline добавляет dynamic Loki label `category`.
- [x] В Grafana Explore подтверждены запросы по `category="gornyak-misis"` и `category="lk-misis"`.
- [x] Grafana App logs panel обновлен под новый service label и новый line_format.
- [x] `ticket_list_requested` сознательно оставлен в App logs panel как полезный признак активности UI/API.
- [x] Старые Prometheus метрики не сломаны.
- [x] Добавлена метрика `supportdesk_tickets_active`.

## Завершено: Product observability v2

- [x] Перед изменениями созданы backup-и `/opt/app/app.py.bak-before-product-observability-v2` и `/opt/app/tickets.json.bak-before-product-observability-v2`.
- [x] Старые compatibility metrics сохранены: `supportdesk_tickets_total`, `supportdesk_tickets_open`, `supportdesk_tickets_in_progress`, `supportdesk_tickets_resolved`, `supportdesk_tickets_active`.
- [x] Добавлена метрика `supportdesk_tickets_current{status,category,resource,priority}`.
- [x] Добавлена метрика `supportdesk_active_ticket_age_seconds_max{category,resource,priority}`.
- [x] Prometheus scrape job `supportdesk-api` видит новые метрики.
- [x] В Grafana добавлен блок Product Observability v2.
- [x] Добавлена panel `Open tickets by category`.
- [x] Добавлена panel `Active tickets by category/resource`.
- [x] Добавлена panel `Critical active tickets`.
- [x] Добавлена panel `Oldest active ticket age`.
- [x] Добавлен alert `SupportDeskTooManyTicketsForResource`.
- [x] Добавлен alert `SupportDeskCriticalTicketsOpen`.
- [x] Добавлен alert `SupportDeskOldCriticalTicket`.
- [x] Старый общий alert `TooManyOpenTickets` удален как дублирующий и менее точный.
- [x] `SupportDeskApiDown` обновлен текстом и label `service=misis-digital-student-support-api`.
- [x] Alertmanager получает новые alerts, проверено через `amtool`.
- [x] `deploy_prometheus_rules.yml` улучшен: readiness check Prometheus использует retries/delay и не падает на кратковременный `503` после restart.
- [x] Изменения в Ansible control-node зафиксированы в Git.

Отложено в будущие этапы:

- [ ] `source` dimension после появления Telegram/API-client.
- [ ] `supportdesk_tickets_created_total{category,resource,priority,source}` после PostgreSQL / `ticket_events`.
- [ ] `supportdesk_tickets_resolved_total{category,resource,priority,source}` после PostgreSQL / `ticket_events`.
- [ ] `supportdesk_ticket_resolution_duration_seconds_*` после полноценной event/SLA observability.
- [ ] Alerts `SupportDeskTicketSpike`, `SupportDeskCreatedOutpacesResolved`, `SupportDeskSlowResolution`, `SupportDeskNoResolutionsForActiveBacklog` после counters/duration metrics.

## Завершено: HTTP/request observability

- [x] Перед изменениями созданы backup-и `/opt/app/app.py.bak-before-http-observability-v1` и `/opt/app/tickets.json.bak-before-http-observability-v1`.
- [x] Проверено, что `prometheus_client` установлен на `app`.
- [x] В `app.py` добавлен `CollectorRegistry` для HTTP metrics.
- [x] Добавлен counter `supportdesk_http_requests_total{method,route,status_code}`.
- [x] Добавлен histogram `supportdesk_http_request_duration_seconds{method,route,status_code}`.
- [x] На `/metrics` появились `supportdesk_http_request_duration_seconds_bucket/sum/count`.
- [x] `/metrics` исключен из пользовательских HTTP request metrics.
- [x] Реализована route normalization: `/v1/tickets/<id>` и `/v1/tickets/<id>/status` не создают high-cardinality labels.
- [x] Проверено, что 404 дает `route="unmatched"`, `status_code="404"`.
- [x] Prometheus видит `supportdesk_http_requests_total{job="supportdesk-api"}`.
- [x] Prometheus видит `supportdesk_http_request_duration_seconds_count{job="supportdesk-api"}`.
- [x] Проверены PromQL-запросы по status code, error count и p95 latency.
- [x] В Prometheus rules добавлены `SupportDeskHigh4xxRate`, `SupportDeskHigh5xxRate`, `SupportDeskHighLatency`.
- [x] `SupportDeskHigh4xxRate` протестирован генерацией 4xx-трафика и перешел в `FIRING`.
- [x] На `web` Promtail config дополнен metrics pipeline для nginx access log.
- [x] Исправлен неудачный длинный regex: финальный pipeline использует минимальный regex для извлечения `status_code`.
- [x] Promtail на `web` после правки снова `active (running)`.
- [x] На `web:9080/metrics` появилась custom metric `promtail_custom_nginx_http_responses_total{status_code}`.
- [x] В Prometheus config добавлен target `promtail-web` на `192.168.85.131:9080`.
- [x] Prometheus показывает `promtail-web (1/1 up)`.
- [x] В Prometheus rules добавлен `Nginx502Spike`.
- [x] `Nginx502Spike` протестирован остановкой `app.service` и запросами через `web/Nginx`; alert перешел в `FIRING`.
- [x] После теста `app.service` восстановлен.
- [x] В Grafana dashboard добавлен минимальный блок `HTTP/API Observability` из 4 panels:
  - [x] `HTTP/API Health Overview`;
  - [x] `API Request Rate by Route`;
  - [x] `API Responses by Status Code`;
  - [x] `API p95 Latency by Route`.
- [x] Дублирующая метрика `supportdesk_errors_total` сознательно не добавлялась: ошибки считаются через `status_code` в `supportdesk_http_requests_total`.

## Завершено: Dockerization

- [x] Docker Engine установлен на `app`.
- [x] `docker.service` active/enabled.
- [x] Docker Compose plugin установлен и работает.
- [x] Создан `/opt/app/Dockerfile` для `misis-digital-student-support-api`.
- [x] Создан `/opt/app/requirements.txt`.
- [x] Создан `/opt/app/docker-compose.yml`.
- [x] Создан `/opt/app/.env`.
- [x] Создан `/opt/app/.dockerignore`.
- [x] Собран image `misis-digital-student-support-api:local`.
- [x] Основной container `misis-digital-student-support-api` запущен через `docker compose up -d`.
- [x] Внешний порт `8080` сохранен: host `8080` -> container `8080`.
- [x] Старый `app.service` остановлен и отключен из autostart.
- [x] `app.service` сохранен как rollback-вариант.
- [x] Nginx продолжает ходить на `app:8080` без изменения proxy config.
- [x] Prometheus `up{job="supportdesk-api"}` возвращает `1`.
- [x] Promtail/Loki/Grafana продолжают получать app logs из `/var/log/app/app.log`.

## Завершено: PostgreSQL / DB / SQL-native backend

- [x] Создан отдельный сервер `db`.
- [x] `db` получил IP `192.168.85.139`.
- [x] Установлен PostgreSQL 17.
- [x] Проверен cluster `17/main`, status `online`, port `5432`.
- [x] Создана роль `supportdesk_user`.
- [x] Создана база `supportdesk`.
- [x] Настроены права/schema для `supportdesk_user`.
- [x] Создана таблица `tickets`.
- [x] Создана таблица `ticket_events`.
- [x] Созданы индексы по `status`, `(category, resource)`, `priority`, `ticket_id`, `event`, `created_at`.
- [x] Настроен `listen_addresses` для localhost и `192.168.85.139`.
- [x] Настроен `pg_hba.conf`: доступ `supportdesk_user` к `supportdesk` только с `app 192.168.85.133/32`.
- [x] Проверено `app -> db:5432` через `nc`.
- [x] Проверено подключение с `app` через `psql` под `supportdesk_user`.
- [x] Мигрированы 13 заявок из `/opt/app/tickets.json` в PostgreSQL.
- [x] Для мигрированных заявок созданы `ticket_events` с `event=imported_from_json`.
- [x] Sequence для `tickets.id` синхронизирован через `setval`.
- [x] В `/opt/app/.env` добавлены `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`.
- [x] В `requirements.txt` добавлен `psycopg2-binary`.
- [x] Backend переведен на PostgreSQL storage.
- [x] Read-path переведен на SQL: `db_list_tickets()`, `db_get_ticket()`.
- [x] Product metrics переведены на SQL: `COUNT`, `GROUP BY`, `MIN(created_at)`.
- [x] Write-path переведен на SQL-native: `INSERT ... RETURNING`, `SELECT ... FOR UPDATE`, `UPDATE ... RETURNING`.
- [x] `ticket_events` получает `ticket_created` и `ticket_status_changed`.
- [x] В `metadata_json` фиксируется `write_path=sql_native`, `storage_backend=postgresql`.
- [x] Старые helpers `load_tickets/save_tickets/next_ticket_id/active_tickets/count_by_status/ticket_age_seconds/make_list_payload` удалены из `app.py`.
- [x] `app.py` полностью почищен и структурирован: config -> validation -> DB -> metrics -> HTTP handler.
- [x] Docker image пересобран после чистки кода.
- [x] Container `misis-digital-student-support-api` запущен и `Up`.
- [x] `/v1/health` возвращает `status=ok`.
- [x] `/metrics` возвращает `supportdesk_tickets_total`.
- [x] `GET /api/v1/tickets` через `web` возвращает заявки из PostgreSQL.
- [x] `POST /api/v1/tickets` создает запись в `tickets` и событие в `ticket_events`.
- [x] Старый `/opt/app:/opt/app` volume удален; код живет в Docker image, данные — в PostgreSQL.

## Текущий следующий этап: DB observability и backups

- [ ] Добавить `db` в Ansible inventory.
- [ ] Установить node_exporter на `db`.
- [ ] Установить postgres_exporter на `db`.
- [ ] Добавить Prometheus scrape targets для `db`.
- [ ] Добавить Grafana DB panels.
- [ ] Добавить DB alerts.
- [ ] Настроить `pg_dump` backup.
- [ ] Выполнить restore test.
- [ ] Продумать хранение секретов БД вне plain `.env` в будущем.

## Далее: Telegram support bot

- [ ] Реализовать `support-bot` через long polling.
- [ ] Использовать Windows portproxy workaround для Telegram API.
- [ ] Хранить bot token в env-файле.
- [ ] Создавать/читать/закрывать tickets через тот же app API v1.
- [ ] Писать `source=telegram`.
- [ ] После появления Telegram/API-client добавить source dimension для product metrics, например `supportdesk_tickets_current_by_source{status,category,resource,priority,source}`.
- [ ] Отправлять bot logs в Loki.

## Далее: hardening и финализация

- [ ] Ограничить прямой доступ к `app:8080`.
- [ ] Ограничить прямой доступ к `db:5432`.
- [ ] Добавить Nginx hardening.
- [ ] Добавить HTTPS/self-signed cert или local CA.
- [ ] Сделать DHCP reservation или static IP.
- [ ] Автоматизировать новую архитектуру через Ansible.
- [ ] Собрать финальный README.
- [ ] Подготовить screenshots и demo сценарии.
- [ ] Сделать Proxmox snapshots.

## Future backlog

Подробный список будущих улучшений вынесен в:

```text
12_future_improvements_backlog.md
```


## Завершено: DB observability и backups

- [x] `db` добавлен в Ansible inventory как `db_nodes`.
- [x] `db_nodes` добавлен в `managed:children`.
- [x] Проверены `ansible db_nodes -m ping` и `ansible managed -m ping`.
- [x] На `db` установлен и проверен node_exporter.
- [x] Prometheus `node` target теперь показывает `5/5 up`, включая `host="db"`.
- [x] На `db` установлен `prometheus-postgres-exporter`.
- [x] Исправлен `DATA_SOURCE_NAME` для postgres_exporter; `pg_up` стал `1`.
- [x] Prometheus добавил job `postgres` для `192.168.85.139:9187`.
- [x] Prometheus показывает `postgres (1/1 up)`.
- [x] Проверены метрики `pg_up`, `pg_database_size_bytes`, `pg_stat_database_numbackends`, `pg_settings_max_connections`.
- [x] Добавлены alerts `PostgreSQLExporterDown`, `PostgreSQLDown`, `PostgreSQLTooManyConnections`.
- [x] DB alerts задеплоены через `deploy_prometheus_rules.yml`.
- [x] Alerts `PostgreSQLExporterDown` и `PostgreSQLDown` протестированы.
- [x] На `db` установлен Promtail 3.5.0.
- [x] Promtail на `db` читает `/var/log/postgresql/*.log`.
- [x] PostgreSQL logs доходят до Loki и Grafana.
- [x] В Grafana добавлен DB-блок: `DB Health`, `DB Connections`, `DB Activity`, `PostgreSQL Important Logs`.
- [x] Создан backup script `/usr/local/sbin/backup_supportdesk.sh`.
- [x] Backup script делает `pg_dump -Fc`, `.sha256`, `latest.dump` и cleanup старше 7 дней.
- [x] Исправлена проблема запуска backup из `/home/pelmel` через `cd /` в скрипте.
- [x] Добавлен `umask 027`, новые backup-файлы создаются с правами `640`.
- [x] Backup проверен через `sha256sum -c` и `pg_restore -l`.
- [x] Restore test выполнен в отдельную БД `supportdesk_restore_test`.
- [x] Counts совпали: `tickets=15`, `ticket_events=18`.
- [x] Последние события `ticket_events` совпали в рабочей и восстановленной БД.
- [x] `supportdesk_restore_test` удалена после проверки.
- [x] Созданы `backup-supportdesk.service` и `backup-supportdesk.timer`.
- [x] Timer active, следующий запуск daily `03:15 MSK`, `Persistent=true`.
- [x] `check_services.yml` обновлен: app проверяется через Docker/API endpoints, db через PostgreSQL/exporters/Promtail/backup timer.
- [x] `ansible-playbook playbooks/check_services.yml` проходит без ошибок.
- [x] Изменения зафиксированы в Git commit `23771ba Add DB observability checks and PostgreSQL alerts`.

## Следующий крупный этап: Telegram support bot

- [ ] Спроектировать minimal bot flow поверх существующего API v1.
- [ ] Выбрать runtime: systemd service или Docker container.
- [ ] Хранить bot token вне Git.
- [ ] Использовать long polling через уже проверенный outbound proxy workaround.
- [ ] Создавать заявки через `POST /v1/tickets` с `source=telegram`.
- [ ] Добавить bot logs в Loki.
- [ ] После появления второго канала вернуться к `source` dimension в product metrics.
