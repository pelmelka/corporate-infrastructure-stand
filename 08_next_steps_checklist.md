# Чек-лист следующих шагов

## Завершить Loki на log

- [ ] Убедиться, что ручной Loki остановлен.
- [ ] Проверить, что порт 3100 свободен: `ss -tulpn | grep :3100`.
- [ ] Создать `/etc/systemd/system/loki.service`.
- [ ] Выполнить `sudo systemctl daemon-reload`.
- [ ] Выполнить `sudo systemctl enable --now loki.service`.
- [ ] Проверить `systemctl status loki.service --no-pager`.
- [ ] Проверить `ss -tulpn | grep :3100`.
- [ ] Проверить `curl http://localhost:3100/ready`.
- [ ] Проверить с `admin`: `curl http://192.168.85.135:3100/ready`.

Ожидаемый итог: Loki работает как systemd service.

## Promtail на web

- [ ] Скачать/установить Promtail.
- [ ] Настроить Promtail config.
- [ ] Читать `/var/log/nginx/access.log`.
- [ ] Читать `/var/log/nginx/error.log`.
- [ ] Отправлять в Loki `http://192.168.85.135:3100/loki/api/v1/push`.
- [ ] Запустить Promtail как systemd service.
- [ ] Сгенерировать HTTP-запросы к web.
- [ ] Убедиться, что логи дошли в Loki.

## Promtail на app

- [ ] Решить, app logs через файл или journald.
- [ ] Настроить Promtail.
- [ ] Добавить labels: `host=app`, `job=app`, `service=python-backend`, `env=lab`.
- [ ] Запустить Promtail как service.
- [ ] Дернуть `/` и `/health`.
- [ ] Убедиться, что app logs появились в Loki.

## monitor

- [ ] Создать VM `monitor`.
- [ ] Установить Debian 13.
- [ ] Настроить SSH.
- [ ] Настроить sudo.
- [ ] Обновить систему.
- [ ] Установить Prometheus.
- [ ] Установить Grafana.
- [ ] Установить Alertmanager.
- [ ] Проверить порты 3000, 9090, 9093.

## node_exporter

- [ ] Установить node_exporter на `web`.
- [ ] Установить node_exporter на `app`.
- [ ] Установить node_exporter на `log`.
- [ ] Возможно установить node_exporter на `monitor`.
- [ ] Добавить targets в Prometheus.
- [ ] Проверить targets в Prometheus UI.

## Grafana datasources

- [ ] Добавить Prometheus datasource.
- [ ] Добавить Loki datasource.
- [ ] Проверить запросы к Prometheus.
- [ ] Проверить запросы к Loki.

## web/app integration

- [ ] Улучшить Python app.
- [ ] Добавить `/info`.
- [ ] Добавить `/api/time`.
- [ ] Возможно перейти на Flask.
- [ ] Настроить Nginx reverse proxy `/api/*` -> `app:8080`.
- [ ] Обновить frontend-страницу.
- [ ] Проверить Browser -> web -> app.

## Dashboards и alerts

- [ ] Dashboard Infrastructure Overview.
- [ ] Dashboard Web.
- [ ] Dashboard App.
- [ ] Dashboard Logs.
- [ ] Alert target down.
- [ ] Alert app health fail.
- [ ] Alert disk usage warning, если нужно.

## Финал

- [ ] README.
- [ ] IP/порты/сервисы.
- [ ] Команды проверки.
- [ ] Snapshots.
- [ ] Ansible inventory.
- [ ] Первые playbook'и.
- [ ] Демонстрационный сценарий.
