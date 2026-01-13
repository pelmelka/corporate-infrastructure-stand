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

## Сценарий 4. App logs

Цель: показать app logs.

Шаги:

```bash
curl http://192.168.85.133:8080/
curl http://192.168.85.133:8080/health
curl http://192.168.85.133:8080/bad-endpoint
```

В Grafana/Loki искать:

```text
{host="app", job="app"}
```

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

## Сценарий 6. Recovery story

Цель: показать инженерный подход к восстановлению.

Последовательность:

1. Создать проблему: остановить `app.service`, сломать nginx config или остановить promtail.
2. Посмотреть симптомы: curl, Grafana, Prometheus, Loki logs.
3. Найти причину: systemctl, journalctl, Grafana logs.
4. Исправить.
5. Проверить восстановление.
