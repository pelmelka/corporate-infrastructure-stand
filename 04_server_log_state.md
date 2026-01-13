# Текущее состояние сервера log

## Назначение

`log` — сервер централизованного логирования.

Роль: запускать Loki, принимать логи от Promtail с `web` и `app`, хранить логи, отдавать логи Grafana на `monitor`.

## Основная информация

- Hostname: `log`
- OS: Debian GNU/Linux 13 (trixie)
- Kernel: Linux 6.12.74+deb13+1-amd64
- Virtualization: KVM
- IP: `192.168.85.135/24`
- Interface: `ens18`
- Default gateway: `192.168.85.2`
- User: `pelmel`
- sudo: работает
- SSH: работает
- Loki: установлен, проверен вручную, systemd-service еще нужно завершить

## Сеть

```text
interface: ens18
inet: 192.168.85.135/24
default via 192.168.85.2 dev ens18
```

DNS и интернет работают, `ping deb.debian.org` проходит.

## SSH и sudo

SSH работает и включен. `sudo whoami` возвращает `root`.

## Loki: пользователь и директории

Создан системный пользователь:

```bash
sudo useradd --system --no-create-home --shell /usr/sbin/nologin loki
```

Директории:

```text
/opt/loki
/etc/loki
/var/lib/loki
```

Права: `loki:loki`.

Назначение:

- `/opt/loki` — бинарник;
- `/etc/loki` — конфиг;
- `/var/lib/loki` — данные.

## Loki: версия

```bash
/opt/loki/loki --version
```

Вывод:

```text
loki, version 3.5.0
branch: k248
revision: 4b16bc4f
go version: go1.24.1
platform: linux/amd64
```

## Loki config

Файл:

```text
/etc/loki/config.yml
```

Содержимое:

```yaml
auth_enabled: false

server:
  http_listen_port: 3100

common:
  path_prefix: /var/lib/loki
  storage:
    filesystem:
      chunks_directory: /var/lib/loki/chunks
      rules_directory: /var/lib/loki/rules
  replication_factor: 1
  ring:
    kvstore:
      store: inmemory

schema_config:
  configs:
    - from: 2024-01-01
      store: tsdb
      object_store: filesystem
      schema: v13
      index:
        prefix: index_
        period: 24h

limits_config:
  allow_structured_metadata: true
  volume_enabled: true

ruler:
  alertmanager_url: http://localhost:9093
```

Права:

```bash
sudo chown loki:loki /etc/loki/config.yml
```

## Ручной запуск Loki

Команда:

```bash
sudo -u loki /opt/loki/loki -config.file=/etc/loki/config.yml
```

Loki успешно стартовал и слушал:

```text
http=[::]:3100
grpc=[::]:9095
```

Проверка:

```bash
curl http://localhost:3100/ready
```

Результат:

```text
ready
```

## 404 на корне

`http://192.168.85.135:3100` возвращал `404 page not found`. Это нормально: Loki — API-сервис, а не веб-сайт. Проверять нужно `/ready`, `/metrics` и API endpoints.

## Ingester not ready

С Windows один раз был ответ:

```text
Ingester not ready: waiting for 15s after being ready
```

Это нормально сразу после старта Loki.

## Остановка ручного процесса

При повторном запуске возникло:

```text
listen tcp :3100: bind: address already in use
```

Причина: ручной Loki уже занимал порт 3100. Через `ps -ef | grep loki` был найден процесс. Он был остановлен через `kill -9`. После этого `ss -tulpn | grep :3100` не показывал слушателей.

## Следующий шаг

Создать systemd unit:

```text
/etc/systemd/system/loki.service
```

Планируемое содержимое:

```ini
[Unit]
Description=Loki Log Aggregation System
After=network.target

[Service]
User=loki
Group=loki
ExecStart=/opt/loki/loki -config.file=/etc/loki/config.yml
WorkingDirectory=/opt/loki
Restart=always

[Install]
WantedBy=multi-user.target
```

Затем:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now loki.service
systemctl status loki.service --no-pager
ss -tulpn | grep :3100
curl http://localhost:3100/ready
```

## Статус

`log`: **база готова, Loki установлен и проверен вручную, осталось оформить Loki как systemd service**.
