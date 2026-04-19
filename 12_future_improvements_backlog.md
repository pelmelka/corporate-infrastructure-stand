# Future improvements backlog

Этот файл хранит только будущие идеи и отложенные улучшения. Фактическое состояние уже реализованных этапов фиксируется в `00_project_overview_and_roadmap.md`, server state files и `06_config_files_current.md`.

## Security / network hardening follow-ups

Базовый firewall/network hardening завершен на этапе 19: UFW включен на `web/app/log/monitor/db`, внутренние порты ограничены allowlist-правилами, а Docker published ports `app:8080` и `app:8090` защищены через `DOCKER-USER` + systemd persistence.

Оставшиеся идеи:

```text
добавить Nginx security headers;
добавить client_max_body_size;
добавить proxy_connect_timeout / proxy_send_timeout / proxy_read_timeout;
добавить rate limiting для /api/;
рассмотреть HTTPS/self-signed cert или local CA;
сделать DHCP reservation или static IP для всех VM;
автоматизировать firewall rules через Ansible role/playbook;
проверить и формализовать права 600/640 на .env/.env.bot/backup credentials;
рассмотреть полный outbound filtering отдельным этапом;
рассмотреть Proxmox firewall, VLAN или отдельные подсети.
```

Не делать без отдельного плана:

```text
массовое изменение firewall rules на всех узлах за один запуск;
закрытие outbound по умолчанию;
публикация web в интернет без отдельного HTTPS/access-control плана;
изменение Docker Compose port bindings без проверки web/monitor/admin flows.
```


## Secrets management

Сейчас секреты хранятся в `.env` и `.env.bot` на `app`, не фиксируются в sources и исключены через `.dockerignore`. Это приемлемо для lab, но есть что улучшить.

Будущие варианты:

```text
Ansible Vault для DB password и Telegram token;
systemd EnvironmentFile с ограниченными правами;
Docker secrets, если будет переход на Swarm/Compose secrets model;
отдельный secrets handoff process перед demo.
```

Перед публичной демонстрацией решить, оставлять ли bot открытым. Если нет — включить:

```env
ALLOWED_TELEGRAM_USER_IDS=<allowed_user_id_1>,<allowed_user_id_2>
```

## Grafana/dashboard lifecycle

Dashboard сейчас собран вручную в Grafana и описан в sources. Для воспроизводимости позже стоит экспортировать JSON.

Идеи:

```text
export Infrastructure Overview dashboard JSON;
хранить JSON в Git/control-node files;
описать import procedure;
позже рассмотреть Grafana provisioning.
```

## Ansible automation v2 follow-ups

Stage 20 Ansible automation v2 is completed. Remaining optional improvements:

```text
Ansible Vault for secrets instead of manual .env handling;
CI lint/syntax-check for playbooks;
ansible-lint adoption;
Molecule-style role tests if project grows;
Grafana dashboard provisioning/export through Ansible;
Loki role if we want full logging stack config management;
firewall apply role only if out-of-band access, rollback plan and serial validation are added.
```

Current decision: firewall changes are intentionally not automated; `network_audit.yml` provides audit/reporting and critical flow validation.

## Logging improvements

Текущее состояние:

```text
app logs: /var/log/app/app.log -> Promtail -> Loki
bot logs: /var/log/bot/support-bot.log -> Promtail -> Loki
postgres logs: /var/log/postgresql/*.log -> Promtail -> Loki
```

Будущие улучшения:

```text
перейти от file logs к stdout/stderr + container log collector;
сделать единый structured JSON/logfmt logging guideline;
разделить App logs dashboard на App activity logs и Ticket change events, если текущая панель станет шумной;
не выносить resource/ticket_id/user_id в Loki labels без явной необходимости, чтобы не раздувать cardinality.
```

## Product observability improvements

Текущая product observability уже покрывает active tickets по status/category/resource/priority и age critical tickets. На этапе Telegram bot source-based product metrics сознательно не добавлялись, чтобы не дублировать слой продукта.

Вернуться к source dimension стоит, если появится задача сравнивать каналы `web/api/telegram`.

Возможные метрики:

```text
supportdesk_tickets_current_by_source{status,category,resource,priority,source}
supportdesk_tickets_created_total{category,resource,priority,source}
supportdesk_tickets_resolved_total{category,resource,priority,source}
```

Возможные alerts:

```text
SupportDeskTicketSpike
SupportDeskCreatedOutpacesResolved
SupportDeskNoResolutionsForActiveBacklog
SupportDeskTelegramCriticalTicketsOpen
```

## SLA / duration metrics

После PostgreSQL и `ticket_events` можно корректно считать duration от создания до закрытия. Пока это отложено: уже есть простая метрика age active critical tickets.

Возможные метрики:

```text
supportdesk_ticket_resolution_duration_seconds_bucket{category,resource,priority,source,le}
supportdesk_ticket_resolution_duration_seconds_sum{category,resource,priority,source}
supportdesk_ticket_resolution_duration_seconds_count{category,resource,priority,source}
```

Возможные alerts:

```text
SupportDeskSlowResolution
SupportDeskSlaViolationRisk
```

## DB observability and backups improvements

Текущее состояние уже готово: postgres_exporter, DB panels, DB alerts, pg_dump backups, checksum, latest symlink, retention 7 days, restore test.

Будущие улучшения:

```text
backup freshness alert через textfile collector или custom exporter;
backup size / last successful backup panel;
remote storage для dumps;
weekly/monthly tiered retention;
automated restore test playbook;
locks / slow queries / cache hit ratio / WAL/checkpoints panels;
connection pooling, если backend runtime усложнится.
```

## Docker/runtime improvements

Текущее состояние:

```text
supportdesk-api container на app:8080;
support-bot container на app:8090 metrics;
code живет в Docker images;
state живет в PostgreSQL;
file logs пока сохраняются через host volumes.
```

Будущие улучшения:

```text
registry/image tags после появления CI/CD или Ansible deploy v2;
healthcheck в docker-compose для supportdesk-api и support-bot;
restart/rollback procedure через tagged images;
stdout/stderr logging + collector;
compose profiles или отдельные compose files для dev/demo.
```

## Final README/demo packaging

Что собрать к финалу:

```text
архитектура и data flows;
IP/порты/сервисы;
команды проверки;
LogQL examples;
PromQL examples;
alerts list;
dashboard screenshots;
demo scripts;
troubleshooting scenarios;
backup/restore scenario;
Proxmox snapshots checklist.
```
