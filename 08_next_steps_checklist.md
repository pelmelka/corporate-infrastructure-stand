# Next steps checklist

Этот файл фиксирует, что уже реализовано, что считается текущим фактом проекта и какой следующий этап нужно начинать. Подробные конфиги лежат в `06_config_files_current.md`, фактическое состояние серверов — в server state files.

## Текущий статус

Последний завершенный этап: **Этап 20. Ansible automation v2**.

Текущий следующий крупный этап: **Этап 21. Финальная документация, README и demo packaging**. Nginx/HTTPS/static IP/secrets improvements оставлены в backlog.

Текущая архитектура продукта:

```text
Browser -> web/Nginx -> supportdesk-api Docker container -> db/PostgreSQL
Telegram user -> Telegram API -> support-bot Docker container -> supportdesk-api -> db/PostgreSQL

app logs -> Promtail -> Loki -> Grafana
bot logs -> Promtail -> Loki -> Grafana
app/bot/db/node metrics -> Prometheus -> Grafana/Alertmanager
```

## Завершено: базовая инфраструктура

- [x] Proxmox VE работает внутри VMware Workstation.
- [x] Основная сеть: `192.168.85.0/24`.
- [x] VM: `admin`, `web`, `app`, `log`, `monitor`, `db`.
- [x] SSH-доступ между `admin` и managed nodes настроен через ключи.
- [x] Ansible inventory, `ansible.cfg`, базовые playbook-и и Git repo на `admin` созданы.

## Завершено: web/app product flow

- [x] `web` обслуживает frontend через Nginx.
- [x] Nginx reverse proxy прокидывает `/api/*` на `app:8080`.
- [x] Backend продукт переименован в `MISIS_Digital Student Support`.
- [x] API использует prefix `/v1`.
- [x] Поддержана product model v2: `category` как digital service, `resource` как service section.
- [x] Поддержаны статусы `open`, `in_progress`, `resolved`, reopen.
- [x] App logs пишутся в logfmt-стиле с `event`, `method`, `path`, `status`, `category`, `resource`, `source`, `client_ip`, `x_forwarded_for`.

## Завершено: logging stack

- [x] Loki 3.5.0 работает на `log:3100`.
- [x] Promtail работает на `web`, `app`, `db`.
- [x] Web/Nginx logs уходят в Loki.
- [x] App logs `/var/log/app/app.log` уходят в Loki с labels `host=app`, `job=app`, `service=misis-digital-student-support-api`.
- [x] Promtail на `app` добавляет `category` как Loki label для app logs.
- [x] Bot logs `/var/log/bot/support-bot.log` уходят в Loki отдельным stream-ом `job=support-bot`.
- [x] App logs panel в Grafana обновлена: скрывает `/metrics`, показывает только непустые поля, отображает `source`, `client`, `via`.

## Завершено: monitoring stack

- [x] Prometheus работает на `monitor:9090`.
- [x] Grafana работает на `monitor:3000`.
- [x] Alertmanager работает на `monitor:9093`.
- [x] node_exporter работает на managed nodes.
- [x] Grafana datasource Prometheus: `http://localhost:9090`.
- [x] Grafana datasource Loki: `http://192.168.85.135:3100`.
- [x] Dashboard `Infrastructure Overview` содержит infrastructure, product, HTTP/API, DB и Telegram bot observability blocks.

## Завершено: product observability

- [x] Backend exports `supportdesk_tickets_total`, `supportdesk_tickets_current{status,category,resource,priority}`, `supportdesk_active_ticket_age_seconds_max{category,resource,priority}`.
- [x] Product panels показывают active tickets по category/resource/priority и age critical tickets.
- [x] Product alerts добавлены: `SupportDeskTooManyTicketsForResource`, `SupportDeskCriticalTicketsOpen`, `SupportDeskOldCriticalTicket`.
- [x] Source-based product metrics пока сознательно не добавлены: bot observability реализована отдельно и не дублирует product layer.

## Завершено: HTTP/API observability

- [x] Backend exports `supportdesk_http_requests_total{method,route,status_code}`.
- [x] Backend exports request duration histogram `supportdesk_http_request_duration_seconds_*`.
- [x] Promtail на `web` формирует `promtail_custom_nginx_http_responses_total{status_code}`.
- [x] Alerts добавлены: `SupportDeskHigh4xxRate`, `SupportDeskHigh5xxRate`, `SupportDeskHighLatency`, `Nginx502Spike`.
- [x] HTTP/API panels добавлены в Grafana.

## Завершено: Dockerization

- [x] Docker Engine и Docker Compose plugin установлены на `app`.
- [x] `supportdesk-api` запускается как container `misis-digital-student-support-api`.
- [x] Host `app:8080` проброшен в container `8080`.
- [x] Старый `app.service` отключен и оставлен только как rollback artifact.
- [x] Nginx и Prometheus внешние контракты не менялись: `web -> app:8080`, `monitor -> app:8080/metrics`.
- [x] После PostgreSQL migration старый `/opt/app:/opt/app` volume убран; код живет в image, состояние — в PostgreSQL.

## Завершено: PostgreSQL-backed storage

- [x] Создан сервер `db` с IP `192.168.85.139`.
- [x] PostgreSQL 17 работает на `db:5432`.
- [x] Созданы database `supportdesk`, role `supportdesk_user`, tables `tickets` и `ticket_events`.
- [x] `pg_hba.conf` разрешает `supportdesk_user` доступ к `supportdesk` только с `app 192.168.85.133/32`.
- [x] `listen_addresses='*'` применен, чтобы PostgreSQL корректно поднимался после reboot при DHCP.
- [x] 13 legacy-заявок мигрированы из `/opt/app/tickets.json`.
- [x] Backend полностью переведен на SQL-native read/write path.
- [x] `ticket_events` фиксирует `imported_from_json`, `ticket_created`, `ticket_status_changed`.
- [x] Старый `tickets.json` больше не является source of truth.

## Завершено: DB observability и backups

- [x] `db` добавлен в Ansible inventory.
- [x] node_exporter работает на `db:9100`.
- [x] postgres_exporter работает на `db:9187`.
- [x] Prometheus jobs `node` и `postgres` видят `db`.
- [x] PostgreSQL logs уходят в Loki как `{host="db", job="postgresql"}`.
- [x] DB panels добавлены: `DB Health`, `DB Connections`, `DB Activity`, `PostgreSQL Important Logs`.
- [x] DB alerts добавлены: `PostgreSQLExporterDown`, `PostgreSQLDown`, `PostgreSQLTooManyConnections`.
- [x] Backup script `/usr/local/sbin/backup_supportdesk.sh` делает `pg_dump -Fc`, `.sha256`, `latest.dump`, retention 7 days.
- [x] `backup-supportdesk.service` и `backup-supportdesk.timer` созданы; timer daily `03:15 MSK`, `Persistent=true`.
- [x] Restore test в `supportdesk_restore_test` выполнен и проверен.
- [x] `check_services.yml` обновлен под Docker/API/PostgreSQL/exporters/backup timer.

## Завершено: Telegram support bot

- [x] Создан Telegram bot `@misis_digital_support_bot`.
- [x] `support-bot` работает через long polling, без webhook и без публикации VM в интернет.
- [x] Outbound Telegram API доступ идет через Windows portproxy/XRay workaround.
- [x] Bot token хранится в `/opt/app/.env.bot`, не фиксируется в sources/Git/image/logs.
- [x] `support-bot` запускается как Docker Compose service на `app`.
- [x] `/start`, `/help`, `/new`, `/tickets`, `/resolve` работают.
- [x] `/new` создает заявку через API v1 с `source=telegram`.
- [x] `/tickets` показывает active tickets с пагинацией.
- [x] `/resolve` закрывает active tickets через API v1 с `source=telegram`.
- [x] UI показывает разные смыслы: `Создана через: <tickets.source>` и `Закрыта через: telegram`.
- [x] HTML-разметка и `html.escape()` защищают сообщения от поломки спецсимволами.
- [x] `ALLOWED_TELEGRAM_USER_IDS` поддержан, но сейчас пустой для открытого lab/demo-доступа.

## Завершено: Telegram bot observability

- [x] Bot logs пишутся в `/var/log/bot/support-bot.log`.
- [x] Promtail читает `/var/log/bot/*.log` отдельным `job=support-bot`.
- [x] Loki stream: `{host="app", job="support-bot", service="misis-digital-support-bot"}`.
- [x] `support-bot` exports native metrics на `:8090/metrics`.
- [x] Prometheus job `support-bot` добавлен; target `192.168.85.133:8090` UP.
- [x] `*_created` auto metrics отключены через `disable_created_metrics()`.
- [x] Метрики добавлены: `support_bot_info`, `support_bot_start_time_seconds`, `support_bot_actions_total`, `support_bot_api_requests_total`, `support_bot_api_request_duration_seconds_*`, `support_bot_errors_total`.
- [x] Alert rules добавлены и проверены: `SupportBotDown`, `SupportBotBackendErrors`, `SupportBotErrorsDetected`.
- [x] `SupportBotDown` протестирован остановкой `support-bot`.
- [x] `SupportBotBackendErrors` протестирован остановкой `supportdesk-api` и реальным Telegram-действием.
- [x] `SupportBotErrorsDetected` исключает `backend_error`, чтобы не дублировать backend dependency alert.
- [x] Grafana row `Telegram Bot Observability` добавлен: alerts, runtime, API dependency, latency by endpoint, requests by endpoint/status, actions, recent logs, error logs.

## Завершено: Security/network hardening

- [x] Составлена полная карта сетевых потоков и access matrix.
- [x] UFW установлен и включен на `db`, `web`, `log`, `monitor`, `app`.
- [x] На hardened-узлах применена модель `default deny incoming`, `default allow outgoing`.
- [x] `admin` сохранил SSH/Ansible-доступ ко всем узлам.
- [x] `db:5432` доступен только `app` и `admin`.
- [x] `db:9100` и `db:9187` доступны только `monitor` и `admin`.
- [x] `web:80` оставлен для Windows/browser и admin diagnostics.
- [x] `web:9080` и `web:9100` доступны только `monitor` и `admin`.
- [x] `log:3100` доступен только `web`, `app`, `db`, `monitor`, `admin`.
- [x] `log:9095` не открыт внешним узлам.
- [x] `monitor:3000`, `monitor:9090`, `monitor:9093` доступны только Windows host `192.168.85.1` и `admin`.
- [x] Лишний доступ `web -> monitor:3000/9090/9093` закрыт.
- [x] `app` host-порты защищены UFW.
- [x] Docker published ports `app:8080` и `app:8090` ограничены через `DOCKER-USER`.
- [x] `web -> app:8080`, `monitor -> app:8080/8090/9100`, `admin -> app:8080/8090` работают.
- [x] `db -> app:8080/8090` и Windows/browser direct access к `app:8080/8090` закрыты.
- [x] Создан `/usr/local/sbin/app-docker-user-firewall.sh` на `app`.
- [x] Создан и включен `app-docker-user-firewall.service` на `app`.
- [x] После reboot `app` подтверждено: `app-docker-user-firewall.service enabled/active`, allow/deny правила сохраняются.
- [x] End-to-end путь `Browser -> web -> app -> db` работает после hardening.
- [x] Prometheus targets и Grafana/Loki observability не сломаны.


## Завершено: Ansible automation v2

- [x] `admin` стал полноценным Ansible control node для deploy/check/audit операций.
- [x] Добавлен `roles_path = ./roles` в `ansible.cfg`.
- [x] Созданы `inventory/group_vars`: `all`, `web_nodes`, `app_nodes`, `log_nodes`, `monitor_nodes`, `db_nodes`.
- [x] Реализованы роли: `common`, `node_exporter`, `app_compose_project`, `docker_compose_service`, `nginx_frontend`, `promtail`, `prometheus`, `postgres_exporter`, `postgres_backup`.
- [x] Реализованы playbook-и: `apply_baseline.yml`, `check.yml`, `check_app_compose_project.yml`, `deploy_app.yml`, `deploy_bot.yml`, `deploy_nginx_frontend.yml`, `deploy_promtail.yml`, `deploy_prometheus.yml`, `deploy_postgres_exporter.yml`, `deploy_postgres_backup.yml`, `run_db_backup.yml`, `network_audit.yml`.
- [x] `supportdesk-api` и `support-bot` деплоятся через одну переиспользуемую роль `docker_compose_service` с разными переменными.
- [x] Nginx frontend/reverse proxy управляется ролью `nginx_frontend` с `nginx -t` перед reload.
- [x] Promtail configs на `web/app/db` управляются одной ролью `promtail`, права приведены к `root:promtail 0640`.
- [x] Prometheus config/rules управляются ролью `prometheus`, валидация выполняется через `promtool`, targets проверяются через JSON API.
- [x] PostgreSQL exporter управляется ролью `postgres_exporter`.
- [x] PostgreSQL backup automation управляется ролью `postgres_backup`; ручной запуск вынесен в `run_db_backup.yml` через `include_role tasks_from=run_backup`.
- [x] Backup canonical path синхронизирован: `/var/backups/postgresql/supportdesk`.
- [x] Backup script права исправлены на `root:postgres 0750`; `latest.dump` проверяется с `follow: true`.
- [x] Добавлен audit-only `network_audit.yml`, который собирает network/firewall/Docker/connectivity reports без изменения firewall rules.
- [x] Финальный `check.yml` после этапа: `failed=0`, `changed=0` на всех узлах.
- [x] Git commit: `03ae409 Add Ansible automation v2 roles and audit playbooks`.

## Далее после Ansible automation v2

- [ ] Финальный README/demo package.
- [ ] Export Grafana dashboard JSON в Git/sources.
- [ ] Подготовить screenshots/dashboard export для README.
- [ ] Подготовить demo сценарии: web/API, Telegram bot, alerts, logs, metrics, backup/restore, network audit.
- [ ] Proxmox snapshots checklist.

## Future backlog

Подробный список будущих улучшений вынесен в `12_future_improvements_backlog.md`.
