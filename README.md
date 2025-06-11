# Установка и запуск проекта ONLINEMIAMI

## Шаг 1: Установка зависимостей

```bash
pip install django
```

## Шаг 2: Создание виртуального окружения

```bash
python -m venv venv
```

## Шаг 3: Создание проекта Django

```bash
django-admin startproject ONLINEMIAMI
```

## Шаг 4: Перенос файлов

Перенесите файлы проекта в созданную папку `ONLINEMIAMI` с заменой существующих.

## Шаг 5: Установка зависимостей из файла

> ⚠️ Обратите внимание: правильное имя файла — `requirements.txt`, а не `requierments.py`.

```bash
pip install -r requirements.txt
```

## Шаг 6: Установка и запуск Redis

```bash
sudo apt update
sudo apt install redis-server
sudo systemctl start redis-server
```

## Шаг 7: Запуск Daphne с SSL

> ⚠️ Убедитесь, что пути к ключам и сертификатам указаны корректно.

```bash
daphne -e ssl:443:privateKey=/etc/letsencrypt/live/miamionline.ru/privkey.pem:certKey=/etc/letsencrypt/live/miamionline.ru/fullchain.pem messenger.asgi:application
```

---

## Примечания

- Проверьте корректность путей к SSL-сертификатам.
- Убедитесь, что вы используете актуальные версии Django и других зависимостей.
