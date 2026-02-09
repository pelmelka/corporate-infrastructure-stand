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

## Текущий следующий этап: node_exporter на web/app/log

На `monitor` node_exporter уже работает.

Дальше:
- [ ] Установить `prometheus-node-exporter` на `web`.
- [ ] Проверить на `web`: `systemctl status prometheus-node-exporter --no-pager`.
- [ ] Проверить на `web`: `curl -s http://localhost:9100/metrics | head`.
- [ ] Проверить с `monitor`: `curl -s http://192.168.85.131:9100/metrics | head`.

- [ ] Установить `prometheus-node-exporter` на `app`.
- [ ] Проверить на `app`: `systemctl status prometheus-node-exporter --no-pager`.
- [ ] Проверить на `app`: `curl -s http://localhost:9100/metrics | head`.
- [ ] Проверить с `monitor`: `curl -s http://192.168.85.133:9100/metrics | head`.

- [ ] Установить `prometheus-node-exporter` на `log`.
- [ ] Проверить на `log`: `systemctl status prometheus-node-exporter --no-pager`.
- [ ] Проверить на `log`: `curl -s http://localhost:9100/metrics | head`.
- [ ] Проверить с `monitor`: `curl -s http://192.168.85.135:9100/metrics | head`.

После установки:
- [ ] Добавить targets в `/etc/prometheus/prometheus.yml`.
- [ ] Проверить конфиг Prometheus.
- [ ] Перезапустить/перезагрузить Prometheus.
- [ ] Проверить Prometheus Targets UI.
- [ ] Проверить, что все node targets `UP`.

## Дальше после node_exporter

### Grafana datasources

- [ ] Добавить Prometheus datasource.
- [ ] Добавить Loki datasource.
- [ ] Проверить запросы к Prometheus.
- [ ] Проверить Loki-запрос `{host="web",job="nginx"}`.
- [ ] Проверить Loki-запрос `{host="app",job="app"}`.

### Dashboards и alerts

- [ ] Dashboard Infrastructure Overview.
- [ ] Dashboard Web.
- [ ] Dashboard App.
- [ ] Dashboard Logs.
- [ ] Alert target down.
- [ ] Alert app health fail.
- [ ] Alert disk usage warning.

### web/app integration

- [ ] Улучшить Python app.
- [ ] Добавить `/info`.
- [ ] Добавить `/api/time`.
- [ ] Настроить Nginx reverse proxy `/api/*` -> `app:8080`.
- [ ] Обновить frontend-страницу.
- [ ] Проверить Browser -> web -> app.

### Финал

- [ ] README.
- [ ] IP/порты/сервисы.
- [ ] Команды проверки.
- [ ] Snapshots.
- [ ] Ansible inventory.
- [ ] Первые playbook'и.
- [ ] Демонстрационный сценарий.
