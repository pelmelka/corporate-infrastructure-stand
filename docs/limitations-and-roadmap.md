# Ограничения и развитие

## Текущая область стенда

Стенд закрывает базовый цикл эксплуатации небольшой внутренней системы: публикация приложения, хранение состояния, логирование, мониторинг, алертинг, backup/restore, сетевой контроль и Ansible-автоматизация.

## Ограничения текущей версии

В текущую версию не входят:

- отказоустойчивый кластер;
- Kubernetes;
- полноценный CI/CD pipeline;
- container registry flow с versioned image tags;
- внешний secrets manager;
- удаленное backup-хранилище;
- Grafana provisioning как обязательный deployment-механизм;
- публичная публикация сервиса в интернет.

## Запланированные улучшения

| Направление | Возможное улучшение |
|---|---|
| TLS | HTTPS/local CA для web и operator endpoints |
| Secrets | Ansible Vault или отдельный secrets management process |
| Docker | tagged images и registry после появления CI/CD |
| Logging | переход на stdout/stderr collection для container logs |
| Grafana | dashboard provisioning через файлы |
| Backups | backup freshness alert, remote storage, регулярный restore test |
| Network | DHCP reservations или static addressing для всех VM |
| Monitoring | дополнительные PostgreSQL panels: locks, slow queries, cache hit ratio |
| Automation | ansible-lint, syntax-check в CI, тесты ролей |

## Что не считается задачей текущего стенда

Стенд не предназначен для демонстрации высокой доступности, горизонтального масштабирования или публичной эксплуатации. Основной фокус — понятная инфраструктурная сборка, наблюдаемость, диагностика и операционная автоматизация.
