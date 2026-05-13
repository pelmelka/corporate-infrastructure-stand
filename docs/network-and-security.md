# Сеть и контроль доступа

## Сетевая схема

![Сеть и управление](../assets/diagrams/network-flow.png)

_Схема сетевых потоков: HTTP-вход, SSH/Ansible, app/db/log/monitoring, Telegram outbound-интеграция и контроль доступа._

В документации используется фактический план адресации стенда.

| Узел | IP |
|---|---:|
| `admin` | `192.168.85.129` |
| `web` | `192.168.85.131` |
| `app` | `192.168.85.133` |
| `log` | `192.168.85.135` |
| `monitor` | `192.168.85.137` |
| `db` | `192.168.85.139` |

## Основная модель доступа

`web:80` является основной HTTP-точкой входа для пользовательского сценария. Остальные сервисы доступны только для нужных внутренних потоков, мониторинга, диагностики или управления.

Полная матрица потоков находится в `../infra/firewall/access-matrix.md`.

## Критические потоки

```text
Browser/operator -> web:80
web -> app:8080
support-bot -> supportdesk-api:8080 внутри Docker Compose network
app -> db:5432
web/app/db -> log:3100
monitor -> exporters/metrics endpoints
admin -> SSH/Ansible -> managed nodes
```

## Firewall и allowlist

На узлах используется модель “запрещено по умолчанию, разрешено только необходимое”. Для Docker-published ports на `app` дополнительно используются правила `DOCKER-USER`, потому что опубликованные Docker-порты требуют отдельного контроля на уровне iptables.

Актуальный сетевой аудит из Ansible сохранен в:

```text
infra/firewall/network-audit-latest/
```

![Critical connectivity audit](../assets/screenshots/network-audit-critical-connectivity.png)

_Отчет critical connectivity audit: HTTP readiness, SSH, application, PostgreSQL, Loki, Prometheus, Grafana, Alertmanager и exporter-порты доступны по ожидаемым потокам._

## Docker published ports

На `app` опубликованы:

- `8080/tcp` — backend API;
- `8090/tcp` — metrics endpoint Telegram-клиента.

Ожидаемая модель доступа для опубликованных host ports:

| Порт | Разрешенные источники | Назначение |
|---:|---|---|
| 8080 | `web`, `monitor`, `admin` | reverse proxy, metrics scrape, диагностика |
| 8090 | `monitor`, `admin` | metrics scrape и диагностика |

Пример правил находится в `../infra/firewall/app-docker-user-firewall.sh`.

## Secrets policy

В финальный пакет не входят реальные env-файлы, пароли, токены, SSH private keys и backup dumps. Хранятся только безопасные шаблоны в `examples/env/`.
