# Текущее состояние сервера admin

## Назначение

`admin` — управляющий сервер проекта, control node.

Роль:

- SSH-подключения к остальным серверам;
- хранение SSH-ключей;
- запуск Ansible;
- хранение inventory, будущих playbook'ов, шаблонов и документации.

## Основная информация

- Hostname: `admin`
- OS: Debian GNU/Linux 13 (trixie)
- Kernel: Linux 6.12.74+deb13+1-amd64
- Virtualization: KVM
- Hardware vendor/model: QEMU / Standard PC i440FX + PIIX
- IP: `192.168.85.129/24`
- Interface: `ens18`
- Default gateway: `192.168.85.2`
- User: `pelmel`
- sudo: работает
- SSH: работает

## Сеть

```text
interface: ens18
inet: 192.168.85.129/24
default via 192.168.85.2 dev ens18
```

DNS и интернет проверены: `ping deb.debian.org` проходит.

## SSH

- service: `ssh.service`
- state: `active (running)`
- autostart: `enabled`
- port: `22`

С Windows выполнялось успешное подключение:

```powershell
ssh pelmel@192.168.85.129
```

## sudo

`pelmel` добавлен в группу `sudo`.

```bash
sudo whoami
```

Результат: `root`.

## Ansible

Ansible установлен.

```text
ansible [core 2.19.4]
python version = 3.13.5
```

Inventory:

```text
~/control-node/inventory/hosts.ini
```

Текущий минимальный inventory:

```ini
[control]
admin ansible_connection=local

[all:vars]
ansible_user=pelmel
```

Проверка:

```bash
ansible all -i ./hosts.ini -m ping
```

Результат:

```text
admin | SUCCESS => {"changed": false, "ping": "pong"}
```

Предупреждение про discovered Python interpreter решено оставить как некритичное.

## SSH-ключи

Создан ключ:

```bash
ssh-keygen -t ed25519 -C "homelab-admin"
```

Файлы:

```text
/home/pelmel/.ssh/id_ed25519
/home/pelmel/.ssh/id_ed25519.pub
```

Публичный ключ позже нужно раскатать на `web`, `app`, `log`, `monitor`.

## Структура проекта

Создана директория:

```text
~/control-node
```

Используется:

```text
~/control-node/inventory/hosts.ini
```

Git пока был пропущен.

## Статус

`admin` считается **минимально готовым control node**.

Осталось: добавить остальные узлы в inventory, раскатать SSH-ключи, создать playbook'и, возможно инициализировать Git, хранить шаблоны и документацию.
