# Стек инструментов проекта

## Виртуализация

### VMware

Используется как среда, внутри которой запущен Proxmox VE. Дает NAT-сеть `192.168.85.0/24`.

### Proxmox VE

Версия по скриншотам: `Proxmox VE 9.1.1`.

Роль: создание VM, управление ресурсами, snapshots, web UI, bridge `vmbr0` и потенциально `vmbr1`.

## OS

### Debian 13

Используется на всех VM. Минимальная установка без GUI.

## Управление и автоматизация

### SSH

Подключения с Windows к `admin`, с `admin` к узлам, будущая база для Ansible.

### sudo

Пользователь `pelmel` добавляется в группу `sudo` на всех узлах.

### Ansible

Установлен на `admin`. Роль: inventory, ad-hoc команды, будущие playbook'и, автоматизация установки и настройки сервисов.

### Git, план

Пока пропущен. В будущем нужен для хранения структуры проекта, README, playbook'ов, шаблонов и истории изменений.

## Web слой

### Nginx

Установлен на `web`. Роль: статический frontend, позже reverse proxy, access/error logs.

## Application слой

### Python

Используется на `app`. Сейчас стандартная библиотека `http.server`; позже возможен Flask.

### systemd

Используется для `app.service`, позже `loki.service`, Promtail, Prometheus, Grafana, Alertmanager, node_exporter.

## Logging

### Loki

Устанавливается на `log`. Роль: хранение логов и API для Grafana.

### Promtail, план

Будет установлен на `web` и `app`. Роль: чтение логов, добавление labels, отправка в Loki.

## Monitoring

### Prometheus, план

Будет установлен на `monitor`. Роль: сбор метрик.

### Grafana, план

Будет установлена на `monitor`. Роль: UI для dashboard'ов, логов и метрик.

### Alertmanager, план

Будет установлен на `monitor`. Роль: alerts.

### node_exporter, план

Будет установлен на `web`, `app`, `log`, возможно `monitor`. Роль: системные метрики.

## Планируемые dashboard'ы

- Infrastructure Overview
- Web Node Dashboard
- App Node Dashboard
- Logs / Observability
- Loki dashboard
- Prometheus targets dashboard

## Планируемые демонстрационные сценарии

1. Нормальная работа: открыть сайт, дернуть backend, увидеть логи и метрики.
2. App down: остановить `app.service`, увидеть ошибку, поднять обратно.
3. Web logs: сгенерировать HTTP-запросы и увидеть nginx logs в Loki.
4. Infrastructure overview: показать состояние всех узлов.
