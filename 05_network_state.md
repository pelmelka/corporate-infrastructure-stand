# Сеть проекта

## Общая схема

Проект работает внутри Proxmox VE, который установлен как VM внутри VMware.

Основная сеть сейчас — VMware NAT:

```text
192.168.85.0/24
```

Proxmox и все VM сейчас находятся в этой сети через bridge `vmbr0`.

## Proxmox

- Web UI: `https://192.168.85.128:8006`
- IP: `192.168.85.128/24`
- Gateway: `192.168.85.2`
- Bridge: `vmbr0`
- Port: `ens33`

## IP-адреса

| Сервер | IP | Назначение | Статус IP |
|---|---:|---|---|
| Proxmox | 192.168.85.128 | гипервизор | зафиксирован на Proxmox |
| admin | 192.168.85.129 | control node | DHCP сейчас держится стабильно |
| web | 192.168.85.131 | nginx frontend | DHCP сейчас держится стабильно |
| app | 192.168.85.133 | python backend | DHCP сейчас держится стабильно |
| log | 192.168.85.135 | Loki logging | DHCP сейчас держится стабильно |
| monitor | 192.168.85.137 | Prometheus/Grafana/Alertmanager | DHCP сейчас держится стабильно |

## Важное замечание про DHCP/static

На текущем этапе VM получают IP через DHCP VMware NAT. В lab-режиме это работает стабильно, потому что VMware NAT обычно выдает адрес “липко” по MAC-адресу VM.

Но для более правильной и воспроизводимой инфраструктуры позже нужно сделать одно из двух:

```text
1. DHCP reservation по MAC-адресам всех VM;
2. статические IP внутри Debian на всех серверах.
```

Это важно, потому что в проекте уже есть зависимости от IP:

```text
Promtail на web/app -> Loki 192.168.85.135:3100
Grafana -> Prometheus 192.168.85.137:9090
Grafana -> Loki 192.168.85.135:3100
Prometheus -> node_exporter targets на web/app/log/monitor
Ansible inventory -> IP всех узлов
будущий reverse proxy web -> app 192.168.85.133:8080
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

## Порты

```text
Proxmox: 8006/tcp
admin:   22/tcp
web:     22/tcp, 80/tcp, 9080/tcp Promtail, 9100/tcp node_exporter план
app:     22/tcp, 8080/tcp, 9080/tcp Promtail, 9100/tcp node_exporter план
log:     22/tcp, 3100/tcp Loki HTTP, 9095/tcp Loki gRPC, 9100/tcp node_exporter план
monitor: 22/tcp, 3000/tcp Grafana, 9090/tcp Prometheus, 9093/tcp Alertmanager, 9100/tcp node_exporter
```

## Проверки связности

`monitor -> Loki`:

```bash
curl http://192.168.85.135:3100/ready
```

Результат:

```text
ready
```

`monitor -> admin/web/app/log`:

```bash
ping 192.168.85.129
ping 192.168.85.131
ping 192.168.85.133
ping 192.168.85.135
```

Результат: связность есть.

## Доступ с Windows

Prometheus:

```text
http://192.168.85.137:9090
```

Grafana:

```text
http://192.168.85.137:3000
```

Alertmanager:

```text
http://192.168.85.137:9093
```

Важно: Debian-пакет Alertmanager не включает полноценный web UI, поэтому по `:9093` показывается простая HTML-страница с API/health links.

## VPN issue

При включенном VPNKA/VPN доступ к Proxmox `https://192.168.85.128:8006` с Windows не работает.

Текущее практическое решение:

```text
Для работы с Proxmox локально отключать VPN.
```

Для скачивания Grafana `.deb` может понадобиться другой интернет/VPN. Если VPN ломает доступ к VM, лучше:

```text
1. скачать .deb на Windows через доступный маршрут;
2. выключить VPN;
3. передать .deb на monitor через scp;
4. установить локально.
```
