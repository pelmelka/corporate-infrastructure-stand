# Текущее состояние сервера web

## Назначение

`web` — frontend / Nginx server.

Роль:

- отдавать frontend Mini Support Desk;
- принимать пользовательские HTTP-запросы;
- проксировать `/api/*` на `app:8080`;
- писать nginx access/error logs;
- отправлять nginx logs в Loki через Promtail;
- отдавать системные метрики через node_exporter.

## Основная информация

- Hostname: `web`
- OS: Debian GNU/Linux 13 (trixie)
- IP: `192.168.85.131/24`
- Interface: `ens18`
- User: `pelmel`
- SSH/sudo: работают
- Nginx: `active/enabled`
- Promtail: `active/enabled`
- node_exporter: `active/enabled`

## Nginx

Сервис:

```text
nginx.service
```

Проверки:

```bash
systemctl status nginx --no-pager
sudo nginx -t
ss -tulpn | grep :80
curl http://localhost/
```

Подтверждено:

- `nginx.service active (running)`;
- порт `80` слушается;
- `sudo nginx -t` успешен;
- frontend Mini Support Desk отдается с `web`.

## Frontend Mini Support Desk

Файл:

```text
/var/www/html/index.html
```

Backup перед изменением:

```text
/var/www/html/index.html.bak-before-supportdesk
```

Функциональность страницы:

- показывает backend status через `GET /api/health`;
- показывает список заявок через `GET /api/tickets`;
- создает заявку через `POST /api/tickets`;
- меняет статус заявки через `PATCH /api/tickets/<id>/status`;
- показывает Last API response;
- отображает backend UTC time и local browser time.

Полный текущий код `index.html` фиксируется в `06_config_files_current.md`, а не дублируется здесь.

## Nginx reverse proxy

Файл:

```text
/etc/nginx/sites-available/default
```

Backup перед изменением:

```text
/etc/nginx/sites-available/default.bak-before-supportdesk-proxy
```

Важный блок:

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

Смысл mapping:

```text
/api/health              -> app:/health
/api/tickets             -> app:/tickets
/api/tickets/<id>/status -> app:/tickets/<id>/status
/api/metrics             -> app:/metrics
```

Проверки:

```bash
curl -s http://localhost/api/health | python3 -m json.tool
curl -s http://localhost/api/tickets | python3 -m json.tool
curl -s http://192.168.85.131/api/health | python3 -m json.tool
```

Результат: `support-desk-api` отвечает через `web` reverse proxy.

## Nginx logs

Файлы:

```text
/var/log/nginx/access.log
/var/log/nginx/error.log
```

После Mini Support Desk flow подтверждены строки вида:

```text
GET /api/health HTTP/1.1 200
GET /api/tickets HTTP/1.1 200
POST /api/tickets HTTP/1.1 201
PATCH /api/tickets/6/status HTTP/1.1 200
```

Promtail читает `/var/log/nginx/*.log` и отправляет logs в Loki с labels:

```text
host=web
job=nginx
service=frontend
env=lab
```

## Proxy headers

Nginx передает в backend:

```text
Host
X-Real-IP
X-Forwarded-For
X-Forwarded-Proto
```

Сейчас `app` логирует TCP peer как `client_ip`, поэтому в app logs виден `client_ip=192.168.85.131`. Улучшение логирования `x_real_ip` и `x_forwarded_for` вынесено в future backlog.

## node_exporter

Сервис:

```text
prometheus-node-exporter.service
```

Подтверждено:

- active/enabled;
- порт `9100` слушается;
- Prometheus видит target `host="web"`.

## Текущий статус

`web` считается готовым frontend/reverse proxy node для Mini Support Desk:

- Nginx отдает frontend;
- `/api/*` проксируется на `app:8080`;
- Browser -> web -> app flow подтвержден;
- nginx logs уходят в Loki;
- системные метрики доступны Prometheus через node_exporter.
