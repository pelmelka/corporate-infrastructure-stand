# Текущее состояние сервера db

## Назначение

`db` — отдельный сервер PostgreSQL для `MISIS_Digital Student Support`.

Роль:

- хранить состояние заявок в таблице `tickets`;
- хранить историю изменений/audit trail в таблице `ticket_events`;
- принимать подключения от `app` по PostgreSQL protocol на `5432`;
- быть будущей точкой для DB observability, backup/restore и postgres_exporter.

## Основная информация

- Hostname: `db`
- OS: Debian GNU/Linux 13 (trixie)
- IP: `192.168.85.139/24`
- Interface: `ens18`
- User: `pelmel`
- SSH: `ssh.service active/enabled`
- QEMU Guest Agent: `qemu-guest-agent.service active/running`
- PostgreSQL: `17 main`, port `5432`, status `online`

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

В `/etc/postgresql/17/main/postgresql.conf` выставлено:

```text
listen_addresses = '*'
```

Причина: после reboot PostgreSQL успевал стартовать раньше, чем DHCP поднимал IP `192.168.85.139` на `ens18`, поэтому появлялось предупреждение `could not bind IPv4 address "192.168.85.139"` и PostgreSQL слушал только localhost. После перехода на `listen_addresses='*'` повторная ошибка после reboot не возникла.

Ожидаемый bind в `ss`:

```text
0.0.0.0:5432
[::]:5432
```

Безопасность не опирается на `listen_addresses`: доступ к базе ограничен в `pg_hba.conf` только для `app` (`192.168.85.133/32`).

Проверка:

```bash
sudo ss -tulpn | grep :5432
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

## Следующие работы по db

- добавить `db` в Ansible inventory;
- установить node_exporter на `db`;
- добавить postgres_exporter;
- добавить Prometheus scrape targets;
- добавить Grafana DB panels;
- добавить DB alerts;
- настроить `pg_dump` backup;
- выполнить restore test.
