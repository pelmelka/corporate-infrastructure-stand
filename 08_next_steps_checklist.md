# Next steps checklist

Этот файл фиксирует, что уже реализовано, что считается текущим фактом проекта и какой следующий этап нужно начинать. Подробные конфиги лежат в `06_config_files_current.md`, фактическое состояние серверов — в server state files.

## Текущий статус

Последний завершенный этап: **Этап 18. Telegram support bot + bot observability**.

Текущий следующий крупный этап: **Этап 19. Security/network hardening**.

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

## Следующий крупный этап: Security/network hardening

- [ ] Ограничить прямой доступ к `app:8080` и `app:8090`, оставив нужные пути для `web`, `monitor` и troubleshooting.
- [ ] Ограничить доступ к `db:5432` только для `app` и admin-maintenance сценариев.
- [ ] Продумать firewall rules на уровне Debian/Proxmox/lab network.
- [ ] Рассмотреть HTTPS/self-signed cert или local CA на `web`.
- [ ] Причесать секреты: `.env`, `.env.bot`, DB password, backup credentials.
- [ ] Сделать DHCP reservation или static IP для стабильности targets/inventory/proxy configs.

## Далее после hardening

- [ ] Ansible automation v2 для Docker app, support-bot, Prometheus rules, Promtail configs, PostgreSQL/backup checks.
- [ ] Финальный README/demo package.
- [ ] Export Grafana dashboard JSON в Git/sources.
- [ ] Proxmox snapshots checklist.

## Future backlog

Подробный список будущих улучшений вынесен в `12_future_improvements_backlog.md`.
