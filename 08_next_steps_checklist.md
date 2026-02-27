# Чек-лист следующих шагов

## Завершено: logging stage

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
- [x] На `web` создан backup `/etc/nginx/sites-available/default.bak-before-supportdesk-proxy`.
- [x] Настроен Nginx reverse proxy `/api/* -> http://192.168.85.133:8080/`.
- [x] Проверен `sudo nginx -t`.
- [x] Выполнен `sudo systemctl reload nginx`.
- [x] На `web` создан backup `/var/www/html/index.html.bak-before-supportdesk`.
- [x] HTML-страница заменена на Mini Support Desk frontend.
- [x] Browser -> web -> app flow подтвержден.
- [x] Через браузер создана тестовая заявка.
- [x] Через браузер изменен статус заявки.
- [x] `nginx access.log` показывает `GET/POST/PATCH /api/*`.
- [x] `app.log` показывает `ticket_created`, `ticket_status_changed`, `ticket_list_requested`, `health_check`.
- [x] Grafana Explore/Loki видит новые product logs запросом `{host="app", job="app"} |= "support-desk-api"`.

## Текущий следующий этап: Полировка logging

- [ ] Финализировать формат product logs.
- [ ] Обновить LogQL для App logs под формат `event=...`.
- [ ] Проверить удобные Loki-запросы по `ticket_created`, `ticket_status_changed`, `ticket_validation_failed`.
- [ ] Решить поведение `old_status == new_status`.
- [ ] Улучшить логирование proxy metadata: `client_ip`, `x_real_ip`, `x_forwarded_for`.
- [ ] Рассмотреть переход app logs с key=value на structured JSON logs.
- [ ] Рассмотреть обновление Promtail label `service` с `python-backend` на `support-desk-api`.

## Следующий этап: Полировка monitoring

- [ ] Добавить Prometheus scrape для `app:/metrics`.
- [ ] Сделать panels по product metrics.
- [ ] Рассмотреть переход с ручного `/metrics` на Prometheus client library.
- [ ] Добавить product alerts и infrastructure alerts.

## Позже: Ansible/admin polish

- [ ] Раскатать SSH-ключи с `admin`.
- [ ] Расширить Ansible inventory.
- [ ] Создать первые playbook'и.

## Позже: финальная документация

- [ ] README.
- [ ] IP/порты/сервисы.
- [ ] Команды проверки.
- [ ] Snapshots.
- [ ] Демонстрационный сценарий.

## Future backlog

Подробный список будущих улучшений вынесен в:

```text
12_future_improvements_backlog.md
```
