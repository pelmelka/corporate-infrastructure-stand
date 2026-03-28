# Текущее состояние сервера web

## Назначение

`web` — frontend / Nginx server.

Роль:

- отдавать frontend `MISIS_Digital Student Support`;
- принимать пользовательские HTTP-запросы из браузера;
- проксировать `/api/*` на `app:8080`;
- писать nginx access/error logs;
- отправлять nginx logs в Loki через Promtail;
- экспортировать nginx-derived HTTP response metrics через Promtail `:9080/metrics`;
- отдавать системные метрики через node_exporter.

## Основная информация

- Hostname: `web`
- OS: Debian GNU/Linux 13 (trixie)
- IP: `192.168.85.131/24`
- Interface: `ens18`
- User: `pelmel`
- SSH/sudo: работают
- Nginx: `active/enabled`
- Promtail: `active/enabled`; после настройки nginx HTTP metrics pipeline снова `active (running)`
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
curl -s http://localhost/api/v1/health | python3 -m json.tool
```

Подтверждено:

- `nginx.service active (running)`;
- порт `80` слушается;
- `sudo nginx -t` успешен;
- frontend `MISIS_Digital Student Support` отдается с `web`;
- proxy `/api/v1/* -> app:/v1/*` работает.

## Frontend MISIS_Digital Student Support

Файл:

```text
/var/www/html/index.html
```

Backup-и:

```text
/var/www/html/index.html.bak-before-supportdesk
/var/www/html/index.html.bak-before-misis-digital-v2
```

Текущая функциональность страницы:

- показывает backend status через `GET /api/v1/health`;
- получает модель сервисов/разделов через `GET /api/v1/support-model`;
- показывает список active-заявок через `GET /api/v1/tickets`;
- показывает resolved-заявки через `GET /api/v1/tickets?status=resolved`;
- показывает все заявки через `GET /api/v1/tickets/all`;
- создает заявку через `POST /api/v1/tickets`;
- меняет статус через `PATCH /api/v1/tickets/<id>/status`;
- поддерживает flow `open -> in_progress -> resolved` и reopen из `resolved` обратно в `open`;
- показывает Last API response.

Продуктовая модель:

```text
category = цифровой сервис университета
resource = раздел/функция внутри выбранного сервиса
```

Текущие категории в UI:

```text
newlms.misis.ru
lk.misis.ru
gornyak.misis.ru
folio.misis.ru
pulse.misis.ru
vector.misis.ru
pay.misis.ru
```

В API/logs/metrics используются короткие slug-и без `.ru`:

```text
newlms-misis
lk-misis
gornyak-misis
folio-misis
pulse-misis
vector-misis
pay-misis
```

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
/api/health                    -> app:/health
/api/v1/health                 -> app:/v1/health
/api/v1/support-model          -> app:/v1/support-model
/api/v1/tickets                -> app:/v1/tickets
/api/v1/tickets?status=...     -> app:/v1/tickets?status=...
/api/v1/tickets/all            -> app:/v1/tickets/all
/api/v1/tickets/<id>/status    -> app:/v1/tickets/<id>/status
/api/metrics                   -> app:/metrics
```

## Nginx logs

Файлы:

```text
/var/log/nginx/access.log
/var/log/nginx/error.log
```

После Product model v2 flow подтверждены строки вида:

```text
GET /api/v1/health HTTP/1.1 200
GET /api/v1/support-model HTTP/1.1 200
GET /api/v1/tickets HTTP/1.1 200
GET /api/v1/tickets?status=resolved HTTP/1.1 200
POST /api/v1/tickets HTTP/1.1 201
PATCH /api/v1/tickets/<id>/status HTTP/1.1 200
```

Promtail читает `/var/log/nginx/*.log` и отправляет logs в Loki с labels:

```text
host=web
job=nginx
service=frontend
env=lab
```

Дополнительно Promtail на `web` теперь строит custom metric из nginx access log:

```text
promtail_custom_nginx_http_responses_total{status_code}
```

Реализация:

```text
nginx access.log -> Promtail regex pipeline -> status_code label -> metrics stage Counter -> web:9080/metrics
```

Эта метрика используется Prometheus job `promtail-web` и alert-ом `Nginx502Spike`. Проверено, что в Prometheus видны статусы nginx, например `status_code="200"`, `status_code="304"`, а при остановке backend-а появляется `status_code="502"`.

Backup перед изменением Promtail config:

```text
/etc/promtail/config.yml.bak-before-nginx-http-metrics
```

Во время настройки длинный regex был заменен на минимальный устойчивый вариант для извлечения HTTP status code, потому что первый вариант был слишком сильно заэкранирован и приводил к падению `promtail.service` с ошибкой regexp.

## Proxy headers

Nginx передает в backend:

```text
Host
X-Real-IP
X-Forwarded-For
X-Forwarded-Proto
```

`app` логирует:

```text
client_ip        = TCP peer для backend-а; обычно web/Nginx: 192.168.85.131
x_forwarded_for  = исходный клиент до Nginx; обычно Windows/Browser: 192.168.85.1
x_forwarded_proto = схема исходного запроса; сейчас http
```

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

`web` считается готовым frontend/reverse proxy node для `MISIS_Digital Student Support`:

- Nginx отдает новый frontend;
- `/api/*` проксируется на `app:8080`;
- Browser -> web -> app/v1 flow подтвержден;
- nginx logs уходят в Loki;
- nginx-derived HTTP response metric `promtail_custom_nginx_http_responses_total` доступна на `:9080/metrics` и собирается Prometheus через `promtail-web`;
- системные метрики доступны Prometheus через node_exporter.
