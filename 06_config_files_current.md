# Важные текущие конфигурационные файлы проекта

## Ansible inventory

Файл:

```text
admin: ~/control-node/inventory/hosts.ini
```

Текущий минимальный вариант:

```ini
[control]
admin ansible_connection=local

[all:vars]
ansible_user=pelmel
```

Будущий вариант:

```ini
[control]
admin ansible_connection=local

[web]
web ansible_host=192.168.85.131

[app]
app ansible_host=192.168.85.133

[log]
log ansible_host=192.168.85.135

[monitor]
monitor ansible_host=192.168.85.137

[all:vars]
ansible_user=pelmel
```

## Loki config

Файл:

```text
log: /etc/loki/config.yml
```

Важный текущий фрагмент:

```yaml
common:
  ring:
    instance_addr: 127.0.0.1
    kvstore:
      store: inmemory

memberlist:
  advertise_addr: 127.0.0.1
```

Причина: без этих строк Loki 3.5.0 после reboot пытался найти `eth0/en0`, которых нет на Debian VM, где интерфейс называется `ens18`.

## Promtail config для web

Файл:

```text
web: /etc/promtail/config.yml
```

Важный фрагмент:

```yaml
clients:
  - url: http://192.168.85.135:3100/loki/api/v1/push

scrape_configs:
  - job_name: nginx
    static_configs:
      - targets:
          - localhost
        labels:
          host: web
          job: nginx
          service: frontend
          env: lab
          __path__: /var/log/nginx/*.log
```

## Promtail config для app

Файл:

```text
app: /etc/promtail/config.yml
```

Важный фрагмент:

```yaml
clients:
  - url: http://192.168.85.135:3100/loki/api/v1/push

scrape_configs:
  - job_name: app
    static_configs:
      - targets:
          - localhost
        labels:
          host: app
          job: app
          service: python-backend
          env: lab
          __path__: /var/log/app/*.log
```

## Prometheus config

Файл:

```text
monitor: /etc/prometheus/prometheus.yml
```

Проверенный фрагмент Alertmanager:

```yaml
alerting:
  alertmanagers:
    - static_configs:
      - targets: ['localhost:9093']
```

Проверка:

```bash
curl -s http://localhost:9090/api/v1/alertmanagers | python3 -m json.tool
```

Результат:

```json
{
    "status": "success",
    "data": {
        "activeAlertmanagers": [
            {
                "url": "http://localhost:9093/api/v2/alerts"
            }
        ],
        "droppedAlertmanagers": []
    }
}
```

Пока Prometheus видит локальные targets:

```text
job="prometheus", instance="localhost:9090"
job="node", instance="localhost:9100"
```

Будущий фрагмент после установки node_exporter на `web`, `app`, `log`:

```yaml
scrape_configs:
  - job_name: node
    static_configs:
      - targets:
          - localhost:9100
          - 192.168.85.131:9100
          - 192.168.85.133:9100
          - 192.168.85.135:9100
```

Важно: перед изменением нужно посмотреть фактический текущий `/etc/prometheus/prometheus.yml` и добавить targets без дублирования.

## Grafana

Grafana установлена на `monitor` через локальный `.deb`.

Сервис:

```text
monitor: grafana-server.service
```

Проверки:

```bash
systemctl is-enabled grafana-server
systemctl is-active grafana-server
ss -tulpn | grep :3000
curl -I http://localhost:3000
```

Подтверждено:

```text
enabled
active
*:3000 LISTEN
HTTP/1.1 302 Found
Location: /login
```

UI:

```text
http://192.168.85.137:3000
```

Datasources пока не добавлены.

Планируемые datasources:

```text
Prometheus: http://localhost:9090
Loki:       http://192.168.85.135:3100
```

## Alertmanager

Alertmanager установлен на `monitor` из пакета `prometheus-alertmanager`.

Сервис:

```text
monitor: prometheus-alertmanager.service
```

Проверки:

```bash
systemctl is-enabled prometheus-alertmanager
systemctl is-active prometheus-alertmanager
ss -tulpn | grep :9093
curl http://localhost:9093/-/ready
```

Подтверждено:

```text
enabled
active
*:9093 LISTEN
OK
```

Debian-пакет Alertmanager не включает полноценный web UI. По `http://192.168.85.137:9093` открывается простая HTML-страница с API/health links.

## node_exporter на monitor

Сервис:

```text
monitor: prometheus-node-exporter.service
```

Проверки:

```bash
systemctl is-enabled prometheus-node-exporter
systemctl is-active prometheus-node-exporter
ss -tulpn | grep :9100
curl -s http://localhost:9100/metrics | head
```

Подтверждено:

```text
enabled
active
*:9100 LISTEN
/metrics возвращает метрики
```

## Важное про Grafana install

Официальный Grafana APT/download с `monitor` был недоступен:

```text
apt.grafana.com/gpg.key -> HTTP 403 Access Denied
apt.grafana.com/gpg-full.key -> HTTP 403
dl.grafana.com/...deb -> HTTP 451
```

Решение: скачать `.deb` на Windows через доступный маршрут, передать на `monitor` через `scp`, установить локально через `sudo apt install ./grafana_...deb`.

После установки временные файлы были очищены:

```bash
rm -f /tmp/grafana.asc
sudo rm -f /etc/apt/keyrings/grafana.asc
sudo rm -f /etc/apt/keyrings/grafana.gpg
sudo rm -f /etc/apt/sources.list.d/grafana.list
rm -f ~/grafana*.deb
sudo apt-get clean
sudo apt-get autoremove -y
sudo apt-get update
```

Директории `/etc/apt/keyrings` и `/etc/apt/sources.list.d` не удалялись.
