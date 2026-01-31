# Чек-лист следующих шагов

## Loki на log — завершено

- [x] Убедиться, что ручной Loki остановлен.
- [x] Проверить, что порт 3100 свободен: `ss -tulpn | grep :3100`.
- [x] Создать `/etc/systemd/system/loki.service`.
- [x] Выполнить `sudo systemctl daemon-reload`.
- [x] Выполнить `sudo systemctl enable --now loki.service`.
- [x] Проверить `systemctl status loki.service --no-pager`.
- [x] Проверить `ss -tulpn | grep :3100`.
- [x] Проверить `curl http://localhost:3100/ready`.
- [x] Проверить с `admin`: `curl http://192.168.85.135:3100/ready`.

Итог: Loki работает как `systemd` service, включен в автозапуск, порт `3100` слушается, `/ready` возвращает `ready` локально и с `admin`.

## Promtail на web — завершено

- [x] Подключиться к `web`: `ssh pelmel@192.168.85.131`.
- [x] Проверить наличие nginx logs: `ls -l /var/log/nginx/`.
- [x] Скачать/установить Promtail 3.5.0.
- [x] Создать пользователя `promtail`.
- [x] Добавить пользователя `promtail` в группу `adm` для чтения nginx logs.
- [x] Создать директории `/opt/promtail`, `/etc/promtail`, `/var/lib/promtail`.
- [x] Настроить Promtail config: `/etc/promtail/config.yml`.
- [x] Читать `/var/log/nginx/access.log`.
- [x] Читать `/var/log/nginx/error.log`.
- [x] Отправлять в Loki `http://192.168.85.135:3100/loki/api/v1/push`.
- [x] Создать `/etc/systemd/system/promtail.service`.
- [x] Запустить Promtail как systemd service.
- [x] Проверить `promtail.service active/enabled`.
- [x] Проверить порт Promtail `9080`.
- [x] Сгенерировать HTTP-запросы к web.
- [x] Убедиться, что логи появились локально в `/var/log/nginx/access.log`.
- [x] Убедиться, что nginx logs дошли в Loki через `query_range`.

Итог: Promtail на `web` работает, nginx logs уходят в Loki и находятся запросом `{host="web",job="nginx"}`. Labels согласованы: `host=web`, `job=nginx`, `service=frontend`, `env=lab`.

## Promtail на app — завершено

- [x] Решить, app logs через файл или journald.
- [x] Выбран вариант через отдельный файл логов.
- [x] Создать `/var/log/app/app.log`.
- [x] Настроить права: `/var/log/app` = `pelmel:adm 750`, `/var/log/app/app.log` = `pelmel:adm 640`.
- [x] Сделать backup `/opt/app/app.py.bak-before-logging`.
- [x] Изменить `/opt/app/app.py`, чтобы приложение писало полезные логи в `/var/log/app/app.log`.
- [x] Перезапустить `app.service`.
- [x] Проверить, что `app.service active/running`.
- [x] Дернуть `/`, `/health`, плохой endpoint.
- [x] Убедиться, что app logs появились локально в `/var/log/app/app.log`.
- [x] Подключиться к `app`: `ssh pelmel@192.168.85.133`.
- [x] Скачать/установить Promtail 3.5.0.
- [x] Создать пользователя `promtail`.
- [x] Добавить пользователя `promtail` в группу `adm`.
- [x] Создать директории `/opt/promtail`, `/etc/promtail`, `/var/lib/promtail`.
- [x] Проверить, что `promtail` может читать `/var/log/app/app.log`.
- [x] Настроить Promtail config.
- [x] Добавить labels: `host=app`, `job=app`, `service=python-backend`, `env=lab`.
- [x] Проверить синтаксис конфига Promtail.
- [x] Создать `/etc/systemd/system/promtail.service`.
- [x] Запустить Promtail как service.
- [x] Проверить `promtail.service active/enabled`.
- [x] Проверить порт Promtail `9080`.
- [x] Проверить, что Promtail начал читать `/var/log/app/app.log`.
- [x] Дернуть `/`, `/health`, плохой endpoint.
- [x] Убедиться, что app logs дошли в Loki через `query_range`.

Итог: Promtail на `app` работает, app logs уходят в Loki и находятся запросом `{host="app",job="app"}`. Labels согласованы: `host=app`, `job=app`, `service=python-backend`, `env=lab`.

## monitor — текущий следующий этап

- [ ] Создать VM `monitor`.
- [ ] Установить Debian 13.
- [ ] Настроить hostname `monitor`.
- [ ] Настроить IP-адрес в сети `192.168.85.0/24`.
- [ ] Настроить SSH.
- [ ] Настроить sudo для пользователя `pelmel`.
- [ ] Обновить систему.
- [ ] Проверить сетевую связность с `admin`, `web`, `app`, `log`.
- [ ] Установить Prometheus.
- [ ] Установить Grafana.
- [ ] Установить Alertmanager.
- [ ] Проверить порты 3000, 9090, 9093.
- [ ] Проверить сервисы `active/enabled`.

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
- [ ] Проверить Loki-запрос `{host="web",job="nginx"}`.
- [ ] Проверить Loki-запрос `{host="app",job="app"}`.

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
