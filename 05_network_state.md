# Сеть проекта

## Общая схема

Проект работает внутри Proxmox VE, который установлен как VM внутри VMware.

Основная сеть сейчас — VMware NAT:

```text
192.168.85.0/24
```

Proxmox и все VM сейчас находятся в этой сети через bridge `vmbr0`.

## IP-адреса

| Сервер | IP | Назначение | Статус IP |
|---|---:|---|---|
| Proxmox | 192.168.85.128 | гипервизор | зафиксирован на Proxmox |
| admin | 192.168.85.129 | control node | DHCP сейчас держится стабильно |
| web | 192.168.85.131 | nginx frontend/reverse proxy | DHCP сейчас держится стабильно |
| app | 192.168.85.133 | Dockerized backend API | DHCP сейчас держится стабильно |
| log | 192.168.85.135 | Loki logging | DHCP сейчас держится стабильно |
| monitor | 192.168.85.137 | Prometheus/Grafana/Alertmanager | DHCP сейчас держится стабильно |
| db | 192.168.85.139 | PostgreSQL storage | DHCP сейчас держится стабильно |

## Gateway/DNS

Для VM:

```text
network: 192.168.85.0/24
gateway: 192.168.85.2
```

Windows VMware NAT adapter:

```text
VMnet8 host adapter: 192.168.85.1
```

## Важное замечание про DHCP/static

Сейчас VM получают IP через DHCP VMware NAT. Для воспроизводимости позже нужно сделать DHCP reservation по MAC или статические IP внутри Debian.

Это особенно важно для:

```text
Promtail clients
Prometheus targets
Grafana datasources
Ansible inventory
Nginx reverse proxy
app -> db PostgreSQL
future Telegram bot
```

## Порты

```text
Proxmox: 8006/tcp
admin:   22/tcp
web:     22/tcp, 80/tcp, 9080/tcp Promtail, 9100/tcp node_exporter
app:     22/tcp, 8080/tcp MISIS_Digital Student Support API, 9080/tcp Promtail, 9100/tcp node_exporter
log:     22/tcp, 3100/tcp Loki HTTP, 9095/tcp Loki gRPC, 9100/tcp node_exporter
monitor: 22/tcp, 3000/tcp Grafana, 9090/tcp Prometheus, 9093/tcp Alertmanager, 9100/tcp node_exporter
db:      22/tcp, 5432/tcp PostgreSQL, 9080/tcp Promtail, 9100/tcp node_exporter, 9187/tcp postgres_exporter
Windows host: 10802/tcp portproxy для будущего Telegram bot outbound proxy
```

## Реализованные network flows

### Web/App/API

```text
Browser/Windows -> web 192.168.85.131:80
web/Nginx -> app 192.168.85.133:8080
```

Reverse proxy:

```text
/api/* -> http://192.168.85.133:8080/
```

После Dockerization внешний endpoint не изменился: `app:8080` обслуживает Docker container `misis-digital-student-support-api`.

### App/DB

```text
app 192.168.85.133 -> db 192.168.85.139:5432 PostgreSQL
```

PostgreSQL на `db` слушает все адреса через `listen_addresses='*'`:

```text
0.0.0.0:5432
[::]:5432
```

Так сделано из-за DHCP: после reboot конкретный IP `192.168.85.139` может появиться на интерфейсе чуть позже старта PostgreSQL. Bind на `*` убирает эту race condition, а доступ всё равно ограничивается не этим параметром, а `pg_hba.conf`.

В `pg_hba.conf` доступ к БД `supportdesk` для роли `supportdesk_user` разрешен только с `app`:

```text
host supportdesk supportdesk_user 192.168.85.133/32 scram-sha-256
```

Проверено с `app`:

```bash
nc -vzn 192.168.85.139 5432
PGPASSWORD='<redacted>' psql -h 192.168.85.139 -U supportdesk_user -d supportdesk -P pager=off -c "SELECT current_user, current_database(), inet_server_addr(), inet_client_addr();"
```

Результат:

```text
server_addr = 192.168.85.139
client_addr = 192.168.85.133
```

### Logging

```text
web Promtail -> log 192.168.85.135:3100 Loki
app Promtail -> log 192.168.85.135:3100 Loki
db Promtail -> log 192.168.85.135:3100 Loki
```

### Monitoring

```text
monitor/Prometheus -> web:9100 node_exporter
monitor/Prometheus -> app:9100 node_exporter
monitor/Prometheus -> log:9100 node_exporter
monitor/Prometheus -> db:9100 node_exporter
monitor/Prometheus -> monitor:9100 node_exporter
monitor/Prometheus -> app:8080/metrics supportdesk-api product/HTTP metrics
monitor/Prometheus -> web:9080/metrics Promtail custom nginx metrics
monitor/Prometheus -> db:9187/metrics postgres_exporter
Prometheus -> Alertmanager localhost:9093
Grafana -> Prometheus localhost:9090
Grafana -> Loki 192.168.85.135:3100
```

DB-specific metrics добавлены: `node_exporter` на `db`, `postgres_exporter` на `db`, Prometheus scrape job `postgres`, Grafana DB panels и DB alerts.

### Admin/Ansible management

Реализовано:

```text
admin/Ansible -> web:22 SSH
admin/Ansible -> app:22 SSH
admin/Ansible -> log:22 SSH
admin/Ansible -> monitor:22 SSH
admin/Ansible -> db:22 SSH
```

`db` добавлен в Ansible inventory и `check_services.yml`.

## Telegram bot outbound proxy workaround

Для будущего Telegram support bot проверен исходящий доступ с VM `app` к Telegram API через Windows proxy.

Текущий workaround:

```text
Windows portproxy:
192.168.85.1:10802 -> 127.0.0.1:10801
```

Будущий env для `support-bot.service`:

```bash
HTTP_PROXY=http://192.168.85.1:10802
HTTPS_PROXY=http://192.168.85.1:10802
NO_PROXY=localhost,127.0.0.1,192.168.85.0/24
```

Webhook для Telegram в текущей NAT-инфраструктуре не выбирается. Реалистичный вариант: long polling + outbound proxy.

## Future network/security changes

Планируется:

```text
web -> app только через разрешенный reverse proxy path
app -> db только к PostgreSQL
admin -> все узлы по SSH/Ansible
monitor -> metrics endpoints
```

Future hardening:

- ограничить прямой доступ к `app:8080`;
- ограничить доступ к `db:5432` только для `app`/admin-maintenance;
- добавить HTTPS termination на `web`;
- добавить DHCP reservation/static IP.

## VPN issue

При включенном VPNKA/VPN доступ к Proxmox `https://192.168.85.128:8006` с Windows не работает. Практическое решение: для работы с Proxmox локально отключать VPN.
