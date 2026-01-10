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

Зафиксированное состояние:

```text
ens33 — active interface
ens34 — second interface, currently unused
vmbr0 — Linux Bridge
vmbr0 ports: ens33
vmbr0 CIDR: 192.168.85.128/24
vmbr0 gateway: 192.168.85.2
```

## IP-адреса

| Сервер | IP | Назначение |
|---|---:|---|
| Proxmox | 192.168.85.128 | гипервизор |
| admin | 192.168.85.129 | control node |
| web | 192.168.85.131 | nginx frontend |
| app | 192.168.85.133 | python backend |
| log | 192.168.85.135 | Loki logging |
| monitor | TBD | Prometheus/Grafana |

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
web:     22/tcp, 80/tcp
app:     22/tcp, 8080/tcp
log:     22/tcp, 3100/tcp, 9095/tcp служебный Loki gRPC
monitor: 22/tcp, 3000/tcp, 9090/tcp, 9093/tcp, 9100/tcp exporters
```

## Проверки связности

`admin -> web`:

```bash
curl http://192.168.85.131
```

`admin -> app`:

```bash
curl http://192.168.85.133:8080
curl http://192.168.85.133:8080/health
```

`log local Loki`:

```bash
curl http://localhost:3100/ready
```

## VPN issue

При включенном VPNKA/VPN доступ к Proxmox `https://192.168.85.128:8006` с Windows не работает.

Наблюдения:

- `ping 192.168.85.128` при включенном VPN дает `Общий сбой`.
- `route print` показывает маршрут до `192.168.85.0/24` через VMware VMnet8.
- `ping 192.168.85.1` при включенном VPN работает.
- Значит сам VMware NAT adapter доступен, но трафик к гостям VMware NAT ломается.
- Вероятная причина: конфликт VPN-клиента с VMware NAT forwarding или фильтрация трафика к NAT-гостям.

Текущее практическое решение:

```text
Для работы с Proxmox локально отключать VPN.
```

Возможное будущее улучшение:

```text
Настроить отдельную Host-only management-сеть для доступа к Proxmox и VM.
```

## vmbr1

Обсуждалось создание `vmbr1` на `ens34` для отдельной внутренней/management-сети. Сейчас основная рабочая схема использует `vmbr0`; `vmbr1` не используется как основная сеть проекта.
