# Чек-лист следующих шагов

## Завершено: logging stage

### Loki на log

- [x] Loki 3.5.0 установлен.
- [x] `loki.service` active/enabled.
- [x] `/ready -> ready`.
- [x] Loki принимает nginx logs от `web`.
- [x] Loki принимает app logs от `app`.
- [x] Исправлен autostart после reboot через:
  - `common.ring.instance_addr: 127.0.0.1`;
  - `memberlist.advertise_addr: 127.0.0.1`.

### Promtail на web

- [x] Promtail 3.5.0 установлен.
- [x] `promtail.service` active/enabled.
- [x] Promtail читает `/var/log/nginx/*.log`.
- [x] Promtail отправляет nginx logs в Loki.
- [x] Loki query_range возвращает `{host="web",job="nginx"}`.

### Promtail на app

- [x] Приложение пишет logs в `/var/log/app/app.log`.
- [x] Promtail 3.5.0 установлен.
- [x] `promtail.service` active/enabled.
- [x] Promtail читает `/var/log/app/*.log`.
- [x] Promtail отправляет app logs в Loki.
- [x] Loki query_range возвращает `{host="app",job="app"}`.

## Завершено: monitor base stack

- [x] Создать VM `monitor`.
- [x] Установить Debian 13.
- [x] Настроить hostname `monitor`.
- [x] Получить IP `192.168.85.137/24`.
- [x] Настроить SSH.
- [x] Настроить sudo для `pelmel`.
- [x] Поставить базовые админские пакеты.
- [x] Проверить связность с `admin`, `web`, `app`, `log`.
- [x] Проверить доступ к Loki с `monitor`.
- [x] Установить Prometheus.
- [x] Проверить `prometheus.service active/enabled`.
- [x] Проверить порт `9090`.
- [x] Проверить `curl http://localhost:9090/-/ready`.
- [x] Проверить Prometheus UI с Windows.
- [x] Проверить Prometheus API query `up`.
- [x] Установить Grafana через локальный `.deb`.
- [x] Проверить `grafana-server active/enabled`.
- [x] Проверить порт `3000`.
- [x] Проверить Grafana UI с Windows.
- [x] Почистить временные файлы/ключи/неудачный Grafana repo.
- [x] Установить Alertmanager.
- [x] Проверить `prometheus-alertmanager active/enabled`.
- [x] Проверить порт `9093`.
- [x] Проверить `curl http://localhost:9093/-/ready -> OK`.
- [x] Проверить, что Prometheus видит Alertmanager через `/api/v1/alertmanagers`.
- [x] Проверить локальный `node_exporter` на `monitor`.
- [x] Проверить порт `9100` на `monitor`.
- [x] Проверить `curl -s http://localhost:9100/metrics | head`.

Итог: `monitor` работает как базовый observability node: Prometheus, Grafana, Alertmanager и локальный node_exporter активны и включены в автозапуск.

## Нужно сделать позже: IP reservation/static

Сейчас IP адреса VM получены через DHCP VMware NAT и держатся стабильно.

Позже нужно:
- [ ] сделать DHCP reservation по MAC-адресам VM; или
- [ ] настроить статические IP внутри Debian;
- [ ] после фиксации IP обновить sources и Ansible inventory.

## Завершено: node_exporter на web/app/log + Prometheus targets

На `monitor` node_exporter уже работал. На этом этапе добавлены остальные узлы.

- [x] Установить `prometheus-node-exporter` на `web`.
- [x] Проверить на `web`: `systemctl status prometheus-node-exporter --no-pager`.
- [x] Проверить на `web`: `curl -s http://localhost:9100/metrics | head`.
- [x] Проверить с `monitor`: `curl -s http://192.168.85.131:9100/metrics | head`.

- [x] Установить `prometheus-node-exporter` на `app`.
- [x] Проверить на `app`: `systemctl status prometheus-node-exporter --no-pager`.
- [x] Проверить на `app`: `curl -s http://localhost:9100/metrics | head`.
- [x] Проверить с `monitor`: `curl -s http://192.168.85.133:9100/metrics | head`.

- [x] Установить `prometheus-node-exporter` на `log`.
- [x] Проверить на `log`: `systemctl status prometheus-node-exporter --no-pager`.
- [x] Проверить на `log`: `curl -s http://localhost:9100/metrics | head`.
- [x] Проверить с `monitor`: `curl -s http://192.168.85.135:9100/metrics | head`.

После установки:
- [x] Добавить targets в `/etc/prometheus/prometheus.yml`.
- [x] Добавить labels `host="monitor"`, `host="web"`, `host="app"`, `host="log"`.
- [x] Проверить конфиг Prometheus через `promtool check config`.
- [x] Перезагрузить Prometheus.
- [x] Проверить Prometheus Targets UI.
- [x] Проверить, что все node targets `UP`.

Подтверждено:

```text
prometheus (1/1 up)
node (4/4 up)
```

Закрепленная теория этапа:

```text
node_exporter + Prometheus = pull-модель метрик.
Prometheus сам приходит на :9100/metrics и забирает метрики.
Promtail + Loki = push-модель логов.
Promtail сам отправляет logs в Loki на /loki/api/v1/push.
```

## Завершено: Grafana datasources

- [x] Добавить Prometheus datasource.
- [x] URL: `http://localhost:9090`.
- [x] Нажать `Save & test`.
- [x] Проверить запрос `up{job="node"}`.
- [x] Подтверждено: 4 series со значением `1` для `web`, `app`, `log`, `monitor`.
- [x] Добавить Loki datasource.
- [x] URL: `http://192.168.85.135:3100`.
- [x] Нажать `Save & test`.
- [x] Проверить Loki-запрос `{host="web", job="nginx"}`.
- [x] Подтверждено: видны nginx access logs с `web`.
- [x] Проверить Loki-запрос `{host="app", job="app"}`.
- [x] Подтверждено: видны app logs с `path=/`, `path=/health`, `path=/bad-endpoint`, `status=200`, `status=404`.

## Текущий следующий этап: web/app integration

### web/app integration

- [ ] Улучшить Python app при необходимости.
- [ ] Добавить `/info`.
- [ ] Добавить `/api/time`.
- [ ] Настроить Nginx reverse proxy `/api/*` -> `app:8080`.
- [ ] Проверить `curl http://192.168.85.131/api/health`.
- [ ] Обновить frontend-страницу на `web`, чтобы она показывала связь с backend.
- [ ] Проверить Browser -> web -> app.
- [ ] Сгенерировать web/app запросы и проверить, что они появились в Grafana dashboard logs panels.

### Dashboards — позже

- [x] Dashboard Infrastructure Overview.
- [ ] Dashboard Web.
- [ ] Dashboard App.
- [ ] Dashboard Logs.

### Alerts — позже, как часть полировки monitoring

- [ ] Alert `TargetDown`: один из Prometheus targets недоступен.
- [ ] Alert `AppHealthFail`: backend health endpoint недоступен.
- [ ] Alert `HighDiskUsage`: высокий процент использования диска.

### Финал

- [ ] README.
- [ ] IP/порты/сервисы.
- [ ] Команды проверки.
- [ ] Snapshots.
- [ ] Ansible inventory.
- [ ] Первые playbook'и.
- [ ] Демонстрационный сценарий.

## Завершено: Grafana dashboard Infrastructure Overview

- [x] Создать dashboard `Infrastructure Overview`.
- [x] Добавить panel `Targets UP`.
- [x] PromQL: `up{job="node"}`.
- [x] Настроить `Legend: {{host}}`.
- [x] Настроить value mappings: `1 -> UP`, `0 -> DOWN`.
- [x] Подтверждено: `web`, `app`, `log`, `monitor` отображаются как `UP`.
- [x] Добавить panel `CPU Usage by host`.
- [x] PromQL: `100 - (avg by (host) (rate(node_cpu_seconds_total{job="node", mode="idle"}[5m])) * 100)`.
- [x] Добавить panel `RAM Usage by host`.
- [x] PromQL: `100 * (1 - (node_memory_MemAvailable_bytes{job="node"} / node_memory_MemTotal_bytes{job="node"}))`.
- [x] Добавить panel `Disk Usage by host`.
- [x] PromQL для `/`: `100 * (1 - (node_filesystem_avail_bytes / node_filesystem_size_bytes))` с фильтрами `job="node"`, `mountpoint="/"`, `fstype!~"tmpfs|overlay|squashfs"`.
- [x] Добавить panel `Web nginx logs`.
- [x] Loki datasource, LogQL: `{host="web", job="nginx"}` с `regexp` и `line_format` для короткого отображения method/path/status/client_ip.
- [x] Добавить panel `App logs`.
- [x] Loki datasource, LogQL: `{host="app", job="app"}` с `regexp` и `line_format` для короткого отображения level/method/path/status/client_ip.
- [x] Сгенерировать свежие web/app запросы через `curl`, чтобы log-панели не были пустыми.
- [x] Сохранить dashboard.

Итог: первый обзорный dashboard готов. Он показывает состояние всех monitored nodes и свежие web/app logs из Loki.

## Следующий практический этап: web/app integration

- [ ] Настроить Nginx на `web` как reverse proxy для `/api/*` -> `192.168.85.133:8080`.
- [ ] Проверить конфиг Nginx через `sudo nginx -t`.
- [ ] Перезагрузить Nginx.
- [ ] Проверить `curl http://192.168.85.131/api/health`.
- [ ] Обновить HTML-страницу на `web`, чтобы она демонстрировала связь frontend/backend.
- [ ] Проверить пользовательский поток Browser -> web -> app.
- [ ] Проверить, что новые запросы видны в Web nginx logs и App logs на dashboard `Infrastructure Overview`.

Базовые alerts (`TargetDown`, `HighDiskUsage`, позже `AppHealthFail`) перенесены в следующий этап полировки monitoring, после связки `web` и `app`.
