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

## Порты

```text
Proxmox: 8006/tcp
admin:   22/tcp
web:     22/tcp, 80/tcp, 9080/tcp Promtail, 9100/tcp node_exporter
app:     22/tcp, 8080/tcp support-desk-api, 9080/tcp Promtail, 9100/tcp node_exporter
log:     22/tcp, 3100/tcp Loki HTTP, 9095/tcp Loki gRPC, 9100/tcp node_exporter
monitor: 22/tcp, 3000/tcp Grafana, 9090/tcp Prometheus, 9093/tcp Alertmanager, 9100/tcp node_exporter
Windows host: 10802/tcp portproxy для будущего Telegram bot outbound proxy
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

Важно: в app logs `client_ip=192.168.85.131`, потому что backend видит Nginx reverse proxy как TCP-клиента. Обработка `X-Real-IP` и `X-Forwarded-For` вынесена в future backlog.

## Проверки Web/App связности

С `web`:

```bash
curl http://192.168.85.133:8080/health
curl http://localhost/api/health
curl http://192.168.85.131/api/health
```

Подтверждено: `support-desk-api` отвечает напрямую и через reverse proxy.

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

## VPN issue

При включенном VPNKA/VPN доступ к Proxmox `https://192.168.85.128:8006` с Windows не работает. Практическое решение: для работы с Proxmox локально отключать VPN.
