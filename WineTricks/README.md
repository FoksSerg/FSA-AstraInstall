# Winetricks - Утилиты для работы с компонентами

Эта папка содержит скрипты для работы с компонентами winetricks: извлечение списка компонентов и загрузка установочных файлов без установки.

## Файлы в папке

### `winetricks`
Оригинальный скрипт winetricks версии 20250102-next. Используется как источник данных для парсинга компонентов.

### `extract_winetricks_components.py`
**Назначение:** Извлекает список всех доступных компонентов winetricks с их метаданными из файла `winetricks`.

**Что делает:**
- Парсит файл `winetricks` и находит все компоненты (dlls, apps, fonts, settings, benchmarks)
- Извлекает метаданные каждого компонента: название, издатель, год, тип загрузки, сайт
- Генерирует два отчета:
  - `winetricks_components.md` - Markdown формат с форматированием
  - `winetricks_components.txt` - Простой текстовый формат

**Использование:**
```bash
python3 extract_winetricks_components.py
```

**Результат:**
- Создает файлы `winetricks_components.md` и `winetricks_components.txt` в текущей папке
- Всего извлекается ~454 компонента:
  - DLLs и библиотеки: ~311
  - Приложения: ~60
  - Шрифты: ~42
  - Настройки: ~33
  - Бенчмарки: ~8

### `download_winetricks_files.py`
**Назначение:** Загружает установочные файлы компонентов winetricks в отдельные папки без их установки.

**Что делает:**
- Парсит функции `load_*` в файле `winetricks`
- Извлекает все вызовы `w_download()` с URL, SHA256 и именами файлов
- Загружает файлы в структуру папок: `downloads/<component_name>/<files>`
- Проверяет SHA256 суммы для безопасности
- Пропускает уже загруженные файлы

**Использование:**

```bash
# Показать список всех компонентов с файлами для загрузки
python3 download_winetricks_files.py --list

# Загрузить все компоненты
python3 download_winetricks_files.py

# Загрузить конкретные компоненты
python3 download_winetricks_files.py --components vcrun2019 dotnet48 d3dx9

# Указать другую папку для загрузки
python3 download_winetricks_files.py --output my_downloads
```

**Параметры:**
- `--winetricks` - путь к файлу winetricks (по умолчанию: `winetricks`)
- `--output, -o` - директория для загрузки (по умолчанию: `downloads`)
- `--components, -c` - список компонентов для загрузки
- `--list, -l` - показать список компонентов с файлами

**Результат:**
- Создает папку `downloads/` (или указанную через `--output`)
- Для каждого компонента создается отдельная подпапка
- Файлы загружаются с проверкой SHA256
- Уже существующие файлы пропускаются

**Пример структуры после загрузки:**
```
downloads/
├── vcrun2019/
│   └── vc_redist.x64.exe
├── dotnet48/
│   └── ndp48-web.exe
└── art2k7min/
    └── AccessRuntime.exe
```

### `winetricks_components.md` и `winetricks_components.txt`
Сгенерированные файлы со списком всех компонентов winetricks. Создаются автоматически при запуске `extract_winetricks_components.py`.

### `winetricks_tracker.py`
**Назначение:** Обертка для winetricks с отслеживанием всех операций установки и автоматической генерацией скрипта деинсталляции.

**Что делает:**
- Захватывает состояние системы до установки (файлы, реестр, DLL overrides)
- Запускает winetricks для установки компонента
- Захватывает состояние системы после установки
- Анализирует изменения (новые файлы, изменения реестра, DLL overrides)
- Генерирует манифест установки в формате JSON
- Создает скрипт деинсталляции для удаления компонента

**Использование:**

```bash
# Установка компонента с отслеживанием
python3 winetricks_tracker.py cabinet

# С принудительной переустановкой
python3 winetricks_tracker.py cabinet --force

# Указать другой путь к winetricks
python3 winetricks_tracker.py cabinet --winetricks /path/to/winetricks
```

**Результат:**
- Создается папка `install_logs/<component_name>/` с:
  - `<component>_manifest.json` - полный манифест установки
  - `registry_before.reg` - реестр до установки
  - `registry_after.reg` - реестр после установки
  - `uninstall_<component>.sh` - скрипт деинсталляции

**Деинсталляция:**
```bash
# Запуск скрипта деинсталляции
bash install_logs/cabinet/uninstall_cabinet.sh
```

**Что отслеживается:**
- ✅ Копирование файлов (DLL, шрифты, другие файлы)
- ✅ Изменения реестра
- ✅ DLL overrides
- ✅ Регистрация DLL (через regsvr32)
- ✅ Создание директорий

## Требования

- Python 3.6+
- Для `download_winetricks_files.py`: один из загрузчиков (curl, wget или aria2c)
- Для `winetricks_tracker.py`: Wine и настроенный WINEPREFIX

## Примечания

- Все скрипты работают относительно папки, в которой они находятся
- Файл `winetricks` должен находиться в той же папке, что и скрипты
- Загруженные файлы можно использовать для офлайн-установки компонентов
- Скрипты автоматически проверяют целостность файлов через SHA256

## Примеры использования

### 1. Получить список всех компонентов
```bash
python3 extract_winetricks_components.py
# Результат: winetricks_components.md и winetricks_components.txt
```

### 2. Посмотреть, какие файлы нужны для компонента
```bash
python3 download_winetricks_files.py --list | grep vcrun2019
```

### 3. Загрузить файлы для конкретного компонента
```bash
python3 download_winetricks_files.py --components vcrun2019
# Файлы будут в downloads/vcrun2019/
```

### 4. Подготовить офлайн-установку нескольких компонентов
```bash
python3 download_winetricks_files.py --components vcrun2019 dotnet48 d3dx9
# Все файлы будут в downloads/
```

### 5. Установить компонент с отслеживанием и генерацией деинсталлятора
```bash
python3 winetricks_tracker.py cabinet
# Создаст install_logs/cabinet/ с манифестом и скриптом деинсталляции
```

### 6. Удалить компонент через сгенерированный скрипт
```bash
bash install_logs/cabinet/uninstall_cabinet.sh
```

