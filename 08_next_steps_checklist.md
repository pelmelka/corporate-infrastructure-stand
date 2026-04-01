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
- [x] `hello-world` container успешно запущен для проверки Docker daemon/client/image pull.
- [x] Создан `/opt/app/Dockerfile` для `misis-digital-student-support-api`.
- [x] Создан `/opt/app/requirements.txt` с `prometheus_client`.
- [x] Создан `/opt/app/docker-compose.yml`.
- [x] Создан `/opt/app/.env` для APP_UID/APP_GID build args.
- [x] Создан `/opt/app/.dockerignore`.
- [x] Backup-и перенесены в `/opt/app/backups/`.
- [x] Собран image `misis-digital-student-support-api:local`.
- [x] Smoke-test container на `18080:8080` успешно прошел.
- [x] Основной container `misis-digital-student-support-api` запущен через `docker compose up -d`.
- [x] Внешний порт `8080` сохранен: host `8080` -> container `8080`.
- [x] Старый `app.service` остановлен и отключен из autostart.
- [x] `app.service` сохранен как rollback-вариант.
- [x] `localhost:8080/v1/health` возвращает `status=ok`.
- [x] `localhost:8080/metrics` отдает product и HTTP/API metrics.
- [x] Nginx продолжает ходить на `app:8080` без изменения proxy config.
- [x] `POST /api/v1/tickets` работает после Dockerization.
- [x] `PATCH /api/v1/tickets/<id>/status` работает после Dockerization.
- [x] Prometheus `up{job="supportdesk-api"}` возвращает `1`.
- [x] Promtail/Loki/Grafana продолжают получать app logs из `/var/log/app/app.log`.
- [x] Зафиксирован временный workaround `/opt/app:/opt/app` до PostgreSQL stage.
- [ ] Позже контейнеризировать `support-bot`.

## Текущий следующий этап: PostgreSQL / DB

## Далее: PostgreSQL / DB

- [ ] Создать отдельную VM `db`.
- [ ] Установить PostgreSQL.
- [ ] Создать DB/user/schema.
- [ ] Перевести app storage с `/opt/app/tickets.json` на PostgreSQL.
- [ ] Добавить таблицу `ticket_events` или аналогичный event storage.
- [ ] После event storage добавить `supportdesk_tickets_created_total{category,resource,priority,source}`.
- [ ] После event storage добавить `supportdesk_tickets_resolved_total{category,resource,priority,source}`.
- [ ] После event storage добавить `supportdesk_ticket_resolution_duration_seconds_*`.
- [ ] Добавить DB env-файл для app.
- [ ] Добавить postgres_exporter.
- [ ] Добавить DB alerts.
- [ ] Добавить backup/restore через `pg_dump`.

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
