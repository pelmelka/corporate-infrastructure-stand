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

Смысл:

- `inventory` позволяет запускать `ansible`/`ansible-playbook` без `-i inventory/hosts.ini` из `~/control-node`;
- `remote_user = pelmel` задает SSH-пользователя по умолчанию;
- `interpreter_python = /usr/bin/python3` фиксирует Python на managed nodes;
- `become = False` оставляет root escalation выключенным по умолчанию; playbook'и, которым нужен root, явно задают `become: true`.

## Ansible playbook: ping_all.yml

Файл:

```text
admin: ~/control-node/playbooks/ping_all.yml
```

Текущий вариант:

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

Текущий вариант:

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

Текущий вариант:

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

## Ansible playbook: deploy_prometheus_rules.yml

Файл:

```text
admin: ~/control-node/playbooks/deploy_prometheus_rules.yml
```

Локальный source-файл rules:

```text
admin: ~/control-node/files/prometheus/supportdesk.rules.yml
```

Текущий вариант:

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
        status_code: 200

  handlers:
    - name: Restart prometheus
      ansible.builtin.systemd_service:
        name: prometheus.service
        state: restarted
```

Особенности:

- `src` у `copy` — локальный файл на `admin`;
- `dest` — файл на `monitor`;
- `validate: "promtool check rules %s"` проверяет новый rules-файл до замены рабочего файла;
- `backup: true` создает backup старого файла на `monitor`, если файл реально изменился;
- `notify` вызывает handler только при `changed`;
- `meta: flush_handlers` запускает handler до readiness-check, чтобы проверять Prometheus уже после возможного restart.

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
          service: support-desk-api
          env: lab
          __path__: /var/log/app/*.log
```

Примечание: после logging polish Promtail label для app приведен к актуальному значению `service=support-desk-api`. Старые строки в Loki могут оставаться с label `service=python-backend`, новые идут с новым label.

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
```

App `/metrics` scrape добавлен и проверен: target `supportdesk-api` показывает `1/1 up`.

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
          service: support-desk-api
        annotations:
          summary: "SupportDesk API is down"
          description: "Prometheus cannot scrape supportdesk-api on {{ $labels.instance }} for more than 30 seconds."

      - alert: TooManyOpenTickets
        expr: supportdesk_tickets_open{job="supportdesk-api"} >= 3
        for: 30s
        labels:
          severity: warning
          service: support-desk-api
        annotations:
          summary: "Too many open support tickets"
          description: "There are {{ $value }} open support tickets in Mini Support Desk."

      - alert: HighDiskUsage
        expr: 100 * (1 - (node_filesystem_avail_bytes{job="node", mountpoint="/", fstype="ext4"} / node_filesystem_size_bytes{job="node", mountpoint="/", fstype="ext4"})) > 80
        for: 2m
        labels:
          severity: warning
          service: node
        annotations:
          summary: "High disk usage on {{ $labels.host }}"
          description: "Root filesystem on {{ $labels.host }} is {{ printf \"%.1f\" $value }}% full."

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

Проверено:

- `SupportDeskApiDown` срабатывает при остановке `app.service`;
- `TooManyOpenTickets` срабатывает при `supportdesk_tickets_open >= 3`;
- `HighDiskUsage` проверен временным порогом `>20`, затем возвращен на `>80`;
- `NodeTargetDown` срабатывает при остановке node_exporter на target node.

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
SupportDesk Tickets
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
```

Active Alerts panel:

```promql
sum(ALERTS{alertstate="firing"}) or vector(0)
```

App logs panel query:

```logql
{host="app", job="app", service="support-desk-api"}
| logfmt
| line_format "{{.event}} | {{.method}} {{.path}} | status={{.status}} | ticket={{.ticket_id}} | {{.old_status}} -> {{.new_status}} | client={{.x_forwarded_for}} | proxy={{.client_ip}}"
```

Примечание: после подключения Prometheus scrape в App logs появляются `metrics_requested | GET /metrics`; это ожидаемый шум от мониторинга и пока оставлено без изменений.

## Nginx reverse proxy для Mini Support Desk

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

Mapping:

```text
/api/health              -> /health
/api/tickets             -> /tickets
/api/tickets/<id>/status -> /tickets/<id>/status
/api/metrics             -> /metrics
```

## Mini Support Desk frontend

Файл:

```text
web: /var/www/html/index.html
```

Backup:

```text
web: /var/www/html/index.html.bak-before-supportdesk
```

Функциональность:

- `GET /api/health`;
- `GET /api/tickets`;
- `POST /api/tickets`;
- `PATCH /api/tickets/<id>/status`;
- Last API response;
- backend UTC time + browser local time.

### Полный текущий код `/var/www/html/index.html`

```html
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>Mini Support Desk</title>
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
            max-width: 1100px;
            margin: 28px auto;
            padding: 0 20px;
        }

        .grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
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
            min-height: 90px;
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

        .meta {
            margin-top: 8px;
            font-size: 14px;
            color: #64748b;
        }

        .status {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 999px;
            font-size: 13px;
            font-weight: bold;
            background: #e0f2fe;
            color: #0369a1;
        }

        .priority {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 999px;
            font-size: 13px;
            font-weight: bold;
            background: #fee2e2;
            color: #991b1b;
            margin-left: 6px;
        }

        .health-ok {
            color: #15803d;
            font-weight: bold;
        }

        .health-bad {
            color: #b91c1c;
            font-weight: bold;
        }

        .full-width {
            margin-top: 24px;
        }

        pre {
            background: #0f172a;
            color: #e2e8f0;
            border-radius: 10px;
            padding: 14px;
            overflow-x: auto;
        }

        @media (max-width: 800px) {
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
    <h1>Mini Support Desk</h1>
    <p>Demo product for Mini Corporate Infrastructure Lab: Browser → web/Nginx → app/API</p>
</header>

<main>
    <div class="grid">
        <section class="card">
            <h2>Backend status</h2>
            <p id="health">Checking backend...</p>
            <button onclick="loadHealth()">Refresh health</button>
            <button class="secondary" onclick="loadTickets()">Refresh tickets</button>
        </section>

        <section class="card">
            <h2>Create ticket</h2>

            <label for="title">Title</label>
            <input id="title" placeholder="Example: Cannot access Grafana">

            <label for="description">Description</label>
            <textarea id="description" placeholder="Describe the issue"></textarea>

            <label for="priority">Priority</label>
            <select id="priority">
                <option value="low">low</option>
                <option value="normal" selected>normal</option>
                <option value="high">high</option>
                <option value="critical">critical</option>
            </select>

            <button onclick="createTicket()">Create ticket</button>
        </section>
    </div>

    <section class="card full-width">
        <h2>Tickets</h2>
        <div id="tickets">Loading tickets...</div>
    </section>

    <section class="card full-width">
        <h2>Last API response</h2>
        <pre id="api-response">No API response yet.</pre>
    </section>
</main>

<script>
    async function loadHealth() {
        const healthEl = document.getElementById("health");
        try {
            const response = await fetch("/api/health");
            const data = await response.json();
            const backendTime = new Date(data.time);

            healthEl.innerHTML = `
                <span class="health-ok">OK</span><br>
                Service: ${data.service}<br>
                Version: ${data.version}<br>
                Environment: ${data.environment}<br>
                Backend time UTC: ${data.time}<br>
                Your local time: ${backendTime.toLocaleString()}
            `;

            showResponse(data);
        } catch (error) {
            healthEl.innerHTML = `<span class="health-bad">Backend unavailable</span>`;
            showResponse({ error: String(error) });
        }
    }

    async function loadTickets() {
        const ticketsEl = document.getElementById("tickets");

        try {
            const response = await fetch("/api/tickets");
            const data = await response.json();

            if (!data.tickets || data.tickets.length === 0) {
                ticketsEl.innerHTML = "No tickets yet.";
                return;
            }

            ticketsEl.innerHTML = data.tickets.map(ticket => `
                <div class="ticket">
                    <div class="ticket-title">#${ticket.id} ${escapeHtml(ticket.title)}</div>
                    <div>${escapeHtml(ticket.description || "")}</div>
                    <div class="meta">
                        <span class="status">${ticket.status}</span>
                        <span class="priority">${ticket.priority}</span>
                        source=${ticket.source}
                    </div>
                    <button onclick="changeStatus(${ticket.id}, 'open')">Open</button>
                    <button onclick="changeStatus(${ticket.id}, 'in_progress')">In progress</button>
                    <button onclick="changeStatus(${ticket.id}, 'resolved')">Resolved</button>
                </div>
            `).join("");

            showResponse(data);
        } catch (error) {
            ticketsEl.innerHTML = "Failed to load tickets.";
            showResponse({ error: String(error) });
        }
    }

    async function createTicket() {
        const title = document.getElementById("title").value.trim();
        const description = document.getElementById("description").value.trim();
        const priority = document.getElementById("priority").value;

        if (!title) {
            alert("Title is required");
            return;
        }

        const payload = {
            title: title,
            description: description,
            priority: priority,
            source: "web"
        };

        const response = await fetch("/api/tickets", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(payload)
        });

        const data = await response.json();
        showResponse(data);

        document.getElementById("title").value = "";
        document.getElementById("description").value = "";

        await loadTickets();
    }

    async function changeStatus(ticketId, status) {
        const response = await fetch(`/api/tickets/${ticketId}/status`, {
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
        await loadTickets();
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

    loadHealth();
    loadTickets();
</script>
</body>
</html>
```

## Mini Support Desk backend

Файл:

```text
app: /opt/app/app.py
```

Backup:

```text
app: /opt/app/app.py.bak-before-supportdesk
/opt/app/app.py.bak-before-logging-polish
```

Данные:

```text
app: /opt/app/tickets.json
```

Endpoints:

```text
GET    /health
GET    /tickets
POST   /tickets
GET    /tickets/<id>
PATCH  /tickets/<id>/status
GET    /metrics
```

Product metrics:

```text
supportdesk_tickets_total
supportdesk_tickets_open
supportdesk_tickets_in_progress
supportdesk_tickets_resolved
```

### Полный текущий код `/opt/app/app.py`

```python
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse
from datetime import datetime, timezone
import json
import logging
import os
import re
import time

HOST = "0.0.0.0"
PORT = 8080

SERVICE_NAME = "support-desk-api"
SERVICE_VERSION = "1.0.0"
ENVIRONMENT = "lab"

LOG_FILE = "/var/log/app/app.log"
DATA_FILE = "/opt/app/tickets.json"


logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s service=support-desk-api %(message)s",
)


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def load_tickets():
    if not os.path.exists(DATA_FILE):
        return [
            {
                "id": 1,
                "title": "VPN access issue",
                "description": "User cannot access internal resources through VPN.",
                "priority": "high",
                "status": "open",
                "source": "seed",
                "created_at": now_iso(),
                "updated_at": now_iso(),
            },
            {
                "id": 2,
                "title": "Grafana access request",
                "description": "New team member needs access to monitoring dashboards.",
                "priority": "normal",
                "status": "in_progress",
                "source": "seed",
                "created_at": now_iso(),
                "updated_at": now_iso(),
            },
            {
                "id": 3,
                "title": "Backend health check",
                "description": "Regular health check ticket for app service.",
                "priority": "low",
                "status": "resolved",
                "source": "seed",
                "created_at": now_iso(),
                "updated_at": now_iso(),
            },
        ]

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_tickets(tickets):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(tickets, f, ensure_ascii=False, indent=2)


def next_ticket_id(tickets):
    if not tickets:
        return 1
    return max(ticket["id"] for ticket in tickets) + 1


def count_by_status(tickets, status):
    return sum(1 for ticket in tickets if ticket["status"] == status)


class SupportDeskHandler(BaseHTTPRequestHandler):
    def send_json(self, status_code, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")

        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_json_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}

        raw_body = self.rfile.read(length)
        return json.loads(raw_body.decode("utf-8"))

    def clean_log_value(self, value):
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

    def log_event(self, level, event, status_code, **fields):
        client_ip = self.client_address[0]
        x_forwarded_for = self.headers.get("X-Forwarded-For", "-")
        x_forwarded_proto = self.headers.get("X-Forwarded-Proto", "-")

        parts = [
            f"event={event}",
            f"method={self.command}",
            f"path={self.path}",
            f"status={status_code}",
            f"client_ip={self.clean_log_value(client_ip)}",
            f"x_forwarded_for={self.clean_log_value(x_forwarded_for)}",
            f"x_forwarded_proto={self.clean_log_value(x_forwarded_proto)}",
        ]

        for key, value in fields.items():
            parts.append(f"{key}={self.clean_log_value(value)}")

        logging.log(level, " ".join(parts))

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        try:
            if path == "/health":
                payload = {
                    "status": "ok",
                    "service": SERVICE_NAME,
                    "version": SERVICE_VERSION,
                    "environment": ENVIRONMENT,
                    "time": now_iso(),
                }
                self.send_json(200, payload)
                self.log_event(logging.INFO, "health_check", 200)

            elif path == "/tickets":
                tickets = load_tickets()
                payload = {
                    "tickets": tickets,
                    "count": len(tickets),
                }
                self.send_json(200, payload)
                self.log_event(
                    logging.INFO,
                    "ticket_list_requested",
                    200,
                    count=len(tickets),
                )

            elif re.fullmatch(r"/tickets/\d+", path):
                ticket_id = int(path.split("/")[-1])
                tickets = load_tickets()
                ticket = next((item for item in tickets if item["id"] == ticket_id), None)

                if ticket is None:
                    self.send_json(404, {"error": "ticket_not_found"})
                    self.log_event(
                        logging.WARNING,
                        "ticket_not_found",
                        404,
                        ticket_id=ticket_id,
                    )
                else:
                    self.send_json(200, ticket)
                    self.log_event(
                        logging.INFO,
                        "ticket_detail_requested",
                        200,
                        ticket_id=ticket_id,
                    )

            elif path == "/metrics":
                tickets = load_tickets()
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
                    "",
                ]
                body = "\n".join(lines).encode("utf-8")

                self.send_response(200)
                self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

                self.log_event(logging.INFO, "metrics_requested", 200)

            else:
                self.send_json(404, {"error": "not_found"})
                self.log_event(logging.WARNING, "endpoint_not_found", 404)

        except Exception as exc:
            self.send_json(500, {"error": "internal_server_error"})
            self.log_event(logging.ERROR, "internal_error", 500, error=type(exc).__name__)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        try:
            if path == "/tickets":
                data = self.read_json_body()

                title = str(data.get("title", "")).strip()
                description = str(data.get("description", "")).strip()
                priority = str(data.get("priority", "normal")).strip().lower()
                source = str(data.get("source", "web")).strip().lower()

                if not title:
                    self.send_json(400, {"error": "missing_title"})
                    self.log_event(
                        logging.WARNING,
                        "ticket_validation_failed",
                        400,
                        reason="missing_title",
                        source=source,
                    )
                    return

                if priority not in ["low", "normal", "high", "critical"]:
                    priority = "normal"

                tickets = load_tickets()
                ticket = {
                    "id": next_ticket_id(tickets),
                    "title": title,
                    "description": description,
                    "priority": priority,
                    "status": "open",
                    "source": source,
                    "created_at": now_iso(),
                    "updated_at": now_iso(),
                }

                tickets.append(ticket)
                save_tickets(tickets)

                self.send_json(201, ticket)
                self.log_event(
                    logging.INFO,
                    "ticket_created",
                    201,
                    ticket_id=ticket["id"],
                    priority=priority,
                    source=source,
                )

            else:
                self.send_json(404, {"error": "not_found"})
                self.log_event(logging.WARNING, "endpoint_not_found", 404)

        except json.JSONDecodeError:
            self.send_json(400, {"error": "invalid_json"})
            self.log_event(logging.WARNING, "ticket_validation_failed", 400, reason="invalid_json")

        except Exception as exc:
            self.send_json(500, {"error": "internal_server_error"})
            self.log_event(logging.ERROR, "internal_error", 500, error=type(exc).__name__)

    def do_PATCH(self):
        parsed = urlparse(self.path)
        path = parsed.path

        try:
            match = re.fullmatch(r"/tickets/(\d+)/status", path)

            if not match:
                self.send_json(404, {"error": "not_found"})
                self.log_event(logging.WARNING, "endpoint_not_found", 404)
                return

            ticket_id = int(match.group(1))
            data = self.read_json_body()

            new_status = str(data.get("status", "")).strip().lower()
            source = str(data.get("source", "web")).strip().lower()

            if new_status not in ["open", "in_progress", "resolved"]:
                self.send_json(400, {"error": "invalid_status"})
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
            ticket = next((item for item in tickets if item["id"] == ticket_id), None)

            if ticket is None:
                self.send_json(404, {"error": "ticket_not_found"})
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
                    ticket_id=ticket_id,
                    old_status=old_status,
                    new_status=new_status,
                    source=source,
                )
                return

            ticket["status"] = new_status
            ticket["updated_at"] = now_iso()
            save_tickets(tickets)

            self.send_json(200, ticket)
            self.log_event(
                logging.INFO,
                "ticket_status_changed",
                200,
                ticket_id=ticket_id,
                old_status=old_status,
                new_status=new_status,
                source=source,
            )

        except json.JSONDecodeError:
            self.send_json(400, {"error": "invalid_json"})
            self.log_event(logging.WARNING, "ticket_validation_failed", 400, reason="invalid_json")

        except Exception as exc:
            self.send_json(500, {"error": "internal_server_error"})
            self.log_event(logging.ERROR, "internal_error", 500, error=type(exc).__name__)

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
