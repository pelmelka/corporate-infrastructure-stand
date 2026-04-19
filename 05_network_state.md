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
support-bot outbound proxy and bot metrics endpoint
```

## Порты

```text
Proxmox: 8006/tcp
admin:   22/tcp
web:     22/tcp, 80/tcp, 9080/tcp Promtail, 9100/tcp node_exporter
app:     22/tcp, 8080/tcp MISIS_Digital Student Support API, 8090/tcp support-bot metrics, 9080/tcp Promtail, 9100/tcp node_exporter
log:     22/tcp, 3100/tcp Loki HTTP, 9095/tcp Loki gRPC, 9100/tcp node_exporter
monitor: 22/tcp, 3000/tcp Grafana, 9090/tcp Prometheus, 9093/tcp Alertmanager, 9100/tcp node_exporter
db:      22/tcp, 5432/tcp PostgreSQL, 9080/tcp Promtail, 9100/tcp node_exporter, 9187/tcp postgres_exporter
Windows host: 10802/tcp portproxy для Telegram bot outbound proxy
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

После этапа 18 workaround используется рабочим Telegram bot container на `app`.

Схема:

```text
support-bot container -> 192.168.85.1:10802 -> Windows portproxy -> 127.0.0.1:10801 -> Invisible Man XRay -> Telegram API
```

Windows portproxy:

```text
192.168.85.1:10802 -> 127.0.0.1:10801
```

Env для `/opt/app/.env.bot`:

```bash
HTTP_PROXY=http://192.168.85.1:10802
HTTPS_PROXY=http://192.168.85.1:10802
NO_PROXY=localhost,127.0.0.1,192.168.85.0/24,supportdesk-api
```

`NO_PROXY` важен: запросы `support-bot -> supportdesk-api` должны оставаться внутри Docker/lab-сети и не уходить во внешний proxy.

Webhook не используется. Причина: lab-инфраструктура за NAT и не имеет публичного HTTPS endpoint-а для входящих Telegram webhook-запросов. Выбран long polling: bot сам забирает updates из Telegram API через исходящий proxy.

Видимость:

```text
Telegram bot глобально доступен как @misis_digital_support_bot внутри Telegram.
VM app/web/db при этом не публикуются в интернет.
Входящие соединения из Telegram к lab-сети не нужны.
```

Docker network на app:

```text
support-bot -> supportdesk-api идет по Docker Compose network.
В backend logs direct/via IP для bot-запросов может выглядеть как 172.18.0.x.
Это внутренний Docker IP контейнера, а не внешний пользователь.
```

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


### Telegram bot outbound и Docker internal flow

```text
Telegram user -> Telegram API -> support-bot container -> supportdesk-api container -> PostgreSQL
```

Telegram bot работает через long polling: входящий публичный webhook не используется, VM не публикуются в интернет. `support-bot` сам ходит наружу к Telegram API через outbound proxy workaround:

```text
support-bot container -> 192.168.85.1:10802 -> Windows portproxy -> 127.0.0.1:10801 -> Invisible Man XRay -> Telegram API
```

Внутренний запрос бота к backend API остается внутри Docker Compose network:

```text
support-bot -> http://supportdesk-api:8080
```

Поэтому в backend logs для Telegram-flow часто виден `via=172.18.0.x`: это внутренний Docker IP контейнера `support-bot`, а не пользователь и не Telegram server.

Bot metrics доступны Prometheus на:

```text
monitor/Prometheus -> app 192.168.85.133:8090/metrics
```

## Security/network hardening access model

Stage 19 changed the practical access model from mostly open lab ports to allowlisted flows.

Implemented firewall model:

```text
UFW active on web/app/log/monitor/db;
default incoming deny;
default outgoing allow;
admin remains the management source;
monitor remains the metrics source;
web remains the user-facing frontend/reverse-proxy source;
app remains the only normal DB client;
Docker-published app ports are restricted through DOCKER-USER.
```

Allowed high-level flows after hardening:

```text
Windows 192.168.85.1 -> web:80
Windows 192.168.85.1 -> monitor:3000/9090/9093
Windows 192.168.85.1 -> admin:22
admin -> all nodes:22
web -> app:8080
monitor -> app:8080/8090/9100
app -> db:5432
monitor -> db:9100/9187
web/app/db -> log:3100
monitor -> log:3100/9100
monitor -> web:9080/9100
```

Explicitly blocked / no longer allowed:

```text
Windows/browser -> app:8080
Windows/browser -> app:8090
web -> db:5432
web -> monitor:3000/9090/9093
db -> app:8080/8090
non-monitor/admin -> exporter ports 9080/9100/9187
non-Promtail/Grafana/admin -> log:3100
external/lab nodes -> log:9095
```

Important note about Docker on `app`:

```text
UFW alone is not the whole app protection story because Docker-published ports use NAT/FORWARD rules.
app:8080 and app:8090 are restricted through the DOCKER-USER chain.
The rules are restored after reboot by app-docker-user-firewall.service.
```

Nginx HTTP hardening, HTTPS/local CA, static/DHCP-reserved IPs and Proxmox/VLAN-level segmentation are not implemented yet and remain in `12_future_improvements_backlog.md`.



## Ansible network/firewall audit after Stage 20

В Stage 20 firewall-правила намеренно не автоматизировались. Вместо этого добавлен audit-only playbook:

```text
admin: ~/control-node/playbooks/network_audit.yml
```

Причина: автоматизация изменений firewall без out-of-band доступа и rollback может отрезать SSH, Prometheus scrape, Loki push или Docker published ports. Поэтому текущая политика:

```text
Firewall/access changes remain manual-review based.
Ansible provides network/firewall audit snapshots and critical flow validation.
```

`network_audit.yml` собирает на `admin`:

```text
docs/network-audit/latest/*-network-audit.txt
docs/network-audit/latest/admin-critical-connectivity.txt
```

Проверяет/сохраняет:

```text
IP addresses, routes, DNS;
listening TCP/UDP sockets;
running relevant services;
UFW status verbose/numbered;
iptables filter/nat/DOCKER-USER;
nft ruleset;
Docker containers, published ports, networks, compose ps;
local HTTP endpoints;
critical HTTP/TCP flows from admin.
```

Последний critical connectivity audit подтвердил:

```text
web frontend       200
web api health     200
loki ready         200
prometheus ready   200
grafana            302
alertmanager ready 200
critical TCP flows open as expected
```

`Grafana 302` является нормальным redirect на login page.
