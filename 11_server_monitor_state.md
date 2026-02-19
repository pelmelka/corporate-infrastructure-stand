# Текущее состояние сервера monitor

## Назначение

`monitor` — сервер мониторинга, визуализации и алертов.

Роль:
- Prometheus — сбор и хранение метрик;
- Grafana — визуализация метрик и логов;
- Alertmanager — прием alerts от Prometheus;
- node_exporter — отдача системных метрик самого `monitor`;
- сбор метрик с `web`, `app`, `log`.

## Основная информация

- Hostname: `monitor`
- IP: `192.168.85.137/24`
- Interface: `ens18`
- Gateway: `192.168.85.2`
- User: `pelmel`
- sudo: работает
- SSH: работает
- IP сейчас выдан через DHCP VMware NAT

Важно: сейчас все VM получают IP через DHCP. В lab-режиме адреса держатся стабильно, но позже нужно сделать одно из двух:
1. DHCP reservation по MAC-адресам VM;
2. статические IP внутри Debian на всех серверах.

Это важно для Promtail, Prometheus targets, Grafana datasources, Ansible inventory и будущего reverse proxy.

## Базовая настройка

Проверено:

```bash
groups
sudo whoami
hostname
ip a
ip route
curl http://192.168.85.135:3100/ready
ping 192.168.85.129
ping 192.168.85.131
ping 192.168.85.133
ping 192.168.85.135
```

Подтверждено:
- `pelmel` в группе `sudo`;
- `sudo whoami -> root`;
- hostname: `monitor`;
- IP: `192.168.85.137/24`;
- default route: `default via 192.168.85.2`;
- Loki на `log` доступен с `monitor`: `/ready -> ready`;
- `admin`, `web`, `app`, `log` пингуются.

Базовые пакеты, которые были поставлены/проверены:
`sudo`, `curl`, `wget`, `vim`, `nano`, `htop`, `tree`, `unzip`, `tar`, `ca-certificates`, `gnupg`, `lsb-release`, `apt-transport-https`, `net-tools`, `iproute2`, `iputils-ping`, `dnsutils`, `traceroute`, `openssh-server`, `systemd-timesyncd`.

## Prometheus

Prometheus установлен из стандартных Debian-репозиториев.

Сервис:

```text
prometheus.service
```

Проверки:

```bash
systemctl status prometheus --no-pager
systemctl is-enabled prometheus
systemctl is-active prometheus
ss -tulpn | grep :9090
curl http://localhost:9090/-/ready
```

Подтверждено:
- `prometheus.service active (running)`;
- `enabled`;
- порт `9090` слушается на `*:9090`;
- `/ - /ready` возвращает `Prometheus Server is Ready.`;
- UI доступен с Windows: `http://192.168.85.137:9090`.

Проверка API:

```bash
curl -G -s "http://localhost:9090/api/v1/query" \
  --data-urlencode 'query=up' | python3 -m json.tool
```

Результат:
- `job="prometheus", instance="localhost:9090", value="1"`;
- `job="node", instance="localhost:9100", value="1"`;
- также после добавления targets возвращает node metrics для `web`, `app`, `log` с labels `host="web"`, `host="app"`, `host="log"`.

## Grafana

Grafana 13.0.1 установлена через локальный `.deb` файл.

Причина: официальный Grafana APT/download был недоступен из текущей сети/маршрута.

Проверенные симптомы:

```text
apt.grafana.com/gpg.key -> HTTP 403 Access Denied
apt.grafana.com/gpg-full.key -> HTTP 403
ответ содержал: Sorry, the provided token is not valid
dl.grafana.com/...deb -> HTTP 451
DNS работал
ping работал
TLS handshake проходил
```

Вывод: проблема была не в Debian, DNS, curl/wget или сертификатах. Grafana CDN отказывал в выдаче файлов.

Фактический способ установки:
1. `.deb` Grafana был скачан на Windows через доступный маршрут.
2. Файл был передан на `monitor` через `scp`.
3. Файл был переименован без пробелов.
4. Установка:

```bash
sudo apt install -y ./grafana_13.0.1_24542347077_linux_amd64.deb
sudo systemctl daemon-reload
sudo systemctl enable --now grafana-server
```

Сервис:

```text
grafana-server.service
```

Проверки:

```bash
systemctl status grafana-server --no-pager
systemctl is-enabled grafana-server
systemctl is-active grafana-server
ss -tulpn | grep :3000
curl -I http://localhost:3000
```

Подтверждено:
- `grafana-server active (running)`;
- `enabled`;
- порт `3000` слушается на `*:3000`;
- `curl -I http://localhost:3000 -> HTTP/1.1 302 Found, Location: /login`;
- UI доступен с Windows: `http://192.168.85.137:3000`.

Пароль Grafana не фиксируется в sources.

После установки очищены следы неудачных попыток:

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

Важно: директории `/etc/apt/keyrings` и `/etc/apt/sources.list.d` не удалялись.

### Grafana datasources

В Grafana добавлены и проверены два datasource.

Prometheus datasource:

```text
Name: Prometheus
URL:  http://localhost:9090
```

Причина использования `localhost`: Prometheus и Grafana находятся на одном сервере `monitor`.

Проверено:

```text
Save & test -> Successfully queried the Prometheus API
```

В Grafana Explore выполнен запрос:

```promql
up{job="node"}
```

Результат: 4 series со значением `1`:

```text
host="web", instance="192.168.85.131:9100"
host="app", instance="192.168.85.133:9100"
host="log", instance="192.168.85.135:9100"
host="monitor", instance="localhost:9100"
```

Loki datasource:

```text
Name: Loki
URL:  http://192.168.85.135:3100
```

Причина использования IP: Loki находится на отдельном сервере `log`, а не на `monitor`.

Проверено:

```text
Save & test -> Data source successfully connected
```

В Grafana Explore выполнены LogQL-запросы:

```logql
{host="web", job="nginx"}
```

Результат: видны nginx access logs с `web`, включая `GET /` и `GET /not-found`.

```logql
{host="app", job="app"}
```

Результат: видны app logs с `app`, включая `path=/`, `path=/health`, `path=/bad-endpoint`, `status=200`, `status=404`, уровни `INFO`/`WARN`.


## Alertmanager

Alertmanager установлен из стандартных Debian-репозиториев как пакет:

```text
prometheus-alertmanager
```

Сервис:

```text
prometheus-alertmanager.service
```

Проверки:

```bash
systemctl status prometheus-alertmanager --no-pager
systemctl is-enabled prometheus-alertmanager
systemctl is-active prometheus-alertmanager
ss -tulpn | grep :9093
curl http://localhost:9093
curl http://localhost:9093/-/ready
```

Подтверждено:
- `prometheus-alertmanager.service active (running)`;
- `enabled`;
- порт `9093` слушается на `*:9093`;
- `/ - /ready -> OK`;
- после исправления параметров запуска сервис также корректно поднимается после reboot.

После выключения/включения VM была обнаружена проблема автозапуска: Alertmanager падал с ошибками `couldn't deduce an advertise address`, `unable to initialize gossip mesh`, `Failed to get final advertise address`. Причина: для single-node lab не нужен cluster/gossip mesh, а Alertmanager не смог сам определить advertise address.

Исправление внесено в файл:

```text
/etc/default/prometheus-alertmanager
```

Текущая строка параметров запуска:

```bash
ARGS="--cluster.listen-address="
```

Пустое значение у `--cluster.listen-address=` отключает cluster/gossip listener. После `reset-failed`, `restart` и последующего reboot `prometheus-alertmanager.service` остается `active (running)`.

`curl -I http://localhost:9093` возвращал `405 Method Not Allowed`, это нормально: `-I` делает HEAD-запрос, а endpoint разрешает `GET, OPTIONS`.

По `http://192.168.85.137:9093` открывается простая HTML-страница Debian-пакета. Debian-пакет Alertmanager не включает полноценный web UI, но API и health endpoints работают.

## Связка Prometheus -> Alertmanager

Проверка конфига:

```bash
grep -n "alerting\|alertmanagers\|9093" /etc/prometheus/prometheus.yml
```

Подтвержден блок:

```yaml
alerting:
  alertmanagers:
    - static_configs:
      - targets: ['localhost:9093']
```

Проверка API:

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

Итог: Prometheus видит Alertmanager и будет отправлять alerts на `localhost:9093`.

Alert rules пока не создавались.

## node_exporter и Prometheus targets

`node_exporter` на `monitor` установлен и работает как Debian-пакет:

```text
prometheus-node-exporter
```

Сервис:

```text
prometheus-node-exporter.service
```

Проверки на `monitor`:

```bash
systemctl status prometheus-node-exporter --no-pager
systemctl is-enabled prometheus-node-exporter
systemctl is-active prometheus-node-exporter
ss -tulpn | grep :9100
curl -s http://localhost:9100/metrics | head
```

Подтверждено:
- `prometheus-node-exporter.service active (running)`;
- `enabled`;
- порт `9100` слушается на `*:9100`;
- `/metrics` возвращает метрики.

Дополнительно node_exporter установлен на `web`, `app`, `log`. Проверено с `monitor`:

```bash
curl -s http://192.168.85.131:9100/metrics | head
curl -s http://192.168.85.133:9100/metrics | head
curl -s http://192.168.85.135:9100/metrics | head
```

Prometheus видит node targets как:

```text
instance="localhost:9100", host="monitor", job="node"
instance="192.168.85.131:9100", host="web", job="node"
instance="192.168.85.133:9100", host="app", job="node"
instance="192.168.85.135:9100", host="log", job="node"
```

Prometheus UI подтверждает:

```text
prometheus (1/1 up)
node (4/4 up)
```

Концептуально:

```text
node_exporter + Prometheus = pull-модель метрик.
node_exporter отдает :9100/metrics, Prometheus сам приходит и забирает метрики.
```

## Текущий статус monitor

`monitor` считается готовым observability node с подключенными Grafana datasources и созданным dashboard `Infrastructure Overview`.

Готово:
- VM `monitor` создана;
- SSH/sudo/сеть работают;
- Prometheus active/enabled, порт `9090`;
- Grafana active/enabled, порт `3000`;
- Alertmanager active/enabled, порт `9093`;
- для Alertmanager отключен cluster/gossip listener через `ARGS="--cluster.listen-address="`, после reboot сервис поднимается корректно;
- Prometheus связан с Alertmanager;
- node_exporter на `monitor`, `web`, `app`, `log` active/enabled, порт `9100`;
- Prometheus targets: `prometheus (1/1 up)`, `node (4/4 up)`;
- node targets имеют labels `host="monitor"`, `host="web"`, `host="app"`, `host="log"`;
- Grafana datasource Prometheus подключен и проверен;
- Grafana datasource Loki подключен и проверен;
- в Grafana Explore видны node metrics, nginx logs и app logs;
- создан dashboard `Infrastructure Overview`;
- dashboard показывает targets UP, Disk, CPU, RAM, Web nginx logs и App logs.

## Grafana dashboard Infrastructure Overview

Создан первый dashboard:

```text
Infrastructure Overview
```

Назначение: один обзорный экран для состояния инфраструктуры: доступность узлов, базовые ресурсы и свежие web/app logs.

Dashboard создан через Grafana UI. JSON export пока не фиксировался в sources.

### Panels

#### Targets UP

Datasource: `Prometheus`.

```promql
up{job="node"}
```

Настройки:

```text
Visualization: Stat
Legend: {{host}}
Type: Instant
Value mappings:
  1 -> UP
  0 -> DOWN
```

Подтверждено: `web`, `app`, `log`, `monitor` отображаются как `UP`.

Важно: `up=1` означает, что Prometheus успешно сделал scrape target `/metrics`. Это не абсолютная проверка здоровья приложения.

#### CPU Usage by host

Datasource: `Prometheus`.

```promql
100 - (avg by (host) (rate(node_cpu_seconds_total{job="node", mode="idle"}[5m])) * 100)
```

#### RAM Usage by host

Datasource: `Prometheus`.

```promql
100 * (1 - (node_memory_MemAvailable_bytes{job="node"} / node_memory_MemTotal_bytes{job="node"}))
```

#### Disk Usage by host

Datasource: `Prometheus`.

```promql
100 * (1 - (
  node_filesystem_avail_bytes{job="node", mountpoint="/", fstype!~"tmpfs|overlay|squashfs"}
  /
  node_filesystem_size_bytes{job="node", mountpoint="/", fstype!~"tmpfs|overlay|squashfs"}
))
```

Настройки:

```text
Visualization: Bar gauge
Legend: {{host}}
Type: Instant
Unit: Percent
Decimals: 1
```

Визуально оставлены разные цвета по host для читаемости. Threshold-based coloring можно добавить позже вместе с alert rules; текущий вариант оставлен для читаемого различения host.

#### Web nginx logs

Datasource: `Loki`.

Базовый LogQL:

```logql
{host="web", job="nginx"}
```

Для красивого отображения использован вариант с `regexp` и `line_format`:

```logql
{host="web", job="nginx"}
| regexp `^(?P<client_ip>\S+) \S+ \S+ \[(?P<time>[^\]]+)\] "(?P<method>\S+) (?P<path>\S+) (?P<proto>[^"]+)" (?P<status>\d{3}) (?P<size>\d+) "(?P<referer>[^"]*)" "(?P<agent>[^"]*)"`
| line_format `{{.method}} {{.path}} → {{.status}} from {{.client_ip}}`
```

#### App logs

Datasource: `Loki`.

Базовый LogQL:

```logql
{host="app", job="app"}
```

Для красивого отображения использован вариант с `regexp` и `line_format`:

```logql
{host="app", job="app"}
| regexp `^(?P<ts>\S+ \S+) (?P<level>\S+) service=(?P<service>\S+) method=(?P<method>\S+) path=(?P<path>\S+) status=(?P<status>\d+) client_ip=(?P<client_ip>\S+)`
| line_format `{{.method}} {{.path}} → {{.status}} from {{.client_ip}}`
```

### Проверка log panels

Для наполнения log-панелей были сгенерированы свежие запросы:

```bash
curl http://192.168.85.131/
curl http://192.168.85.131/not-found-grafana-test
curl http://192.168.85.133:8080/
curl http://192.168.85.133:8080/health
curl http://192.168.85.133:8080/bad-endpoint-grafana-test
```

После refresh dashboard свежие nginx/app logs появились в соответствующих панелях.
