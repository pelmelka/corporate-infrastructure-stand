# Ansible automation v2 — текущее состояние этапа

## Статус

Этап **Ansible automation v2** технически завершен и зафиксирован в Git на `admin`.

```text
Git commit: 03ae409 Add Ansible automation v2 roles and audit playbooks
Branch: master
Repo path: /home/pelmel/control-node
Final check: ansible-playbook playbooks/check.yml -> failed=0, changed=0 on all nodes
```

Главный результат этапа: `admin` теперь является полноценным control node, а ключевые runtime/config слои проекта управляются Ansible roles/playbooks. Firewall-изменения намеренно **не автоматизированы**; вместо этого добавлен audit-only playbook для сетевого и firewall-состояния.

## Production-like принцип этапа

Ansible v2 не пытается «переизобрести» уже рабочую инфраструктуру. Подход был таким:

```text
1. Снять текущие рабочие файлы с серверов на admin.
2. Сделать admin/control-node source of truth.
3. Разложить роли с четкими зонами ответственности.
4. Проверять каждый слой после применения.
5. Не хранить секреты в Git.
6. Не автоматизировать рискованные firewall changes без rollback/out-of-band доступа.
```

## Структура control-node после этапа

Ключевые новые директории и файлы:

```text
~/control-node/
├── ansible.cfg
├── inventory/
│   ├── hosts.ini
│   └── group_vars/
│       ├── all.yml
│       ├── web_nodes.yml
│       ├── app_nodes.yml
│       ├── log_nodes.yml
│       ├── monitor_nodes.yml
│       └── db_nodes.yml
├── playbooks/
│   ├── apply_baseline.yml
│   ├── check.yml
│   ├── check_app_compose_project.yml
│   ├── deploy_app.yml
│   ├── deploy_bot.yml
│   ├── deploy_nginx_frontend.yml
│   ├── deploy_promtail.yml
│   ├── deploy_prometheus.yml
│   ├── deploy_postgres_exporter.yml
│   ├── deploy_postgres_backup.yml
│   ├── run_db_backup.yml
│   └── network_audit.yml
├── roles/
│   ├── common/
│   ├── node_exporter/
│   ├── app_compose_project/
│   ├── docker_compose_service/
│   ├── nginx_frontend/
│   ├── promtail/
│   ├── prometheus/
│   ├── postgres_exporter/
│   └── postgres_backup/
├── files/
│   ├── app/
│   ├── bot/
│   ├── app_compose/
│   ├── nginx/
│   ├── promtail/
│   ├── prometheus/
│   └── postgres_backup/
└── docs/
    └── network-audit/
        └── latest/
```

`ansible.cfg` теперь содержит `roles_path = ./roles`, чтобы playbooks из `playbooks/` могли находить роли в корневом `roles/`.

## Inventory и переменные

Inventory сохранен как `inventory/hosts.ini`:

```text
control: admin
managed: web, app, log, monitor, db
web_nodes: web
app_nodes: app
log_nodes: log
monitor_nodes: monitor
db_nodes: db
```

`inventory/group_vars/all.yml` содержит общие параметры проекта: IP-адреса, порты, service names, URLs и общую заметку `ansible_managed_note`.

Групповые переменные разделены по ролям узлов:

```text
web_nodes.yml      nginx paths, backend target, promtail config template, expected services
app_nodes.yml      docker compose paths, supportdesk-api/support-bot definitions, log paths
log_nodes.yml      loki service/config/ready URL
monitor_nodes.yml  prometheus/grafana/alertmanager config, expected jobs
 db_nodes.yml      postgres cluster, postgres_exporter, backup paths, promtail db config
```

Важная правка этапа: переменная `postgres_exporter_service_name` должна соответствовать реальному Debian unit:

```yaml
postgres_exporter_service_name: "prometheus-postgres-exporter.service"
```

Backup canonical path синхронизирован с текущим скриптом:

```yaml
backup_dir: "/var/backups/postgresql/supportdesk"
backup_latest_dump_path: "/var/backups/postgresql/supportdesk/latest.dump"
```

## Роли

### `common`

Базовая безопасная роль для managed nodes:

```text
- устанавливает общие operational packages;
- гарантирует базовые директории;
- проверяет, что become/sudo работает.
```

### `node_exporter`

Универсальная роль для managed nodes:

```text
- устанавливает prometheus-node-exporter;
- включает и запускает prometheus-node-exporter.service;
- проверяет service active;
- проверяет http://localhost:9100/metrics.
```

### `app_compose_project`

Готовит и валидирует Docker Compose runtime на `app`, но не деплоит конкретный сервис:

```text
- проверяет docker.service;
- проверяет docker compose version;
- гарантирует /opt/app;
- гарантирует /var/log/app и /var/log/bot;
- проверяет docker-compose.yml и .dockerignore;
- проверяет наличие .env и .env.bot без вывода секретов;
- выставляет права на env-файлы;
- показывает docker compose ps.
```

Политика прав:

```text
/opt/app                         root:root 0755
/opt/app/app.py                  root:root 0644
/opt/app/bot.py                  root:root 0644
/opt/app/Dockerfile*             root:root 0644
/opt/app/requirements*.txt       root:root 0644
/opt/app/docker-compose.yml      root:root 0644
/opt/app/.dockerignore           root:root 0644
/opt/app/.env                    root:root 0600
/opt/app/.env.bot                root:root 0600
/var/log/app                     pelmel:adm 2750
/var/log/bot                     pelmel:adm 2750
/var/log/app/app.log             pelmel:adm 0640
/var/log/bot/support-bot.log     pelmel:adm 0640
```

Смысл: code/config/secrets managed by root/Ansible, runtime logs доступны Promtail через группу `adm`.

### `docker_compose_service`

Переиспользуемая роль для деплоя одного Docker Compose service. Используется для `supportdesk-api` и `support-bot`.

```text
- проверяет compose_project_dir;
- проверяет env-файл без вывода секретов;
- копирует source files с admin в /opt/app;
- вызывает handler docker compose up -d --build <service> только при изменениях;
- проверяет docker compose ps --status running <service>;
- проверяет health и/или metrics endpoint.
```

Playbooks:

```text
deploy_app.yml -> supportdesk-api, files/app/*, .env, :8080/v1/health, :8080/metrics
deploy_bot.yml -> support-bot, files/bot/*, .env.bot, :8090/metrics
```

### `nginx_frontend`

Управляет frontend и reverse proxy на `web`:

```text
- устанавливает nginx;
- деплоит files/nginx/index.html -> /var/www/html/index.html;
- деплоит files/nginx/default.conf -> /etc/nginx/sites-available/default;
- выполняет nginx -t;
- reload nginx только при изменении config;
- проверяет http://localhost/;
- проверяет http://localhost/api/v1/health.
```

### `promtail`

Одна роль для node-specific Promtail configs на `web`, `app`, `db`:

```text
web -> files/promtail/web-promtail.yml
app -> files/promtail/app-promtail.yml
db  -> files/promtail/db-promtail.yml
```

Политика прав после роли:

```text
/etc/promtail/config.yml -> root:promtail 0640
```

Роль рестартит Promtail только при изменении конфига и проверяет service active + `:9080/metrics`.

### `prometheus`

Управляет Prometheus config и alert rules на `monitor`:

```text
- деплоит files/prometheus/prometheus.yml;
- деплоит files/prometheus/supportdesk.rules.yml;
- валидирует через promtool check config/rules;
- рестартит Prometheus только при изменениях;
- ждет /-/ready с retries;
- читает targets API как JSON;
- проверяет expected jobs.
```

Expected jobs подтверждены:

```text
prometheus
node
supportdesk-api
support-bot
promtail-web
postgres
```

### `postgres_exporter`

Управляет PostgreSQL exporter на `db`:

```text
- устанавливает prometheus-postgres-exporter;
- включает и запускает prometheus-postgres-exporter.service;
- проверяет service active;
- проверяет http://localhost:9187/metrics;
- проверяет наличие pg_up.
```

### `postgres_backup`

Управляет backup automation на `db`:

```text
- деплоит /usr/local/sbin/backup_supportdesk.sh;
- деплоит backup-supportdesk.service;
- деплоит backup-supportdesk.timer;
- daemon-reload при изменении unit-файлов;
- включает и запускает timer;
- показывает timer status;
- мягко показывает состояние latest.dump;
- отдельный tasks/run_backup.yml запускает backup вручную и строго проверяет dump/checksum.
```

Важная правка прав:

```text
/usr/local/sbin/backup_supportdesk.sh -> root:postgres 0750
```

Потому что `backup-supportdesk.service` запускается от `User=postgres`, и `postgres` должен иметь право выполнить скрипт.

`latest.dump` является symlink, поэтому `stat` используется с `follow: true`, чтобы проверять реальный dump-файл, а не размер symlink.

## Playbooks

### `apply_baseline.yml`

Применяет базовый слой ко всем managed nodes:

```text
common
node_exporter
```

### `check.yml`

Новый общий health-check playbook. Проверяет:

```text
web: nginx, promtail, node_exporter
app: docker.service, API health, API metrics, bot metrics, promtail, node_exporter
log: loki, node_exporter
monitor: prometheus, grafana, alertmanager, node_exporter, readiness/targets
 db: PostgreSQL cluster, node_exporter, postgres_exporter, promtail, backup timer
admin/control: public web endpoint и public API health через web
```

Финальное состояние после этапа:

```text
admin failed=0 changed=0
web failed=0 changed=0
app failed=0 changed=0
log failed=0 changed=0
monitor failed=0 changed=0
db failed=0 changed=0
```

### `network_audit.yml`

Audit-only playbook без отдельной роли. Ничего не меняет на managed nodes, но создает отчеты на `admin`:

```text
docs/network-audit/latest/admin-network-audit.txt
docs/network-audit/latest/web-network-audit.txt
docs/network-audit/latest/app-network-audit.txt
docs/network-audit/latest/db-network-audit.txt
docs/network-audit/latest/log-network-audit.txt
docs/network-audit/latest/monitor-network-audit.txt
docs/network-audit/latest/admin-critical-connectivity.txt
```

Также создается timestamped snapshot в `docs/network-audit/YYYYMMDD_HHMMSS/`, но такие исторические snapshot-директории добавлены в `.gitignore`:

```gitignore
docs/network-audit/20*/
```

Собирает:

```text
hostnamectl, kernel, IP addresses, routes, DNS;
ss -tulpn;
running services;
ufw status verbose/numbered;
iptables filter/nat/DOCKER-USER;
nft ruleset;
docker ps, docker network ls, docker compose ps;
local HTTP endpoint checks;
critical admin -> node HTTP/TCP connectivity checks.
```

Итоговый critical connectivity audit:

```text
web frontend       200
web api health     200
loki ready         200
prometheus ready   200
grafana            302
alertmanager ready 200
critical TCP flows open as expected
```

`grafana 302` нормален: это redirect на login page.

## Source files, перенесенные на admin

Серверные working files были сняты на `admin` и теперь находятся в `files/`:

```text
files/app/app.py
files/app/Dockerfile
files/app/requirements.txt
files/bot/bot.py
files/bot/Dockerfile.bot
files/bot/requirements-bot.txt
files/app_compose/docker-compose.yml
files/app_compose/.dockerignore
files/nginx/default.conf
files/nginx/index.html
files/promtail/web-promtail.yml
files/promtail/app-promtail.yml
files/promtail/db-promtail.yml
files/prometheus/prometheus.yml
files/prometheus/supportdesk.rules.yml
files/postgres_backup/backup_supportdesk.sh
files/postgres_backup/backup-supportdesk.service
files/postgres_backup/backup-supportdesk.timer
```

Секреты не переносились и не коммитились:

```text
/opt/app/.env
/opt/app/.env.bot
Telegram token
DB password
```

## Что намеренно не автоматизировано

Firewall rule changes не автоматизировались. Причина: firewall automation без out-of-band доступа/rollback может отрезать SSH, Prometheus, Loki или Docker published ports.

Текущая политика:

```text
Firewall/access changes remain manual-review based.
Ansible provides network/firewall audit snapshots and critical flow validation.
```

## Финальные проверки этапа

Успешно пройдены:

```bash
ansible-playbook playbooks/apply_baseline.yml
ansible-playbook playbooks/check_app_compose_project.yml
ansible-playbook playbooks/deploy_app.yml
ansible-playbook playbooks/deploy_bot.yml
ansible-playbook playbooks/deploy_nginx_frontend.yml
ansible-playbook playbooks/deploy_promtail.yml
ansible-playbook playbooks/deploy_prometheus.yml
ansible-playbook playbooks/deploy_postgres_exporter.yml
ansible-playbook playbooks/deploy_postgres_backup.yml
ansible-playbook playbooks/run_db_backup.yml
ansible-playbook playbooks/network_audit.yml
ansible-playbook playbooks/check.yml
```

Backup manual run подтвердил:

```text
latest.dump path: /var/backups/postgresql/supportdesk/latest.dump
latest.dump size: 10126 bytes
checksum files found: 6
```

Git commit этапа:

```text
03ae409 Add Ansible automation v2 roles and audit playbooks
```
