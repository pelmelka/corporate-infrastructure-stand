# Mini Corporate Infrastructure Lab — план и roadmap

## Цель проекта

Собрать учебный, но production-like pet-project в формате мини-инфраструктуры корпоративного типа на базе Proxmox VE внутри VMware: frontend, backend, централизованное логирование, мониторинг, alerting, базовая автоматизация, дальнейшая контейнеризация, БД, Telegram-клиент и демонстрационные сценарии troubleshooting.

Итоговая ценность проекта: показать Linux administration, DevOps-подход, systemd, SSH, Ansible, Nginx, Python-сервис, Loki/Promtail, Prometheus/Grafana/Alertmanager, node_exporter, reverse proxy, product metrics, alerts, Docker, PostgreSQL, backup/restore и диагностику end-to-end.

---

## Текущий продуктовый концепт

Текущий учебный продукт проекта — `MISIS_Digital Student Support`.

Это сервис поддержки студентов по цифровым сервисам университета. Пользователь выбирает цифровой сервис, затем конкретный раздел/функцию внутри сервиса, описывает проблему и создает заявку.

Модель:

```text
category = цифровой сервис университета
resource = раздел/функция внутри выбранного сервиса
```

Категории в API/logs/metrics:

```text
newlms-misis
lk-misis
gornyak-misis
folio-misis
pulse-misis
vector-misis
pay-misis
```

Человекочитаемые labels в UI:

```text
newlms.misis.ru
lk.misis.ru
gornyak.misis.ru
folio.misis.ru
pulse.misis.ru
vector.misis.ru
pay.misis.ru
```

Пример заявки:

```text
category=lk-misis
resource=gradebook
priority=high
description="В электронной зачетке не отображается оценка"
```

Смысл observability: видеть не только техническое состояние серверов, но и продуктовые сигналы — по каким цифровым сервисам и разделам студенты создают больше всего заявок.

---

## Итоговая архитектура текущего состояния

```text
Windows host / Browser / SSH client
        |
        | VMware NAT / local access
        v
Proxmox VE node: 192.168.85.128:8006
        |
        +-- admin    192.168.85.129  control node / Ansible foundation
        +-- web      192.168.85.131  Nginx frontend + reverse proxy + Promtail + node_exporter
        +-- app      192.168.85.133  MISIS_Digital Student Support API + app logs + app metrics + Promtail + node_exporter
        +-- log      192.168.85.135  Loki logging server + node_exporter
        +-- monitor  192.168.85.137  Prometheus + Grafana + Alertmanager + node_exporter
```

## Реализованные потоки

```text
Browser -> web:80                                              # реализовано: MISIS_Digital Student Support frontend
Browser -> web:80/api/v1/* -> app:8080/v1/*                    # реализовано: Nginx reverse proxy /api/* -> app
web -> Promtail -> log:3100 Loki                               # реализовано: nginx access/error logs
app -> Promtail -> log:3100 Loki                               # реализовано: product logs with category label
monitor:9090 Prometheus -> node_exporter targets               # реализовано: node (4/4 up)
monitor:9090 Prometheus -> app:8080/metrics                    # реализовано: supportdesk product metrics
Grafana -> Prometheus:9090                                     # реализовано: datasource подключен
Grafana -> Loki:3100                                           # реализовано: datasource подключен
Prometheus -> Alertmanager:9093                                # реализовано: alerts отправляются в Alertmanager
admin -> SSH/Ansible -> web/app/log/monitor                    # реализовано: базовый control node
```

## Важное замечание про IP

Все VM сейчас получают IP через DHCP VMware NAT. В lab-режиме адреса держатся стабильно, но позже нужно сделать одно из двух:

```text
1. DHCP reservation по MAC-адресам всех VM;
2. статические IP внутри Debian на всех серверах.
```

Это важно для Promtail, Prometheus targets, Grafana datasources, Ansible inventory, Nginx reverse proxy, будущей БД, Docker deployment и Telegram-бота.

---

# Роли серверов

## admin

Управляющий сервер. На нем SSH-ключи, Ansible, inventory, playbook'и, шаблоны, документация и Git.

## web

Frontend / Nginx server. Сейчас отдает страницу `MISIS_Digital Student Support`, проксирует `/api/*` на `app:8080`, пишет nginx access/error logs, отправляет их в Loki через Promtail и отдает системные метрики через node_exporter.

## app

Backend/application node. Сейчас Python-приложение работает как `misis-digital-student-support-api`: `/v1/health`, `/v1/support-model`, `/v1/tickets`, `/v1/tickets/all`, `/v1/tickets/<id>`, `/v1/tickets/<id>/status`, `/metrics`. Заявки хранятся в `/opt/app/tickets.json`; product logs пишутся в `/var/log/app/app.log`; app logs отправляются в Loki через Promtail; product metrics собираются Prometheus.

## log

Централизованный сервер логирования. На нем Loki. Принимает nginx logs от `web` и app product logs от `app`. Для app logs добавлен dynamic Loki label `category`.

## monitor

Сервер мониторинга, визуализации и алертов. На нем Prometheus, Grafana, Alertmanager и node_exporter. Dashboard `Infrastructure Overview` показывает infrastructure metrics, app/product metrics, active alerts, web nginx logs и app product logs.

---

# Завершенные этапы

## Этап 1. Loki на log — завершено

Loki 3.5.0 установлен как `loki.service`, `active/enabled`, `/ready -> ready`, принимает web/app logs.

## Этап 2. Promtail на web — завершено

Promtail читает `/var/log/nginx/*.log` и отправляет nginx logs в Loki с labels `host=web`, `job=nginx`, `service=frontend`, `env=lab`.

## Этап 3. Promtail на app — завершено

Promtail читает `/var/log/app/*.log` и отправляет app logs в Loki. После Product model v2 static label приведен к `service=misis-digital-student-support-api`, а `category` извлекается из app log line как dynamic Loki label.

Что теперь можно делать:

```logql
{host="app", job="app", service="misis-digital-student-support-api"}
{host="app", job="app", category="lk-misis"}
```

## Этап 4. Monitor base stack — завершено

На `monitor` установлены Prometheus, Grafana, Alertmanager и node_exporter. Сервисы active/enabled.

## Этап 5. Метрики node_exporter — завершено

node_exporter установлен на `web`, `app`, `log`, `monitor`; Prometheus видит `node (4/4 up)` с host labels.

## Этап 6. Grafana datasources — завершено

В Grafana подключены Prometheus datasource (`http://localhost:9090`) и Loki datasource (`http://192.168.85.135:3100`).

## Этап 7. Grafana dashboard Infrastructure Overview — завершено

Dashboard показывает Targets UP, CPU/RAM/Disk по host, Web nginx logs, App logs, product ticket metrics и Active Alerts.

## Этап 8. Web/App integration — завершено

Первоначально был реализован продукт `Mini Support Desk` через поток:

```text
Browser -> web/Nginx -> app/support-desk-api
```

Позже на этапе Product model v2 продукт был переосмыслен и заменен на `MISIS_Digital Student Support`, сохранив тот же infrastructure flow.

## Этап 9. Полировка logging — завершено

Финализирован формат product logs: `key=value`, proxy metadata, корректное различение `ticket_status_changed` и `ticket_status_unchanged`, validation/not_found события, LogQL/panel.

## Этап 10. Полировка monitoring — завершено

Добавлены product metrics, dashboard panels и базовые alert rules.

Текущие product metrics:

```text
supportdesk_tickets_total
supportdesk_tickets_open
supportdesk_tickets_in_progress
supportdesk_tickets_resolved
supportdesk_tickets_active
```

Текущие alerts:

```text
SupportDeskApiDown
TooManyOpenTickets
HighDiskUsage
NodeTargetDown
```

## Этап 11. Admin/Ansible foundation — завершено

Сделано:

```text
1. Раскатан SSH-ключ admin -> web/app/log/monitor.
2. Проверен SSH-вход с admin на managed nodes без пароля пользователя.
3. Расширен inventory.
4. Проверены ansible all -m ping и ansible managed -m ping.
5. Создана структура ~/control-node.
6. Добавлен ansible.cfg.
7. Созданы playbook'и: ping_all.yml, check_services.yml, restart_app.yml, deploy_prometheus_rules.yml.
8. Инициализирован Git repo.
9. Сделаны первые commit'ы.
```

## Этап 12. Product model v2 — завершено

Цель этапа: превратить простую форму заявок в самостоятельный продукт `MISIS_Digital Student Support` с моделью `category/resource`, active/resolved разделением и API v1.

Сделано:

```text
1. Новый продуктовый концепт: MISIS_Digital Student Support.
2. category = цифровой сервис университета.
3. resource = раздел/функция внутри выбранного сервиса.
4. category/resource обязательны.
5. Backend валидирует, что resource разрешен для выбранной category.
6. Старые заявки v1 сохранены в backup tickets.json; рабочий tickets.json очищен.
7. legacy-категория не используется.
8. Добавлены schema_version=2, category_label, resource_label, resolved_at.
9. Реализовано active/resolved разделение:
   /tickets -> active
   /tickets?status=resolved -> history
   /tickets/all -> all
10. Добавлены /v1/* endpoints.
11. Frontend переведен на category-first dropdown: сначала digital service, потом service section.
12. Исправлен статусный баг: in_progress корректно нормализуется через normalize_status.
13. Promtail app label обновлен на service=misis-digital-student-support-api.
14. Promtail pipeline добавляет Loki label category.
15. Grafana App logs panel обновлен под новую модель.
16. Prometheus метрики сохранены совместимыми; добавлена supportdesk_tickets_active.
```

Что теперь можно делать:

```text
Создать заявку:
category=lk-misis
resource=gradebook
priority=high

Увидеть:
- заявку в UI Active;
- POST /api/v1/tickets в nginx logs;
- event=ticket_created category=lk-misis resource=gradebook в app logs;
- stream category="lk-misis" в Loki;
- изменение supportdesk_tickets_* metrics в Prometheus/Grafana.
```

---

# Новый production-like roadmap от текущей точки до финала

## Этап 13. Product observability v2 — metrics и alerts по category/resource

Цель: добавить продуктовую observability поверх новой модели `MISIS_Digital Student Support`.

Что добавить в `/metrics`:

```text
supportdesk_tickets_by_status{status="open"}
supportdesk_tickets_by_category{category="newlms-misis",status="open"}
supportdesk_tickets_by_resource{category="newlms-misis",resource="schedule",status="open"}
supportdesk_tickets_by_priority{priority="critical",status="open"}
supportdesk_tickets_created_total{category,resource,priority,source}
supportdesk_tickets_resolved_total{category,resource}
```

Новые alerts:

```text
SupportDeskTooManyTicketsForCategory
SupportDeskTooManyTicketsForResource
SupportDeskCriticalTicketsOpen
SupportDeskTicketSpike
```

Ожидаемый итог:

```text
Monitoring показывает не только общее число заявок,
а концентрацию проблем вокруг конкретного цифрового сервиса или раздела.
```

Пример:

```text
Много open-заявок по category=newlms-misis resource=schedule
→ Possible LMS schedule incident
```

## Этап 14. HTTP request metrics, error-rate alerts и latency

Цель: мониторить качество работы API: rate, errors, status codes, latency.

Что добавить:

```text
supportdesk_requests_total{method,path,status}
supportdesk_errors_total{status}
supportdesk_request_duration_seconds_bucket
supportdesk_request_duration_seconds_sum
supportdesk_request_duration_seconds_count
```

Желательно перейти с ручного `/metrics` на Prometheus client library.

Alerts:

```text
SupportDeskHigh5xxRate
SupportDeskHigh4xxRate
SupportDeskHighLatency
Nginx502Spike
```

## Этап 15. Dockerization — экологично добавить Docker

Цель: добавить Docker как production-like способ доставки приложения, не ломая текущую инфраструктурную модель.

Что контейнеризировать:

```text
misis-digital-student-support-api на app
support-bot позже
```

Что пока не переносить в Docker:

```text
Prometheus
Grafana
Loki
Alertmanager
Nginx
node_exporter
admin
```

## Этап 16. PostgreSQL вместо tickets.json

Цель: заменить учебное файловое хранилище на нормальную БД.

Новая архитектура:

```text
web -> app -> db/PostgreSQL
```

Минимальная таблица `tickets`:

```text
id
schema_version
category
category_label
resource
resource_label
description
priority
status
source
created_at
updated_at
resolved_at
```

## Этап 17. DB observability и backups

Цель: сделать БД наблюдаемой и восстановимой.

Что сделать:

```text
node_exporter на db
postgres_exporter на db
Prometheus scrape для db metrics
Grafana DB panels
DB alerts
pg_dump backup + restore test
```

## Этап 18. Telegram support bot

Цель: добавить второго клиента к тому же backend API.

Архитектура:

```text
Browser -> web -> app -> db
Telegram -> support-bot.service/container -> app -> db
```

Команды бота:

```text
/start
/new
/tickets
/resolve
```

Бот должен создавать заявки через тот же API v1 и писать `source=telegram`.

## Этап 19. Security/network hardening

Цель: приблизить сетевую модель к production-like варианту.

Что сделать:

```text
ограничить прямой доступ к app:8080
ограничить db:5432
Nginx hardening
HTTPS/self-signed cert или local CA
секреты вне Git
DHCP reservation или static IP
```

## Этап 20. Ansible automation v2

Цель: автоматизировать уже новую архитектуру: app, Docker, DB, bot, monitoring rules.

Playbooks/roles:

```text
common.yml
nginx.yml
app.yml
docker_app.yml
promtail.yml
prometheus.yml
postgres.yml
bot.yml
backup.yml
```

## Этап 21. Финальная документация, README и demo packaging

Цель: упаковать проект как законченный pet-project.

Что подготовить:

```text
README с архитектурой
IP/порты/сервисы
Data flows
Команды проверки
Dashboard screenshots
Alerts list
Demo сценарии
Troubleshooting scenarios
Backup/restore scenario
Snapshots/контрольные точки в Proxmox
```

---

# Текущий маркер прогресса

```text
Последний завершенный этап: Этап 12. Product model v2.
Текущий следующий этап: Этап 13. Product observability v2.
Далее: category/resource metrics, product alerts, HTTP/error-rate metrics, Dockerization, PostgreSQL, DB observability, Telegram bot, hardening, Ansible automation v2, final README/demo.
```

## Текущий прогресс проекта

Важно: прогресс считается относительно расширенного production-like roadmap.

```text
Формальная готовность по расширенному roadmap: 12/21 основных этапов завершены ≈ 57%.
Готовность core infrastructure lab: 100% по этапам 1–10.
Admin/Ansible foundation: 100%.
Product model v2: 100%.
Инженерная готовность по новому production-like scope: 62–67%.
Демонстрационная готовность текущего core-проекта: 88–92%.
Финальная демонстрационная готовность с DB/Docker/Bot/Ansible v2: 52–60%.
```

Разбивка по этапам:

| Этап | Статус | Готовность | Комментарий |
|---|---:|---:|---|
| 1. Loki на log | завершено | 100% | Loki работает как systemd service и принимает logs. |
| 2. Promtail на web | завершено | 100% | nginx logs уходят в Loki. |
| 3. Promtail на app | завершено | 100% | app logs уходят в Loki, category label добавлен. |
| 4. Monitor base stack | завершено | 100% | Prometheus, Grafana, Alertmanager, node_exporter active/enabled. |
| 5. Метрики node_exporter | завершено | 100% | Prometheus видит node targets `4/4 up`. |
| 6. Grafana datasources | завершено | 100% | Prometheus и Loki подключены к Grafana. |
| 7. Grafana dashboard Infrastructure Overview | завершено | 100% | Есть рабочий обзорный dashboard. |
| 8. Web/App integration | завершено | 100% | Browser -> web -> app flow работает. |
| 9. Полировка logging | завершено | 100% | Product logs, proxy metadata, LogQL/panel. |
| 10. Полировка monitoring | завершено | 100% | App metrics, product panels, active alerts, alert rules. |
| 11. Admin/Ansible foundation | завершено | 100% | SSH keys, inventory, ansible.cfg, playbook-и и Git repo готовы. |
| 12. Product model v2 | завершено | 100% | MISIS_Digital Student Support, category/resource, active/resolved, API v1, UI, Loki category label. |
| 13. Product observability v2 | следующий этап | 0–10% | Metrics/alerts by category/resource еще не реализованы. |
| 14. HTTP request/error-rate observability | план | 0–10% | Request metrics, latency и error-rate alerts еще не реализованы. |
| 15. Dockerization | план | 0–5% | Docker пока не внедрен. |
| 16. PostgreSQL migration | план | 0–5% | Сейчас используется `/opt/app/tickets.json`. |
| 17. DB observability + backups | план | 0–5% | Зависит от появления DB server. |
| 18. Telegram support bot | plan/future | 5–10% | Сетевой workaround проверен, сам bot еще не реализован. |
| 19. Security/network hardening | план | 5–10% | Есть proxy headers, но ограничения доступа/HTTPS еще впереди. |
| 20. Ansible automation v2 | план | 0–10% | Зависит от дальнейшей формализации deploy. |
| 21. Final README/demo packaging | план | 25–35% | Sources ведутся, но финальный README/demo/snapshots еще не собраны. |

Короткая интерпретация:

```text
Проект уже можно демонстрировать как работающий infrastructure lab с web/app/logging/monitoring/alerts, базовым Ansible control node и самостоятельным продуктовым сценарием MISIS_Digital Student Support.
```

---

# Future improvements

Подробный backlog будущих улучшений вынесен отдельно в файл:

```text
12_future_improvements_backlog.md
```
