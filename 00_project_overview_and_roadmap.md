# Mini Corporate Infrastructure Lab — план и roadmap

## Цель проекта

Собрать учебный pet-project в формате мини-инфраструктуры корпоративного типа на базе Proxmox VE внутри VMware: frontend, backend, централизованное логирование, мониторинг, базовая автоматизация и демонстрационные сценарии troubleshooting.

Итоговая ценность проекта: показать Linux administration, DevOps-подход, systemd, SSH, Ansible, Nginx, Python-сервис, Loki/Promtail, Prometheus/Grafana/Alertmanager, node_exporter, reverse proxy и диагностику.

## Итоговая архитектура

```text
Windows host / Browser / SSH client
        |
        | VMware NAT / local access
        v
Proxmox VE node: 192.168.85.128:8006
        |
        +-- admin    192.168.85.129  control node / Ansible
        +-- web      192.168.85.131  Nginx frontend + reverse proxy + Promtail + node_exporter
        +-- app      192.168.85.133  support-desk-api + app logs + app metrics + Promtail + node_exporter
        +-- log      192.168.85.135  Loki logging server + node_exporter
        +-- monitor  192.168.85.137  Prometheus + Grafana + Alertmanager + node_exporter
```

## Реализованные потоки

```text
Browser -> web:80                                      # реализовано: Mini Support Desk frontend
Browser -> web:80/api/* -> app:8080                    # реализовано: Nginx reverse proxy /api/* -> app
web -> Promtail -> log:3100 Loki                       # реализовано: nginx access/error logs
app -> Promtail -> log:3100 Loki                       # реализовано: support-desk-api product logs
monitor:9090 Prometheus -> node_exporter targets       # реализовано: node (4/4 up)
Grafana -> Prometheus:9090                             # реализовано: datasource подключен
Grafana -> Loki:3100                                   # реализовано: datasource подключен
Grafana dashboard Infrastructure Overview              # реализовано: targets UP, CPU/RAM/Disk, web/app logs
Prometheus -> Alertmanager:9093                        # реализовано: связь есть, alert rules пока не создавались
```

## Важное замечание про IP

Все VM сейчас получают IP через DHCP VMware NAT. В lab-режиме адреса держатся стабильно, но позже нужно сделать одно из двух:

```text
1. DHCP reservation по MAC-адресам всех VM;
2. статические IP внутри Debian на всех серверах.
```

Это важно для Promtail, Prometheus targets, Grafana datasources, Ansible inventory, Nginx reverse proxy и будущего Telegram-бота.

## Роли серверов

### admin

Управляющий сервер. На нем SSH-ключи, Ansible, inventory, будущие playbook'и, шаблоны, документация и, возможно, Git.

### web

Frontend / Nginx server. Сейчас отдает страницу Mini Support Desk, проксирует `/api/*` на `app:8080`, пишет nginx access/error logs, отправляет их в Loki через Promtail и отдает системные метрики через node_exporter.

### app

Backend/application node. Сейчас Python-приложение работает как `support-desk-api`: `/health`, `/tickets`, `/tickets/<id>`, `/tickets/<id>/status`, `/metrics`. Заявки хранятся в `/opt/app/tickets.json`; product logs пишутся в `/var/log/app/app.log`; app logs отправляются в Loki через Promtail.

### log

Централизованный сервер логирования. На нем Loki. Принимает nginx logs от `web` и app product logs от `app`.

### monitor

Сервер мониторинга, визуализации и алертов. На нем Prometheus, Grafana, Alertmanager и node_exporter. Dashboard `Infrastructure Overview` создан. Alertmanager связан с Prometheus, но alert rules пока не создавались.

## Завершенные этапы

### Этап 1. Loki на log — завершено

Loki 3.5.0 установлен как `loki.service`, `active/enabled`, `/ready -> ready`, принимает web/app logs.

### Этап 2. Promtail на web — завершено

Promtail читает `/var/log/nginx/*.log` и отправляет nginx logs в Loki с labels `host=web`, `job=nginx`, `service=frontend`, `env=lab`.

### Этап 3. Promtail на app — завершено

Promtail читает `/var/log/app/*.log` и отправляет app logs в Loki с labels `host=app`, `job=app`, `service=python-backend`, `env=lab`.

### Этап 4. Monitor base stack — завершено

На `monitor` установлены Prometheus, Grafana, Alertmanager и node_exporter. Сервисы active/enabled.

### Этап 5. Метрики node_exporter — завершено

node_exporter установлен на `web`, `app`, `log`, `monitor`; Prometheus видит `node (4/4 up)` с host labels.

### Этап 6. Grafana datasources — завершено

В Grafana подключены Prometheus datasource (`http://localhost:9090`) и Loki datasource (`http://192.168.85.135:3100`).

### Этап 7. Grafana dashboard Infrastructure Overview — завершено

Dashboard показывает Targets UP, CPU/RAM/Disk по host, Web nginx logs и App logs.

### Этап 8. Web/App integration — завершено

Реализован продукт `Mini Support Desk`:

```text
Browser -> web/Nginx -> app/support-desk-api
```

Готово:

- `web` отдает frontend `/var/www/html/index.html`;
- `web` проксирует `/api/*` на `http://192.168.85.133:8080/`;
- `app` работает как `support-desk-api`;
- заявки создаются через UI и сохраняются в `/opt/app/tickets.json`;
- статус заявки меняется через UI;
- nginx access logs показывают `GET/POST/PATCH /api/*`;
- app product logs показывают `event=ticket_created`, `event=ticket_status_changed`, `event=ticket_list_requested`, `event=health_check`;
- Loki/Grafana видит новые product logs по запросу `{host="app", job="app"} |= "support-desk-api"`.

## Оставшиеся этапы и ожидаемые итоги

### Этап 9. Полировка logging — текущий следующий этап

Фокус: довести логирование Mini Support Desk до более production-like состояния.

Ожидаемый итог:

- product logs `support-desk-api` имеют финальный удобный формат;
- app logs содержат достаточно полей для troubleshooting пользовательского действия;
- отдельно продуман `client_ip` как TCP peer и proxy metadata `X-Real-IP` / `X-Forwarded-For`;
- решено поведение для повторного нажатия текущего статуса заявки;
- LogQL-запросы удобно показывают `event=ticket_created`, `event=ticket_status_changed`, validation/not_found/internal_error события;
- при необходимости обновлена Grafana panel `App logs` под новый формат `event=...`.

### Этап 10. Полировка monitoring

Фокус: добавить продуктовые метрики приложения в Prometheus и сделать более полезные панели/алерты.

Ожидаемый итог:

- Prometheus scrape для app `/metrics`;
- Grafana panels по product metrics: total/open/in_progress/resolved tickets;
- позже — метрики по `resource`, `category`, priority, request rate, errors и latency;
- базовые alerts: `TargetDown`, `HighDiskUsage`, `AppHealthFail`;
- product alerts: слишком много open tickets, всплеск заявок, много жалоб на один resource/category, рост 5xx/502.

### Этап 11. Полировка Ansible/admin

Фокус: привести `admin` к роли нормального control node.

Ожидаемый итог:

- Ansible inventory содержит все реальные узлы;
- SSH-ключи раскатаны на `web`, `app`, `log`, `monitor`;
- Ansible ad-hoc ping проходит по всем узлам;
- появились первые playbook'и или заготовки ролей для базовой настройки, nginx/app/promtail/node_exporter;
- структура `~/control-node` готова для Git/README/templates.

### Этап 12. Финальная документация и демонстрационный сценарий

Фокус: собрать проект в демонстрируемый pet-project.

Ожидаемый итог:

- README с архитектурой, IP/портами, сервисами, проверками и screenshots;
- финальный demo flow: открыть Mini Support Desk, создать заявку, увидеть web/app logs и метрики;
- recovery story: остановить `app.service`, получить проблему через `/api/health`, найти причину через `systemctl`, `journalctl`, nginx/app logs, восстановить сервис;
- snapshots/контрольные точки в Proxmox;
- финальная структура sources актуальна и не дублирует лишнюю информацию.

### Опциональный будущий этап. Telegram support bot

Фокус: добавить второй клиент к тому же `support-desk-api`.

Ожидаемый итог:

- `support-bot.service` работает через long polling;
- бот ходит в Telegram API через Windows outbound proxy workaround `192.168.85.1:10802`;
- бот создает/читает/закрывает tickets через тот же app API;
- в logs видно `source=telegram`;
- bot logs при необходимости отправляются в Loki отдельным job/service.

Этот этап не блокирует основной DevOps-проект и остается future enhancement.

## Текущий маркер прогресса

```text
Последний завершенный этап: Этап 8. Web/App integration.
Текущий следующий этап: Этап 9. Полировка logging.
Далее: Этап 10. Полировка monitoring, Этап 11. Полировка Ansible/admin, Этап 12. Финальная документация и demo.
```

## Текущий прогресс проекта

Оценка прогресса примерная, потому что этапы не равны по трудоемкости. По формальному счетчику завершено 8 из 12 основных этапов, но самые тяжелые инфраструктурные части уже выполнены: logging stack, observability stack, node metrics, Grafana dashboard и Web/App integration.

```text
Примерная инженерная готовность проекта: 92–94%.
Демонстрационная готовность проекта: 90–92%.
Формальная готовность по roadmap: 8/12 основных этапов завершены.
```

Разбивка по этапам:

| Этап | Статус | Примерная готовность | Комментарий |
|---|---:|---:|---|
| 1. Loki на log | завершено | 100% | Loki работает как systemd service и принимает logs. |
| 2. Promtail на web | завершено | 100% | nginx logs уходят в Loki. |
| 3. Promtail на app | завершено | 100% | app product logs уходят в Loki. |
| 4. Monitor base stack | завершено | 100% | Prometheus, Grafana, Alertmanager, node_exporter active/enabled. |
| 5. Метрики node_exporter | завершено | 100% | Prometheus видит node targets `4/4 up`. |
| 6. Grafana datasources | завершено | 100% | Prometheus и Loki подключены к Grafana. |
| 7. Grafana dashboard Infrastructure Overview | завершено | 100% | Есть первый обзорный dashboard. |
| 8. Web/App integration | завершено | 100% | Mini Support Desk работает через `Browser -> web -> app`. |
| 9. Полировка logging | текущий следующий этап | 0–10% | Нужно финализировать product logs, proxy headers, LogQL. |
| 10. Полировка monitoring | план | 0–10% | Нужно добавить app `/metrics` в Prometheus, product panels и alerts. |
| 11. Полировка Ansible/admin | план | 15–25% | `admin` и базовый Ansible есть, но inventory/playbook'и еще не доведены. |
| 12. Финальная документация и demo | план | 20–30% | Sources ведутся, но README/final demo/snapshots еще не собраны. |
| Опционально. Telegram support bot | future enhancement | 5–10% | Сетевой workaround проверен, сам bot еще не реализован. |

Короткая интерпретация:

```text
Проект уже можно демонстрировать как работающий infrastructure lab с продуктовым web/app flow.
Оставшиеся этапы в основном повышают качество: logging polish, monitoring polish, automation/admin polish, README и demo packaging.
```

## Полный roadmap основных этапов

```text
1. Loki на log                                      # завершено
2. Promtail на web                                  # завершено
3. Promtail на app                                  # завершено
4. Monitor base stack                               # завершено
5. Метрики node_exporter                            # завершено
6. Grafana datasources                              # завершено
7. Grafana dashboard Infrastructure Overview         # завершено
8. Web/App integration                              # завершено
9. Полировка logging                                # текущий следующий этап
10. Полировка monitoring                             # план
11. Полировка Ansible/admin                          # план
12. Финальная документация и демонстрационный сценарий # план
Optional. Telegram support bot                       # future enhancement
```

## Future improvements

Подробный backlog будущих улучшений вынесен отдельно в файл:

```text
12_future_improvements_backlog.md
```
