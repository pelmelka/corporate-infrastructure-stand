# Важные текущие конфигурационные файлы проекта

Этот файл хранит именно текущие важные конфиги и полный код, который нужен для восстановления состояния. Server state files фиксируют состояние, проверки, paths и роли компонентов, но не полный код.

## Ansible inventory

Файл:

```text
admin: ~/control-node/inventory/hosts.ini
```

Текущий вариант:

```ini
[control]
admin ansible_connection=local

[web_nodes]
web ansible_host=192.168.85.131

[app_nodes]
app ansible_host=192.168.85.133

[log_nodes]
log ansible_host=192.168.85.135

[monitor_nodes]
monitor ansible_host=192.168.85.137

[managed:children]
web_nodes
app_nodes
log_nodes
monitor_nodes

[all:vars]
ansible_user=pelmel
ansible_python_interpreter=/usr/bin/python3
```

Примечание: группы названы `*_nodes`, чтобы не создавать конфликт host/group с одинаковым именем (`web`, `app`, `log`, `monitor`).

## Ansible config

Файл:

```text
admin: ~/control-node/ansible.cfg
```

Текущий вариант:

```ini
[defaults]
inventory = inventory/hosts.ini
remote_user = pelmel
host_key_checking = False
interpreter_python = /usr/bin/python3
retry_files_enabled = False

[privilege_escalation]
become = False
```

## Ansible playbook: ping_all.yml

Файл:

```text
admin: ~/control-node/playbooks/ping_all.yml
```

```yaml
---
- name: Ping all infrastructure nodes
  hosts: all
  gather_facts: false

  tasks:
    - name: Check Ansible connection
      ansible.builtin.ping:
```

## Ansible playbook: check_services.yml

Файл:

```text
admin: ~/control-node/playbooks/check_services.yml
```

```yaml
---
- name: Check web services
  hosts: web_nodes
  gather_facts: false

  tasks:
    - name: Check nginx
      ansible.builtin.command: systemctl is-active nginx.service
      changed_when: false

    - name: Check promtail
      ansible.builtin.command: systemctl is-active promtail.service
      changed_when: false

    - name: Check node_exporter
      ansible.builtin.command: systemctl is-active prometheus-node-exporter.service
      changed_when: false


- name: Check app services
  hosts: app_nodes
  gather_facts: false

  tasks:
    - name: Check app
      ansible.builtin.command: systemctl is-active app.service
      changed_when: false

    - name: Check promtail
      ansible.builtin.command: systemctl is-active promtail.service
      changed_when: false

    - name: Check node_exporter
      ansible.builtin.command: systemctl is-active prometheus-node-exporter.service
      changed_when: false


- name: Check log services
  hosts: log_nodes
  gather_facts: false

  tasks:
    - name: Check loki
      ansible.builtin.command: systemctl is-active loki.service
      changed_when: false

    - name: Check node_exporter
      ansible.builtin.command: systemctl is-active prometheus-node-exporter.service
      changed_when: false


- name: Check monitor services
  hosts: monitor_nodes
  gather_facts: false

  tasks:
    - name: Check prometheus
      ansible.builtin.command: systemctl is-active prometheus.service
      changed_when: false

    - name: Check grafana
      ansible.builtin.command: systemctl is-active grafana-server.service
      changed_when: false

    - name: Check alertmanager
      ansible.builtin.command: systemctl is-active prometheus-alertmanager.service
      changed_when: false

    - name: Check node_exporter
      ansible.builtin.command: systemctl is-active prometheus-node-exporter.service
      changed_when: false
```

## Ansible playbook: restart_app.yml

Файл:

```text
admin: ~/control-node/playbooks/restart_app.yml
```

```yaml
---
- name: Restart support-desk-api service
  hosts: app_nodes
  gather_facts: false
  become: true

  vars_prompt:
    - name: ansible_become_password
      prompt: "BECOME password"
      private: true

  tasks:
    - name: Restart app.service
      ansible.builtin.systemd_service:
        name: app.service
        state: restarted

    - name: Check app.service is active
      ansible.builtin.command: systemctl is-active app.service
      changed_when: false

    - name: Check local health endpoint
      ansible.builtin.uri:
        url: http://localhost:8080/health
        method: GET
        status_code: 200
        return_content: true
```

Примечание: playbook пока называется универсально и перезапускает `app.service`. После Product model v2 сервис внутри приложения называется `misis-digital-student-support-api`, но systemd unit остался `app.service`.

## Ansible playbook: deploy_prometheus_rules.yml

Файл:

```text
admin: ~/control-node/playbooks/deploy_prometheus_rules.yml
```

Локальный source-файл rules:

```text
admin: ~/control-node/files/prometheus/supportdesk.rules.yml
```

```yaml
---
- name: Deploy Prometheus alert rules
  hosts: monitor_nodes
  gather_facts: false
  become: true

  vars:
    prometheus_rules_src: "{{ playbook_dir }}/../files/prometheus/supportdesk.rules.yml"

  vars_prompt:
    - name: ansible_become_password
      prompt: "BECOME password"
      private: true

  tasks:
    - name: Deploy Prometheus rules with validation
      ansible.builtin.copy:
        src: "{{ prometheus_rules_src }}"
        dest: /etc/prometheus/supportdesk.rules.yml
        owner: root
        group: root
        mode: "0644"
        backup: true
        validate: "promtool check rules %s"
      notify: Restart prometheus

    - name: Check Prometheus config syntax
      ansible.builtin.command: promtool check config /etc/prometheus/prometheus.yml
      changed_when: false

    - name: Run handlers now if rules changed
      ansible.builtin.meta: flush_handlers

    - name: Check Prometheus is ready after deploy
      ansible.builtin.uri:
        url: http://localhost:9090/-/ready
        method: GET
        status_code: [200, 503]
      register: prometheus_ready
      retries: 10
      delay: 3
      until: prometheus_ready.status == 200
      failed_when: prometheus_ready.status != 200

  handlers:
    - name: Restart prometheus
      ansible.builtin.systemd_service:
        name: prometheus.service
        state: restarted
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
    pipeline_stages:
      - regex:
          expression: '^.*" (?P<status_code>[0-9]{3}) .*$'
      - labels:
          status_code:
      - metrics:
          nginx_http_responses_total:
            type: Counter
            description: "Total nginx HTTP responses by status code"
            source: status_code
            config:
              action: inc

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

Особенности:

- Promtail продолжает отправлять nginx logs в Loki;
- `regex` извлекает `status_code` из nginx access log;
- `metrics` stage создает counter `promtail_custom_nginx_http_responses_total{status_code}` на `web:9080/metrics`;
- метрика используется Prometheus job `promtail-web` и alert-ом `Nginx502Spike`.

## Promtail config для app

Файл:

```text
app: /etc/promtail/config.yml
```

Текущий вариант после Product model v2:

```yaml
clients:
  - url: http://192.168.85.135:3100/loki/api/v1/push

scrape_configs:
  - job_name: app
    pipeline_stages:
      - regex:
          expression: '(^|.*\s)category=(?P<category>[a-z0-9-]+)(\s|$)'
      - labels:
          category:

    static_configs:
      - targets:
          - localhost
        labels:
          host: app
          job: app
          service: misis-digital-student-support-api
          env: lab
          __path__: /var/log/app/*.log
```

Особенности:

- static label `service` изменен на `misis-digital-student-support-api`;
- `category` извлекается из app log line и становится dynamic Loki label;
- `resource` пока остается полем строки и фильтруется через LogQL `|= "resource=..."` или `| logfmt`.

## Prometheus config

Файл:

```text
monitor: /etc/prometheus/prometheus.yml
```

Проверенный Alertmanager block:

```yaml
alerting:
  alertmanagers:
    - static_configs:
      - targets: ['localhost:9093']
```

Текущий `rule_files` block:

```yaml
rule_files:
  - /etc/prometheus/supportdesk.rules.yml
```

Текущий `scrape_configs` block:

```yaml
scrape_configs:
  - job_name: node
    static_configs:
      - targets: ['localhost:9100']
        labels:
          host: monitor

      - targets: ['192.168.85.131:9100']
        labels:
          host: web

      - targets: ['192.168.85.133:9100']
        labels:
          host: app

      - targets: ['192.168.85.135:9100']
        labels:
          host: log

  - job_name: supportdesk-api
    metrics_path: /metrics
    static_configs:
      - targets: ['192.168.85.133:8080']
        labels:
          host: app
          service: support-desk-api
          env: lab

  - job_name: promtail-web
    metrics_path: /metrics
    static_configs:
      - targets: ['192.168.85.131:9080']
        labels:
          host: web
          service: promtail
          env: lab
```

Примечание: Prometheus job/label `supportdesk-api` пока сохранен для совместимости с существующими panels и alerts, хотя приложение теперь называется `misis-digital-student-support-api`. Job `promtail-web` добавлен для custom metrics Promtail на `web:9080`, прежде всего для nginx status code metric и `Nginx502Spike`.

## Prometheus alert rules

Файл:

```text
monitor: /etc/prometheus/supportdesk.rules.yml
```

Полный текущий вариант:

```yaml
groups:
  - name: supportdesk.rules
    rules:
      - alert: SupportDeskApiDown
        expr: up{job="supportdesk-api"} == 0
        for: 30s
        labels:
          severity: critical
          service: misis-digital-student-support-api
        annotations:
          summary: "MISIS_Digital Student Support API is down"
          description: "Prometheus cannot scrape MISIS_Digital Student Support API on {{ $labels.instance }} for more than 30 seconds."

      - alert: SupportDeskTooManyTicketsForResource
        expr: sum by(category, resource) (supportdesk_tickets_current{job="supportdesk-api",status=~"open|in_progress"}) >= 3
        for: 30s
        labels:
          severity: warning
          service: misis-digital-student-support-api
        annotations:
          summary: "Too many active tickets for {{ $labels.category }} / {{ $labels.resource }}"
          description: "There are {{ $value }} active tickets for {{ $labels.category }} / {{ $labels.resource }}."

      - alert: SupportDeskCriticalTicketsOpen
        expr: sum by(category, resource) (supportdesk_tickets_current{job="supportdesk-api",status=~"open|in_progress",priority="critical"}) > 0
        for: 30s
        labels:
          severity: critical
          service: misis-digital-student-support-api
        annotations:
          summary: "Critical support ticket is open for {{ $labels.category }} / {{ $labels.resource }}"
          description: "There are {{ $value }} active critical tickets for {{ $labels.category }} / {{ $labels.resource }}."

      - alert: SupportDeskOldCriticalTicket
        expr: max by(category, resource) (supportdesk_active_ticket_age_seconds_max{job="supportdesk-api",priority="critical"}) > 600
        for: 30s
        labels:
          severity: critical
          service: misis-digital-student-support-api
        annotations:
          summary: "Old critical support ticket for {{ $labels.category }} / {{ $labels.resource }}"
          description: "The oldest active critical ticket for {{ $labels.category }} / {{ $labels.resource }} is {{ $value }} seconds old."

      - alert: SupportDeskHigh4xxRate
        expr: |
          (
            sum(rate(supportdesk_http_requests_total{job="supportdesk-api",status_code=~"4.."}[5m]))
            /
            sum(rate(supportdesk_http_requests_total{job="supportdesk-api"}[5m]))
          ) > 0.30
          and
          sum(increase(supportdesk_http_requests_total{job="supportdesk-api"}[5m])) >= 5
        for: 2m
        labels:
          severity: warning
          service: misis-digital-student-support-api
        annotations:
          summary: "High 4xx rate for MISIS_Digital Student Support API"
          description: "More than 30% of recent API requests returned 4xx responses. This usually means many invalid client/UI/API requests."

      - alert: SupportDeskHigh5xxRate
        expr: |
          (
            sum(rate(supportdesk_http_requests_total{job="supportdesk-api",status_code=~"5.."}[5m]))
            /
            sum(rate(supportdesk_http_requests_total{job="supportdesk-api"}[5m]))
          ) > 0.05
          and
          sum(increase(supportdesk_http_requests_total{job="supportdesk-api"}[5m])) >= 5
        for: 1m
        labels:
          severity: critical
          service: misis-digital-student-support-api
        annotations:
          summary: "High 5xx rate for MISIS_Digital Student Support API"
          description: "More than 5% of recent API requests returned 5xx responses. This usually means backend-side errors."

      - alert: SupportDeskHighLatency
        expr: |
          histogram_quantile(
            0.95,
            sum by(le) (
              rate(supportdesk_http_request_duration_seconds_bucket{job="supportdesk-api"}[5m])
            )
          ) > 0.5
          and
          sum(increase(supportdesk_http_requests_total{job="supportdesk-api"}[5m])) >= 5
        for: 2m
        labels:
          severity: warning
          service: misis-digital-student-support-api
        annotations:
          summary: "High latency for MISIS_Digital Student Support API"
          description: "p95 API latency is above 0.5 seconds for more than 2 minutes."

      - alert: Nginx502Spike
        expr: |
          sum(increase(promtail_custom_nginx_http_responses_total{job="promtail-web",host="web",status_code="502"}[5m])) >= 3
        for: 30s
        labels:
          severity: critical
          service: frontend
        annotations:
          summary: "Nginx is returning 502 responses"
          description: "Nginx on web returned {{ $value }} HTTP 502 responses in the last 5 minutes. This usually means the backend app is unavailable or reverse proxy upstream is broken."

      - alert: HighDiskUsage
        expr: 100 * (1 - (node_filesystem_avail_bytes{job="node", mountpoint="/", fstype="ext4"} / node_filesystem_size_bytes{job="node", mountpoint="/", fstype="ext4"})) > 80
        for: 2m
        labels:
          severity: warning
          service: node
        annotations:
          summary: "High disk usage on {{ $labels.host }}"
          description: "Root filesystem on {{ $labels.host }} is {{ printf "%.1f" $value }}% full."

      - alert: NodeTargetDown
        expr: up{job="node"} == 0
        for: 30s
        labels:
          severity: critical
          service: node
        annotations:
          summary: "Node target is down: {{ $labels.host }}"
          description: "Prometheus cannot scrape node_exporter on {{ $labels.host }} at {{ $labels.instance }} for more than 30 seconds."
```

Проверено после HTTP/API observability:

- `SupportDeskApiDown` остается для API availability;
- `SupportDeskTooManyTicketsForResource` срабатывает при концентрации active-заявок на одном `category/resource`;
- `SupportDeskCriticalTicketsOpen` срабатывает при active critical-заявке;
- `SupportDeskOldCriticalTicket` срабатывает при active critical-заявке старше 600 секунд;
- `HighDiskUsage` проверен временным порогом `>20`, затем возвращен на `>80`;
- `NodeTargetDown` срабатывает при остановке node_exporter на target node;
- `SupportDeskHigh4xxRate` срабатывает при генерации 4xx-трафика;
- `Nginx502Spike` срабатывает при остановке `app.service` и запросах через `web/Nginx`;
- `SupportDeskApiDown` при этом также срабатывает, потому что Prometheus теряет `supportdesk-api` target;
- старый `TooManyOpenTickets` удален как менее точный общий product alert.

## Alertmanager

Файл пользовательских параметров запуска:

```text
monitor: /etc/default/prometheus-alertmanager
```

Текущая важная строка:

```bash
ARGS="--cluster.listen-address="
```

Причина: в single-node lab cluster/gossip listener не нужен; пустое значение отключает cluster listener и решает autostart issue после reboot.

## Grafana datasources

Prometheus datasource:

```text
Name: Prometheus
URL:  http://localhost:9090
```

Loki datasource:

```text
Name: Loki
URL:  http://192.168.85.135:3100
```

## Grafana dashboard: Infrastructure Overview

Dashboard создан через Grafana UI. JSON export пока не зафиксирован.

Основные panels:

```text
Targets UP
Disk Usage by host
CPU Usage by host
RAM Usage by host
SupportDesk API UP
SupportDesk Tickets / Student Support Tickets
Active Alerts
Web nginx logs
App logs
```

Product/API panels:

```promql
up{job="supportdesk-api"}
```

```promql
supportdesk_tickets_total{job="supportdesk-api"}
supportdesk_tickets_open{job="supportdesk-api"}
supportdesk_tickets_in_progress{job="supportdesk-api"}
supportdesk_tickets_resolved{job="supportdesk-api"}
supportdesk_tickets_active{job="supportdesk-api"}
```

Product Observability v2 panels:

```promql
sum by(category) (supportdesk_tickets_current{job="supportdesk-api",status="open"})
```

```promql
topk(10, sum by(category, resource) (supportdesk_tickets_current{job="supportdesk-api",status=~"open|in_progress"}))
```

```promql
sum by(category, resource) (supportdesk_tickets_current{job="supportdesk-api",status=~"open|in_progress",priority="critical"})
```

```promql
topk(10, max by(category, resource, priority) (supportdesk_active_ticket_age_seconds_max{job="supportdesk-api"}))
```

Active Alerts panel:

```promql
sum(ALERTS{alertstate="firing"}) or vector(0)
```


HTTP/API Observability panels:

`HTTP/API Health Overview` — Stat panel, all queries Instant:

```promql
100 *
(
  sum(rate(supportdesk_http_requests_total{job="supportdesk-api",status_code=~"4.."}[5m]))
  or vector(0)
)
/
clamp_min(
  sum(rate(supportdesk_http_requests_total{job="supportdesk-api"}[5m])),
  0.001
)
```

```promql
100 *
(
  sum(rate(supportdesk_http_requests_total{job="supportdesk-api",status_code=~"5.."}[5m]))
  or vector(0)
)
/
clamp_min(
  sum(rate(supportdesk_http_requests_total{job="supportdesk-api"}[5m])),
  0.001
)
```

```promql
(
  1000 *
  histogram_quantile(
    0.95,
    sum by(le) (
      rate(supportdesk_http_request_duration_seconds_bucket{job="supportdesk-api"}[15m])
    )
  )
)
unless on()
(
  sum(rate(supportdesk_http_request_duration_seconds_count{job="supportdesk-api"}[15m])) == 0
)
or vector(0)
```

```promql
sum(
  increase(promtail_custom_nginx_http_responses_total{job="promtail-web",host="web",status_code="502"}[5m])
)
or vector(0)
```

```promql
sum(
  ALERTS{alertname=~"SupportDeskHigh4xxRate|SupportDeskHigh5xxRate|SupportDeskHighLatency|Nginx502Spike",alertstate="firing"}
)
or vector(0)
```

`API Request Rate by Route`:

```promql
sum by(method, route) (
  rate(supportdesk_http_requests_total{job="supportdesk-api"}[5m])
)
```

`API Responses by Status Code`:

```promql
sum by(status_code) (
  rate(supportdesk_http_requests_total{job="supportdesk-api"}[5m])
)
```

`API p95 Latency by Route` — Bar gauge:

```promql
topk(
  8,
  1000 *
  histogram_quantile(
    0.95,
    sum by(le, route) (
      rate(supportdesk_http_request_duration_seconds_bucket{job="supportdesk-api"}[15m])
    )
  )
)
```

Решение по dashboard: отдельная подробная панель Nginx responses by status code не добавлялась, чтобы сохранить минимальный набор из 4 panels; proxy-level 502 уже виден в `HTTP/API Health Overview`.


App logs panel query:

```logql
{host="app", job="app", service="misis-digital-student-support-api"}
| logfmt
| line_format "{{.event}} | {{.method}} {{.path}} | status={{.status}} | category={{.category}} | resource={{.resource}} | ticket={{.ticket_id}} | {{.old_status}} -> {{.new_status}} | client={{.x_forwarded_for}} | proxy={{.client_ip}}"
```

Примечание: `ticket_list_requested` сознательно оставлен в panel, потому что показывает, что UI реально ходит в backend за списком заявок.


## Docker runtime для MISIS_Digital Student Support backend

Этап 15 перевел backend с `app.service` на Docker container без изменения внешнего порта `8080`.

### Docker installation on app

Проверено на `app`:

```text
Docker Engine 29.4.3
Docker Compose v5.1.3
docker.service active/enabled
```

### Dockerfile

Файл:

```text
app: /opt/app/Dockerfile
```

```dockerfile
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

ARG APP_UID=1000
ARG APP_GID=1000

RUN groupadd --gid ${APP_GID} appuser \
    && useradd --uid ${APP_UID} --gid ${APP_GID} --home-dir /opt/app --shell /usr/sbin/nologin appuser

WORKDIR /opt/app

COPY requirements.txt /opt/app/requirements.txt
RUN pip install --no-cache-dir -r /opt/app/requirements.txt

COPY app.py /opt/app/app.py

RUN mkdir -p /var/log/app \
    && chown -R appuser:appuser /opt/app /var/log/app

USER appuser

EXPOSE 8080

CMD ["python", "/opt/app/app.py"]
```

### requirements.txt

Файл:

```text
app: /opt/app/requirements.txt
```

```text
prometheus_client
```

### docker-compose.yml

Файл:

```text
app: /opt/app/docker-compose.yml
```

```yaml
services:
  supportdesk-api:
    build:
      context: .
      args:
        APP_UID: ${APP_UID:-1000}
        APP_GID: ${APP_GID:-1000}
    image: misis-digital-student-support-api:local
    container_name: misis-digital-student-support-api
    restart: unless-stopped
    ports:
      - "8080:8080"
    volumes:
      - /opt/app:/opt/app
      - /var/log/app:/var/log/app
    environment:
      TZ: UTC
```

Примечание: `/opt/app:/opt/app` — временный workaround до PostgreSQL stage. Он оставлен, потому что текущий `tickets.json` storage сохраняет файл через `tickets.json.tmp` и `os.replace()`. Mount только одного файла `/opt/app/tickets.json:/opt/app/tickets.json` приводил к `500` на `POST/PATCH`. После перехода на PostgreSQL этот volume нужно убрать, чтобы код жил в image, а состояние — в БД.

`/var/log/app:/var/log/app` сохранен, чтобы текущий Promtail продолжал читать `/var/log/app/app.log`. Позже возможен переход на stdout/stderr container logs.

### .env

Файл:

```text
app: /opt/app/.env
```

```env
APP_UID=1000
APP_GID=1000
```

Фактические значения соответствуют UID/GID пользователя `pelmel` на `app`.

### .dockerignore

Файл:

```text
app: /opt/app/.dockerignore
```

```dockerignore
backups/
*.bak*
__pycache__/
*.pyc
.env
```

### Runtime commands

```bash
cd /opt/app
sudo docker compose build
sudo docker compose up -d
sudo docker compose ps
sudo docker compose restart
sudo docker compose down
```

### Проверки после Dockerization

```bash
curl -s http://localhost:8080/v1/health | python3 -m json.tool
curl -s http://localhost:8080/metrics | head
curl -s http://192.168.85.131/api/v1/health | python3 -m json.tool
curl -s 'http://192.168.85.137:9090/api/v1/query?query=up%7Bjob%3D%22supportdesk-api%22%7D' | python3 -m json.tool
```

Подтверждено:

```text
container misis-digital-student-support-api Up
host 8080 -> container 8080
/v1/health -> ok
/metrics -> supportdesk_* and supportdesk_http_* metrics
POST /api/v1/tickets -> ok
PATCH /api/v1/tickets/<id>/status -> ok
Prometheus up{job="supportdesk-api"} -> 1
```

### Legacy app.service rollback

Файл:

```text
app: /etc/systemd/system/app.service
```

Текущее состояние после Dockerization:

```text
inactive/dead
disabled
```

Rollback:

```bash
cd /opt/app
sudo docker compose down
sudo systemctl start app.service
```

## Nginx reverse proxy для MISIS_Digital Student Support

Файл:

```text
web: /etc/nginx/sites-available/default
```

Backup:

```text
web: /etc/nginx/sites-available/default.bak-before-supportdesk-proxy
```

Фрагмент:

```nginx
location /api/ {
    proxy_pass http://192.168.85.133:8080/;

    proxy_http_version 1.1;

    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

## MISIS_Digital Student Support frontend

Файл:

```text
web: /var/www/html/index.html
```

Backup-и:

```text
web: /var/www/html/index.html.bak-before-supportdesk
web: /var/www/html/index.html.bak-before-misis-digital-v2
```

Функциональность:

- `GET /api/v1/health`;
- `GET /api/v1/support-model`;
- `GET /api/v1/tickets`;
- `GET /api/v1/tickets?status=resolved`;
- `GET /api/v1/tickets/all`;
- `POST /api/v1/tickets`;
- `PATCH /api/v1/tickets/<id>/status`;
- dynamic dropdown: `category -> resource`;
- active/resolved/all tabs;
- Last API response.

### Полный текущий код `/var/www/html/index.html`

```html
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>MISIS_Digital Student Support</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">

    <style>
        body {
            margin: 0;
            font-family: Arial, sans-serif;
            background: #f4f6f8;
            color: #1f2933;
        }

        header {
            background: #111827;
            color: white;
            padding: 24px 40px;
        }

        header h1 {
            margin: 0;
            font-size: 32px;
        }

        header p {
            margin: 8px 0 0;
            color: #cbd5e1;
        }

        main {
            max-width: 1150px;
            margin: 28px auto;
            padding: 0 20px;
        }

        .grid {
            display: grid;
            grid-template-columns: 1fr 1.2fr;
            gap: 24px;
        }

        .card {
            background: white;
            border-radius: 14px;
            padding: 22px;
            box-shadow: 0 8px 20px rgba(15, 23, 42, 0.08);
        }

        .card h2 {
            margin-top: 0;
            font-size: 22px;
        }

        label {
            display: block;
            margin-top: 14px;
            font-weight: bold;
        }

        input, textarea, select {
            width: 100%;
            box-sizing: border-box;
            margin-top: 6px;
            padding: 10px;
            border: 1px solid #cbd5e1;
            border-radius: 8px;
            font-size: 15px;
        }

        textarea {
            min-height: 95px;
        }

        button {
            margin-top: 16px;
            padding: 10px 16px;
            border: none;
            border-radius: 8px;
            background: #2563eb;
            color: white;
            font-weight: bold;
            cursor: pointer;
        }

        button:hover {
            background: #1d4ed8;
        }

        .secondary {
            background: #475569;
            margin-left: 8px;
        }

        .secondary:hover {
            background: #334155;
        }

        .danger {
            background: #dc2626;
        }

        .danger:hover {
            background: #b91c1c;
        }

        .full-width {
            margin-top: 24px;
        }

        .tabs {
            display: flex;
            gap: 10px;
            margin-bottom: 18px;
            flex-wrap: wrap;
        }

        .tab {
            background: #e2e8f0;
            color: #1f2933;
            margin-top: 0;
        }

        .tab.active {
            background: #2563eb;
            color: white;
        }

        .ticket {
            border: 1px solid #e2e8f0;
            border-radius: 10px;
            padding: 14px;
            margin-bottom: 12px;
            background: #f8fafc;
        }

        .ticket-title {
            font-weight: bold;
            font-size: 17px;
        }

        .description {
            margin-top: 8px;
        }

        .meta {
            margin-top: 10px;
            font-size: 14px;
            color: #64748b;
            line-height: 1.6;
        }

        .pill {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 999px;
            font-size: 13px;
            font-weight: bold;
            margin-right: 6px;
            background: #e0f2fe;
            color: #0369a1;
        }

        .priority {
            background: #fee2e2;
            color: #991b1b;
        }

        .category {
            background: #ede9fe;
            color: #5b21b6;
        }

        .resource {
            background: #dcfce7;
            color: #166534;
        }

        .health-ok {
            color: #15803d;
            font-weight: bold;
        }

        .health-bad {
            color: #b91c1c;
            font-weight: bold;
        }

        pre {
            background: #0f172a;
            color: #e2e8f0;
            border-radius: 10px;
            padding: 14px;
            overflow-x: auto;
        }

        .hint {
            color: #64748b;
            font-size: 14px;
            margin-top: 8px;
        }

        @media (max-width: 850px) {
            .grid {
                grid-template-columns: 1fr;
            }

            header {
                padding: 22px;
            }
        }
    </style>
</head>

<body>
<header>
    <h1>MISIS_Digital Student Support</h1>
    <p>Support portal for MISIS digital student services: LMS, personal account, dormitory portal, events, library, career and payments.</p>
</header>

<main>
    <div class="grid">
        <section class="card">
            <h2>Backend status</h2>
            <p id="health">Checking backend...</p>
            <button onclick="loadHealth()">Refresh health</button>
            <button class="secondary" onclick="loadTickets(currentFilter)">Refresh tickets</button>
        </section>

        <section class="card">
            <h2>Create support request</h2>

            <label for="category">Digital service</label>
            <select id="category" onchange="onCategoryChange()"></select>
            <div class="hint">Choose the university digital service where the problem happened.</div>

            <label for="resource">Service section</label>
            <select id="resource"></select>

            <label for="priority">Priority</label>
            <select id="priority">
                <option value="low">low</option>
                <option value="normal" selected>normal</option>
                <option value="high">high</option>
                <option value="critical">critical</option>
            </select>

            <label for="description">Description</label>
            <textarea id="description" placeholder="Describe what happened. Example: В расписании отображается неправильная аудитория"></textarea>

            <button onclick="createTicket()">Create ticket</button>
        </section>
    </div>

    <section class="card full-width">
        <h2>Tickets</h2>

        <div class="tabs">
            <button id="tab-active" class="tab active" onclick="loadTickets('active')">Active</button>
            <button id="tab-resolved" class="tab" onclick="loadTickets('resolved')">Resolved</button>
            <button id="tab-all" class="tab" onclick="loadTickets('all')">All</button>
        </div>

        <div id="summary" class="hint">Loading summary...</div>
        <div id="tickets">Loading tickets...</div>
    </section>

    <section class="card full-width">
        <h2>Last API response</h2>
        <pre id="api-response">No API response yet.</pre>
    </section>
</main>

<script>
    let supportModel = null;
    let currentFilter = "active";

    async function loadHealth() {
        const healthEl = document.getElementById("health");

        try {
            const response = await fetch("/api/v1/health");
            const data = await response.json();
            const backendTime = new Date(data.time);

            healthEl.innerHTML = `
                <span class="health-ok">OK</span><br>
                Product: ${escapeHtml(data.product)}<br>
                Service: ${escapeHtml(data.service)}<br>
                Version: ${escapeHtml(data.version)}<br>
                Environment: ${escapeHtml(data.environment)}<br>
                API version: ${escapeHtml(data.api_version)}<br>
                Backend time UTC: ${escapeHtml(data.time)}<br>
                Your local time: ${backendTime.toLocaleString()}
            `;

            showResponse(data);
        } catch (error) {
            healthEl.innerHTML = `<span class="health-bad">Backend unavailable</span>`;
            showResponse({ error: String(error) });
        }
    }

    async function loadSupportModel() {
        const response = await fetch("/api/v1/support-model");
        supportModel = await response.json();

        const categorySelect = document.getElementById("category");
        categorySelect.innerHTML = supportModel.categories.map(category => `
            <option value="${escapeHtml(category.value)}">${escapeHtml(category.label)}</option>
        `).join("");

        onCategoryChange();
    }

    function onCategoryChange() {
        const categoryValue = document.getElementById("category").value;
        const resourceSelect = document.getElementById("resource");
        const category = supportModel.categories.find(item => item.value === categoryValue);

        if (!category) {
            resourceSelect.innerHTML = "";
            return;
        }

        resourceSelect.innerHTML = category.resources.map(resource => `
            <option value="${escapeHtml(resource.value)}">${escapeHtml(resource.label)}</option>
        `).join("");
    }

    async function loadTickets(filter = "active") {
        currentFilter = filter;
        setActiveTab(filter);

        const ticketsEl = document.getElementById("tickets");
        const summaryEl = document.getElementById("summary");

        try {
            let url = "/api/v1/tickets";
            if (filter === "resolved") {
                url = "/api/v1/tickets?status=resolved";
            } else if (filter === "all") {
                url = "/api/v1/tickets/all";
            }

            const response = await fetch(url);
            const data = await response.json();

            summaryEl.innerHTML = `
                Filter: <b>${escapeHtml(data.filter)}</b> |
                Active: <b>${data.active_count}</b> |
                Open: <b>${data.open_count}</b> |
                In progress: <b>${data.in_progress_count}</b> |
                Resolved: <b>${data.resolved_count}</b> |
                Total: <b>${data.total}</b>
            `;

            if (!data.tickets || data.tickets.length === 0) {
                ticketsEl.innerHTML = "No tickets in this view.";
                showResponse(data);
                return;
            }

            ticketsEl.innerHTML = data.tickets.map(ticket => renderTicket(ticket)).join("");
            showResponse(data);
        } catch (error) {
            ticketsEl.innerHTML = "Failed to load tickets.";
            showResponse({ error: String(error) });
        }
    }

    function renderTicket(ticket) {
        const resolvedInfo = ticket.resolved_at
            ? `<br>Resolved at: ${escapeHtml(ticket.resolved_at)}`
            : "";

        const actionButtons = ticket.status === "resolved"
            ? `
                <button onclick="changeStatus(${ticket.id}, 'open')">Reopen</button>
              `
            : `
                <button onclick="changeStatus(${ticket.id}, 'open')">Open</button>
                <button onclick="changeStatus(${ticket.id}, 'in_progress')">In progress</button>
                <button class="danger" onclick="changeStatus(${ticket.id}, 'resolved')">Resolved</button>
              `;

        return `
            <div class="ticket">
                <div class="ticket-title">#${ticket.id} ${escapeHtml(ticket.title)}</div>
                <div class="description">${escapeHtml(ticket.description || "")}</div>

                <div class="meta">
                    <span class="pill">${escapeHtml(ticket.status)}</span>
                    <span class="pill priority">${escapeHtml(ticket.priority)}</span>
                    <span class="pill category">${escapeHtml(ticket.category_label || ticket.category)}</span>
                    <span class="pill resource">${escapeHtml(ticket.resource_label || ticket.resource)}</span>
                    <br>
                    source=${escapeHtml(ticket.source)}
                    | category=${escapeHtml(ticket.category)}
                    | resource=${escapeHtml(ticket.resource)}
                    <br>
                    Created at: ${escapeHtml(ticket.created_at)}
                    <br>
                    Updated at: ${escapeHtml(ticket.updated_at)}
                    ${resolvedInfo}
                </div>

                ${actionButtons}
            </div>
        `;
    }

    async function createTicket() {
        const category = document.getElementById("category").value;
        const resource = document.getElementById("resource").value;
        const priority = document.getElementById("priority").value;
        const description = document.getElementById("description").value.trim();

        if (!category || !resource) {
            alert("Choose digital service and service section");
            return;
        }

        if (!description) {
            alert("Description is required");
            return;
        }

        const payload = {
            category: category,
            resource: resource,
            priority: priority,
            description: description,
            source: "web"
        };

        const response = await fetch("/api/v1/tickets", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(payload)
        });

        const data = await response.json();
        showResponse(data);

        if (!response.ok) {
            alert(`Failed to create ticket: ${data.error || response.status}`);
            return;
        }

        document.getElementById("description").value = "";
        await loadTickets("active");
    }

    async function changeStatus(ticketId, status) {
        const response = await fetch(`/api/v1/tickets/${ticketId}/status`, {
            method: "PATCH",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                status: status,
                source: "web"
            })
        });

        const data = await response.json();
        showResponse(data);

        if (!response.ok) {
            alert(`Failed to change status: ${data.error || response.status}`);
            return;
        }

        await loadTickets(currentFilter);
    }

    function setActiveTab(filter) {
        for (const value of ["active", "resolved", "all"]) {
            const tab = document.getElementById(`tab-${value}`);
            if (tab) {
                tab.classList.toggle("active", value === filter);
            }
        }
    }

    function showResponse(data) {
        document.getElementById("api-response").textContent =
            JSON.stringify(data, null, 2);
    }

    function escapeHtml(value) {
        return String(value)
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll("\"", "&quot;")
            .replaceAll("'", "&#039;");
    }

    async function init() {
        await loadSupportModel();
        await loadHealth();
        await loadTickets("active");
    }

    init();
</script>
</body>
</html>

```

## MISIS_Digital Student Support backend

Файл:

```text
app: /opt/app/app.py
```

Backup-и:

```text
app: /opt/app/app.py.bak-before-supportdesk
app: /opt/app/app.py.bak-before-logging-polish
app: /opt/app/app.py.bak-before-product-model-v2
app: /opt/app/app.py.bak-before-product-observability-v2
app: /opt/app/app.py.bak-before-http-observability-v1
```

Данные:

```text
app: /opt/app/tickets.json
```

Backup старых заявок:

```text
app: /opt/app/tickets.json.bak-before-product-model-v2-...
app: /opt/app/tickets.json.bak-before-product-observability-v2
app: /opt/app/tickets.json.bak-before-http-observability-v1
```

Endpoints:

```text
GET    /health
GET    /v1/health
GET    /v1/support-model
GET    /tickets
GET    /v1/tickets
GET    /tickets/all
GET    /v1/tickets/all
GET    /tickets/<id>
GET    /v1/tickets/<id>
POST   /tickets
POST   /v1/tickets
PATCH  /tickets/<id>/status
PATCH  /v1/tickets/<id>/status
GET    /metrics
```

Product metrics:

```text
supportdesk_tickets_total
supportdesk_tickets_open
supportdesk_tickets_in_progress
supportdesk_tickets_resolved
supportdesk_tickets_active
supportdesk_tickets_current{status,category,resource,priority}
supportdesk_active_ticket_age_seconds_max{category,resource,priority}
```

HTTP/API metrics:

```text
supportdesk_http_requests_total{method,route,status_code}
supportdesk_http_request_duration_seconds_bucket{method,route,status_code,le}
supportdesk_http_request_duration_seconds_sum{method,route,status_code}
supportdesk_http_request_duration_seconds_count{method,route,status_code}
```

### Полный текущий код `/opt/app/app.py`

```python
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timezone
import json
import logging
import os
import re
import time

from prometheus_client import Counter, Histogram, CollectorRegistry, generate_latest

try:
    from prometheus_client import disable_created_metrics
    disable_created_metrics()
except ImportError:
    pass

HOST = "0.0.0.0"
PORT = 8080

PRODUCT_NAME = "MISIS_Digital Student Support"
SERVICE_NAME = "misis-digital-student-support-api"
SERVICE_VERSION = "1.1.0"
ENVIRONMENT = "lab"

LOG_FILE = "/var/log/app/app.log"
DATA_FILE = "/opt/app/tickets.json"
MAX_BODY_BYTES = 64 * 1024

STATUS_VALUES = ["open", "in_progress", "resolved"]
ACTIVE_STATUSES = ["open", "in_progress"]
PRIORITY_VALUES = ["low", "normal", "high", "critical"]

CATEGORY_LABELS = {
    "newlms-misis": "newlms.misis.ru",
    "lk-misis": "lk.misis.ru",
    "gornyak-misis": "gornyak.misis.ru",
    "folio-misis": "folio.misis.ru",
    "pulse-misis": "pulse.misis.ru",
    "vector-misis": "vector.misis.ru",
    "pay-misis": "pay.misis.ru",
}

RESOURCE_LABELS = {
    "login": "Login",
    "courses": "Courses",
    "schedule": "Schedule",
    "assignments": "Assignments",
    "tests": "Tests",
    "grades": "Grades",
    "files": "Files",
    "notifications": "Notifications",
    "video-lessons": "Video lessons",

    "gradebook": "Electronic gradebook",
    "attendance": "Attendance journal",
    "service-requests": "Service requests",
    "study-certificate": "Study certificate",
    "academic-leave": "Academic leave",
    "diploma-documents": "Diploma documents",
    "personal-data": "Personal data",

    "dorm-payment": "Dormitory payment",
    "cleaning-request": "Cleaning request",
    "plumber-request": "Plumber request",
    "electrician-request": "Electrician request",
    "commandant-appointment": "Commandant appointment",
    "room-info": "Room information",
    "documents": "Documents",

    "book-search": "Book search",
    "digital-books": "Digital books",
    "article-access": "Article access",
    "book-reservation": "Book reservation",
    "return-deadline": "Return deadline",
    "reader-profile": "Reader profile",

    "event-list": "Event list",
    "event-registration": "Event registration",
    "qr-ticket": "QR ticket",
    "event-reminders": "Event reminders",
    "attendance-check": "Attendance check",
    "certificates": "Certificates",
    "event-feedback": "Event feedback",

    "internships": "Internships",
    "vacancies": "Vacancies",
    "practice-documents": "Practice documents",
    "company-events": "Company events",
    "resume-upload": "Resume upload",
    "application-status": "Application status",
    "career-consultation": "Career consultation",

    "tuition-payment": "Tuition payment",
    "invoice": "Invoice",
    "payment-status": "Payment status",
    "refund": "Refund",
    "receipt": "Receipt",
}

CATEGORY_TO_RESOURCES = {
    "newlms-misis": [
        "login",
        "courses",
        "schedule",
        "assignments",
        "tests",
        "grades",
        "files",
        "notifications",
        "video-lessons",
    ],
    "lk-misis": [
        "login",
        "gradebook",
        "attendance",
        "service-requests",
        "study-certificate",
        "academic-leave",
        "diploma-documents",
        "personal-data",
        "notifications",
    ],
    "gornyak-misis": [
        "login",
        "dorm-payment",
        "cleaning-request",
        "plumber-request",
        "electrician-request",
        "commandant-appointment",
        "room-info",
        "documents",
    ],
    "folio-misis": [
        "login",
        "book-search",
        "digital-books",
        "article-access",
        "book-reservation",
        "return-deadline",
        "reader-profile",
    ],
    "pulse-misis": [
        "event-list",
        "event-registration",
        "qr-ticket",
        "event-reminders",
        "attendance-check",
        "certificates",
        "event-feedback",
    ],
    "vector-misis": [
        "internships",
        "vacancies",
        "practice-documents",
        "company-events",
        "resume-upload",
        "application-status",
        "career-consultation",
    ],
    "pay-misis": [
        "tuition-payment",
        "dorm-payment",
        "invoice",
        "payment-status",
        "refund",
        "receipt",
    ],
}

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s service=misis-digital-student-support-api %(message)s",
)


HTTP_METRICS_REGISTRY = CollectorRegistry()

HTTP_REQUESTS_TOTAL = Counter(
    "supportdesk_http_requests_total",
    "Total HTTP requests handled by MISIS Digital Student Support API",
    ["method", "route", "status_code"],
    registry=HTTP_METRICS_REGISTRY,
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "supportdesk_http_request_duration_seconds",
    "HTTP request duration in seconds for MISIS Digital Student Support API",
    ["method", "route", "status_code"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
    registry=HTTP_METRICS_REGISTRY,
)


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def as_text(value, default=""):
    if value is None:
        return default
    return str(value).strip()


def normalize_slug(value, default=""):
    text = as_text(value, default).lower()
    text = text.replace("_", "-").replace(" ", "-")
    text = re.sub(r"[^a-z0-9-]", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text or default


def normalize_status(value, default=""):
    text = as_text(value, default).lower()
    text = text.replace("-", "_").replace(" ", "_")
    text = re.sub(r"[^a-z0-9_]", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text or default


def clean_log_value(value):
    if value is None or value == "":
        return "-"
    return (
        str(value)
        .replace("\\", "\\\\")
        .replace("\n", "_")
        .replace("\r", "_")
        .replace("\t", "_")
        .replace(" ", "_")
    )


def category_label(category):
    return CATEGORY_LABELS.get(category, category)


def resource_label(resource):
    return RESOURCE_LABELS.get(resource, resource.replace("-", " ").title())


def build_title(category, resource):
    return f"{resource_label(resource)} issue on {category_label(category)}"


def validate_category_resource(category_value, resource_value):
    category = normalize_slug(category_value)
    resource = normalize_slug(resource_value)

    if not category:
        return None, None, "missing_category"

    if not resource:
        return None, None, "missing_resource"

    if category not in CATEGORY_TO_RESOURCES:
        return None, None, f"invalid_category:{category}"

    if resource not in CATEGORY_TO_RESOURCES[category]:
        return None, None, f"invalid_resource_for_category:{category}:{resource}"

    return category, resource, None


def validate_ticket(ticket):
    if not isinstance(ticket, dict):
        raise ValueError("ticket_must_be_object")

    category, resource, error = validate_category_resource(
        ticket.get("category"),
        ticket.get("resource"),
    )
    if error:
        raise ValueError(error)

    status = normalize_status(ticket.get("status"), "open")
    if status not in STATUS_VALUES:
        raise ValueError(f"invalid_status:{status}")

    priority = normalize_slug(ticket.get("priority"), "normal")
    if priority not in PRIORITY_VALUES:
        raise ValueError(f"invalid_priority:{priority}")

    normalized = dict(ticket)
    normalized["category"] = category
    normalized["category_label"] = category_label(category)
    normalized["resource"] = resource
    normalized["resource_label"] = resource_label(resource)
    normalized["status"] = status
    normalized["priority"] = priority
    normalized["source"] = normalize_slug(ticket.get("source"), "unknown")
    normalized["title"] = as_text(ticket.get("title")) or build_title(category, resource)
    normalized["description"] = as_text(ticket.get("description"))
    normalized["schema_version"] = 2

    if not normalized.get("created_at"):
        normalized["created_at"] = now_iso()

    if not normalized.get("updated_at"):
        normalized["updated_at"] = normalized["created_at"]

    if status == "resolved":
        if not normalized.get("resolved_at"):
            normalized["resolved_at"] = normalized["updated_at"]
    else:
        normalized["resolved_at"] = None

    return normalized


def service_model():
    return {
        "product": PRODUCT_NAME,
        "service": SERVICE_NAME,
        "version": SERVICE_VERSION,
        "categories": [
            {
                "value": category,
                "label": category_label(category),
                "resources": [
                    {
                        "value": resource,
                        "label": resource_label(resource),
                    }
                    for resource in resources
                ],
            }
            for category, resources in CATEGORY_TO_RESOURCES.items()
        ],
        "priorities": PRIORITY_VALUES,
        "statuses": STATUS_VALUES,
    }


def save_tickets(tickets):
    temp_file = f"{DATA_FILE}.tmp"

    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(tickets, f, ensure_ascii=False, indent=2)
        f.write("\n")

    os.replace(temp_file, DATA_FILE)


def load_tickets():
    if not os.path.exists(DATA_FILE):
        save_tickets([])
        return []

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        tickets = json.load(f)

    if not isinstance(tickets, list):
        raise ValueError("tickets_storage_must_be_list")

    normalized_tickets = []
    changed = False

    for index, ticket in enumerate(tickets, start=1):
        normalized = validate_ticket(ticket)

        try:
            ticket_id = int(normalized.get("id", index))
        except (TypeError, ValueError):
            ticket_id = index

        if normalized.get("id") != ticket_id:
            normalized["id"] = ticket_id
            changed = True

        if normalized != ticket:
            changed = True

        normalized_tickets.append(normalized)

    if changed:
        save_tickets(normalized_tickets)

    return normalized_tickets


def next_ticket_id(tickets):
    if not tickets:
        return 1
    return max(int(ticket["id"]) for ticket in tickets) + 1


def count_by_status(tickets, status):
    return sum(1 for ticket in tickets if ticket["status"] == status)


def active_tickets(tickets):
    return [ticket for ticket in tickets if ticket["status"] in ACTIVE_STATUSES]


def prometheus_label_value(value):
    return clean_log_value(value).replace("\\", "\\\\").replace('"', '\\"')


def prometheus_labels(**labels):
    return ",".join(
        f'{key}="{prometheus_label_value(value)}"'
        for key, value in labels.items()
    )


def ticket_age_seconds(ticket):
    try:
        created_at = datetime.fromisoformat(ticket["created_at"])
        return max(0, int((datetime.now(timezone.utc) - created_at).total_seconds()))
    except Exception:
        return 0


def make_list_payload(tickets, selected_tickets, selected_filter):
    return {
        "tickets": selected_tickets,
        "count": len(selected_tickets),
        "filter": selected_filter,
        "total": len(tickets),
        "active_count": len(active_tickets(tickets)),
        "open_count": count_by_status(tickets, "open"),
        "in_progress_count": count_by_status(tickets, "in_progress"),
        "resolved_count": count_by_status(tickets, "resolved"),
    }


def normalize_path(path):
    normalized = path.rstrip("/")
    return normalized or "/"


def strip_version_prefix(path):
    if path == "/v1":
        return "/"
    if path.startswith("/v1/"):
        return path[3:]
    return path


def api_version(path):
    if path == "/v1" or path.startswith("/v1/"):
        return "v1"
    return "legacy"


def metrics_route(raw_path):
    try:
        path = normalize_path(urlparse(raw_path).path)
    except Exception:
        return "unmatched"

    exact_routes = {
        "/health",
        "/v1/health",
        "/support-model",
        "/v1/support-model",
        "/model",
        "/v1/model",
        "/tickets",
        "/v1/tickets",
        "/tickets/all",
        "/v1/tickets/all",
        "/metrics",
    }

    if path in exact_routes:
        return path

    if re.fullmatch(r"/tickets/\d+", path):
        return "/tickets/{id}"

    if re.fullmatch(r"/v1/tickets/\d+", path):
        return "/v1/tickets/{id}"

    if re.fullmatch(r"/tickets/\d+/status", path):
        return "/tickets/{id}/status"

    if re.fullmatch(r"/v1/tickets/\d+/status", path):
        return "/v1/tickets/{id}/status"

    return "unmatched"


class SupportDeskHandler(BaseHTTPRequestHandler):
    def handle_one_request(self):
        self._request_started_at = time.monotonic()
        self._response_status_code = 0

        try:
            super().handle_one_request()
        finally:
            raw_path = getattr(self, "path", "")
            method = getattr(self, "command", "UNKNOWN")

            if not raw_path:
                return

            route = metrics_route(raw_path)

            if route == "/metrics":
                return

            status_code = str(getattr(self, "_response_status_code", 0) or 0)
            duration = time.monotonic() - self._request_started_at

            try:
                HTTP_REQUESTS_TOTAL.labels(
                    method=method,
                    route=route,
                    status_code=status_code,
                ).inc()

                HTTP_REQUEST_DURATION_SECONDS.labels(
                    method=method,
                    route=route,
                    status_code=status_code,
                ).observe(duration)
            except Exception:
                pass

    def send_response(self, code, message=None):
        self._response_status_code = int(code)
        super().send_response(code, message)

    def send_json(self, status_code, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")

        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def send_api_error(self, status_code, error, **fields):
        payload = {"error": error}
        payload.update(fields)
        self.send_json(status_code, payload)

    def read_json_body(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
        except ValueError:
            raise ValueError("invalid_content_length")

        if length == 0:
            return {}

        if length > MAX_BODY_BYTES:
            raise ValueError("request_body_too_large")

        raw_body = self.rfile.read(length)
        data = json.loads(raw_body.decode("utf-8"))

        if not isinstance(data, dict):
            raise ValueError("json_body_must_be_object")

        return data

    def log_event(self, level, event, status_code, **fields):
        client_ip = self.client_address[0]
        x_forwarded_for = self.headers.get("X-Forwarded-For", "-")
        x_forwarded_proto = self.headers.get("X-Forwarded-Proto", "-")

        parts = [
            f"event={event}",
            f"method={self.command}",
            f"path={clean_log_value(self.path)}",
            f"status={status_code}",
            f"client_ip={clean_log_value(client_ip)}",
            f"x_forwarded_for={clean_log_value(x_forwarded_for)}",
            f"x_forwarded_proto={clean_log_value(x_forwarded_proto)}",
        ]

        for key, value in fields.items():
            parts.append(f"{key}={clean_log_value(value)}")

        logging.log(level, " ".join(parts))

    def handle_internal_error(self, exc):
        self.send_api_error(500, "internal_server_error")
        self.log_event(logging.ERROR, "internal_error", 500, error=type(exc).__name__)

    def do_GET(self):
        parsed = urlparse(self.path)
        raw_path = normalize_path(parsed.path)
        path = strip_version_prefix(raw_path)
        version = api_version(raw_path)
        query = parse_qs(parsed.query)

        try:
            if path == "/health":
                payload = {
                    "status": "ok",
                    "product": PRODUCT_NAME,
                    "service": SERVICE_NAME,
                    "version": SERVICE_VERSION,
                    "environment": ENVIRONMENT,
                    "api_version": version,
                    "supported_api_versions": ["legacy", "v1"],
                    "time": now_iso(),
                }
                self.send_json(200, payload)
                self.log_event(logging.INFO, "health_check", 200, api_version=version)
                return

            if path in ["/support-model", "/model"]:
                self.send_json(200, service_model())
                self.log_event(logging.INFO, "support_model_requested", 200, api_version=version)
                return

            if path == "/tickets":
                tickets = load_tickets()
                status_filter = normalize_status(query.get("status", ["active"])[0], "active")

                if status_filter == "active":
                    selected_tickets = active_tickets(tickets)
                    selected_filter = "active"
                elif status_filter == "all":
                    selected_tickets = tickets
                    selected_filter = "all"
                elif status_filter in STATUS_VALUES:
                    selected_tickets = [
                        ticket for ticket in tickets
                        if ticket["status"] == status_filter
                    ]
                    selected_filter = status_filter
                else:
                    self.send_api_error(
                        400,
                        "invalid_status_filter",
                        allowed=["active", "all"] + STATUS_VALUES,
                    )
                    self.log_event(
                        logging.WARNING,
                        "ticket_validation_failed",
                        400,
                        reason="invalid_status_filter",
                    )
                    return

                payload = make_list_payload(tickets, selected_tickets, selected_filter)
                self.send_json(200, payload)
                self.log_event(
                    logging.INFO,
                    "ticket_list_requested",
                    200,
                    api_version=version,
                    filter=selected_filter,
                    count=len(selected_tickets),
                )
                return

            if path == "/tickets/all":
                tickets = load_tickets()
                payload = make_list_payload(tickets, tickets, "all")
                self.send_json(200, payload)
                self.log_event(
                    logging.INFO,
                    "ticket_list_requested",
                    200,
                    api_version=version,
                    filter="all",
                    count=len(tickets),
                )
                return

            detail_match = re.fullmatch(r"/tickets/(\d+)", path)
            if detail_match:
                ticket_id = int(detail_match.group(1))
                tickets = load_tickets()
                ticket = next(
                    (item for item in tickets if int(item["id"]) == ticket_id),
                    None,
                )

                if ticket is None:
                    self.send_api_error(404, "ticket_not_found")
                    self.log_event(
                        logging.WARNING,
                        "ticket_not_found",
                        404,
                        ticket_id=ticket_id,
                    )
                    return

                self.send_json(200, ticket)
                self.log_event(
                    logging.INFO,
                    "ticket_detail_requested",
                    200,
                    api_version=version,
                    ticket_id=ticket_id,
                    category=ticket.get("category"),
                    resource=ticket.get("resource"),
                )
                return

            if path == "/metrics":
                tickets = load_tickets()
                active = active_tickets(tickets)

                current_counts = {}
                oldest_active_age = {}

                for ticket in tickets:
                    current_key = (
                        ticket.get("status", "unknown"),
                        ticket.get("category", "unknown"),
                        ticket.get("resource", "unknown"),
                        ticket.get("priority", "unknown"),
                    )
                    current_counts[current_key] = current_counts.get(current_key, 0) + 1

                for ticket in active:
                    age = ticket_age_seconds(ticket)
                    age_key = (
                        ticket.get("category", "unknown"),
                        ticket.get("resource", "unknown"),
                        ticket.get("priority", "unknown"),
                    )
                    oldest_active_age[age_key] = max(
                        oldest_active_age.get(age_key, 0),
                        age,
                    )

                lines = [
                    "# HELP supportdesk_tickets_total Total number of support desk tickets",
                    "# TYPE supportdesk_tickets_total gauge",
                    f"supportdesk_tickets_total {len(tickets)}",
                    "# HELP supportdesk_tickets_open Number of open support desk tickets",
                    "# TYPE supportdesk_tickets_open gauge",
                    f"supportdesk_tickets_open {count_by_status(tickets, 'open')}",
                    "# HELP supportdesk_tickets_in_progress Number of in-progress support desk tickets",
                    "# TYPE supportdesk_tickets_in_progress gauge",
                    f"supportdesk_tickets_in_progress {count_by_status(tickets, 'in_progress')}",
                    "# HELP supportdesk_tickets_resolved Number of resolved support desk tickets",
                    "# TYPE supportdesk_tickets_resolved gauge",
                    f"supportdesk_tickets_resolved {count_by_status(tickets, 'resolved')}",
                    "# HELP supportdesk_tickets_active Number of active support desk tickets",
                    "# TYPE supportdesk_tickets_active gauge",
                    f"supportdesk_tickets_active {len(active)}",
                    "# HELP supportdesk_tickets_current Current support desk tickets by status, category, resource and priority",
                    "# TYPE supportdesk_tickets_current gauge",
                ]

                for (status, category, resource, priority), count in sorted(current_counts.items()):
                    labels = prometheus_labels(
                        status=status,
                        category=category,
                        resource=resource,
                        priority=priority,
                    )
                    lines.append(f"supportdesk_tickets_current{{{labels}}} {count}")

                lines.extend([
                    "# HELP supportdesk_active_ticket_age_seconds_max Oldest active support desk ticket age in seconds by category, resource and priority",
                    "# TYPE supportdesk_active_ticket_age_seconds_max gauge",
                ])

                for (category, resource, priority), age in sorted(oldest_active_age.items()):
                    labels = prometheus_labels(
                        category=category,
                        resource=resource,
                        priority=priority,
                    )
                    lines.append(f"supportdesk_active_ticket_age_seconds_max{{{labels}}} {age}")

                lines.append("")
                product_metrics_body = "\n".join(lines).encode("utf-8")
                http_metrics_body = generate_latest(HTTP_METRICS_REGISTRY)
                body = product_metrics_body + http_metrics_body

                self.send_response(200)
                self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)

                self.log_event(logging.INFO, "metrics_requested", 200, api_version=version)
                return

            self.send_api_error(404, "not_found")
            self.log_event(logging.WARNING, "endpoint_not_found", 404, api_version=version)

        except json.JSONDecodeError:
            self.send_api_error(500, "tickets_storage_invalid_json")
            self.log_event(logging.ERROR, "internal_error", 500, error="tickets_storage_invalid_json")
        except ValueError as exc:
            self.send_api_error(500, "tickets_storage_invalid", detail=str(exc))
            self.log_event(logging.ERROR, "internal_error", 500, error=str(exc))
        except Exception as exc:
            self.handle_internal_error(exc)

    def do_POST(self):
        parsed = urlparse(self.path)
        raw_path = normalize_path(parsed.path)
        path = strip_version_prefix(raw_path)
        version = api_version(raw_path)

        try:
            if path != "/tickets":
                self.send_api_error(404, "not_found")
                self.log_event(logging.WARNING, "endpoint_not_found", 404, api_version=version)
                return

            try:
                data = self.read_json_body()
            except json.JSONDecodeError:
                self.send_api_error(400, "invalid_json")
                self.log_event(logging.WARNING, "ticket_validation_failed", 400, reason="invalid_json")
                return
            except ValueError as exc:
                self.send_api_error(400, str(exc))
                self.log_event(logging.WARNING, "ticket_validation_failed", 400, reason=str(exc))
                return

            category, resource, error = validate_category_resource(
                data.get("category"),
                data.get("resource"),
            )
            if error:
                self.send_api_error(400, error)
                self.log_event(logging.WARNING, "ticket_validation_failed", 400, reason=error)
                return

            priority = normalize_slug(data.get("priority", "normal"), "normal")
            if priority not in PRIORITY_VALUES:
                self.send_api_error(400, "invalid_priority", allowed=PRIORITY_VALUES)
                self.log_event(logging.WARNING, "ticket_validation_failed", 400, reason="invalid_priority")
                return

            title = as_text(data.get("title")) or build_title(category, resource)
            description = as_text(data.get("description"))
            source = normalize_slug(data.get("source", "web"), "web")
            created_at = now_iso()
            tickets = load_tickets()

            ticket = {
                "id": next_ticket_id(tickets),
                "schema_version": 2,
                "title": title,
                "category": category,
                "category_label": category_label(category),
                "resource": resource,
                "resource_label": resource_label(resource),
                "description": description,
                "priority": priority,
                "status": "open",
                "source": source,
                "created_at": created_at,
                "updated_at": created_at,
                "resolved_at": None,
            }

            tickets.append(ticket)
            save_tickets(tickets)

            self.send_json(201, ticket)
            self.log_event(
                logging.INFO,
                "ticket_created",
                201,
                api_version=version,
                ticket_id=ticket["id"],
                category=category,
                resource=resource,
                priority=priority,
                source=source,
            )

        except Exception as exc:
            self.handle_internal_error(exc)

    def do_PATCH(self):
        parsed = urlparse(self.path)
        raw_path = normalize_path(parsed.path)
        path = strip_version_prefix(raw_path)
        version = api_version(raw_path)

        try:
            match = re.fullmatch(r"/tickets/(\d+)/status", path)
            if not match:
                self.send_api_error(404, "not_found")
                self.log_event(logging.WARNING, "endpoint_not_found", 404, api_version=version)
                return

            ticket_id = int(match.group(1))

            try:
                data = self.read_json_body()
            except json.JSONDecodeError:
                self.send_api_error(400, "invalid_json")
                self.log_event(
                    logging.WARNING,
                    "ticket_validation_failed",
                    400,
                    reason="invalid_json",
                    ticket_id=ticket_id,
                )
                return
            except ValueError as exc:
                self.send_api_error(400, str(exc))
                self.log_event(
                    logging.WARNING,
                    "ticket_validation_failed",
                    400,
                    reason=str(exc),
                    ticket_id=ticket_id,
                )
                return

            new_status = normalize_status(data.get("status"), "")
            source = normalize_slug(data.get("source", "web"), "web")

            if new_status not in STATUS_VALUES:
                self.send_api_error(400, "invalid_status", allowed=STATUS_VALUES)
                self.log_event(
                    logging.WARNING,
                    "ticket_validation_failed",
                    400,
                    reason="invalid_status",
                    ticket_id=ticket_id,
                    source=source,
                )
                return

            tickets = load_tickets()
            ticket = next(
                (item for item in tickets if int(item["id"]) == ticket_id),
                None,
            )

            if ticket is None:
                self.send_api_error(404, "ticket_not_found")
                self.log_event(
                    logging.WARNING,
                    "ticket_not_found",
                    404,
                    ticket_id=ticket_id,
                    source=source,
                )
                return

            old_status = ticket["status"]

            if old_status == new_status:
                self.send_json(200, ticket)
                self.log_event(
                    logging.INFO,
                    "ticket_status_unchanged",
                    200,
                    api_version=version,
                    ticket_id=ticket_id,
                    old_status=old_status,
                    new_status=new_status,
                    category=ticket.get("category"),
                    resource=ticket.get("resource"),
                    source=source,
                )
                return

            changed_at = now_iso()
            ticket["status"] = new_status
            ticket["updated_at"] = changed_at
            ticket["resolved_at"] = changed_at if new_status == "resolved" else None
            ticket["schema_version"] = 2

            save_tickets(tickets)

            self.send_json(200, ticket)
            self.log_event(
                logging.INFO,
                "ticket_status_changed",
                200,
                api_version=version,
                ticket_id=ticket_id,
                old_status=old_status,
                new_status=new_status,
                category=ticket.get("category"),
                resource=ticket.get("resource"),
                source=source,
                resolved_at=ticket.get("resolved_at"),
            )

        except Exception as exc:
            self.handle_internal_error(exc)

    def log_message(self, format, *args):
        return


if __name__ == "__main__":
    server = HTTPServer((HOST, PORT), SupportDeskHandler)
    server.serve_forever()

```

## Windows portproxy для будущего Telegram bot

Текущий workaround без секретов:

```text
192.168.85.1:10802 -> 127.0.0.1:10801
```

Команды:

```cmd
netsh interface portproxy add v4tov4 listenaddress=192.168.85.1 listenport=10802 connectaddress=127.0.0.1 connectport=10801
netsh advfirewall firewall add rule name="Allow VM to XRay proxy 10802" dir=in action=allow protocol=TCP localip=192.168.85.1 localport=10802 remoteip=192.168.85.0/24
```

Проверка с `app`:

```bash
nc -vzn 192.168.85.1 10802
curl -x http://192.168.85.1:10802 -I https://api.telegram.org
```

Будущий env:

```bash
HTTP_PROXY=http://192.168.85.1:10802
HTTPS_PROXY=http://192.168.85.1:10802
NO_PROXY=localhost,127.0.0.1,192.168.85.0/24
```
