# Демонстрационные сценарии проекта

## Сценарий 1. Нормальная работа системы

Цель: показать, что frontend, backend, логирование и мониторинг работают вместе.

Шаги:

1. Открыть сайт `http://192.168.85.131`.
2. Проверить backend: `curl http://192.168.85.133:8080/health`.
3. После reverse proxy проверить `curl http://192.168.85.131/api/health`.
4. Открыть Grafana.
5. Показать метрики `web`, `app`, логи nginx и app.

Ожидаемый итог: сайт и backend работают, запросы видны в логах, узлы видны в мониторинге.

Текущее состояние: frontend и backend уже работают, nginx logs и app logs доходят в Loki. Prometheus, Grafana и Alertmanager на `monitor` подняты. node_exporter работает на `web`, `app`, `log`, `monitor`; Prometheus показывает `node (4/4 up)`. В Grafana подключены datasources Prometheus и Loki; в Explore проверены `up{job="node"}`, `{host="web", job="nginx"}`, `{host="app", job="app"}`. Следующий шаг — собрать dashboard Infrastructure Overview.

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

Ожидаемый итог: видно обнаружение проблемы, диагностика, восстановление и подтверждение восстановления.

Дополнительно после восстановления можно проверить app logs:

```bash
tail -n 20 /var/log/app/app.log
```

И в Loki:

```text
{host="app", job="app"}
```

## Сценарий 3. Web access logs

Цель: показать централизованный сбор nginx logs.

Шаги:

```bash
curl http://192.168.85.131
curl http://192.168.85.131/not-found
```

Локально это должно попасть в:

```text
/var/log/nginx/access.log
/var/log/nginx/error.log
```

Promtail отправляет в Loki. В Grafana/Loki искать:

```text
{host="web", job="nginx"}
```

Текущее состояние: этот сценарий уже технически подтвержден через Loki API `query_range`. После генерации запросов Loki вернул nginx access logs с labels `host=web`, `job=nginx`, `service=frontend`, `env=lab`.

## Сценарий 4. App logs

Цель: показать централизованный сбор backend logs.

Шаги:

```bash
curl http://192.168.85.133:8080/
curl http://192.168.85.133:8080/health
curl http://192.168.85.133:8080/bad-endpoint
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

Promtail отправляет в Loki. В Grafana/Loki искать:

```text
{host="app", job="app"}
```

Текущее состояние: этот сценарий уже технически подтвержден через Loki API `query_range`. После генерации запросов Loki вернул app logs с labels `host=app`, `job=app`, `service=python-backend`, `env=lab`, `filename=/var/log/app/app.log`.

## Сценарий 5. Infrastructure overview

Цель: показать Grafana dashboard.

Должно быть видно:

- `web` UP;
- `app` UP;
- `log` UP;
- `monitor` UP;
- CPU/RAM/Disk по каждому узлу;
- targets Prometheus;
- статус Loki;
- последние ошибки из логов.

Текущее состояние: база готова. `monitor`, Prometheus, Grafana, Alertmanager и node_exporter на всех monitored nodes уже подняты. Prometheus показывает `node (4/4 up)`. Prometheus и Loki datasources в Grafana уже подключены и проверены. Для полноценного Infrastructure Overview осталось создать/импортировать Grafana dashboard.

## Сценарий 6. Recovery story

Цель: показать инженерный подход к восстановлению.

Последовательность:

1. Создать проблему: остановить `app.service`, сломать nginx config или остановить promtail.
2. Посмотреть симптомы: curl, Grafana, Prometheus, Loki logs.
3. Найти причину: systemctl, journalctl, Grafana logs.
4. Исправить.
5. Проверить восстановление.

Текущее состояние: базовая часть для recovery уже есть — `app.service`, `promtail.service`, `loki.service`, nginx logs, app logs, Prometheus, Grafana и Alertmanager. В Grafana уже подключены Prometheus и Loki datasources, поэтому демонстрация через метрики и логи технически возможна в Grafana Explore. Для красивой демонстрации осталось создать dashboard.
