# Важные текущие конфигурационные файлы проекта

Файл хранит **только актуальные конфиги** текущего состояния Mini Corporate Infrastructure Lab после Stage 18.

Что важно:

- полный код больших runtime-файлов **не дублируется здесь**;
- актуальный backend-код лежит отдельным файлом `app.py` в источниках;
- актуальный Telegram bot-код лежит отдельным файлом `bot.py` в источниках;
- секреты не фиксируются: пароли и Telegram token заменены на `<redacted>`;
- маленькие конфиги и dashboard/alert queries фиксируются здесь полностью, чтобы в новом чате можно было быстро восстановить контекст.

---

## 1. Admin / Ansible

### `admin: ~/control-node/inventory/hosts.ini`

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

[db_nodes]
db ansible_host=192.168.85.139

[managed:children]
web_nodes
app_nodes
log_nodes
monitor_nodes
db_nodes

[all:vars]
ansible_user=pelmel
ansible_python_interpreter=/usr/bin/python3
```

### `admin: ~/control-node/ansible.cfg`

```ini
[defaults]
roles_path = ./roles
inventory = inventory/hosts.ini
remote_user = pelmel
host_key_checking = False
interpreter_python = /usr/bin/python3
retry_files_enabled = False

[privilege_escalation]
become = False
```

### `admin: ~/control-node/playbooks/ping_all.yml`

```yaml
---
- name: Ping all infrastructure nodes
  hosts: all
  gather_facts: false

  tasks:
    - name: Check Ansible connection
      ansible.builtin.ping:
```

### `admin: ~/control-node/playbooks/check_services.yml`

Вариант идеала (пока реализован без проверки состояния контейнера с ботом - он учитывает, что backend и Telegram bot на `app` работают как Docker Compose services, а не как `app.service`.

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
    - name: Check supportdesk-api container is running
      ansible.builtin.command: docker compose ps --status running supportdesk-api
      args:
        chdir: /opt/app
      changed_when: false

    - name: Check support-bot container is running
      ansible.builtin.command: docker compose ps --status running support-bot
      args:
        chdir: /opt/app
      changed_when: false

    - name: Check supportdesk-api health endpoint
      ansible.builtin.uri:
        url: http://localhost:8080/v1/health
        method: GET
        status_code: 200
        return_content: false

    - name: Check support-bot metrics endpoint
      ansible.builtin.uri:
        url: http://localhost:8090/metrics
        method: GET
        status_code: 200
        return_content: false

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


- name: Check db services
  hosts: db_nodes
  gather_facts: false

  tasks:
    - name: Check postgresql
      ansible.builtin.command: systemctl is-active postgresql.service
      changed_when: false

    - name: Check postgres_exporter
      ansible.builtin.command: systemctl is-active postgres_exporter.service
      changed_when: false

    - name: Check promtail
      ansible.builtin.command: systemctl is-active promtail.service
      changed_when: false

    - name: Check node_exporter
      ansible.builtin.command: systemctl is-active prometheus-node-exporter.service
      changed_when: false
```

### `admin: ~/control-node/playbooks/restart_app.yml`

Актуальный смысл (точно также как с предыдущим, пока не реализовано, сюда как вариант идеала загружен): перезапуск backend-контейнера через Docker Compose.

```yaml
---
- name: Restart supportdesk-api container
  hosts: app_nodes
  gather_facts: false
  become: true

  vars_prompt:
    - name: ansible_become_password
      prompt: "BECOME password"
      private: true

  tasks:
    - name: Restart supportdesk-api Docker Compose service
      ansible.builtin.command: docker compose restart supportdesk-api
      args:
        chdir: /opt/app
      changed_when: true

    - name: Check supportdesk-api container is running
      ansible.builtin.command: docker compose ps --status running supportdesk-api
      args:
        chdir: /opt/app
      changed_when: false

    - name: Check local health endpoint
      ansible.builtin.uri:
        url: http://localhost:8080/v1/health
        method: GET
        status_code: 200
        return_content: true
```

### `admin: ~/control-node/playbooks/deploy_prometheus_rules.yml`

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

---

## 2. Docker runtime на app

### `app: /opt/app/Dockerfile`

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

### `app: /opt/app/requirements.txt`

```text
prometheus_client
psycopg2-binary
```

### `app: /opt/app/Dockerfile.bot`

```dockerfile
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

ARG APP_UID=1000
ARG APP_GID=1000

RUN groupadd --gid ${APP_GID} botuser \
    && useradd --uid ${APP_UID} --gid ${APP_GID} --home-dir /opt/app --shell /usr/sbin/nologin botuser

WORKDIR /opt/app

COPY requirements-bot.txt /opt/app/requirements-bot.txt
RUN pip install --no-cache-dir -r /opt/app/requirements-bot.txt

COPY bot.py /opt/app/bot.py

RUN mkdir -p /var/log/bot \
    && chown -R botuser:botuser /opt/app /var/log/bot

USER botuser

EXPOSE 8090

CMD ["python", "/opt/app/bot.py"]
```

### `app: /opt/app/requirements-bot.txt`

```text
python-telegram-bot==22.7
httpx
prometheus_client
```

### `app: /opt/app/docker-compose.yml`

```yaml
services:
  supportdesk-api:
    build:
      context: .
      dockerfile: Dockerfile
      args:
        APP_UID: ${APP_UID:-1000}
        APP_GID: ${APP_GID:-1000}
    image: misis-digital-student-support-api:local
    container_name: misis-digital-student-support-api
    restart: unless-stopped
    env_file:
      - .env
    ports:
      - "8080:8080"
    volumes:
      - /var/log/app:/var/log/app
    environment:
      TZ: UTC

  support-bot:
    build:
      context: .
      dockerfile: Dockerfile.bot
      args:
        APP_UID: ${APP_UID:-1000}
        APP_GID: ${APP_GID:-1000}
    image: misis-digital-support-bot:local
    container_name: misis-digital-support-bot
    restart: unless-stopped
    env_file:
      - .env.bot
    ports:
      - "8090:8090"
    volumes:
      - /var/log/bot:/var/log/bot
    environment:
      TZ: UTC
      METRICS_PORT: 8090
    depends_on:
      - supportdesk-api
```

### `app: /opt/app/.dockerignore`

```dockerignore
backups/
*.bak*
__pycache__/
*.pyc
.env
.env.bot
```

### `app: /opt/app/.env` template

```env
APP_UID=1000
APP_GID=1000

DB_HOST=192.168.85.139
DB_PORT=5432
DB_NAME=supportdesk
DB_USER=supportdesk_user
DB_PASSWORD=<redacted>
```

### `app: /opt/app/.env.bot` template

```env
TELEGRAM_BOT_TOKEN=<redacted>
TELEGRAM_BOT_USERNAME=misis_digital_support_bot
SUPPORTDESK_API_URL=http://supportdesk-api:8080
METRICS_PORT=8090

HTTP_PROXY=http://192.168.85.1:10802
HTTPS_PROXY=http://192.168.85.1:10802
NO_PROXY=localhost,127.0.0.1,supportdesk-api,192.168.85.133,192.168.85.131,192.168.85.135,192.168.85.137,192.168.85.139

ALLOWED_TELEGRAM_USER_IDS=
```

Примечания:

- `.env` и `.env.bot` не входят в Docker image и не должны попадать в Git/source archive;
- bot token после leak был перевыпущен через BotFather;
- `ALLOWED_TELEGRAM_USER_IDS` пока пустой: bot открыт для lab/demo; перед публичной демонстрацией whitelist лучше включить.

---

## 3. Nginx reverse proxy на web

### `web: /etc/nginx/sites-available/default`

```nginx
server {
    listen 80 default_server;
    listen [::]:80 default_server;

    root /var/www/html;
    index index.html index.htm index.nginx-debian.html;

    server_name _;

    location / {
        try_files $uri $uri/ =404;
    }

    location /api/ {
        proxy_pass http://192.168.85.133:8080/;

        proxy_http_version 1.1;

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Смысл:

- frontend лежит в `/var/www/html/index.html`;
- все `/api/*` уходят на backend `app:8080`;
- `X-Forwarded-For` сохраняет исходный client IP для backend logs.

---

## 4. PostgreSQL network access

### `db: /etc/postgresql/17/main/postgresql.conf`

```conf
listen_addresses = '*'
```

Причина: при привязке к конкретному DHCP-IP после reboot PostgreSQL мог стартовать до появления IP на интерфейсе и слушал только localhost. После перехода на `*` повторной ошибки bind после reboot не было.

### `db: /etc/postgresql/17/main/pg_hba.conf`

```conf
host    supportdesk    supportdesk_user    192.168.85.133/32    scram-sha-256
```

Важно: `listen_addresses='*'` не означает открытый доступ всем. Реальный доступ ограничен `pg_hba.conf`: подключаться к БД `supportdesk` под ролью `supportdesk_user` разрешено только `app`-серверу `192.168.85.133`.

---

## 5. Promtail

### `web: /etc/promtail/config.yml`

```yaml
server:
  http_listen_port: 9080
  grpc_listen_port: 0

positions:
  filename: /var/lib/promtail/positions.yaml

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

### `app: /etc/promtail/config.yml`

```yaml
server:
  http_listen_port: 9080
  grpc_listen_port: 0

positions:
  filename: /var/lib/promtail/positions.yaml

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

  - job_name: support-bot
    static_configs:
      - targets:
          - localhost
        labels:
          host: app
          job: support-bot
          service: misis-digital-support-bot
          env: lab
          __path__: /var/log/bot/*.log
```

### `db: /etc/promtail/config.yml`

```yaml
server:
  http_listen_port: 9080
  grpc_listen_port: 0

positions:
  filename: /var/lib/promtail/positions.yaml

clients:
  - url: http://192.168.85.135:3100/loki/api/v1/push

scrape_configs:
  - job_name: postgresql
    static_configs:
      - targets:
          - localhost
        labels:
          host: db
          job: postgresql
          service: postgresql
          env: lab
          __path__: /var/log/postgresql/*.log
```

---

## 6. Prometheus

### `monitor: /etc/prometheus/prometheus.yml`

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

alerting:
  alertmanagers:
    - static_configs:
        - targets:
            - localhost:9093

rule_files:
  - /etc/prometheus/supportdesk.rules.yml

scrape_configs:
  - job_name: prometheus
    static_configs:
      - targets:
          - localhost:9090

  - job_name: node
    static_configs:
      - targets:
          - localhost:9100
        labels:
          host: monitor

      - targets:
          - 192.168.85.131:9100
        labels:
          host: web

      - targets:
          - 192.168.85.133:9100
        labels:
          host: app

      - targets:
          - 192.168.85.135:9100
        labels:
          host: log

      - targets:
          - 192.168.85.139:9100
        labels:
          host: db

  - job_name: supportdesk-api
    metrics_path: /metrics
    static_configs:
      - targets:
          - 192.168.85.133:8080
        labels:
          host: app
          service: support-desk-api
          env: lab

  - job_name: support-bot
    metrics_path: /metrics
    static_configs:
      - targets:
          - 192.168.85.133:8090
        labels:
          host: app
          service: misis-digital-support-bot
          env: lab

  - job_name: promtail-web
    metrics_path: /metrics
    static_configs:
      - targets:
          - 192.168.85.131:9080
        labels:
          host: web
          service: promtail
          env: lab

  - job_name: postgres
    metrics_path: /metrics
    static_configs:
      - targets:
          - 192.168.85.139:9187
        labels:
          host: db
          service: postgresql
          env: lab
```

### `monitor: /etc/prometheus/supportdesk.rules.yml`

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
          summary: "Support Desk API is down"
          description: "Prometheus cannot scrape MISIS_Digital Student Support API for more than 30 seconds. Instance: {{ $labels.instance }}."

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
          summary: "Support Desk API has high 4xx rate"
          description: "More than 30% of recent API requests returned 4xx responses. This usually means many invalid client, UI or API requests."

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
          summary: "Support Desk API has high 5xx rate"
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
          summary: "Support Desk API has high latency"
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
          description: "Nginx on web returned {{ printf \"%.0f\" $value }} HTTP 502 responses in the last 5 minutes. This usually means the backend app is unavailable or reverse proxy upstream is broken."

      - alert: PostgreSQLExporterDown
        expr: up{job="postgres"} == 0
        for: 30s
        labels:
          severity: critical
          service: postgresql
        annotations:
          summary: "PostgreSQL exporter is down"
          description: "Prometheus cannot scrape postgres_exporter for more than 30 seconds. Host: {{ $labels.host }}. Instance: {{ $labels.instance }}."

      - alert: PostgreSQLDown
        expr: pg_up{job="postgres"} == 0
        for: 30s
        labels:
          severity: critical
          service: postgresql
        annotations:
          summary: "PostgreSQL is unavailable"
          description: "postgres_exporter is reachable, but it cannot connect to PostgreSQL. Host: {{ $labels.host }}."

      - alert: PostgreSQLTooManyConnections
        expr: |
          max by(host) (
            pg_stat_database_numbackends{job="postgres",datname="supportdesk"}
          )
          /
          max by(host) (
            pg_settings_max_connections{job="postgres"}
          ) > 0.8
        for: 2m
        labels:
          severity: warning
          service: postgresql
        annotations:
          summary: "PostgreSQL has too many connections"
          description: "The supportdesk database is using more than 80% of max_connections. Host: {{ $labels.host }}."

      - alert: HighDiskUsage
        expr: 100 * (1 - (node_filesystem_avail_bytes{job="node", mountpoint="/", fstype="ext4"} / node_filesystem_size_bytes{job="node", mountpoint="/", fstype="ext4"})) > 80
        for: 2m
        labels:
          severity: warning
          service: node
        annotations:
          summary: "Root disk usage is high"
          description: "Root filesystem usage is above 80%. Host: {{ $labels.host }}. Current usage: {{ printf \"%.1f\" $value }}%."

      - alert: NodeTargetDown
        expr: up{job="node"} == 0
        for: 30s
        labels:
          severity: critical
          service: node
        annotations:
          summary: "Node exporter target is down"
          description: "Prometheus cannot scrape node_exporter for more than 30 seconds. Host: {{ $labels.host }}. Instance: {{ $labels.instance }}."

      - alert: SupportDeskTooManyTicketsForResource
        expr: sum by(category, resource) (supportdesk_tickets_current{job="supportdesk-api",status=~"open|in_progress"}) >= 3
        for: 30s
        labels:
          severity: warning
          service: support-desk-api
        annotations:
          summary: "Too many active tickets for one resource"
          description: "There are {{ printf \"%.0f\" $value }} active tickets for category={{ $labels.category }}, resource={{ $labels.resource }}."

      - alert: SupportDeskCriticalTicketsOpen
        expr: sum by(category, resource) (supportdesk_tickets_current{job="supportdesk-api",status=~"open|in_progress",priority="critical"}) > 0
        for: 30s
        labels:
          severity: critical
          service: support-desk-api
        annotations:
          summary: "Critical support ticket is open"
          description: "There are {{ printf \"%.0f\" $value }} active critical tickets for category={{ $labels.category }}, resource={{ $labels.resource }}."

      - alert: SupportDeskOldCriticalTicket
        expr: max by(category, resource) (supportdesk_active_ticket_age_seconds_max{job="supportdesk-api",priority="critical"}) > 600
        for: 30s
        labels:
          severity: critical
          service: support-desk-api
        annotations:
          summary: "Old critical support ticket is still open"
          description: "The oldest active critical ticket is older than 10 minutes. Category: {{ $labels.category }}. Resource: {{ $labels.resource }}. Age: {{ printf \"%.0f\" $value }} seconds."

      - alert: SupportBotDown
        expr: up{job="support-bot"} == 0
        for: 30s
        labels:
          severity: critical
          service: misis-digital-support-bot
        annotations:
          summary: "Telegram support bot is down"
          description: "Prometheus cannot scrape the support-bot metrics endpoint for more than 30 seconds. Instance: {{ $labels.instance }}."

      - alert: SupportBotBackendErrors
        expr: |
          sum by(endpoint, method, status_code) (
            increase(
              support_bot_api_requests_total{
                job="support-bot",
                status_code!~"2.."
              }[10m]
            )
          ) >= 1
        for: 30s
        labels:
          severity: warning
          service: misis-digital-support-bot
        annotations:
          summary: "Telegram support bot has backend API errors"
          description: "The bot received failed backend API responses during the last 10 minutes. Endpoint: {{ $labels.endpoint }}. Method: {{ $labels.method }}. Status: {{ $labels.status_code }}. Errors: {{ printf \"%.0f\" $value }}."

      - alert: SupportBotErrorsDetected
        expr: |
          increase(
            support_bot_errors_total{
              job="support-bot",
              type!="backend_error"
            }[10m]
          ) >= 1
        for: 30s
        labels:
          severity: warning
          service: misis-digital-support-bot
        annotations:
          summary: "Telegram support bot has non-backend errors"
          description: "The bot recorded non-backend errors during the last 10 minutes. Error type: {{ $labels.type }}. Errors: {{ printf \"%.0f\" $value }}."
```

---

## 7. Alertmanager

### `monitor: /etc/default/prometheus-alertmanager`

```bash
ARGS="--cluster.listen-address="
```

Причина: в single-node lab cluster/gossip listener не нужен. Пустое значение отключает cluster listener и решает autostart issue после reboot.

---

## 8. PostgreSQL backup service/timer на db

### `db: /usr/local/sbin/backup-supportdesk.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="/var/backups/postgresql/supportdesk"
RETENTION_DAYS="7"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_FILE="${BACKUP_DIR}/supportdesk-${TIMESTAMP}.dump"
CHECKSUM_FILE="${BACKUP_FILE}.sha256"
LOG_FILE="/var/log/postgresql/supportdesk-backup.log"

mkdir -p "${BACKUP_DIR}"

{
  echo "$(date --iso-8601=seconds) backup_start file=${BACKUP_FILE}"

  sudo -u postgres pg_dump -Fc supportdesk -f "${BACKUP_FILE}"

  sha256sum "${BACKUP_FILE}" > "${CHECKSUM_FILE}"
  ln -sfn "${BACKUP_FILE}" "${BACKUP_DIR}/latest.dump"

  find "${BACKUP_DIR}" -type f -name 'supportdesk-*.dump' -mtime +"${RETENTION_DAYS}" -delete
  find "${BACKUP_DIR}" -type f -name 'supportdesk-*.dump.sha256' -mtime +"${RETENTION_DAYS}" -delete

  echo "$(date --iso-8601=seconds) backup_success file=${BACKUP_FILE} checksum=${CHECKSUM_FILE}"
} >> "${LOG_FILE}" 2>&1
```

### `db: /etc/systemd/system/backup-supportdesk.service`

```ini
[Unit]
Description=Backup supportdesk PostgreSQL database

[Service]
Type=oneshot
ExecStart=/usr/local/sbin/backup-supportdesk.sh
```

### `db: /etc/systemd/system/backup-supportdesk.timer`

```ini
[Unit]
Description=Run supportdesk PostgreSQL backup daily

[Timer]
OnCalendar=*-*-* 03:15:00
Persistent=true
Unit=backup-supportdesk.service

[Install]
WantedBy=timers.target
```

---

## 9. Grafana datasources

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

---

## 10. Grafana dashboard: Infrastructure Overview

Dashboard создан через Grafana UI. JSON export пока не зафиксирован. Ниже — актуальные PromQL/LogQL для ключевых panels.

### 10.1 Product/API panels

`SupportDesk API UP`:

```promql
up{job="supportdesk-api"}
```

`SupportDesk Tickets`:

```promql
supportdesk_tickets_total{job="supportdesk-api"}
supportdesk_tickets_open{job="supportdesk-api"}
supportdesk_tickets_in_progress{job="supportdesk-api"}
supportdesk_tickets_resolved{job="supportdesk-api"}
supportdesk_tickets_active{job="supportdesk-api"}
```

`Open tickets by category`:

```promql
sum by(category) (supportdesk_tickets_current{job="supportdesk-api",status="open"})
```

`Active tickets by category/resource`:

```promql
topk(10, sum by(category, resource) (supportdesk_tickets_current{job="supportdesk-api",status=~"open|in_progress"}))
```

`Critical active tickets`:

```promql
sum by(category, resource) (supportdesk_tickets_current{job="supportdesk-api",status=~"open|in_progress",priority="critical"})
```

`Oldest active tickets`:

```promql
topk(10, max by(category, resource, priority) (supportdesk_active_ticket_age_seconds_max{job="supportdesk-api"}))
```

### 10.2 HTTP/API observability panels

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

`API p95 Latency by Route`:

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

### 10.3 App logs panel

`App logs` — Loki datasource:

```logql
{host="app", job="app", service="misis-digital-student-support-api"}
| logfmt
| path != "/metrics"
| line_format "{{.event}}{{ if .method }} | {{.method}}{{ end }}{{ if .path }} {{.path}}{{ end }}{{ if .status }} | status={{.status}}{{ end }}{{ if .ticket_id }} | ticket={{.ticket_id}}{{ end }}{{ if .old_status }} | {{.old_status}}{{ end }}{{ if .new_status }} -> {{.new_status}}{{ end }}{{ if .category }} | category={{.category}}{{ end }}{{ if .resource }} | resource={{.resource}}{{ end }}{{ if .priority }} | priority={{.priority}}{{ end }}{{ if .source }} | source={{.source}}{{ end }}{{ if .filter }} | filter={{.filter}}{{ end }}{{ if .count }} | count={{.count}}{{ end }}{{ if .reason }} | reason={{.reason}}{{ end }}{{ if and .x_forwarded_for (ne .x_forwarded_for \"-\") }} | client={{.x_forwarded_for}}{{ end }}{{ if .client_ip }} | via={{.client_ip}}{{ end }}{{ if .error }} | error={{.error}}{{ end }}"
```

`via` в этой панели означает direct/remote IP — кто физически подключился к backend API. Для Telegram bot это обычно Docker IP вида `172.18.0.x`; для Prometheus `/metrics`-шум убран через `path != "/metrics"`.

### 10.4 Telegram Bot Observability row

`Telegram Bot Alerts` — Alert list panel:

```text
Datasource: prometheus
Alert name filter: SupportBot
Show alerts with 0 instances: ON
Alert state filter: Normal, Pending, Firing
Sort order: Alphabetical (asc)
```

`Telegram Bot Runtime` — Stat panel:

```promql
time() - max(support_bot_start_time_seconds{job="support-bot"})
```

Legend: `Uptime`, unit: duration seconds.

```promql
round(
  sum(
    increase(
      support_bot_actions_total{job="support-bot"}[30m]
    )
  ) or vector(0)
)
```

Legend: `Actions / 30m`, decimals: 0.

```promql
round(
  sum(
    increase(
      support_bot_api_requests_total{job="support-bot"}[30m]
    )
  ) or vector(0)
)
```

Legend: `API calls / 30m`, decimals: 0.

`Bot -> API latency by endpoint / 30m` — Bar gauge, Instant ON, unit seconds, min `0`, max `0.2`, thresholds `0 green`, `0.1 yellow`, `0.2 red`:

```promql
histogram_quantile(
  0.95,
  sum by(endpoint, le) (
    increase(
      support_bot_api_request_duration_seconds_bucket{job="support-bot"}[30m]
    )
  )
)
```

Legend: `{{endpoint}}`.

`Bot API requests by endpoint/status / 30m` — Bar gauge, Instant ON:

```promql
round(
  sum by(endpoint, status_code) (
    increase(
      support_bot_api_requests_total{job="support-bot"}[30m]
    )
  )
) > 0
```

Legend: `{{endpoint}} {{status_code}}`.

`Bot actions / 30m` — Bar gauge, Instant ON:

```promql
round(
  sum by(action) (
    increase(
      support_bot_actions_total{job="support-bot"}[30m]
    )
  )
) > 0
```

Legend: `{{action}}`.

`Bot recent logs` — Loki datasource:

```logql
{host="app", job="support-bot", service="misis-digital-support-bot"}
| logfmt
| line_format "{{.event}}{{ if .normalized_action }} | action={{.normalized_action}}{{ end }}{{ if .ticket_id }} | ticket={{.ticket_id}}{{ end }}{{ if .new_status }} | status={{.new_status}}{{ end }}{{ if .category }} | category={{.category}}{{ end }}{{ if .resource }} | resource={{.resource}}{{ end }}{{ if .count }} | count={{.count}}{{ end }}{{ if .page }} | page={{.page}}{{ end }}{{ if .error_type }} | error_type={{.error_type}}{{ end }}{{ if .error }} | error={{.error}}{{ end }}{{ if .telegram_user_id }} | user={{.telegram_user_id}}{{ end }}"
```

`Bot error logs` — Loki datasource:

```logql
{host="app", job="support-bot", service="misis-digital-support-bot"}
|~ "handler_error|backend_health_failed|ticket_create_failed|ticket_resolve_failed|support_model_load_failed|active_tickets_request_failed|resolve_menu_failed|handler_error_notify_failed"
| logfmt
| line_format "{{.event}}{{ if .error_type }} | type={{.error_type}}{{ end }}{{ if .ticket_id }} | ticket={{.ticket_id}}{{ end }}{{ if .normalized_action }} | action={{.normalized_action}}{{ end }}{{ if .category }} | category={{.category}}{{ end }}{{ if .resource }} | resource={{.resource}}{{ end }}{{ if .error }} | error={{.error}}{{ end }}{{ if .telegram_user_id }} | user={{.telegram_user_id}}{{ end }}"
```

---

## 11. Runtime verification commands

### App server

```bash
cd /opt/app
sudo docker compose ps
curl -s http://localhost:8080/v1/health | python3 -m json.tool
curl -s http://localhost:8080/metrics | grep supportdesk_tickets_total
curl -s http://localhost:8090/metrics | grep support_bot
```

### Web/API path

```bash
curl -s http://192.168.85.131/api/v1/health | python3 -m json.tool
curl -s http://192.168.85.131/api/v1/tickets | python3 -m json.tool | head -n 30
```

### Prometheus targets

```promql
up{job="supportdesk-api"}
up{job="support-bot"}
up{job="postgres"}
up{job="node"}
```

### Loki streams

```logql
{host="app", job="app", service="misis-digital-student-support-api"}
{host="app", job="support-bot", service="misis-digital-support-bot"}
{host="web", job="nginx", service="frontend"}
{host="db", job="postgresql", service="postgresql"}
```

## 12. Security/network hardening configs

### UFW policy summary

Applied on:

```text
web
app
log
monitor
db
```

Common baseline:

```text
Default: deny (incoming), allow (outgoing), disabled (routed)
Logging: on (low)
```

### `db` UFW allowlist

```text
22/tcp     ALLOW IN  192.168.85.129  # admin ssh
5432/tcp   ALLOW IN  192.168.85.133  # app to postgresql
5432/tcp   ALLOW IN  192.168.85.129  # admin postgresql maintenance
9100/tcp   ALLOW IN  192.168.85.137  # monitor node_exporter
9100/tcp   ALLOW IN  192.168.85.129  # admin node_exporter diagnostics
9187/tcp   ALLOW IN  192.168.85.137  # monitor postgres_exporter
9187/tcp   ALLOW IN  192.168.85.129  # admin postgres_exporter diagnostics
```

### `web` UFW allowlist

```text
22/tcp     ALLOW IN  192.168.85.129  # admin ssh
80/tcp     ALLOW IN  192.168.85.1    # windows browser frontend
80/tcp     ALLOW IN  192.168.85.129  # admin frontend diagnostics
9080/tcp   ALLOW IN  192.168.85.137  # monitor promtail metrics
9080/tcp   ALLOW IN  192.168.85.129  # admin promtail metrics diagnostics
9100/tcp   ALLOW IN  192.168.85.137  # monitor node_exporter
9100/tcp   ALLOW IN  192.168.85.129  # admin node_exporter diagnostics
```

### `log` UFW allowlist

```text
22/tcp     ALLOW IN  192.168.85.129  # admin ssh
3100/tcp   ALLOW IN  192.168.85.131  # web promtail to loki
3100/tcp   ALLOW IN  192.168.85.133  # app promtail to loki
3100/tcp   ALLOW IN  192.168.85.139  # db promtail to loki
3100/tcp   ALLOW IN  192.168.85.137  # monitor grafana loki datasource
3100/tcp   ALLOW IN  192.168.85.129  # admin loki diagnostics
9100/tcp   ALLOW IN  192.168.85.137  # monitor node_exporter
9100/tcp   ALLOW IN  192.168.85.129  # admin node_exporter diagnostics
```

`9095/tcp` Loki gRPC is intentionally not opened to external nodes.

### `monitor` UFW allowlist

```text
22/tcp     ALLOW IN  192.168.85.129  # admin ssh
3000/tcp   ALLOW IN  192.168.85.1    # windows grafana ui
3000/tcp   ALLOW IN  192.168.85.129  # admin grafana diagnostics
9090/tcp   ALLOW IN  192.168.85.1    # windows prometheus ui
9090/tcp   ALLOW IN  192.168.85.129  # admin prometheus diagnostics
9093/tcp   ALLOW IN  192.168.85.1    # windows alertmanager
9093/tcp   ALLOW IN  192.168.85.129  # admin alertmanager diagnostics
9100/tcp   ALLOW IN  192.168.85.129  # admin node_exporter diagnostics
```

Prometheus local scrape of monitor node_exporter uses localhost/loopback, so no self-rule for `192.168.85.137 -> 9100` is required.

### `app` UFW allowlist

```text
22/tcp     ALLOW IN  192.168.85.129  # admin ssh
8080/tcp   ALLOW IN  192.168.85.131  # web to supportdesk-api
8080/tcp   ALLOW IN  192.168.85.137  # monitor supportdesk-api metrics
8080/tcp   ALLOW IN  192.168.85.129  # admin supportdesk-api diagnostics
8090/tcp   ALLOW IN  192.168.85.137  # monitor support-bot metrics
8090/tcp   ALLOW IN  192.168.85.129  # admin support-bot metrics diagnostics
9100/tcp   ALLOW IN  192.168.85.137  # monitor node_exporter
9100/tcp   ALLOW IN  192.168.85.129  # admin node_exporter diagnostics
9080/tcp   ALLOW IN  192.168.85.129  # admin promtail metrics diagnostics
```

### `app: /usr/local/sbin/app-docker-user-firewall.sh`

```sh
#!/bin/sh
set -eu

IPTABLES="/usr/sbin/iptables"
CHAIN="DOCKER-USER"
EXT_IF="ens18"

WEB_IP="192.168.85.131"
MONITOR_IP="192.168.85.137"
ADMIN_IP="192.168.85.129"

$IPTABLES -N "$CHAIN" 2>/dev/null || true
$IPTABLES -F "$CHAIN"

$IPTABLES -A "$CHAIN" -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT

$IPTABLES -A "$CHAIN" -i "$EXT_IF" -s "$WEB_IP" -p tcp --dport 8080 -j ACCEPT
$IPTABLES -A "$CHAIN" -i "$EXT_IF" -s "$MONITOR_IP" -p tcp --dport 8080 -j ACCEPT
$IPTABLES -A "$CHAIN" -i "$EXT_IF" -s "$ADMIN_IP" -p tcp --dport 8080 -j ACCEPT

$IPTABLES -A "$CHAIN" -i "$EXT_IF" -s "$MONITOR_IP" -p tcp --dport 8090 -j ACCEPT
$IPTABLES -A "$CHAIN" -i "$EXT_IF" -s "$ADMIN_IP" -p tcp --dport 8090 -j ACCEPT

$IPTABLES -A "$CHAIN" -i "$EXT_IF" -p tcp --dport 8080 -j DROP
$IPTABLES -A "$CHAIN" -i "$EXT_IF" -p tcp --dport 8090 -j DROP

exit 0
```

### `app: /etc/systemd/system/app-docker-user-firewall.service`

```ini
[Unit]
Description=Apply DOCKER-USER firewall rules for MISIS Digital app
After=docker.service
Wants=docker.service

[Service]
Type=oneshot
ExecStart=/usr/local/sbin/app-docker-user-firewall.sh
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
```

Confirmed after reboot:

```text
systemctl is-enabled app-docker-user-firewall.service -> enabled
systemctl is-active app-docker-user-firewall.service  -> active
```



## 13. Ansible automation v2 source-of-truth

Этап Ansible automation v2 зафиксирован в Git:

```text
03ae409 Add Ansible automation v2 roles and audit playbooks
```

### `admin: ~/control-node/ansible.cfg`

```ini
[defaults]
roles_path = ./roles
inventory = inventory/hosts.ini
remote_user = pelmel
host_key_checking = False
interpreter_python = /usr/bin/python3
retry_files_enabled = False

[privilege_escalation]
become = False
```

### `admin: ~/control-node/inventory/group_vars/`

```text
all.yml             common project variables: IPs, ports, service names, URLs
web_nodes.yml       Nginx/frontend/reverse proxy and web Promtail variables
app_nodes.yml       Docker Compose project, supportdesk-api, support-bot, log paths
db_nodes.yml        PostgreSQL cluster, postgres_exporter, backup, db Promtail variables
log_nodes.yml       Loki variables
monitor_nodes.yml   Prometheus/Grafana/Alertmanager variables and expected Prometheus jobs
```

Important values:

```yaml
postgres_exporter_service_name: "prometheus-postgres-exporter.service"
backup_dir: "/var/backups/postgresql/supportdesk"
backup_latest_dump_path: "/var/backups/postgresql/supportdesk/latest.dump"
prometheus_expected_jobs:
  - prometheus
  - node
  - supportdesk-api
  - support-bot
  - promtail-web
  - postgres
```

### Roles

```text
common                  baseline packages/directories and become check
node_exporter           install/start/check node_exporter
app_compose_project     validate /opt/app, env files and app/bot log permissions
docker_compose_service  reusable deploy/rebuild/check for one compose service
nginx_frontend          deploy Nginx site config + index.html, nginx -t, reload, checks
promtail                deploy node-specific Promtail config and restart/check service
prometheus              deploy prometheus.yml and rules with promtool validation
postgres_exporter       install/start/check prometheus-postgres-exporter
postgres_backup         deploy backup script/systemd units/timer and provide manual run tasks
```

### Playbooks

```text
apply_baseline.yml              common + node_exporter for managed nodes
check.yml                       full health check for all nodes and public app path
check_app_compose_project.yml   validate app Docker Compose project
 deploy_app.yml                 deploy supportdesk-api via docker_compose_service
 deploy_bot.yml                 deploy support-bot via docker_compose_service
 deploy_nginx_frontend.yml      deploy/check web Nginx frontend and reverse proxy
 deploy_promtail.yml            deploy/check Promtail configs on web/app/db
 deploy_prometheus.yml          deploy/check Prometheus config/rules/targets
 deploy_postgres_exporter.yml   deploy/check postgres_exporter on db
 deploy_postgres_backup.yml     deploy/check backup script/service/timer on db
 run_db_backup.yml              manual backup run using postgres_backup tasks_from=run_backup
 network_audit.yml              audit-only network/firewall/Docker/connectivity reports
```

### Managed file ownership policy

```text
/opt/app code/config files              root:root 0644
/opt/app/.env, /opt/app/.env.bot        root:root 0600
/var/log/app, /var/log/bot              pelmel:adm 2750
/var/log/app/app.log                    pelmel:adm 0640
/var/log/bot/support-bot.log            pelmel:adm 0640
/etc/promtail/config.yml                root:promtail 0640
/usr/local/sbin/backup_supportdesk.sh   root:postgres 0750
/etc/systemd/system/backup-*.{service,timer} root:root 0644
```

### Network audit artifacts

```text
docs/network-audit/latest/admin-network-audit.txt
docs/network-audit/latest/web-network-audit.txt
docs/network-audit/latest/app-network-audit.txt
docs/network-audit/latest/db-network-audit.txt
docs/network-audit/latest/log-network-audit.txt
docs/network-audit/latest/monitor-network-audit.txt
docs/network-audit/latest/admin-critical-connectivity.txt
```

Timestamped directories `docs/network-audit/20*/` are ignored by Git. `latest/` is kept as the current audit snapshot.

Firewall changes are intentionally not applied by Ansible. The project uses Ansible for audit/reporting and critical flow validation; firewall rule changes remain manual-review based.
