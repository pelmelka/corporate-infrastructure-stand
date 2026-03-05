# Mini Corporate Infrastructure Lab — план и roadmap

## Цель проекта

Собрать учебный, но production-like pet-project в формате мини-инфраструктуры корпоративного типа на базе Proxmox VE внутри VMware: frontend, backend, централизованное логирование, мониторинг, alerting, базовая автоматизация, дальнейшая контейнеризация, БД, Telegram-клиент и демонстрационные сценарии troubleshooting.

Итоговая ценность проекта: показать Linux administration, DevOps-подход, systemd, SSH, Ansible, Nginx, Python-сервис, Loki/Promtail, Prometheus/Grafana/Alertmanager, node_exporter, reverse proxy, product metrics, alerts, Docker, PostgreSQL, backup/restore и диагностику end-to-end.

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
        +-- app      192.168.85.133  support-desk-api + app logs + app metrics + Promtail + node_exporter
        +-- log      192.168.85.135  Loki logging server + node_exporter
        +-- monitor  192.168.85.137  Prometheus + Grafana + Alertmanager + node_exporter
```

## Реализованные потоки

```text
Browser -> web:80                                      # реализовано: Mini Support Desk frontend
Browser -> web:80/api/* -> app:8080                    # реализовано: Nginx reverse proxy /api/* -> app
web -> Promtail -> log:3100 Loki                       # реализовано: nginx access/error logs
app -> Promtail -> log:3100 Loki                       # реализовано: support-desk-api product logs
monitor:9090 Prometheus -> node_exporter targets       # реализовано: node (4/4 up)
monitor:9090 Prometheus -> app:8080/metrics            # реализовано: supportdesk-api product metrics
Grafana -> Prometheus:9090                             # реализовано: datasource подключен
Grafana -> Loki:3100                                   # реализовано: datasource подключен
Prometheus -> Alertmanager:9093                        # реализовано: alerts отправляются в Alertmanager
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

Управляющий сервер. На нем SSH-ключи, Ansible, inventory, будущие playbook'и, шаблоны, документация и Git. Следующий крупный практический этап — сделать `admin` полноценным control node.

## web

Frontend / Nginx server. Сейчас отдает страницу Mini Support Desk, проксирует `/api/*` на `app:8080`, пишет nginx access/error logs, отправляет их в Loki через Promtail и отдает системные метрики через node_exporter.

## app

Backend/application node. Сейчас Python-приложение работает как `support-desk-api`: `/health`, `/tickets`, `/tickets/<id>`, `/tickets/<id>/status`, `/metrics`. Заявки хранятся в `/opt/app/tickets.json`; product logs пишутся в `/var/log/app/app.log`; app logs отправляются в Loki через Promtail; product metrics собираются Prometheus.

## log

Централизованный сервер логирования. На нем Loki. Принимает nginx logs от `web` и app product logs от `app`.

## monitor

Сервер мониторинга, визуализации и алертов. На нем Prometheus, Grafana, Alertmanager и node_exporter. Dashboard `Infrastructure Overview` показывает infrastructure metrics, supportdesk-api health, product ticket metrics, active alerts и logs.

---

# Завершенные этапы

## Этап 1. Loki на log — завершено

Loki 3.5.0 установлен как `loki.service`, `active/enabled`, `/ready -> ready`, принимает web/app logs.

Что теперь можно делать:

```text
curl http://192.168.85.135:3100/ready
# ready
```

## Этап 2. Promtail на web — завершено

Promtail читает `/var/log/nginx/*.log` и отправляет nginx logs в Loki с labels `host=web`, `job=nginx`, `service=frontend`, `env=lab`.

Что теперь можно делать:

```logql
{host="web", job="nginx"}
```

## Этап 3. Promtail на app — завершено

Promtail читает `/var/log/app/*.log` и отправляет app logs в Loki. После logging polish label `service` приведен к актуальному значению `support-desk-api`.

Что теперь можно делать:

```logql
{host="app", job="app", service="support-desk-api"}
```

## Этап 4. Monitor base stack — завершено

На `monitor` установлены Prometheus, Grafana, Alertmanager и node_exporter. Сервисы active/enabled.

## Этап 5. Метрики node_exporter — завершено

node_exporter установлен на `web`, `app`, `log`, `monitor`; Prometheus видит `node (4/4 up)` с host labels.

Что теперь можно делать:

```promql
up{job="node"}
```

## Этап 6. Grafana datasources — завершено

В Grafana подключены Prometheus datasource (`http://localhost:9090`) и Loki datasource (`http://192.168.85.135:3100`).

## Этап 7. Grafana dashboard Infrastructure Overview — завершено

Dashboard показывает Targets UP, CPU/RAM/Disk по host, Web nginx logs и App logs.

## Этап 8. Web/App integration — завершено

Реализован продукт `Mini Support Desk`:

```text
Browser -> web/Nginx -> app/support-desk-api
```

Готово:

- `web` отдает frontend `/var/www/html/index.html`;
- `web` проксирует `/api/*` на `http://192.168.85.133:8080/`;
- `app` работает как `support-desk-api`;
- заявки создаются через UI и сохраняются в `/opt/app/tickets.json`;
- статус заявки меняется через UI;
- nginx access logs показывают `GET/POST/PATCH /api/*`;
- app product logs показывают `event=ticket_created`, `event=ticket_status_changed`, `event=ticket_list_requested`, `event=health_check`;
- Loki/Grafana видит product logs.

Что теперь можно делать:

```text
Открыть http://192.168.85.131
создать заявку
изменить статус
увидеть web log + app product log + ticket metrics
```

## Этап 9. Полировка logging — завершено

Финализирован формат product logs Mini Support Desk.

Сделано:

- `client_ip` оставлен как TCP peer backend-а;
- добавлены `x_forwarded_for` и `x_forwarded_proto` как proxy metadata;
- `x_real_ip` сознательно не логируется, чтобы не дублировать `x_forwarded_for` в текущей single-proxy схеме;
- `old_status == new_status` теперь пишет `event=ticket_status_unchanged`, а не `ticket_status_changed`;
- подтверждены события `ticket_validation_failed`, `ticket_not_found`, `endpoint_not_found`;
- App logs panel в Grafana обновлена под `event=...` формат;
- Promtail label для app изменен с `service=python-backend` на `service=support-desk-api`.

Что теперь можно делать:

```logql
{host="app", job="app", service="support-desk-api"}
| logfmt
| line_format "{{.event}} | {{.method}} {{.path}} | status={{.status}} | ticket={{.ticket_id}} | {{.old_status}} -> {{.new_status}} | client={{.x_forwarded_for}} | proxy={{.client_ip}}"
```

Пример читаемой строки:

```text
ticket_status_changed | PATCH /tickets/7/status | status=200 | ticket=7 | open -> resolved | client=192.168.85.1 | proxy=192.168.85.131
```

## Этап 10. Полировка monitoring — завершено

Добавлены product metrics, dashboard panels и базовые alert rules.

Сделано:

- Prometheus scrape job `supportdesk-api` добавлен;
- target `supportdesk-api` показывает `1/1 up`;
- Prometheus собирает `supportdesk_tickets_total`, `supportdesk_tickets_open`, `supportdesk_tickets_in_progress`, `supportdesk_tickets_resolved`;
- Grafana dashboard дополнен panels:
  - `SupportDesk Tickets`;
  - `SupportDesk API UP`;
  - `Active Alerts`;
- создан rules file `/etc/prometheus/supportdesk.rules.yml`;
- настроены и протестированы alerts:
  - `SupportDeskApiDown`;
  - `TooManyOpenTickets`;
  - `HighDiskUsage`;
  - `NodeTargetDown`;
- подтверждено, что `SupportDeskApiDown` доходит до Alertmanager через `amtool`.

Что теперь можно делать:

```text
Остановить app.service
→ supportdesk-api target DOWN
→ SupportDeskApiDown FIRING
→ alert виден через Prometheus /alerts и amtool

Создать много open-заявок
→ TooManyOpenTickets FIRING

Остановить node_exporter на web/app/log/monitor
→ NodeTargetDown FIRING

Временно снизить порог HighDiskUsage
→ проверить расчет disk usage alert без забивания диска
```

---

# Новый production-like roadmap от текущей точки до финала

## Этап 11. Admin/Ansible foundation — завершено

Цель: сделать `admin` полноценным control node перед крупными изменениями продукта, БД и Docker.

Сделано:

```text
1. Раскатан SSH-ключ admin -> web/app/log/monitor.
2. Проверен SSH-вход с admin на managed nodes без пароля пользователя.
3. Расширен inventory:
   [control]
   [web_nodes]
   [app_nodes]
   [log_nodes]
   [monitor_nodes]
   [managed:children]
4. Проверены ansible all -m ping и ansible managed -m ping.
5. Создана структура ~/control-node:
   inventory/
   playbooks/
   roles/
   templates/
   files/
   docs/
6. Добавлен ansible.cfg.
7. Созданы первые playbook'и:
   - ping_all.yml
   - check_services.yml
   - restart_app.yml
   - deploy_prometheus_rules.yml
8. Инициализирован Git repo.
9. Сделаны первые commit'ы:
   - initial Ansible control node setup
   - Add Ansible project directory placeholders
```

Итог:

```text
admin перестал быть просто сервером с установленным Ansible и стал рабочим control node:
SSH-доступ, inventory, ansible.cfg, operational playbook'и и Git-история готовы.
```

Что теперь можно делать:

```bash
cd ~/control-node
ansible all -m ping
ansible managed -m ping
ansible-playbook playbooks/ping_all.yml
ansible-playbook playbooks/check_services.yml
ansible-playbook playbooks/restart_app.yml
ansible-playbook playbooks/deploy_prometheus_rules.yml
git status
git log --oneline
```

Практическая ценность:

```text
Теперь часть инфраструктурного управления выполняется из одного места через Ansible,
а состояние control-node файлов фиксируется в Git.
Это база для будущей автоматизации app/web/promtail/prometheus/db/bot/docker.
```

## Этап 12. Product model v2 — resource/category и active/resolved tickets

Цель: превратить Mini Support Desk из простой формы с `Title` в систему классификации заявок.

Что сделать:

```text
1. Заменить/дополнить Title на Resource dropdown.
2. Добавить Category dropdown.
3. Оставить Description и Priority.
4. В ticket model добавить:
   resource
   category
   resolved_at
5. Разделить выдачу:
   GET /tickets              -> active tickets: open + in_progress
   GET /tickets?status=resolved -> resolved tickets
   GET /tickets/all          -> all tickets
6. При status=resolved заявка исчезает из активного списка, но сохраняется в storage.
7. Начать переход к API versioning:
   /api/v1/tickets
   /api/v1/health
   /api/v1/metrics
```

Примеры `resource`:

```text
grafana, prometheus, loki, web, app, ssh, vpn, database, telegram-bot
```

Примеры `category`:

```text
observability, application, access, network, database, automation
```

Ожидаемый итог:

```text
Пользователь создает не произвольную заявку “что-то сломалось”,
а классифицированное событие: resource=grafana, category=observability, priority=critical.
```

Что теперь можно делать:

```text
Создать заявку:
resource=grafana
category=observability
priority=critical
description="Dashboard unavailable"

Потом увидеть:
- активную заявку в UI;
- resource/category в app logs;
- фильтрацию по resource/category в будущих metrics/alerts;
- исчезновение заявки из active list после resolved при сохранении в истории.
```

## Этап 13. Product observability v2 — metrics и alerts по resource/category

Цель: добавить продуктовую observability поверх новой модели заявки.

Что добавить в `/metrics`:

```text
supportdesk_tickets_by_status{status="open"}
supportdesk_tickets_by_resource{resource="grafana",status="open"}
supportdesk_tickets_by_category{category="observability",status="open"}
supportdesk_tickets_by_priority{priority="critical",status="open"}
supportdesk_tickets_created_total{resource,category,priority,source}
supportdesk_tickets_resolved_total{resource,category}
```

Новые alerts:

```text
SupportDeskTooManyTicketsForResource
SupportDeskCategoryIncident
SupportDeskCriticalTicketsOpen
SupportDeskTicketSpike
```

Ожидаемый итог:

```text
Monitoring показывает не только общее число заявок,
а концентрацию проблем вокруг конкретного ресурса или категории.
```

Что теперь можно делать:

```text
Создать 4 open-заявки на resource=grafana
→ Grafana показывает grafana=4
→ SupportDeskTooManyTicketsForResource FIRING

Создать заявки по grafana/prometheus/loki в category=observability
→ SupportDeskCategoryIncident FIRING
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

Ожидаемый итог:

```text
Можно видеть не только состояние заявок,
но и качество HTTP/API-слоя: ошибки, 502, latency, request rate.
```

Что теперь можно делать:

```text
Остановить app.service
→ Nginx начинает отдавать 502
→ Nginx502Spike / SupportDeskApiDown

Сгенерировать 400/404 запросы
→ увидеть рост 4xx/error-rate
```

## Этап 15. Dockerization — экологично добавить Docker

Цель: добавить Docker как production-like способ доставки приложения, не ломая текущую инфраструктурную модель.

Что контейнеризировать:

```text
support-desk-api на app
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

Почему так: observability stack уже хорошо работает как systemd-сервисы, а Docker логичнее добавить как способ упаковки backend-а и будущего bot-а.

Что сделать:

```text
1. Создать Dockerfile для support-desk-api.
2. Создать docker-compose.yml на app.
3. Оставить внешний порт 8080.
4. Вынести config/secrets в env file.
5. Сохранить логи через volume:
   container -> /var/log/app/app.log на host
   Promtail -> читает тот же файл
6. Проверить:
   web/Nginx -> app:8080
   Prometheus -> app:8080/metrics
   Promtail -> Loki
7. Добавить Ansible playbook для deploy docker compose.
```

Ожидаемый итог:

```text
Раньше backend запускался как обычный Python systemd service.
Теперь backend упакован в Docker image и запускается воспроизводимо через Docker Compose,
при этом внешний flow web -> app:8080 и observability не ломаются.
```

Что теперь можно делать:

```bash
docker compose ps
docker compose logs support-desk-api
curl http://localhost:8080/health
```

## Этап 16. PostgreSQL вместо tickets.json

Цель: заменить учебное файловое хранилище на нормальную БД.

Новая архитектура:

```text
web -> app -> db/PostgreSQL
```

Что сделать:

```text
1. Создать VM db.
2. Установить PostgreSQL.
3. Создать database supportdesk.
4. Создать пользователя supportdesk_user.
5. Создать таблицы tickets и позже ticket_events.
6. Переписать app storage layer:
   tickets.json -> PostgreSQL queries.
7. Вынести DB config в env file.
8. Проверить create/list/status/resolved flow.
```

Минимальная таблица `tickets`:

```text
id
resource
category
description
priority
status
source
created_at
updated_at
resolved_at
```

Ожидаемый итог:

```text
Заявки больше не лежат в одном JSON-файле.
Появляется нормальное persistent storage с фильтрацией, историей и будущими backup/restore сценариями.
```

Что теперь можно делать:

```sql
select resource, count(*) from tickets group by resource;
select * from tickets where status = 'resolved';
```

## Этап 17. DB observability и backups

Цель: сделать БД наблюдаемой и восстановимой.

Что сделать:

```text
1. node_exporter на db.
2. postgres_exporter на db.
3. Prometheus scrape для db metrics.
4. Grafana panels:
   - PostgreSQL UP
   - DB size
   - connections
   - transaction rate
5. Alerts:
   - PostgreSQLDown
   - TooManyConnections
   - DatabaseDiskUsageHigh
6. Backup:
   - pg_dump script
   - systemd timer или cron
   - restore test
```

Ожидаемый итог:

```text
БД становится полноценным инфраструктурным компонентом,
а не черным ящиком за backend-ом.
```

Что теперь можно делать:

```text
Остановить PostgreSQL
→ PostgreSQLDown alert

Сделать backup
→ удалить тестовую заявку
→ восстановить backup
→ показать recovery story
```

## Этап 18. Telegram support bot

Цель: добавить второго клиента к тому же backend API.

Архитектура:

```text
Browser -> web -> app -> db
Telegram -> support-bot.service/container -> app -> db
```

Что сделать:

```text
1. Реализовать support-bot через long polling.
2. Использовать уже проверенный Windows portproxy workaround.
3. Хранить bot token в env-файле, не в коде.
4. Команды:
   /start
   /new
   /tickets
   /resolve
5. Все действия бота делать через app API.
6. В tickets писать source=telegram.
7. Bot logs отправлять в Loki отдельным service/job.
8. Позже добавить bot metrics.
```

Ожидаемый итог:

```text
Mini Support Desk получает два клиента: web UI и Telegram bot.
Оба работают через один backend API и одну БД.
```

Что теперь можно делать:

```text
Создать заявку из Telegram
→ увидеть source=telegram в UI/logs/metrics
→ закрыть заявку из web или Telegram
```

## Этап 19. Security/network hardening

Цель: приблизить сетевую модель к production-like варианту.

Что сделать:

```text
1. Ограничить прямой доступ к app:8080:
   разрешить только web/admin/bot.
2. Ограничить db:5432:
   разрешить только app/admin.
3. Добавить Nginx hardening:
   - security headers;
   - body size limit;
   - proxy timeouts;
   - rate limiting.
4. Добавить HTTPS на web:
   - self-signed cert для lab;
   - или локальный CA.
5. Секреты:
   - bot token не в Git;
   - DB password в env-файле;
   - права 600 на env-файлы.
6. Сделать DHCP reservation или static IP.
```

Ожидаемый итог:

```text
Пользователь ходит в web,
web ходит в app,
app ходит в db,
а не все узлы ходят напрямую ко всем сервисам.
```

Что теперь можно делать:

```text
curl app:8080 напрямую с неразрешенного узла
→ отказ

curl web/api/health
→ работает
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

Ожидаемый итог:

```text
Проект становится воспроизводимым: важные конфиги и деплой раскатываются не руками, а Ansible playbook-ами.
```

Что теперь можно делать:

```bash
ansible-playbook playbooks/deploy_app.yml
ansible-playbook playbooks/deploy_prometheus_rules.yml
ansible-playbook playbooks/deploy_bot.yml
ansible-playbook playbooks/backup_postgres.yml
```

## Этап 21. Финальная документация, README и demo packaging

Цель: упаковать проект как законченный pet-project.

Что подготовить:

```text
1. README с архитектурой.
2. IP/порты/сервисы.
3. Data flows:
   Browser -> web -> app -> db
   app/web/bot -> logs -> Loki -> Grafana
   Prometheus -> exporters -> Alertmanager/Grafana
4. Команды проверки.
5. Dashboard screenshots.
6. Alerts list.
7. Demo сценарии.
8. Troubleshooting scenarios.
9. Backup/restore scenario.
10. Snapshots/контрольные точки в Proxmox.
```

Ожидаемый итог:

```text
Проект можно показывать на собеседовании или в портфолио как end-to-end infrastructure lab.
```

Что теперь можно делать:

```text
За 5–10 минут показать:
- нормальный product flow;
- logs;
- metrics;
- alerts;
- app down recovery;
- DB backup/restore;
- Telegram-created ticket;
- Ansible-managed configs.
```

---

# Текущий маркер прогресса

```text
Последний завершенный этап: Этап 11. Admin/Ansible foundation.
Текущий следующий этап: Этап 12. Product model v2.
Далее: Product model v2, Product observability v2, HTTP/error-rate metrics, Dockerization, PostgreSQL, DB observability, Telegram bot, hardening, Ansible automation v2, final README/demo.
```

## Текущий прогресс проекта

Важно: прогресс пересчитан относительно нового расширенного production-like roadmap. Поэтому процент стал ниже, чем в старом roadmap, где проект был почти завершен по первоначальному scope.

```text
Формальная готовность по расширенному roadmap: 11/21 основных этапов завершены ≈ 52%.
Готовность core infrastructure lab: 100% по этапам 1–10.
Admin/Ansible foundation: 100%.
Инженерная готовность по новому production-like scope: 58–63%.
Демонстрационная готовность текущего core-проекта: 85–88%.
Финальная демонстрационная готовность с DB/Docker/Bot/Ansible: 48–58%.
```

Разбивка по этапам:

| Этап | Статус | Готовность | Комментарий |
|---|---:|---:|---|
| 1. Loki на log | завершено | 100% | Loki работает как systemd service и принимает logs. |
| 2. Promtail на web | завершено | 100% | nginx logs уходят в Loki. |
| 3. Promtail на app | завершено | 100% | app product logs уходят в Loki. |
| 4. Monitor base stack | завершено | 100% | Prometheus, Grafana, Alertmanager, node_exporter active/enabled. |
| 5. Метрики node_exporter | завершено | 100% | Prometheus видит node targets `4/4 up`. |
| 6. Grafana datasources | завершено | 100% | Prometheus и Loki подключены к Grafana. |
| 7. Grafana dashboard Infrastructure Overview | завершено | 100% | Есть рабочий обзорный dashboard. |
| 8. Web/App integration | завершено | 100% | Mini Support Desk работает через `Browser -> web -> app`. |
| 9. Полировка logging | завершено | 100% | Product logs, proxy metadata, status unchanged, LogQL/panel, Promtail label. |
| 10. Полировка monitoring | завершено | 100% | App metrics, product panels, active alerts, alert rules. |
| 11. Admin/Ansible foundation | завершено | 100% | SSH keys, inventory, ansible.cfg, playbook-и и Git repo готовы. |
| 12. Product model v2 | следующий этап | 0–10% | Resource/category/active-resolved/API v1 еще не реализованы. |
| 13. Product observability v2 | план | 0–10% | Metrics/alerts by resource/category еще не реализованы. |
| 14. HTTP request/error-rate observability | план | 0–10% | Request metrics, latency и error-rate alerts еще не реализованы. |
| 15. Dockerization | план | 0–5% | Docker пока не внедрен, но добавлен как будущий этап. |
| 16. PostgreSQL migration | план | 0–5% | Сейчас используется `/opt/app/tickets.json`. |
| 17. DB observability + backups | план | 0–5% | Зависит от появления DB server. |
| 18. Telegram support bot | plan/future | 5–10% | Сетевой workaround проверен, сам bot еще не реализован. |
| 19. Security/network hardening | план | 5–10% | Есть proxy headers, но ограничения доступа/HTTPS еще впереди. |
| 20. Ansible automation v2 | план | 0–10% | Зависит от этапа Admin/Ansible foundation. |
| 21. Final README/demo packaging | план | 20–30% | Sources ведутся, но финальный README/demo/snapshots еще не собраны. |

Короткая интерпретация:

```text
Проект уже можно демонстрировать как работающий infrastructure lab с web/app/logging/monitoring/alerts и базовым Ansible control node.
Новый roadmap расширяет цель до production-like стенда с automation, product model v2, Docker, PostgreSQL, Telegram bot, hardening и финальным demo package.
```

---

# Future improvements

Подробный backlog будущих улучшений вынесен отдельно в файл:

```text
12_future_improvements_backlog.md
```
