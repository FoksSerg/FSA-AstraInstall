# DockerManager

Модуль управления Docker сборками для проектов FSA.

**Версия:** V3.1.162 (2025.12.07)  
**Компания:** ООО "НПА Вира-Реалтайм"  
**Разработчик:** @FoksSegr & AI Assistant (@LLM)

## 📋 Описание

DockerManager - это универсальная система для автоматизации сборки бинарных файлов из Python проектов с использованием Docker. Модуль поддерживает:

- ✅ Локальную и удаленную сборку через Docker
- ✅ Сборку для разных платформ (Astra Linux 1.7, 1.8)
- ✅ Управление Docker образами
- ✅ Загрузку/скачивание исходников и результатов
- ✅ Графический интерфейс (GUI) для управления сборками
- ✅ Командную строку (CLI) для автоматизации
- ✅ Детальное логирование всех операций

## 🏗️ Архитектура

```
DockerManager/
├── __init__.py              # Инициализация модуля
├── config.py                # Конфигурация (сервер, платформы, проекты)
├── cli.py                   # CLI интерфейс
├── build_manager_gui.py     # GUI приложение
├── build_runner.py          # Оркестратор сборки (локально/удаленно)
├── docker_manager.py        # Управление Docker образами
├── file_manager.py          # Загрузка/скачивание файлов
├── server_connection.py     # SSH/SCP соединение с сервером
├── logger.py                # Централизованное логирование
├── scripts/                 # Скрипты для Docker контейнеров
│   ├── docker_build.sh     # Скрипт сборки в контейнере
│   └── fix_future_imports.py # Исправление __future__ импортов
├── dockerfiles/             # Dockerfile для разных платформ
│   ├── Dockerfile.astra-1.7
│   └── Dockerfile.astra-1.8
├── run_gui.py              # Запуск GUI (Python)
└── README.md               # Эта документация
```

## 🚀 Быстрый старт

### Запуск GUI

```bash
# Способ 1: Через Python модуль
python3 -m DockerManager.cli --gui

# Способ 2: Через Python скрипт
python3 DockerManager/run_gui.py
```

### Запуск сборки через CLI

```bash
# Локальная сборка для Astra Linux 1.8
python3 -m DockerManager.cli --project FSA-AstraInstall --platform astra-1.8

# Удаленная сборка для Astra Linux 1.7
python3 -m DockerManager.cli --project FSA-AstraInstall --platform astra-1.7 --remote
```

## 📦 Компоненты

### 1. config.py
Централизованная конфигурация модуля:
- **REMOTE_SERVER** - настройки удаленного сервера сборки
- **BUILD_PLATFORMS** - конфигурация платформ для сборки
- **PROJECTS** - список проектов и их настройки
- **DOCKER_CONFIG** - настройки Docker
- **GUI_CONFIG** - настройки GUI

### 2. build_runner.py
Оркестратор процесса сборки:
- `build()` - главная функция сборки
- `build_local()` - локальная сборка через Docker
- `build_remote()` - удаленная сборка на сервере
- `check_platform()` - проверка платформы (macOS)

### 3. docker_manager.py
Управление Docker образами:
- `check_image_exists()` - проверка существования образа
- `build_image()` - сборка Docker образа
- `check_remote_image_exists()` - проверка образа на сервере
- `build_remote_image()` - сборка образа на сервере
- `get_dockerfile_path()` - получение пути к Dockerfile

### 4. file_manager.py
Работа с файлами:
- `upload_sources()` - загрузка исходников на сервер
- `download_build()` - скачивание результатов сборки
- `list_builds()` - список доступных сборок
- `check_unified_file()` - проверка объединенного файла

### 5. server_connection.py
SSH/SCP соединение с сервером:
- `execute_ssh_command()` - выполнение SSH команд
- `scp_upload()` - загрузка файлов через SCP
- `scp_download()` - скачивание файлов через SCP
- `test_connection()` - проверка соединения
- `create_remote_directory()` - создание удаленных директорий

### 6. logger.py
Централизованное логирование:
- `setup_logger()` - настройка логгера
- `get_logger()` - получение логгера
- `get_log_file()` - получение пути к лог файлу
- `setup_stdout_stderr_capture()` - перехват stdout/stderr

### 7. build_manager_gui.py
Графический интерфейс с вкладками:
- **Настройки сервера** - конфигурация удаленного сервера
- **Docker образы** - управление образами (список, создание, удаление)
- **Исходники** - управление исходниками (загрузка, просмотр, очистка)
- **Сборка** - запуск сборки (выбор проекта/платформы, прогресс)
- **Результаты** - список сборок (фильтрация, скачивание, удаление)
- **Лог работы** - реальное время логов всех операций

### 8. cli.py
Командная строка:
- `--gui` - запуск GUI
- `--project` - выбор проекта
- `--platform` - выбор платформы
- `--remote` - удаленная сборка

## ⚙️ Конфигурация

### Настройка сервера

Настройки сервера находятся в `config.py`:

```python
REMOTE_SERVER = {
    "host": "10.10.55.77",           # IP сервера
    "user": "fsa",                    # SSH пользователь
    "base_path": "/mnt/v/UbuMount",   # Базовый путь на сервере
    "docker_data": "docker-data",     # Папка для данных Docker
    "incoming": "incoming",            # Входящие исходники
    "outgoing": "outgoing"            # Исходящие сборки
}
```

Можно переопределить через переменные окружения:
```bash
export FSA_BUILD_SERVER="10.10.55.77"
export FSA_BUILD_USER="fsa"
export FSA_BUILD_STORAGE_PATH="/mnt/v/UbuMount"
```

### Добавление новой платформы

В `config.py` добавьте новую платформу в `BUILD_PLATFORMS`:

```python
BUILD_PLATFORMS = {
    "astra-1.9": {
        "base_image": "debian:trixie",
        "glibc": "2.39",
        "python": "3.12",
        "description": "Astra Linux 1.9.x (GLIBC 2.39)",
        "dockerfile": "Dockerfile.astra-1.9",
        "image_name": "fsa-astrainstall-builder:astra-1.9"
    }
}
```

Создайте соответствующий Dockerfile в `dockerfiles/Dockerfile.astra-1.9`.

### Добавление нового проекта

В `config.py` добавьте проект в `PROJECTS`:

```python
PROJECTS = {
    "MyProject": {
        "name": "MyProject",
        "description": "Описание проекта",
        "unified_script": "../Build/build_unified.py",
        "output_name": "MyProject"
    }
}
```

## 🔧 Использование

### GUI режим

1. Запустите GUI: `python3 -m DockerManager.cli --gui`
2. Настройте сервер в вкладке "Настройки сервера"
3. Выберите проект и платформу в вкладке "Сборка"
4. Нажмите "Начать сборку"
5. Следите за прогрессом в реальном времени
6. Скачайте результат в вкладке "Результаты"

### CLI режим

```bash
# Локальная сборка
python3 -m DockerManager.cli \
    --project FSA-AstraInstall \
    --platform astra-1.8

# Удаленная сборка
python3 -m DockerManager.cli \
    --project FSA-AstraInstall \
    --platform astra-1.7 \
    --remote
```

### Программный интерфейс

```python
from DockerManager.build_runner import build

# Локальная сборка
success = build("FSA-AstraInstall", "astra-1.8", remote=False)

# Удаленная сборка
success = build("FSA-AstraInstall", "astra-1.7", remote=True)
```

## 📝 Процесс сборки

### Локальная сборка

1. Проверка платформы (должна быть macOS)
2. Проверка Docker
3. Проверка объединенного файла (`FSA-AstraInstall.py`)
4. Получение Dockerfile для платформы
5. Проверка/сборка Docker образа
6. Запуск контейнера с монтированием проекта
7. Выполнение скрипта сборки в контейнере
8. Копирование результата из контейнера
9. Очистка временных контейнеров

### Удаленная сборка

1. Проверка SSH соединения с сервером
2. Загрузка исходников на сервер (tar.gz архив)
3. Проверка/сборка Docker образа на сервере
4. Запуск сборки в контейнере на сервере
5. Скачивание результата с сервера
6. Очистка временных файлов на сервере

## 📂 Структура на сервере

```
/mnt/v/UbuMount/
├── docker-data/          # Данные Docker (образы, контейнеры)
├── incoming/             # Входящие исходники
│   └── FSA-AstraInstall/
│       ├── FSA-AstraInstall.py
│       └── DockerManager/
│           ├── scripts/
│           └── dockerfiles/
└── outgoing/             # Исходящие сборки
    └── FSA-AstraInstall/
        ├── astra-1.7/
        │   └── FSA-AstraInstall
        └── astra-1.8/
            └── FSA-AstraInstall
```

## 🔍 Логирование

Все операции логируются в файл:
```
DockerManager/logs/dockermanager_YYYYMMDD_HHMMSS.log
```

Логи включают:
- Все SSH команды и их вывод
- Все Docker операции
- Загрузку/скачивание файлов
- Прогресс сборки
- Ошибки и предупреждения

В GUI все логи отображаются в реальном времени в вкладке "Лог работы".

## 🛠️ Требования

### Локальная сборка
- macOS (для запуска DockerManager)
- Docker Desktop
- Python 3.7+
- SSH доступ к серверу (для удаленной сборки)

### Удаленный сервер
- Linux (Ubuntu/Debian/WSL2)
- Docker
- SSH сервер
- Достаточно места на диске для образов и сборок

## 🐛 Решение проблем

### Ошибка подключения к серверу

1. Проверьте SSH доступ: `ssh fsa@10.10.55.77`
2. Проверьте настройки в GUI или `config.py`
3. Убедитесь что SSH ключи настроены

### Docker образ не собирается

1. Проверьте Dockerfile в `dockerfiles/`
2. Проверьте логи в `DockerManager/logs/`
3. Убедитесь что базовый образ доступен

### Сборка завершается с ошибкой

1. Проверьте лог файл в `DockerManager/logs/`
2. Убедитесь что объединенный файл существует
3. Проверьте что все зависимости установлены в Dockerfile

## 📚 Примеры

### Пример 1: Сборка для Astra Linux 1.8

```bash
# Генерируем объединенный файл
python3 Build/generate_unified.py

# Собираем бинарник
python3 -m DockerManager.cli \
    --project FSA-AstraInstall \
    --platform astra-1.8 \
    --remote
```

### Пример 2: Управление образами через GUI

1. Запустите GUI
2. Перейдите в "Docker образы"
3. Нажмите "Обновить список"
4. Выберите образ и нажмите "Удалить" (если нужно)

### Пример 3: Просмотр результатов сборки

```python
from DockerManager.file_manager import list_builds

# Список всех сборок
builds = list_builds("FSA-AstraInstall")

# Список сборок для конкретной платформы
builds = list_builds("FSA-AstraInstall", platform="astra-1.8")
```

## 🔐 Безопасность

- SSH соединения используют опции для обхода проверки host key (только для внутренней сети)
- Все операции логируются для аудита
- Docker контейнеры запускаются изолированно
- Временные файлы автоматически очищаются

## 📄 Лицензия

Проект разработан ООО "НПА Вира-Реалтайм"

## 👥 Разработчики

- @FoksSegr - Основной разработчик
- AI Assistant (@LLM) - Помощь в разработке

## 📞 Поддержка

При возникновении проблем:
1. Проверьте логи в `DockerManager/logs/`
2. Проверьте документацию
3. Обратитесь к разработчикам
