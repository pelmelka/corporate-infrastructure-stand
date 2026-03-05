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
| app | 192.168.85.133 | support-desk-api backend | DHCP сейчас держится стабильно |
| log | 192.168.85.135 | Loki logging | DHCP сейчас держится стабильно |
| monitor | 192.168.85.137 | Prometheus/Grafana/Alertmanager | DHCP сейчас держится стабильно |

Future planned:

```text
db 192.168.85.xxx PostgreSQL
```

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

Сейчас VM получают IP через DHCP VMware NAT. Для более воспроизводимой инфраструктуры позже нужно сделать DHCP reservation по MAC или статические IP внутри Debian.

Это особенно важно для:

```text
Promtail clients
Prometheus targets
Grafana datasources
Ansible inventory
Nginx reverse proxy
future db server
future Docker deployment
future Telegram bot
```

## Порты

```text
Proxmox: 8006/tcp
admin:   22/tcp
web:     22/tcp, 80/tcp, 9080/tcp Promtail, 9100/tcp node_exporter
app:     22/tcp, 8080/tcp support-desk-api, 9080/tcp Promtail, 9100/tcp node_exporter
log:     22/tcp, 3100/tcp Loki HTTP, 9095/tcp Loki gRPC, 9100/tcp node_exporter
monitor: 22/tcp, 3000/tcp Grafana, 9090/tcp Prometheus, 9093/tcp Alertmanager, 9100/tcp node_exporter
Windows host: 10802/tcp portproxy для будущего Telegram bot outbound proxy
future db: 22/tcp, 5432/tcp PostgreSQL, 9100/tcp node_exporter, возможно postgres_exporter
```

## Web/App integration network flow

Реализован поток:

```text
Browser/Windows -> web 192.168.85.131:80
web/Nginx -> app 192.168.85.133:8080
```

Внешние URL:

```text
http://192.168.85.131/
http://192.168.85.131/api/health
http://192.168.85.131/api/tickets
```

Reverse proxy:

```text
/api/* -> http://192.168.85.133:8080/
```

Важно: в app logs `client_ip=192.168.85.131`, потому что backend видит Nginx reverse proxy как TCP-клиента. Исходный клиент фиксируется через `x_forwarded_for`, обычно `192.168.85.1`.

## Monitoring network flow

Реализовано:

```text
monitor/Prometheus -> web:9100 node_exporter
monitor/Prometheus -> app:9100 node_exporter
monitor/Prometheus -> log:9100 node_exporter
monitor/Prometheus -> monitor:9100 node_exporter
monitor/Prometheus -> app:8080/metrics supportdesk-api product metrics
Prometheus -> Alertmanager localhost:9093
Grafana -> Prometheus localhost:9090
Grafana -> Loki 192.168.85.135:3100
```

## Admin/Ansible management flow

Реализовано:

```text
admin/Ansible -> web:22 SSH
admin/Ansible -> app:22 SSH
admin/Ansible -> log:22 SSH
admin/Ansible -> monitor:22 SSH
```

SSH key-based login с `admin` на managed nodes работает без пароля пользователя `pelmel`.

Ansible inventory использует текущие адреса:

```text
web     ansible_host=192.168.85.131
app     ansible_host=192.168.85.133
log     ansible_host=192.168.85.135
monitor ansible_host=192.168.85.137
```

Подтверждено:

```bash
ansible all -m ping
ansible managed -m ping
ansible-playbook playbooks/check_services.yml
```

Результат: `SUCCESS` / `failed=0` для всех актуальных managed nodes.

## Проверки Web/App связности

С `web`:

```bash
curl http://192.168.85.133:8080/health
curl http://localhost/api/health
curl http://192.168.85.131/api/health
```

С `monitor`:

```bash
curl -s http://192.168.85.133:8080/metrics
```

Подтверждено: `support-desk-api` отвечает напрямую и через reverse proxy, а Prometheus может scrape app `/metrics`.

## Telegram bot outbound proxy workaround

Для будущего Telegram support bot проверен исходящий доступ с VM `app` к Telegram API через Windows proxy.

Проблема:

- `app` напрямую не могла подключиться к `https://api.telegram.org`;
- Invisible Man XRay на Windows слушал только `127.0.0.1:10801`, что недоступно из VM.

Решение:

```text
Windows portproxy:
192.168.85.1:10802 -> 127.0.0.1:10801
```

Команды на Windows cmd от администратора:

```cmd
netsh interface portproxy add v4tov4 listenaddress=192.168.85.1 listenport=10802 connectaddress=127.0.0.1 connectport=10801
netsh advfirewall firewall add rule name="Allow VM to XRay proxy 10802" dir=in action=allow protocol=TCP localip=192.168.85.1 localport=10802 remoteip=192.168.85.0/24
```

Проверка с `app`:

```bash
nc -vzn 192.168.85.1 10802
curl -x http://192.168.85.1:10802 -I https://api.telegram.org
```

Результат:

```text
nc -> open
curl через proxy -> HTTP response от Telegram
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
- ограничить доступ к `db:5432`;
- добавить HTTPS termination на `web`;
- добавить DHCP reservation/static IP.

## VPN issue

При включенном VPNKA/VPN доступ к Proxmox `https://192.168.85.128:8006` с Windows не работает. Практическое решение: для работы с Proxmox локально отключать VPN.
