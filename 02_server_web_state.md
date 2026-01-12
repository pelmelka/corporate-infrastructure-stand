# Текущее состояние сервера web

## Назначение

`web` — frontend / Nginx server.

Роль: отдавать веб-страницу, позже проксировать запросы к `app`, писать access/error логи, отправлять логи в Loki через Promtail, отдавать системные метрики через node_exporter.

## Основная информация

- Hostname: `web`
- OS: Debian GNU/Linux 13 (trixie)
- Kernel: Linux 6.12.74+deb13+1-amd64
- Virtualization: KVM
- IP: `192.168.85.131/24`
- Interface: `ens18`
- User: `pelmel`
- sudo: работает
- SSH: работает
- Nginx: работает

## SSH и sudo

`ssh.service` работает, включен в автозапуск, порт 22 слушается. `sudo whoami` возвращает `root`.

## Nginx

Nginx установлен и запущен.

Проверки:

```bash
systemctl status nginx
ss -tulpn | grep :80
curl http://localhost
```

Состояние:

- `nginx.service`: `active (running)`
- порт `80`: слушается
- `curl http://localhost`: возвращает пользовательский HTML

## Конфигурация Nginx

Файл:

```text
/etc/nginx/sites-available/default
```

Важные строки:

```nginx
root /var/www/html;
index index.html index.htm index.nginx-debian.html;
server_name _;
```

Nginx берет сайт из `/var/www/html` и первым ищет `index.html`.

## HTML-страница

Файл:

```text
/var/www/html/index.html
```

Текущее содержимое:

```html
<!doctype html>
<html>
<head>
    <meta charset="utf-8">
    <title>Web node</title>
</head>
<body>
    <h1>web server is working</h1>
    <p>Mini Corporate Infrastructure Lab</p>
</body>
</html>
```

Файл `/var/www/html/index.nginx-debian.html` остался, но не мешает, потому что `index.html` имеет приоритет.

## Проверка с admin

```bash
curl http://192.168.85.131
```

Результат: пользовательская страница `web server is working`.

## Статус

`web` считается **минимально готовым web node**.

Осталось: более осмысленная страница, reverse proxy к `app`, Promtail, nginx logs в Loki, node_exporter, подключение к Prometheus.
