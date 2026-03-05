# Чек-лист следующих шагов

## Завершено: logging base

- [x] Loki 3.5.0 установлен на `log`.
- [x] `loki.service` active/enabled.
- [x] Loki принимает nginx logs от `web`.
- [x] Loki принимает app logs от `app`.
- [x] Promtail установлен на `web`.
- [x] Promtail на `web` читает `/var/log/nginx/*.log`.
- [x] Promtail установлен на `app`.
- [x] Promtail на `app` читает `/var/log/app/*.log`.

## Завершено: monitor base stack

- [x] Создана VM `monitor`.
- [x] Prometheus active/enabled.
- [x] Grafana active/enabled.
- [x] Alertmanager active/enabled.
- [x] Prometheus видит Alertmanager.
- [x] node_exporter работает на `monitor`.

## Завершено: node_exporter + Prometheus targets

- [x] node_exporter установлен на `web`.
- [x] node_exporter установлен на `app`.
- [x] node_exporter установлен на `log`.
- [x] node_exporter работает на `monitor`.
- [x] Prometheus показывает `node (4/4 up)`.

## Завершено: Grafana datasources

- [x] Prometheus datasource подключен.
- [x] Loki datasource подключен.
- [x] `up{job="node"}` показывает `web`, `app`, `log`, `monitor`.
- [x] Loki показывает nginx logs и app logs.

## Завершено: Grafana dashboard Infrastructure Overview

- [x] Создан dashboard `Infrastructure Overview`.
- [x] Добавлены panels Targets UP, CPU, RAM, Disk.
- [x] Добавлены panels Web nginx logs и App logs.

## Завершено: Web/App integration

- [x] Выбрана продуктовая реализация: Mini Support Desk.
- [x] На `app` создан backup `/opt/app/app.py.bak-before-supportdesk`.
- [x] Backend заменен на `support-desk-api`.
- [x] `app.service` перезапущен и active/running.
- [x] Проверены `/health`, `/tickets`, `POST /tickets`, `PATCH /tickets/<id>/status`, `/metrics`.
- [x] Создан `/opt/app/tickets.json`.
- [x] App пишет product logs `service=support-desk-api event=...`.
- [x] На `web` настроен Nginx reverse proxy `/api/* -> http://192.168.85.133:8080/`.
- [x] На `web` заменен frontend на Mini Support Desk.
- [x] Browser -> web -> app flow подтвержден.
- [x] Через браузер создана тестовая заявка.
- [x] Через браузер изменен статус заявки.
- [x] `nginx access.log` показывает `GET/POST/PATCH /api/*`.
- [x] `app.log` показывает product events.
- [x] Grafana Explore/Loki видит product logs.

## Завершено: Полировка logging

- [x] Финализирован формат product logs в `key=value` формате.
- [x] Добавлен `clean_log_value()`.
- [x] `client_ip` оставлен как TCP peer backend-а.
- [x] Добавлены `x_forwarded_for` и `x_forwarded_proto`.
- [x] `x_real_ip` сознательно не логируется, чтобы не дублировать `x_forwarded_for` в текущей схеме.
- [x] `old_status == new_status` пишет `event=ticket_status_unchanged`.
- [x] Реальные изменения статуса пишут `event=ticket_status_changed`.
- [x] Подтверждены `ticket_validation_failed`, `ticket_not_found`, `endpoint_not_found`.
- [x] App logs panel в Grafana обновлена под `event=...` формат.
- [x] Promtail label на `app` изменен с `service=python-backend` на `service=support-desk-api`.
- [x] Новые logs доступны по LogQL `{host="app", job="app", service="support-desk-api"}`.

## Завершено: Полировка monitoring

- [x] Проверен доступ `monitor -> app:8080/metrics`.
- [x] В Prometheus добавлен scrape job `supportdesk-api`.
- [x] Target `supportdesk-api` показывает `1/1 up`.
- [x] Prometheus видит `supportdesk_tickets_total`, `supportdesk_tickets_open`, `supportdesk_tickets_in_progress`, `supportdesk_tickets_resolved`.
- [x] В Grafana добавлена panel `SupportDesk Tickets`.
- [x] В Grafana добавлена panel `SupportDesk API UP`.
- [x] В Grafana добавлена panel `Active Alerts`.
- [x] Создан `/etc/prometheus/supportdesk.rules.yml`.
- [x] В `prometheus.yml` подключен `rule_files` для `supportdesk.rules.yml`.
- [x] Alert `SupportDeskApiDown` добавлен и протестирован.
- [x] Alert `TooManyOpenTickets` добавлен и протестирован.
- [x] Alert `HighDiskUsage` добавлен и протестирован через временный порог.
- [x] Alert `NodeTargetDown` добавлен и протестирован.
- [x] Проверено, что Alertmanager получает alert через `amtool`.

## Завершено: Admin/Ansible foundation

- [x] Раскатаны SSH-ключи с `admin` на `web`, `app`, `log`, `monitor`.
- [x] Проверен SSH-вход с `admin` на managed nodes без пароля пользователя.
- [x] Расширен Ansible inventory всеми узлами.
- [x] Группы inventory приведены к виду `web_nodes`, `app_nodes`, `log_nodes`, `monitor_nodes`, чтобы не было конфликтов имени host/group.
- [x] Добавлена группа `managed` как children-группа для `web/app/log/monitor`.
- [x] Проверены `ansible all -m ping` и `ansible managed -m ping`.
- [x] Создана структура `~/control-node`: `inventory/`, `playbooks/`, `roles/`, `templates/`, `files/`, `docs/`.
- [x] Добавлен `ansible.cfg`; подтверждено, что Ansible использует `/home/pelmel/control-node/ansible.cfg`.
- [x] Создан `playbooks/ping_all.yml`.
- [x] Создан и проверен `playbooks/check_services.yml`.
- [x] Создан и проверен `playbooks/restart_app.yml` с `become: true`, `vars_prompt`, restart `app.service` и healthcheck.
- [x] Создан и проверен `playbooks/deploy_prometheus_rules.yml` с `promtool` validation, handler restart Prometheus и readiness check.
- [x] Локальный source-файл Prometheus rules сохранен в `files/prometheus/supportdesk.rules.yml`.
- [x] Инициализирован Git repo в `~/control-node`.
- [x] Настроены локальные Git user.name/user.email.
- [x] Сделан первый commit `initial Ansible control node setup`.
- [x] Добавлены `.gitkeep` для пустых директорий `roles/`, `templates/`, `docs/` и сделан commit `Add Ansible project directory placeholders`.

## Текущий следующий этап: Product model v2

- [ ] Заменить/дополнить `Title` на `Resource` dropdown.
- [ ] Добавить `Category` dropdown.
- [ ] Добавить поля `resource`, `category`, `resolved_at` в ticket model.
- [ ] Сделать active/resolved разделение заявок.
- [ ] Сделать так, чтобы resolved-заявки исчезали из active list, но сохранялись в истории.
- [ ] Подготовить переход к `/api/v1/*`.

## Далее: Product observability v2

- [ ] Добавить metrics by resource/category/priority/source.
- [ ] Добавить panels по resource/category.
- [ ] Добавить `SupportDeskTooManyTicketsForResource`.
- [ ] Добавить `SupportDeskCategoryIncident`.
- [ ] Добавить `SupportDeskCriticalTicketsOpen`.

## Далее: HTTP/request observability

- [ ] Перейти на Prometheus client library или расширить ручной `/metrics`.
- [ ] Добавить `supportdesk_requests_total{method,path,status}`.
- [ ] Добавить `supportdesk_errors_total{status}`.
- [ ] Добавить `supportdesk_request_duration_seconds`.
- [ ] Добавить HTTP status / error-rate alerts.

## Далее: Dockerization

- [ ] Создать Dockerfile для `support-desk-api`.
- [ ] Создать `docker-compose.yml` на `app`.
- [ ] Оставить внешний порт `8080`.
- [ ] Сохранить app logs через volume `/var/log/app/app.log`.
- [ ] Проверить, что Nginx, Prometheus и Promtail продолжают работать без изменения внешнего flow.
- [ ] Позже контейнеризировать `support-bot`.

## Далее: PostgreSQL / DB

- [ ] Создать отдельную VM `db`.
- [ ] Установить PostgreSQL.
- [ ] Создать DB/user/schema.
- [ ] Перевести app storage с `/opt/app/tickets.json` на PostgreSQL.
- [ ] Добавить DB env-файл для app.
- [ ] Добавить postgres_exporter.
- [ ] Добавить DB alerts.
- [ ] Добавить backup/restore через `pg_dump`.

## Далее: Telegram support bot

- [ ] Реализовать `support-bot` через long polling.
- [ ] Использовать Windows portproxy workaround для Telegram API.
- [ ] Хранить bot token в env-файле.
- [ ] Создавать/читать/закрывать tickets через тот же app API.
- [ ] Писать `source=telegram`.
- [ ] Отправлять bot logs в Loki.

## Далее: hardening и финализация

- [ ] Ограничить прямой доступ к `app:8080`.
- [ ] Ограничить прямой доступ к `db:5432`.
- [ ] Добавить Nginx hardening.
- [ ] Добавить HTTPS/self-signed cert или local CA.
- [ ] Сделать DHCP reservation или static IP.
- [ ] Автоматизировать новую архитектуру через Ansible.
- [ ] Собрать финальный README.
- [ ] Подготовить screenshots и demo сценарии.
- [ ] Сделать Proxmox snapshots.

## Future backlog

Подробный список будущих улучшений вынесен в:

```text
12_future_improvements_backlog.md
```
