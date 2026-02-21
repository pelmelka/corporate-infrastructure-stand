# Демонстрационные сценарии проекта

## Сценарий 1. Нормальная работа системы

Цель: показать, что frontend, backend, логирование и мониторинг работают вместе.

Текущий статус: frontend и backend уже работают отдельно, nginx logs и app logs доходят в Loki, Prometheus/Grafana/Alertmanager подняты на `monitor`, dashboard `Infrastructure Overview` создан. Следующий недостающий элемент для полноценного пользовательского сценария — reverse proxy `web -> app`.

Шаги сейчас:

1. Открыть сайт `http://192.168.85.131`.
2. Проверить backend напрямую: `curl http://192.168.85.133:8080/health`.
3. Открыть Grafana dashboard `Infrastructure Overview`.
4. Показать `Targets UP`, CPU/RAM/Disk, `Web nginx logs`, `App logs`.

Шаги после web/app integration:

1. Открыть сайт `http://192.168.85.131`.
2. Проверить backend через web reverse proxy: `curl http://192.168.85.131/api/health`.
3. Показать, что запросы видны в nginx logs и app logs.
4. Показать состояние узлов и ресурсов в dashboard `Infrastructure Overview`.

Ожидаемый итог: сайт и backend связаны в один пользовательский поток `Browser -> web -> app`; запросы видны в логах, узлы видны в мониторинге.

## Сценарий 2. App service down

Цель: показать troubleshooting backend-сервиса.

Шаги:

```bash
sudo systemctl stop app.service
curl http://192.168.85.133:8080/health
systemctl status app.service
journalctl -u app.service -n 50
sudo systemctl start app.service
curl http://192.168.85.133:8080/health
```

После web/app integration дополнительно проверить через `web`:

```bash
curl http://192.168.85.131/api/health
```

Ожидаемый итог: видно обнаружение проблемы, диагностика, восстановление и подтверждение восстановления.

Дополнительно после восстановления можно проверить app logs:

```bash
tail -n 20 /var/log/app/app.log
```

И в Loki/Grafana:

```text
{host="app", job="app"}
```

## Сценарий 3. Web access logs

Цель: показать централизованный сбор nginx logs.

Шаги:

```bash
curl http://192.168.85.131/
curl http://192.168.85.131/not-found-grafana-test
```

После reverse proxy также:

```bash
curl http://192.168.85.131/api/health
```

Локально это должно попасть в:

```text
/var/log/nginx/access.log
/var/log/nginx/error.log
```

Promtail отправляет nginx logs в Loki. В Grafana/Loki искать:

```text
{host="web", job="nginx"}
```

Текущее состояние: сценарий технически подтвержден. Dashboard `Infrastructure Overview` содержит panel `Web nginx logs`, где строки отображаются в сокращенном виде через LogQL `regexp` и `line_format`.

## Сценарий 4. App logs

Цель: показать централизованный сбор backend logs.

Шаги:

```bash
curl http://192.168.85.133:8080/
curl http://192.168.85.133:8080/health
curl http://192.168.85.133:8080/bad-endpoint-grafana-test
```

После reverse proxy часть запросов будет приходить через `web`:

```bash
curl http://192.168.85.131/api/health
```

Локально это должно попасть в:

```text
/var/log/app/app.log
```

Примеры строк:

```text
INFO service=python-backend method=GET path=/ status=200 client_ip=...
INFO service=python-backend method=GET path=/health status=200 client_ip=...
WARNING service=python-backend method=GET path=/bad-endpoint status=404 client_ip=...
```

Promtail отправляет app logs в Loki. В Grafana/Loki искать:

```text
{host="app", job="app"}
```

Текущее состояние: сценарий технически подтвержден. Dashboard `Infrastructure Overview` содержит panel `App logs`, где строки отображаются в сокращенном виде через LogQL `regexp` и `line_format`.

## Сценарий 5. Infrastructure overview

Цель: показать Grafana dashboard.

Должно быть видно:

- `web` UP;
- `app` UP;
- `log` UP;
- `monitor` UP;
- CPU/RAM/Disk по каждому узлу;
- web nginx logs;
- app logs.

Текущее состояние: dashboard `Infrastructure Overview` создан и сохранен в Grafana. Он использует Prometheus datasource для `Targets UP`, CPU, RAM, Disk и Loki datasource для `Web nginx logs`, `App logs`.

Для наполнения log-панелей свежими событиями можно выполнить:

```bash
curl http://192.168.85.131/
curl http://192.168.85.131/not-found-grafana-test
curl http://192.168.85.133:8080/
curl http://192.168.85.133:8080/health
curl http://192.168.85.133:8080/bad-endpoint-grafana-test
```

После web/app integration дополнительно:

```bash
curl http://192.168.85.131/api/health
```

## Сценарий 6. Recovery story

Цель: показать инженерный подход к восстановлению.

Последовательность:

1. Создать проблему: остановить `app.service`, сломать nginx config или остановить promtail.
2. Посмотреть симптомы: curl, Grafana dashboard, Prometheus targets, Loki logs.
3. Найти причину: `systemctl`, `journalctl`, локальные logs, Grafana logs panels.
4. Исправить.
5. Проверить восстановление.

Текущее состояние: базовая часть для recovery уже есть — `app.service`, `promtail.service`, `loki.service`, nginx logs, app logs, Prometheus, Grafana, Alertmanager и dashboard `Infrastructure Overview`. После web/app integration recovery-сценарий станет нагляднее, потому что можно будет показать отказ backend через пользовательский путь `Browser -> web -> app`.
