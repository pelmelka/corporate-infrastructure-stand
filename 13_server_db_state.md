# Текущее состояние сервера db

## Назначение

`db` — отдельный сервер PostgreSQL для `MISIS_Digital Student Support`.

Роль:

- хранить состояние заявок в таблице `tickets`;
- хранить историю изменений/audit trail в таблице `ticket_events`;
- принимать подключения от `app` по PostgreSQL protocol на `5432`;
- отдавать PostgreSQL metrics через postgres_exporter;
- отправлять PostgreSQL logs в Loki через Promtail;
- создавать daily pg_dump backup-и;
- иметь проверенный restore test как доказательство восстановимости.

## Основная информация

- Hostname: `db`
- OS: Debian GNU/Linux 13 (trixie)
- IP: `192.168.85.139/24`
- Interface: `ens18`
- User: `pelmel`
- SSH: `ssh.service active/enabled`
- QEMU Guest Agent: `qemu-guest-agent.service active/running`
- PostgreSQL: `17 main`, port `5432`, status `online`
- node_exporter: `prometheus-node-exporter.service active/enabled`, port `9100`
- postgres_exporter: `prometheus-postgres-exporter.service active/enabled`, port `9187`
- Promtail: `promtail.service active/enabled`, port `9080`
- Backup timer: `backup-supportdesk.timer active`, daily `03:15 MSK`

## PostgreSQL cluster

Проверка:

```bash
pg_lsclusters
```

Текущее состояние:

```text
Ver Cluster Port Status Owner    Data directory              Log file
17  main    5432 online postgres /var/lib/postgresql/17/main /var/log/postgresql/postgresql-17-main.log
```

`postgresql.service` на Debian может отображаться как `active (exited)`, потому что это umbrella-service. Фактическое состояние cluster проверяется через `pg_lsclusters`.

Перезапуск cluster:

```bash
sudo pg_ctlcluster 17 main restart
```

## Network/listen

PostgreSQL слушает:

```text
127.0.0.1:5432
192.168.85.139:5432
[::1]:5432
```

Проверка:

```bash
sudo ss -tulpn | grep :5432
```

## Observability ports

Текущие observability endpoints на `db`:

```text
:9100/metrics  node_exporter, системные метрики Linux-ноды
:9187/metrics  postgres_exporter, метрики PostgreSQL
:9080/metrics  Promtail self-metrics
```

Проверки:

```bash
curl -s http://localhost:9187/metrics | grep -E '^(pg_up|pg_database_size_bytes|pg_stat_database_numbackends|pg_settings_max_connections)'
curl -s http://localhost:9080/metrics | head
```

Подтверждено:

```text
pg_up 1
pg_database_size_bytes{datname="supportdesk"} ...
pg_stat_database_numbackends{datname="supportdesk"} ...
pg_settings_max_connections{server="localhost:5432"} 100
```


## Access control

База приложения:

```text
database: supportdesk
role: supportdesk_user
schema: public
```

`pg_hba.conf` разрешает подключение роли `supportdesk_user` к базе `supportdesk` только с `app`:

```text
host supportdesk supportdesk_user 192.168.85.133/32 scram-sha-256
```

Проверено с `app`:

```bash
PGPASSWORD='<redacted>' psql -h 192.168.85.139 -U supportdesk_user -d supportdesk -P pager=off -c "SELECT current_user, current_database(), inet_server_addr(), inet_client_addr();"
```

Ожидаемый результат:

```text
supportdesk_user | supportdesk | 192.168.85.139 | 192.168.85.133
```

## Schema

Таблицы:

```text
public.tickets
public.ticket_events
```

`tickets` хранит текущее состояние заявки.

`ticket_events` хранит историю событий:

```text
imported_from_json
ticket_created
ticket_status_changed
```

Связь:

```text
ticket_events.ticket_id -> tickets.id ON DELETE CASCADE
```

## Индексы

Созданы индексы:

```text
tickets_pkey                       PRIMARY KEY по tickets(id)
ticket_events_pkey                 PRIMARY KEY по ticket_events(id)
idx_tickets_status                 tickets(status)
idx_tickets_category_resource      tickets(category, resource)
idx_tickets_priority               tickets(priority)
idx_ticket_events_ticket_id        ticket_events(ticket_id)
idx_ticket_events_event            ticket_events(event)
idx_ticket_events_created_at       ticket_events(created_at)
```

После перевода read-path на SQL подтверждено, что PostgreSQL может использовать `idx_tickets_status` для active-фильтра:

```text
Bitmap Index Scan on idx_tickets_status
```

## Миграция данных

Старый источник:

```text
app:/opt/app/tickets.json
```

Миграция:

- 13 заявок перенесены в `tickets`;
- для них созданы события `imported_from_json` в `ticket_events`;
- sequence для `tickets.id` синхронизирован через `setval`, чтобы новые заявки получали корректные id.

После переключения backend:

```text
PostgreSQL tickets count увеличивается при POST.
/opt/app/tickets.json остается legacy artifact и больше не является source of truth.
```

Проверенный пример после финальной чистки `app.py`:

```text
id=15 category=lk-misis resource=service-requests status=open source=web
```

Последнее событие:

```text
event=ticket_created
new_status=open
source=web
metadata_json={"write_path": "sql_native", "storage_backend": "postgresql"}
```

## PostgreSQL exporter

Сервис:

```text
prometheus-postgres-exporter.service
```

Пакетный unit использует:

```text
EnvironmentFile=/etc/default/prometheus-postgres-exporter
ExecStart=/usr/bin/prometheus-postgres-exporter $ARGS
```

В `/etc/default/prometheus-postgres-exporter` задан DSN для подключения к локальной PostgreSQL:

```text
DATA_SOURCE_NAME=postgresql://postgres_exporter:<redacted>@localhost:5432/postgres?sslmode=disable
```

Пароль не фиксируется в sources. Роль `postgres_exporter` создана только для чтения метрик. Ошибка `pg_up 0` была исправлена после корректного заполнения `DATA_SOURCE_NAME` и перезапуска exporter-а.

Prometheus target:

```text
job="postgres"
instance="192.168.85.139:9187"
host="db"
service="postgresql"
env="lab"
```

## PostgreSQL logs via Promtail

Файл логов PostgreSQL:

```text
/var/log/postgresql/postgresql-17-main.log
```

Права:

```text
postgres:adm 640
```

Пользователь `promtail` добавлен в группу `adm`, поэтому может читать PostgreSQL log file.

Promtail config:

```text
/etc/promtail/config.yml
```

Loki stream:

```logql
{host="db", job="postgresql"}
```

Important logs panel использует фильтр:

```logql
{host="db", job="postgresql"}
|~ "(ERROR|FATAL|PANIC|shutting down|ready to accept connections|starting PostgreSQL|terminating connection|deadlock)"
```

Тест доставки logs выполнен безопасной ошибкой:

```bash
sudo -u postgres psql -d supportdesk -c "SELECT * FROM promtail_db_log_test_table;" || true
```

Ожидаемая строка дошла до Loki/Grafana:

```text
ERROR: relation "promtail_db_log_test_table" does not exist
STATEMENT: SELECT * FROM promtail_db_log_test_table;
```

## Backups

Backup directory:

```text
/var/backups/postgresql/supportdesk
owner: postgres:postgres
mode: 750
```

Backup script:

```text
/usr/local/sbin/backup_supportdesk.sh
```

Скрипт:

- использует `set -euo pipefail`;
- задает `umask 027`;
- делает `cd /`, чтобы запуск не зависел от текущей директории пользователя;
- создает `pg_dump -Fc supportdesk`;
- проверяет, что dump не пустой через `test -s`;
- создает `.sha256` checksum;
- обновляет `latest.dump` symlink;
- удаляет dump/checksum старше 7 дней.

Systemd automation:

```text
backup-supportdesk.service  Type=oneshot, User=postgres, WorkingDirectory=/
backup-supportdesk.timer    OnCalendar=*-*-* 03:15:00, Persistent=true
```

Проверено вручную:

```bash
sudo systemctl start backup-supportdesk.service
systemctl status backup-supportdesk.service --no-pager
sudo journalctl -u backup-supportdesk.service -n 50 --no-pager
```

Подтверждено:

```text
Backup created: /var/backups/postgresql/supportdesk/supportdesk_YYYYMMDD-HHMMSS.dump
Checksum created: ...dump.sha256
Latest link: /var/backups/postgresql/supportdesk/latest.dump
status=0/SUCCESS
```

Новые backup-файлы создаются с правами:

```text
-rw-r----- postgres postgres ... supportdesk_*.dump
-rw-r----- postgres postgres ... supportdesk_*.dump.sha256
```

## Restore test

Restore test выполнен в отдельную БД:

```text
supportdesk_restore_test
```

Проверено:

```text
рабочая supportdesk:            tickets=15, ticket_events=18
supportdesk_restore_test:       tickets=15, ticket_events=18
последние ticket_events совпали
после проверки supportdesk_restore_test удалена
```

Команды проверки:

```bash
sudo -u postgres bash -c 'sha256sum -c /var/backups/postgresql/supportdesk/*.sha256'
sudo -u postgres bash -c 'pg_restore -l /var/backups/postgresql/supportdesk/latest.dump | head -n 40'
sudo -u postgres dropdb --if-exists supportdesk_restore_test
sudo -u postgres createdb supportdesk_restore_test
sudo -u postgres pg_restore --clean --if-exists -d supportdesk_restore_test /var/backups/postgresql/supportdesk/latest.dump
```

## Базовые команды

Проверить cluster:

```bash
pg_lsclusters
```

Проверить порт:

```bash
sudo ss -tulpn | grep :5432
```

Показать роли:

```bash
sudo -u postgres psql -P pager=off -c "\du"
```

Показать базы:

```bash
sudo -u postgres psql -P pager=off -c "\l"
```

Показать таблицы:

```bash
sudo -u postgres psql -P pager=off -d supportdesk -c "\dt"
```

Показать структуру:

```bash
sudo -u postgres psql -P pager=off -d supportdesk -c "\d tickets"
sudo -u postgres psql -P pager=off -d supportdesk -c "\d ticket_events"
```

Проверить count:

```bash
PGPASSWORD='<redacted>' psql -h 192.168.85.139 -U supportdesk_user -d supportdesk -P pager=off -c "SELECT count(*) FROM tickets;"
```

Проверить события:

```bash
PGPASSWORD='<redacted>' psql -h 192.168.85.139 -U supportdesk_user -d supportdesk -P pager=off -c "SELECT event, count(*) FROM ticket_events GROUP BY event ORDER BY event;"
```

## Текущий статус db

`db` считается готовым database node для текущего этапа:

- PostgreSQL 17 хранит `supportdesk` data;
- `app` использует PostgreSQL как source of truth;
- node_exporter дает системные метрики `db`;
- postgres_exporter дает PostgreSQL metrics;
- Prometheus видит `node` target `host="db"` и `postgres` target `host="db"`;
- Promtail отправляет PostgreSQL logs в Loki;
- Grafana показывает DB Health, DB Connections, DB Activity и PostgreSQL Important Logs;
- DB alerts добавлены и протестированы;
- daily pg_dump backup автоматизирован через systemd timer;
- restore test доказал, что backup реально восстанавливается.
