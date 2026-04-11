# Текущее состояние сервера admin

## Назначение

`admin` — управляющий сервер проекта, полноценный Ansible control node.

Роль:

- SSH-подключения к остальным серверам;
- хранение SSH-ключей;
- запуск Ansible ad-hoc команд и playbook'ов;
- хранение inventory, playbook'ов, файлов, будущих roles/templates/docs;
- хранение Git-репозитория с Ansible control-node структурой.

## Основная информация

- Hostname: `admin`
- OS: Debian GNU/Linux 13 (trixie)
- Kernel: Linux 6.12.74+deb13+1-amd64
- Virtualization: KVM
- Hardware vendor/model: QEMU / Standard PC i440FX + PIIX
- IP: `192.168.85.129/24`
- Interface: `ens18`
- Default gateway: `192.168.85.2`
- User: `pelmel`
- sudo: работает
- SSH: работает

## Сеть

```text
interface: ens18
inet: 192.168.85.129/24
default via 192.168.85.2 dev ens18
```

DNS и интернет проверены: `ping deb.debian.org` проходит.

## SSH

- service: `ssh.service`
- state: `active (running)`
- autostart: `enabled`
- port: `22`

С Windows выполнялось успешное подключение:

```powershell
ssh pelmel@192.168.85.129
```

## sudo

`pelmel` добавлен в группу `sudo`.

```bash
sudo whoami
```

Результат: `root`.

Важно: SSH key-based login с `admin` на managed nodes работает без пароля, но `sudo`/Ansible `become: true` по-прежнему требует sudo-пароль, если playbook не использует `vars_prompt` или запуск без `-K` не настроен через `NOPASSWD`.

## SSH-ключи

Создан ключ:

```bash
ssh-keygen -t ed25519 -C "homelab-admin"
```

Файлы на `admin`:

```text
/home/pelmel/.ssh/id_ed25519
/home/pelmel/.ssh/id_ed25519.pub
```

Публичный ключ раскатан на managed nodes:

```text
web     192.168.85.131
app     192.168.85.133
log     192.168.85.135
monitor 192.168.85.137
db      192.168.85.139
```

Проверка SSH с `admin`:

```bash
ssh pelmel@192.168.85.131 "hostname"  # web
ssh pelmel@192.168.85.133 "hostname"  # app
ssh pelmel@192.168.85.135 "hostname"  # log
ssh pelmel@192.168.85.137 "hostname"  # monitor
```

Результат: все hostnames совпали, вход по SSH-ключу работает.

## Ansible

Ansible установлен.

```text
ansible [core 2.19.4]
python version = 3.13.5
```

Ansible использует проектный конфиг:

```text
config file = /home/pelmel/control-node/ansible.cfg
```

Главные файлы:

```text
~/control-node/ansible.cfg
~/control-node/inventory/hosts.ini
~/control-node/playbooks/ping_all.yml
~/control-node/playbooks/check_services.yml
~/control-node/playbooks/restart_app.yml
~/control-node/playbooks/deploy_prometheus_rules.yml
```

Текущий inventory:

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

Группы `web_nodes`, `app_nodes`, `log_nodes`, `monitor_nodes` используются вместо одноименных `[web]`, `[app]`, `[log]`, `[monitor]`, чтобы не было предупреждений Ansible `Found both group and host with same name`.

Текущий `ansible.cfg`:

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

Проверки:

```bash
cd ~/control-node
ansible-inventory --graph
ansible all -m ping
ansible managed -m ping
ansible-playbook playbooks/ping_all.yml
ansible-playbook playbooks/check_services.yml
ansible-playbook playbooks/restart_app.yml
ansible-playbook playbooks/deploy_prometheus_rules.yml
```

Подтверждено:

- `ansible all -m ping` возвращает `SUCCESS` для `admin`, `web`, `app`, `log`, `monitor`, `db`;
- `ansible managed -m ping` возвращает `SUCCESS` для `web`, `app`, `log`, `monitor`, `db`;
- `ping_all.yml` проходит по всем узлам;
- `check_services.yml` проверяет ключевые сервисы без изменений (`changed=0`): web/log/monitor systemd services, Dockerized app через `docker.service` + HTTP endpoints, db через `pg_lsclusters`, exporters, Promtail и backup timer;
- `restart_app.yml` остается legacy playbook для старого `app.service`; основной runtime после Dockerization проверяется через `check_services.yml` по Docker/API endpoints;
- `deploy_prometheus_rules.yml` деплоит `/etc/prometheus/supportdesk.rules.yml` на `monitor` с `promtool` validation, проверяет `prometheus.yml`, запускает handlers при изменении rules и проверяет `/-/ready` с retries/delay, чтобы не падать на кратковременный `503` сразу после restart Prometheus.

## Operational playbook'и

Текущие playbook'и:

```text
ping_all.yml                  проверка Ansible-связности всех узлов
check_services.yml            проверка ключевых сервисов web/app/log/monitor
restart_app.yml               legacy controlled restart app.service + healthcheck
deploy_prometheus_rules.yml   деплой Prometheus alert rules + promtool validation + readiness check with retries
```

`restart_app.yml` и `deploy_prometheus_rules.yml` используют `become: true` и `vars_prompt` для ввода `ansible_become_password`, чтобы не хранить sudo-пароль в файлах проекта.

После этапов HTTP/API observability и DB observability локальный source-файл Prometheus rules содержит app/product/HTTP/infrastructure/DB alert rules.

Дополнительно на этапе 17 обновлен `check_services.yml`:

```text
app: docker.service + http://localhost:8080/v1/health + http://localhost:8080/metrics + promtail + node_exporter
db: pg_lsclusters --no-header + node_exporter + postgres_exporter + promtail + backup-supportdesk.timer
```

`ansible-playbook playbooks/check_services.yml` проходит без ошибок:

```text
app ok=5 failed=0
db ok=5 failed=0
log ok=2 failed=0
monitor ok=4 failed=0
web ok=3 failed=0
```


## Структура проекта

Создана структура:

```text
~/control-node/
├── ansible.cfg
├── inventory/
│   └── hosts.ini
├── playbooks/
│   ├── ping_all.yml
│   ├── check_services.yml
│   ├── restart_app.yml
│   └── deploy_prometheus_rules.yml
├── files/
│   └── prometheus/
│       └── supportdesk.rules.yml
├── roles/
│   └── .gitkeep
├── templates/
│   └── .gitkeep
└── docs/
    └── .gitkeep
```

`roles/`, `templates/`, `docs/` пока пустые и сохранены в Git через `.gitkeep`, потому что Git не отслеживает пустые директории.

## Git

Git установлен:

```text
git version 2.47.3
```

В `~/control-node` инициализирован Git repository.

Локальные настройки repo:

```text
user.name=Pelmel
user.email=pelmel@homelab.local
```

Текущая ветка оставлена стандартной:

```text
master
```

Сделаны commit'ы:

```text
23771ba Add DB observability checks and PostgreSQL alerts
adaa6bd Clean up SupportDesk alert rules
782db47 Improve Prometheus rules deploy readiness check
cb5794d Add Ansible project directory placeholders
b98b8f9 initial Ansible control node setup
```

Коммит `782db47` также зафиксировал Product observability v2 Prometheus rules и улучшенный readiness check. Коммит `adaa6bd` удалил старый общий `TooManyOpenTickets` и обновил alert text/service labels под `MISIS_Digital Student Support`. Коммит `23771ba` добавил `db` в inventory, DB alert rules и обновленные service checks под Dockerized app и DB observability.

`git status` после commit'ов показывает:

```text
nothing to commit, working tree clean
```

## Статус

`admin` считается **готовым Ansible control node foundation**.

Завершено:

- SSH key-based доступ с `admin` на `web`, `app`, `log`, `monitor`, `db`;
- полный inventory с `db_nodes`;
- `ansible.cfg`;
- базовая структура `~/control-node`;
- первые operational playbook'и;
- Git repo с первыми commit'ами.

Последний завершенный этап проекта: `Telegram support bot + bot observability` — support-bot реализован вручную на `app` как Docker Compose service, подключен к Loki/Prometheus/Grafana/alerts.

Важно для admin/Ansible: deployment support-bot пока не автоматизирован отдельной role/playbook. Это задача будущего Ansible automation v2.

## Security/network hardening operational notes

During Stage 19 `admin` was used as the control node for firewall rollout.

New local documentation artifacts created on `admin`:

```text
~/control-node/docs/security-hardening/01_before_listening_ports.txt
~/control-node/docs/security-hardening/02_before_firewall_rules.txt
```

Operational approach:

```text
one node at a time;
start with db, then web, log, monitor, app;
never enable default-deny firewall before adding SSH allow rule from admin;
verify allowed and denied flows after each node;
app handled last because Docker-published ports require DOCKER-USER rules.
```

Admin management access preserved:

```text
admin -> web/app/log/monitor/db:22 works after hardening;
ansible-playbook playbooks/check_services.yml passes after hardening.
```

