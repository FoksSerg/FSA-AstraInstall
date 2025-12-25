# План модульного рефакторинга FSA-AstraInstall

**Версия документа:** 1.0.0  
**Дата создания:** 2025.12.23  
**Проект:** FSA-AstraInstall  
**Компания:** ООО "НПА Вира-Реалтайм"  
**Текущая версия проекта:** V3.6.203 (2025.12.23)  
**Статус:** 📋 ПЛАН  
**Авторы:** @FoksSegr & AI Assistant (@LLM)

---

## 📋 Оглавление

1. [Общая концепция](#общая-концепция)
2. [Текущее состояние](#текущее-состояние)
3. [Цели рефакторинга](#цели-рефакторинга)
4. [Новая структура проекта](#новая-структура-проекта)
5. [Детальное распределение кода](#детальное-распределение-кода)
6. [Поэтапный план миграции](#поэтапный-план-миграции)
7. [Проверка работоспособности](#проверка-работоспособности)
8. [Влияние на сборку бинарника](#влияние-на-сборку-бинарника)
9. [Риски и митигация](#риски-и-митигация)
10. [Контрольные точки](#контрольные-точки)

---

## 🎯 Общая концепция

### Принципы рефакторинга

1. **Сохранение функциональности** - весь существующий функционал сохраняется без изменений
2. **Постепенная миграция** - разбиение на этапы с проверкой работоспособности на каждом этапе
3. **Обратная совместимость** - на время миграции поддерживается работа как единого файла, так и модульной структуры
4. **Минимизация изменений** - изменяются только пути импортов и структура, логика кода остается неизменной
5. **Тестирование на каждом этапе** - после каждого этапа проверяется работа скрипта и сборка бинарника

### Преимущества новой структуры

- ✅ **Навигация** - легче найти нужный код
- ✅ **Переиспользование** - модули можно использовать отдельно
- ✅ **Тестирование** - проще писать unit-тесты
- ✅ **Параллельная разработка** - меньше конфликтов при работе в команде
- ✅ **Кэширование PyInstaller** - быстрее инкрементальные сборки
- ✅ **Масштабируемость** - легче добавлять новый функционал

---

## 📊 Текущее состояние

### Параметры проекта

| Параметр | Значение |
|----------|----------|
| **Размер основного файла** | ~37,726 строк кода |
| **Количество классов** | 34 класса |
| **Количество функций** | ~42 функции верхнего уровня |
| **Размер бинарника** | 13-16 MB |
| **Архитектура** | Монолитный файл |
| **Сборка** | PyInstaller onefile |

### Проблемы текущей структуры

1. **Монолитный файл** - 37,726 строк затрудняют навигацию
2. **Дублирование кода** - повторяющиеся паттерны в разных классах
3. **Высокая связанность** - классы тесно связаны через глобальные переменные
4. **Сложность тестирования** - невозможно тестировать отдельные компоненты изолированно
5. **Замедление разработки** - сложно работать параллельно над разными частями

---

## 🎯 Цели рефакторинга

### Основные цели

1. **Модульная структура** - разбиение на логические модули по функциональности
2. **Устранение дублирования** - вынос общего функционала в утилиты
3. **Улучшение навигации** - четкая структура директорий и файлов
4. **Упрощение тестирования** - изоляция компонентов для unit-тестов
5. **Сохранение сборки** - поддержка существующего процесса сборки бинарника

### Ожидаемые результаты

- ✅ Модульная структура из 47 файлов вместо 1 монолитного
- ✅ Четкое разделение ответственности между модулями
- ✅ Устранение дублирования кода
- ✅ Улучшение поддерживаемости кода
- ✅ Сохранение размера бинарника (~13-16 MB)
- ✅ Ускорение инкрементальных сборок

---

## 📁 Новая структура проекта

```
FSA-AstraInstall/
│
├── 📄 FSA-AstraInstall.py          # ТОЧКА ВХОДА (~200 строк)
│
├── 📁 Code/                         # Все модули приложения
│   │
│   ├── 📁 core/                     # Базовые системы (5 модулей, ~8,000 строк)
│   │   ├── __init__.py
│   │   ├── logging.py               # DualStreamLogger, universal_print
│   │   ├── process_runner.py        # UniversalProcessRunner
│   │   ├── progress.py              # UniversalProgressManager
│   │   ├── activity.py              # ActivityTracker
│   │   └── config.py                # Глобальные константы и конфигурации
│   │
│   ├── 📁 handlers/                 # Обработчики компонентов (7 модулей, ~15,000 строк)
│   │   ├── __init__.py
│   │   ├── base.py                  # ComponentHandler (ABC)
│   │   ├── wine.py                  # WinePackageHandler, WineConfigHandler, WineEnvironmentHandler
│   │   ├── winetricks.py            # WinetricksHandler
│   │   ├── apt.py                   # AptPackageHandler
│   │   ├── application.py           # ApplicationHandler, WineApplicationHandler
│   │   ├── shortcut.py              # DesktopShortcutHandler
│   │   └── system.py                # SystemConfigHandler
│   │
│   ├── 📁 managers/                 # Менеджеры и координаторы (5 модулей, ~12,000 строк)
│   │   ├── __init__.py
│   │   ├── component_status.py      # ComponentStatusManager
│   │   ├── component_installer.py   # ComponentInstaller
│   │   ├── wine_instance.py         # WineApplicationInstanceManager
│   │   ├── system_updater.py        # SystemUpdater, SystemUpdateParser
│   │   └── winetricks_manager.py    # WinetricksManager
│   │
│   ├── 📁 gui/                      # Графический интерфейс (11 модулей, ~16,000 строк)
│   │   ├── __init__.py
│   │   ├── main_window.py           # AutomationGUI (основной класс)
│   │   ├── widgets/
│   │   │   ├── __init__.py
│   │   │   ├── tooltip.py           # ToolTip
│   │   │   └── terminal_redirector.py # TerminalRedirector
│   │   └── tabs/
│   │       ├── __init__.py
│   │       ├── main_tab.py          # Вкладка "Обновление ОС"
│   │       ├── repos_tab.py         # Вкладка "Репозитории"
│   │       ├── terminal_tab.py      # Вкладка "Терминал"
│   │       ├── wine_tab.py          # Вкладка "Установка Программ"
│   │       ├── system_tab.py        # Вкладка "О системе"
│   │       ├── filesystem_tab.py    # Вкладка "Файловая система"
│   │       ├── processes_tab.py     # Вкладка "Мониторинг"
│   │       └── packages_tab.py      # Вкладка "Пакеты"
│   │
│   ├── 📁 utils/                    # Вспомогательные утилиты (7 модулей, ~3,000 строк)
│   │   ├── __init__.py
│   │   ├── path_utils.py            # Работа с путями
│   │   ├── file_utils.py            # Работа с файлами/архивами
│   │   ├── permission_utils.py      # Управление правами доступа
│   │   ├── component_utils.py       # Утилиты для компонентов
│   │   ├── system_utils.py          # SystemStats, RepoChecker
│   │   ├── platform_utils.py        # Определение платформы
│   │   ├── ntp_utils.py             # Синхронизация времени NTP
│   │   └── text_utils.py            # Текстовые утилиты
│   │
│   ├── 📁 monitoring/               # Системы мониторинга (4 модуля, ~2,000 строк)
│   │   ├── __init__.py
│   │   ├── process_monitor.py       # ProcessMonitor
│   │   ├── installation_monitor.py  # InstallationMonitor
│   │   ├── filesystem_monitor.py    # DirectoryMonitor, DirectorySnapshot
│   │   └── filesystem_filter.py     # FilesystemFilter
│   │
│   ├── 📁 interactive/              # Интерактивные системы (3 модуля, ~600 строк)
│   │   ├── __init__.py
│   │   ├── handler.py               # InteractiveHandler
│   │   ├── config.py                # InteractiveConfig
│   │   └── replay.py                # LogReplaySimulator
│   │
│   ├── 📁 updater/                  # Система обновлений (1 модуль, ~1,300 строк)
│   │   ├── __init__.py
│   │   └── self_updater.py          # SelfUpdater
│   │
│   └── 📁 runtime/                  # Runtime функции (3 модуля, ~800 строк)
│       ├── __init__.py
│       ├── startup.py               # Функции запуска приложения
│       ├── tcl_tk_loader.py         # Загрузка Tcl/Tk библиотек
│       └── main_functions.py        # Функции main()
│
├── 📁 PackageManager/               # (без изменений)
├── 📁 DockerManager/                # (без изменений)
├── 📁 CommitManager/                # (без изменений)
└── 📁 ... (остальные директории без изменений)
```

---

## 📝 Детальное распределение кода

### Core модули

#### `core/logging.py` (строки 129-822)
**Классы и функции:**
- `DualStreamLogger` (класс) - управление двумя потоками логирования
- `universal_print()` (функция) - универсальная функция вывода
- `_init_logging_early()` (функция) - ранняя инициализация логирования
- `create_default_logger()` (функция) - создание логгера по умолчанию

**Зависимости:**
- Стандартная библиотека: `os`, `sys`, `datetime`, `threading`, `queue`

#### `core/process_runner.py` (строки 10219-11087)
**Классы и функции:**
- `UniversalProcessRunner` (класс) - универсальный обработчик процессов
- `get_global_universal_runner()` (функция) - получение глобального экземпляра

**Зависимости:**
- `Code.core.logging` - DualStreamLogger
- Стандартная библиотека: `subprocess`, `threading`, `queue`

#### `core/progress.py` (строки 30600-31152)
**Классы и функции:**
- `UniversalProgressManager` (класс) - менеджер прогресса
- `get_global_progress_manager()` (функция)
- `set_global_progress_manager()` (функция)
- `set_process_state()` (функция) - установка состояния процесса
- `get_process_state()` (функция) - получение состояния процесса
- `is_process_running()` (функция) - проверка запущенности процесса

**Зависимости:**
- Стандартная библиотека: `threading`, `time`

#### `core/activity.py` (строки 2393-2473)
**Классы и функции:**
- `ActivityTracker` (класс) - отслеживание активности классов
- `track_class_activity()` (функция-декоратор) - декоратор для отслеживания активности

**Зависимости:**
- Стандартная библиотека: `time`, `collections`

#### `core/config.py` (строки 12-1071)
**Глобальные константы:**
- `APP_VERSION`, `APP_NAME`
- `ASTRAPACK_DIR_NAME`
- `COMPONENTS_CONFIG` - конфигурация всех компонентов
- `UPDATE_SOURCES_CONFIG` - конфигурация источников обновлений
- `GLOBAL_LOG_FILE`, `PROCESS_STATE`, `PROCESS_PAUSED`
- `CURRENT_PLATFORM`
- `TKINTER_AVAILABLE`
- `UPDATE_SOURCES_CONFIG`

**Зависимости:**
- Нет (только константы и словари)

---

### Handlers модули

#### `handlers/base.py` (строки 2600-4567)
**Классы:**
- `ComponentHandler` (ABC) - базовый абстрактный класс

**Методы:**
- `__init__()` - инициализация обработчика
- `_log()` - универсальное логирование
- `_get_source_dir()` - получение директории источника
- `_get_script_dir()` - получение директории скрипта
- `_resolve_single_file()` - разрешение одного файла из различных источников
- `_resolve_archive_path_with_dialog()` - разрешение пути архива через диалог
- `install()` (abstract) - установка компонента
- `uninstall()` (abstract) - удаление компонента
- `check_status()` (abstract) - проверка статуса компонента
- `get_category()` (abstract) - получение категории компонента

**Зависимости:**
- `Code.core.logging` - DualStreamLogger
- `Code.core.process_runner` - UniversalProcessRunner
- `Code.core.progress` - UniversalProgressManager
- `Code.utils.path_utils` - работа с путями

#### `handlers/wine.py` (строки 4568-5993)
**Классы:**
- `WinePackageHandler` - обработчик Wine пакетов (wine_astraregul, wine_9)
- `WineConfigHandler` - обработчик конфигурации Wine
- `WineEnvironmentHandler` - обработчик Wine окружения (WINEPREFIX)

**Зависимости:**
- `Code.handlers.base` - ComponentHandler
- `Code.utils.file_utils` - работа с файлами
- `Code.utils.component_utils` - утилиты компонентов

#### `handlers/winetricks.py` (строки 6960-7408)
**Классы:**
- `WinetricksHandler` - обработчик winetricks компонентов

**Зависимости:**
- `Code.handlers.base` - ComponentHandler
- `Code.managers.winetricks_manager` - WinetricksManager

#### `handlers/apt.py` (строки 7409-7662)
**Классы:**
- `AptPackageHandler` - обработчик APT пакетов Linux

**Зависимости:**
- `Code.handlers.base` - ComponentHandler

#### `handlers/application.py` (строки 7663-9568)
**Классы:**
- `WineApplicationHandler` - обработчик Wine приложений Windows
- `ApplicationHandler` - обработчик приложений (Astra.IDE, CONT-Designer)

**Зависимости:**
- `Code.handlers.base` - ComponentHandler
- `Code.managers.wine_instance` - WineApplicationInstanceManager

#### `handlers/shortcut.py` (строки 9569-10003)
**Классы:**
- `DesktopShortcutHandler` - обработчик ярлыков рабочего стола

**Зависимости:**
- `Code.handlers.base` - ComponentHandler

#### `handlers/system.py` (строки 5075-5573)
**Классы:**
- `SystemConfigHandler` - обработчик системных настроек

**Зависимости:**
- `Code.handlers.base` - ComponentHandler

---

### Managers модули

#### `managers/component_status.py` (строки 12559-12776)
**Классы:**
- `ComponentStatusManager` - менеджер статусов компонентов

**Методы:**
- `get_all_components_status()` - получение статусов всех компонентов
- `get_component_status()` - получение статуса компонента
- `check_component_status()` - проверка статуса компонента
- `get_missing_components()` - получение отсутствующих компонентов
- `is_fully_installed()` - проверка полной установки

**Зависимости:**
- `Code.core.logging` - логирование
- `Code.handlers.*` - все обработчики компонентов

#### `managers/component_installer.py` (строки 12777-13939)
**Классы:**
- `ComponentInstaller` - координатор установки/удаления компонентов

**Методы:**
- `install_components()` - установка компонентов
- `uninstall_components()` - удаление компонентов
- `_install_single_component()` - установка одного компонента
- `_uninstall_single_component()` - удаление одного компонента

**Зависимости:**
- `Code.managers.component_status` - ComponentStatusManager
- `Code.handlers.*` - все обработчики компонентов
- `Code.core.progress` - UniversalProgressManager

#### `managers/wine_instance.py` (строки 2475-2599)
**Классы:**
- `WineApplicationInstanceManager` - менеджер экземпляров Wine приложений

**Методы:**
- `create_instance_id()` - создание ID экземпляра
- `get_or_create_instance()` - получение или создание экземпляра
- `get_instances_for_wineprefix()` - получение экземпляров для wineprefix
- `remove_instances_for_wineprefix()` - удаление экземпляров для wineprefix
- `get_instance_config()` - получение конфигурации экземпляра

**Зависимости:**
- `Code.core.config` - COMPONENTS_CONFIG
- Стандартная библиотека: `json`, `os`

#### `Code/managers/system_updater.py` (строки 31249-32254, 32255-34065)
**Классы:**
- `SystemUpdateParser` - парсер обновлений системы
- `SystemUpdater` - обновление Linux пакетов

**Зависимости:**
- `Code.core.process_runner` - UniversalProcessRunner
- `Code.core.logging` - DualStreamLogger
- `Code.utils.system_utils` - RepoChecker

#### `managers/winetricks_manager.py` (строки 11862-12558)
**Классы:**
- `WinetricksManager` - управление winetricks

**Зависимости:**
- `Code.core.process_runner` - UniversalProcessRunner
- `Code.core.logging` - логирование

---

### GUI модули

#### `gui/main_window.py` (строки 14064-30413)
**Классы:**
- `AutomationGUI` - основной класс GUI приложения

**Методы:**
- `__init__()` - инициализация GUI
- `create_widgets()` - создание всех виджетов
- `run()` - запуск главного цикла
- `load_settings()` - загрузка настроек
- `save_window_geometry()` - сохранение геометрии окна
- Методы управления состоянием кнопок
- Методы работы с таймерами

**Зависимости:**
- `Code.gui.tabs.*` - все вкладки
- `Code.gui.widgets.*` - виджеты
- `Code.core.*` - базовые системы
- `Code.managers.*` - менеджеры

#### `gui/widgets/tooltip.py` (строки 13940-14032)
**Классы:**
- `ToolTip` - всплывающие подсказки

**Зависимости:**
- Стандартная библиотека: `tkinter`

#### `gui/widgets/terminal_redirector.py` (строки 14033-14063)
**Классы:**
- `TerminalRedirector` - перенаправление sys.stdout/stderr

**Зависимости:**
- `Code.core.logging` - universal_print

#### `gui/tabs/main_tab.py` (строки 15954-16052)
**Функции:**
- `create_main_tab()` - создание вкладки "Обновление ОС"

**Зависимости:**
- `Code.gui.main_window` - AutomationGUI
- `Code.managers.system_updater` - SystemUpdater

#### `gui/tabs/repos_tab.py` (строки 16053-16162)
**Функции:**
- `create_repos_tab()` - создание вкладки "Репозитории"

**Зависимости:**
- `Code.gui.main_window` - AutomationGUI
- `Code.utils.system_utils` - RepoChecker

#### `gui/tabs/terminal_tab.py` (строки 16163-16810)
**Функции:**
- `create_terminal_tab()` - создание вкладки "Терминал"
- `create_terminal_control_panel()` - панель управления терминалом

**Зависимости:**
- `Code.gui.main_window` - AutomationGUI
- `Code.core.logging` - DualStreamLogger

#### `gui/tabs/wine_tab.py` (строки 16811-17095)
**Функции:**
- `create_wine_tab()` - создание вкладки "Установка Программ"

**Зависимости:**
- `Code.gui.main_window` - AutomationGUI
- `Code.managers.component_installer` - ComponentInstaller
- `Code.managers.component_status` - ComponentStatusManager

#### `gui/tabs/system_tab.py` (строки 17096-17392)
**Функции:**
- `create_system_info_tab()` - создание вкладки "О системе"

**Зависимости:**
- `Code.gui.main_window` - AutomationGUI
- `Code.utils.system_utils` - SystemStats

#### `gui/tabs/filesystem_tab.py` (строки 17393-21823)
**Функции:**
- `create_filesystem_monitor_tab()` - создание вкладки "Файловая система"

**Зависимости:**
- `Code.gui.main_window` - AutomationGUI
- `Code.monitoring.filesystem_monitor` - DirectoryMonitor

#### `gui/tabs/processes_tab.py` (строки 21824-22274)
**Функции:**
- `create_processes_monitor_tab()` - создание вкладки "Мониторинг"

**Зависимости:**
- `Code.gui.main_window` - AutomationGUI
- `Code.monitoring.process_monitor` - ProcessMonitor

#### `gui/tabs/packages_tab.py` (строки 22275-25964)
**Функции:**
- `create_packages_tab()` - создание вкладки "Пакеты"
- `create_update_process_subtab()` - подвкладка процесса обновления
- `create_installed_packages_subtab()` - подвкладка установленных пакетов
- `create_available_packages_subtab()` - подвкладка доступных пакетов
- Методы работы с пакетами

**Зависимости:**
- `Code.gui.main_window` - AutomationGUI
- `Code.managers.system_updater` - SystemUpdater

---

### Utils модули

#### `Code/utils/path_utils.py` (строки 93-127)
**Функции:**
- `_get_start_dir()` - получение стартовой директории бинарника/скрипта
- `START_DIR` (глобальная переменная)

**Зависимости:**
- Стандартная библиотека: `os`, `sys`, `platform`

#### `Code/utils/file_utils.py` (строки 1571-1906)
**Функции:**
- `extract_archive()` - извлечение архива с прогрессом

**Зависимости:**
- Стандартная библиотека: `tarfile`, `os`, `shutil`

#### `Code/utils/permission_utils.py` (строки 1437-1542)
**Функции:**
- `fix_permissions()` - исправление прав доступа к файлам
- `fix_permissions_async()` - асинхронное исправление прав

**Зависимости:**
- Стандартная библиотека: `os`, `stat`, `threading`

#### `Code/utils/component_utils.py` (строки 1543-2351)
**Функции:**
- `get_component_field()` - получение поля компонента
- `get_component_data()` - получение данных компонента
- `check_component_status()` - проверка статуса компонента
- `resolve_dependencies()` - разрешение зависимостей
- `resolve_dependencies_for_install()` - разрешение зависимостей для установки
- `resolve_dependencies_for_uninstall()` - разрешение зависимостей для удаления
- `validate_component_config()` - валидация конфигурации компонентов

**Зависимости:**
- `Code.core.config` - COMPONENTS_CONFIG
- Стандартная библиотека: `os`

#### `Code/utils/system_utils.py` (строки 11088-11520)
**Классы:**
- `RepoChecker` - проверка репозиториев
- `SystemStats` - анализ статистики системы

**Зависимости:**
- Стандартная библиотека: `subprocess`, `re`

#### `Code/utils/platform_utils.py` (строки 35300-35397)
**Функции:**
- `detect_astra_version()` - определение версии Astra Linux
- `_init_current_platform()` - инициализация текущей платформы
- `_is_astra_1_7()` - проверка Astra Linux 1.7
- `CURRENT_PLATFORM` (глобальная переменная)

**Зависимости:**
- Стандартная библиотека: `os`, `subprocess`, `platform`

#### `Code/utils/ntp_utils.py` (строки 33605-33775)
**Функции:**
- `_get_ntp_servers_list()` - получение списка NTP серверов
- `sync_system_time()` - синхронизация системного времени
- `sync_system_time_async()` - асинхронная синхронизация времени

**Зависимости:**
- Стандартная библиотека: `subprocess`, `threading`

#### `Code/utils/text_utils.py` (строки 1113-1436)
**Функции:**
- `get_source_description()` - получение описания источника
- `expand_user_path()` - расширение пути пользователя
- `_remove_emoji()` - удаление emoji из текста

**Зависимости:**
- Стандартная библиотека: `os`, `pwd`, `re`

---

### Monitoring модули

#### `monitoring/process_monitor.py` (строки 11521-11616)
**Классы:**
- `ProcessMonitor` - мониторинг процессов приложения

**Зависимости:**
- `Code.core.process_runner` - UniversalProcessRunner
- Опционально: `psutil`

#### `monitoring/installation_monitor.py` (строки 11617-11861)
**Классы:**
- `InstallationMonitor` - мониторинг установки

**Зависимости:**
- `Code.core.process_runner` - UniversalProcessRunner
- `Code.core.progress` - UniversalProgressManager

#### `monitoring/filesystem_monitor.py` (строки 34184-35139)
**Классы:**
- `DirectorySnapshot` - снимок состояния директории
- `DirectoryMonitor` - мониторинг изменений в директории

**Зависимости:**
- `Code.monitoring.filesystem_filter` - FilesystemFilter
- Стандартная библиотека: `os`, `time`

#### `monitoring/filesystem_filter.py` (строки 34106-34183)
**Классы:**
- `FilesystemFilter` - фильтр файловой системы

**Зависимости:**
- Стандартная библиотека: `fnmatch`, `os`

---

### Interactive модули

#### `interactive/handler.py` (строки 30454-30599)
**Классы:**
- `InteractiveHandler` - обработка интерактивных запросов

**Зависимости:**
- `Code.interactive.config` - InteractiveConfig
- `Code.core.process_runner` - UniversalProcessRunner

#### `interactive/config.py` (строки 10149-10218)
**Классы:**
- `InteractiveConfig` - конфигурация интерактивных запросов

**Зависимости:**
- Стандартная библиотека: `re`

#### `interactive/replay.py` (строки 10004-10148)
**Классы:**
- `LogReplaySimulator` - симулятор воспроизведения логов

**Зависимости:**
- `Code.interactive.config` - InteractiveConfig

---

### Updater модуль

#### `Code/updater/self_updater.py` (строки 35492-36767)
**Классы:**
- `SelfUpdater` - самообновление приложения

**Методы:**
- `check_for_updates()` - проверка обновлений
- `download_and_apply()` - загрузка и применение обновления
- `_check_source()` - проверка источника обновлений
- `_download_from_source()` - загрузка из источника
- `_apply_update()` - применение обновления

**Зависимости:**
- `Code.core.config` - APP_VERSION, UPDATE_SOURCES_CONFIG
- `Code.utils.text_utils` - get_source_description
- Стандартная библиотека: `urllib`, `shutil`, `os`

---

### Runtime модули

#### `runtime/startup.py` (строки 35140-35491)
**Функции:**
- `find_running_instance()` - поиск запущенного экземпляра программы
- `activate_existing_window()` - активация существующего окна
- `ensure_correct_binary_name()` - проверка и исправление имени бинарника
- `restart_with_path()` - перезапуск с новым путем

**Зависимости:**
- Стандартная библиотека: `os`, `subprocess`, `psutil`
- Опционально: `wmctrl`

#### `runtime/tcl_tk_loader.py` (строки 37026-37109)
**Функции:**
- `_load_tcl_tk_libraries()` - загрузка библиотек Tcl/Tk для PyInstaller

**Зависимости:**
- Стандартная библиотека: `os`, `ctypes`, `sys`

#### `runtime/main_functions.py` (строки 33776-34105)
**Функции:**
- `run_repo_checker()` - запуск проверки репозиториев
- `run_system_stats()` - запуск анализа статистики системы
- `run_interactive_handler()` - запуск обработчика интерактивных запросов
- `run_system_updater()` - запуск обновления системы
- `run_gui_monitor()` - запуск GUI мониторинга
- `cleanup_temp_files()` - очистка временных файлов

**Зависимости:**
- `Code.utils.system_utils` - RepoChecker, SystemStats
- `Code.interactive.handler` - InteractiveHandler
- `Code.managers.system_updater` - SystemUpdater
- `Code.gui.main_window` - AutomationGUI

---

### Точка входа

#### `FSA-AstraInstall.py` - Точка входа

**Содержимое:**
- Импорты всех необходимых модулей из папки `Code/`
- Функция `main()` - главная функция приложения
- Блок `if __name__ == '__main__':` - точка входа

**Пример импортов:**
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os

# Убеждаемся, что корневая директория проекта в sys.path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Импорты из Code.core
from Code.core import (
    APP_VERSION, APP_NAME,
    _init_logging_early,
    get_global_progress_manager
)

# Импорты из Code.runtime
from Code.runtime.startup import (
    find_running_instance,
    activate_existing_window,
    ensure_correct_binary_name
)

# Импорты из Code.gui
from Code.gui import AutomationGUI

# Импорты из Code.updater
from Code.updater.self_updater import SelfUpdater
```

**Размер:** ~200 строк (вместо 37,726)

---

## 🔄 Поэтапный план миграции

### Этап 0: Подготовка

#### Задачи:
1. ✅ Создать резервную копию проекта
2. ✅ Инициализировать git репозиторий (если еще не инициализирован)
3. ✅ Создать ветку для рефакторинга: `git checkout -b refactoring/modular-structure`
4. ✅ Подготовить структуру директорий:
   - Создать папку `Code/`
   - Создать все подпапки внутри `Code/` (core, handlers, managers, gui, utils, monitoring, interactive, updater, runtime)
   - Создать подпапки gui/widgets и gui/tabs
5. ✅ Создать все `__init__.py` файлы (пока пустые) во всех папках

#### Контрольная точка:
- ✅ Все директории созданы
- ✅ Все `__init__.py` файлы на месте
- ✅ Резервная копия создана

---

### Этап 1: Core модули

#### Задачи:
1. **`Code/core/config.py`**
   - Перенести все глобальные константы (строки 12-1071)
   - Создать `__init__.py` с экспортом констант
   - Обновить импорты в основном файле

2. **`Code/core/logging.py`**
   - Перенести `DualStreamLogger` (строки 129-822)
   - Перенести `universal_print()`, `_init_logging_early()`, `create_default_logger()`
   - Обновить импорты в основном файле

3. **`Code/core/process_runner.py`**
   - Перенести `UniversalProcessRunner` (строки 10219-11087)
   - Перенести `get_global_universal_runner()`
   - Обновить импорты в основном файле

4. **`Code/core/progress.py`**
   - Перенести `UniversalProgressManager` (строки 30600-31152)
   - Перенести все функции управления прогрессом
   - Обновить импорты в основном файле

5. **`Code/core/activity.py`**
   - Перенести `ActivityTracker` (строки 2393-2473)
   - Перенести `track_class_activity()`
   - Обновить импорты в основном файле

#### Тестирование:
- ✅ Проверка импортов всех модулей
- ✅ Проверка работы `universal_print()`
- ✅ Проверка работы `UniversalProcessRunner`
- ✅ Запуск приложения в режиме скрипта
- ✅ Проверка сборки бинарника

#### Контрольная точка:
- ✅ Все core модули перенесены
- ✅ Все импорты обновлены
- ✅ Приложение запускается
- ✅ Бинарник собирается и работает

---

### Этап 2: Utils модули

#### Задачи:
1. **`Code/utils/path_utils.py`**
   - Перенести `_get_start_dir()`, `START_DIR` (строки 93-127)
   - Обновить импорты в основном файле

2. **`Code/utils/text_utils.py`**
   - Перенести `get_source_description()`, `expand_user_path()`, `_remove_emoji()` (строки 1113-1436)

3. **`Code/utils/permission_utils.py`**
   - Перенести `fix_permissions()`, `fix_permissions_async()` (строки 1437-1542)

4. **`Code/utils/component_utils.py`**
   - Перенести все функции работы с компонентами (строки 1543-2351)

5. **`Code/utils/file_utils.py`**
   - Перенести `extract_archive()` (строки 1571-1906)

6. **`Code/utils/system_utils.py`**
   - Перенести `RepoChecker`, `SystemStats` (строки 11088-11520)

7. **`Code/utils/platform_utils.py`**
   - Перенести функции определения платформы (строки 35300-35397)

8. **`Code/utils/ntp_utils.py`**
   - Перенести функции синхронизации времени (строки 33605-33775)

#### Тестирование:
- ✅ Проверка всех утилит
- ✅ Проверка работы с путями
- ✅ Проверка работы с компонентами
- ✅ Запуск приложения
- ✅ Проверка сборки бинарника

#### Контрольная точка:
- ✅ Все utils модули перенесены
- ✅ Все импорты обновлены
- ✅ Приложение запускается
- ✅ Бинарник собирается и работает

---

### Этап 3: Handlers модули

#### Задачи:
1. **`handlers/base.py`**
   - Перенести `ComponentHandler` (ABC) (строки 2600-4567)
   - Перенести общие методы: `_log()`, `_get_source_dir()`, `_resolve_single_file()` и т.д.

2. **`handlers/wine.py`**
   - Перенести `WinePackageHandler`, `WineConfigHandler`, `WineEnvironmentHandler` (строки 4568-5993)

3. **`handlers/winetricks.py`**
   - Перенести `WinetricksHandler` (строки 6960-7408)

4. **`handlers/apt.py`**
   - Перенести `AptPackageHandler` (строки 7409-7662)

5. **`handlers/application.py`**
   - Перенести `WineApplicationHandler`, `ApplicationHandler` (строки 7663-9568)

6. **`handlers/shortcut.py`**
   - Перенести `DesktopShortcutHandler` (строки 9569-10003)

7. **`handlers/system.py`**
   - Перенести `SystemConfigHandler` (строки 5075-5573)

#### Тестирование:
- ✅ Проверка установки каждого типа компонента
- ✅ Проверка удаления компонентов
- ✅ Проверка статусов компонентов
- ✅ Запуск приложения
- ✅ Проверка сборки бинарника

#### Контрольная точка:
- ✅ Все handlers модули перенесены
- ✅ Все импорты обновлены
- ✅ Установка/удаление компонентов работает
- ✅ Бинарник собирается и работает

---

### Этап 4: Managers модули

#### Задачи:
1. **`managers/wine_instance.py`**
   - Перенести `WineApplicationInstanceManager` (строки 2475-2599)

2. **`managers/component_status.py`**
   - Перенести `ComponentStatusManager` (строки 12559-12776)

3. **`managers/component_installer.py`**
   - Перенести `ComponentInstaller` (строки 12777-13939)

4. **`managers/winetricks_manager.py`**
   - Перенести `WinetricksManager` (строки 11862-12558)

5. **`Code/managers/system_updater.py`**
   - Перенести `SystemUpdateParser`, `SystemUpdater` (строки 31249-34065)

#### Тестирование:
- ✅ Проверка работы всех менеджеров
- ✅ Проверка установки компонентов через ComponentInstaller
- ✅ Проверка обновления системы
- ✅ Запуск приложения
- ✅ Проверка сборки бинарника

#### Контрольная точка:
- ✅ Все managers модули перенесены
- ✅ Все импорты обновлены
- ✅ Менеджеры работают корректно
- ✅ Бинарник собирается и работает

---

### Этап 5: Monitoring модули

#### Задачи:
1. **`monitoring/filesystem_filter.py`**
   - Перенести `FilesystemFilter` (строки 34106-34183)

2. **`monitoring/filesystem_monitor.py`**
   - Перенести `DirectorySnapshot`, `DirectoryMonitor` (строки 34184-35139)

3. **`monitoring/process_monitor.py`**
   - Перенести `ProcessMonitor` (строки 11521-11616)

4. **`monitoring/installation_monitor.py`**
   - Перенести `InstallationMonitor` (строки 11617-11861)

#### Тестирование:
- ✅ Проверка мониторинга файловой системы
- ✅ Проверка мониторинга процессов
- ✅ Проверка мониторинга установки
- ✅ Запуск приложения
- ✅ Проверка сборки бинарника

#### Контрольная точка:
- ✅ Все monitoring модули перенесены
- ✅ Все импорты обновлены
- ✅ Мониторинг работает корректно
- ✅ Бинарник собирается и работает

---

### Этап 6: Interactive модули

#### Задачи:
1. **`interactive/config.py`**
   - Перенести `InteractiveConfig` (строки 10149-10218)

2. **`interactive/replay.py`**
   - Перенести `LogReplaySimulator` (строки 10004-10148)

3. **`interactive/handler.py`**
   - Перенести `InteractiveHandler` (строки 30454-30599)

#### Тестирование:
- ✅ Проверка обработки интерактивных запросов
- ✅ Проверка симуляции логов
- ✅ Запуск приложения
- ✅ Проверка сборки бинарника

#### Контрольная точка:
- ✅ Все interactive модули перенесены
- ✅ Все импорты обновлены
- ✅ Интерактивные системы работают
- ✅ Бинарник собирается и работает

---

### Этап 7: Updater модуль

#### Задачи:
1. **`Code/updater/self_updater.py`**
   - Перенести `SelfUpdater` (строки 35492-36767)

#### Тестирование:
- ✅ Проверка проверки обновлений
- ✅ Проверка загрузки обновлений (в тестовом режиме)
- ✅ Запуск приложения
- ✅ Проверка сборки бинарника

#### Контрольная точка:
- ✅ Updater модуль перенесен
- ✅ Все импорты обновлены
- ✅ Система обновлений работает
- ✅ Бинарник собирается и работает

---

### Этап 8: Runtime модули

#### Задачи:
1. **`runtime/startup.py`**
   - Перенести функции запуска (строки 35140-35491)

2. **`runtime/tcl_tk_loader.py`**
   - Перенести загрузку Tcl/Tk (строки 37026-37109)

3. **`runtime/main_functions.py`**
   - Перенести функции main() (строки 33776-34105)

#### Тестирование:
- ✅ Проверка запуска приложения
- ✅ Проверка загрузки Tcl/Tk для бинарника
- ✅ Запуск приложения
- ✅ Проверка сборки бинарника

#### Контрольная точка:
- ✅ Все runtime модули перенесены
- ✅ Все импорты обновлены
- ✅ Приложение запускается корректно
- ✅ Бинарник собирается и работает

---

### Этап 9: GUI модули - часть 1 (Widgets)

#### Задачи:
1. **`gui/widgets/tooltip.py`**
   - Перенести `ToolTip` (строки 13940-14032)

2. **`gui/widgets/terminal_redirector.py`**
   - Перенести `TerminalRedirector` (строки 14033-14063)

#### Тестирование:
- ✅ Проверка работы подсказок
- ✅ Проверка перенаправления терминала
- ✅ Запуск приложения
- ✅ Проверка сборки бинарника

#### Контрольная точка:
- ✅ Все widgets модули перенесены
- ✅ Все импорты обновлены
- ✅ Виджеты работают корректно
- ✅ Бинарник собирается и работает

---

### Этап 10: GUI модули - часть 2 (Tabs)

#### Задачи:
1. **`gui/tabs/main_tab.py`**
   - Перенести создание вкладки "Обновление ОС" (строки 15954-16052)

2. **`gui/tabs/repos_tab.py`**
   - Перенести создание вкладки "Репозитории" (строки 16053-16162)

3. **`gui/tabs/terminal_tab.py`**
   - Перенести создание вкладки "Терминал" (строки 16163-16810)

4. **`gui/tabs/wine_tab.py`**
   - Перенести создание вкладки "Установка Программ" (строки 16811-17095)

5. **`gui/tabs/system_tab.py`**
   - Перенести создание вкладки "О системе" (строки 17096-17392)

6. **`gui/tabs/filesystem_tab.py`**
   - Перенести создание вкладки "Файловая система" (строки 17393-21823)

7. **`gui/tabs/processes_tab.py`**
   - Перенести создание вкладки "Мониторинг" (строки 21824-22274)

8. **`gui/tabs/packages_tab.py`**
   - Перенести создание вкладки "Пакеты" (строки 22275-25964)

#### Тестирование:
- ✅ Проверка каждой вкладки отдельно
- ✅ Проверка переключения между вкладками
- ✅ Проверка всех функций в каждой вкладке
- ✅ Запуск приложения
- ✅ Проверка сборки бинарника

#### Контрольная точка:
- ✅ Все tabs модули перенесены
- ✅ Все импорты обновлены
- ✅ Все вкладки работают корректно
- ✅ Бинарник собирается и работает

---

### Этап 11: GUI модули - часть 3 (Main Window)

#### Задачи:
1. **`gui/main_window.py`**
   - Перенести `AutomationGUI` (строки 14064-30413)
   - Разбить большой класс на логические методы
   - Обновить все вызовы вкладок на импорты из модулей

#### Тестирование:
- ✅ Проверка создания главного окна
- ✅ Проверка всех методов GUI
- ✅ Проверка работы всех вкладок
- ✅ Запуск приложения
- ✅ Проверка сборки бинарника

#### Контрольная точка:
- ✅ Main window модуль перенесен
- ✅ Все импорты обновлены
- ✅ GUI работает полностью
- ✅ Бинарник собирается и работает

---

### Этап 12: Финальный этап - Точка входа

#### Задачи:
1. **`FSA-AstraInstall.py`**
   - Обновить все импорты
   - Оставить только функцию `main()` и блок `if __name__ == '__main__':`
   - Удалить весь перенесенный код
   - Проверить, что файл стал ~200 строк

#### Тестирование:
- ✅ Полное функциональное тестирование
- ✅ Проверка всех функций приложения
- ✅ Проверка работы в режиме скрипта
- ✅ Проверка сборки бинарника
- ✅ Проверка работы бинарника на целевых платформах

#### Контрольная точка:
- ✅ Файл FSA-AstraInstall.py обновлен
- ✅ Размер файла ~200 строк
- ✅ Все функции работают
- ✅ Бинарник собирается и работает на всех платформах

---

### Этап 13: Очистка и оптимизация

#### Задачи:
1. Удалить неиспользуемые импорты из всех модулей
2. Оптимизировать `__init__.py` файлы
3. Проверить все циклические импорты
4. Добавить docstrings в новые модули
5. Проверить соответствие PEP 8

#### Тестирование:
- ✅ Проверка отсутствия неиспользуемых импортов
- ✅ Проверка отсутствия циклических импортов
- ✅ Проверка работы приложения
- ✅ Проверка сборки бинарника

#### Контрольная точка:
- ✅ Код очищен и оптимизирован
- ✅ Нет циклических импортов
- ✅ Все работает корректно
- ✅ Бинарник собирается и работает

---

## ✅ Проверка работоспособности

### Тесты на каждом этапе

#### Базовые тесты:
1. **Импорты**
   ```bash
   python3 -c "from Code.core import *; print('OK')"
   ```

2. **Запуск скрипта**
   ```bash
   python3 FSA-AstraInstall.py --help
   ```

3. **Запуск GUI (если доступен)**
   ```bash
   python3 FSA-AstraInstall.py
   ```

4. **Синтаксис Python**
   ```bash
   python3 -m py_compile FSA-AstraInstall.py
   python3 -m py_compile Code/core/*.py
   python3 -m py_compile Code/handlers/*.py
   python3 -m py_compile Code/managers/*.py
   python3 -m py_compile Code/gui/*.py
   python3 -m py_compile Code/utils/*.py
   # ... и т.д.
   ```

#### Функциональные тесты:
1. **Обновление системы** - проверка вкладки "Обновление ОС"
2. **Установка компонентов** - проверка установки Wine, winetricks
3. **Удаление компонентов** - проверка удаления компонентов
4. **Мониторинг** - проверка всех вкладок мониторинга
5. **Репозитории** - проверка работы с репозиториями
6. **Пакеты** - проверка работы с пакетами

#### Тесты сборки:
1. **Сборка бинарника**
   ```bash
   python3 -m DockerManager.cli --project FSA-AstraInstall --platform astra-1.8
   ```

2. **Проверка размера бинарника**
   - Ожидаемый размер: 13-16 MB

3. **Запуск бинарника**
   ```bash
   ./FSA-AstraInstall-1-8 --help
   ```

---

## 📦 Влияние на сборку бинарника

### Текущий процесс сборки

1. **PyInstaller onefile** - упаковывает один файл `FSA-AstraInstall.py`
2. **Результат** - автономный бинарник 13-16 MB

### После рефакторинга

#### Преимущества:
- ✅ **Кэширование** - PyInstaller кэширует изменения отдельных модулей
- ✅ **Инкрементальные сборки** - пересборка только измененных модулей
- ✅ **Отладка** - проще локализовать проблемы в конкретном модуле

#### Возможные проблемы:
- ⚠️ **Скрытые импорты** - PyInstaller может пропустить динамические импорты
- **Решение:** Использовать `--hidden-import` в .spec файле

#### Рекомендации для PyInstaller:

**Создать `.spec` файл:**
```python
# FSA-AstraInstall.spec
a = Analysis(
    ['FSA-AstraInstall.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('AstraPack', 'AstraPack'),
        ('Icons', 'Icons'),
    ],
    hiddenimports=[
        # Core
        'Code.core.logging',
        'Code.core.process_runner',
        'Code.core.progress',
        'Code.core.activity',
        'Code.core.config',
        # Handlers
        'Code.handlers.base',
        'Code.handlers.wine',
        'Code.handlers.winetricks',
        'Code.handlers.apt',
        'Code.handlers.application',
        'Code.handlers.shortcut',
        'Code.handlers.system',
        # Managers
        'Code.managers.component_status',
        'Code.managers.component_installer',
        'Code.managers.wine_instance',
        'Code.managers.system_updater',
        'Code.managers.winetricks_manager',
        # GUI
        'Code.gui.main_window',
        'Code.gui.widgets.tooltip',
        'Code.gui.widgets.terminal_redirector',
        'Code.gui.tabs.main_tab',
        'Code.gui.tabs.repos_tab',
        'Code.gui.tabs.terminal_tab',
        'Code.gui.tabs.wine_tab',
        'Code.gui.tabs.system_tab',
        'Code.gui.tabs.filesystem_tab',
        'Code.gui.tabs.processes_tab',
        'Code.gui.tabs.packages_tab',
        # Utils
        'Code.utils.path_utils',
        'Code.utils.file_utils',
        'Code.utils.permission_utils',
        'Code.utils.component_utils',
        'Code.utils.system_utils',
        'Code.utils.platform_utils',
        'Code.utils.ntp_utils',
        'Code.utils.text_utils',
        # Monitoring
        'Code.monitoring.process_monitor',
        'Code.monitoring.installation_monitor',
        'Code.monitoring.filesystem_monitor',
        'Code.monitoring.filesystem_filter',
        # Interactive
        'Code.interactive.handler',
        'Code.interactive.config',
        'Code.interactive.replay',
        # Updater
        'Code.updater.self_updater',
        # Runtime
        'Code.runtime.startup',
        'Code.runtime.tcl_tk_loader',
        'Code.runtime.main_functions',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='FSA-AstraInstall',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
```

#### Размер бинарника:

| Параметр | До рефакторинга | После рефакторинга |
|----------|-----------------|-------------------|
| **Размер Python файла** | ~37,726 строк | ~37,900 строк (распределено) |
| **Размер бинарника** | 13-16 MB | 13-16 MB (примерно) |
| **Время сборки (полная)** | ~5-10 минут | ~5-10 минут |
| **Время сборки (инкрементальная)** | ~5-10 минут | ~1-2 минуты (только измененные модули) |

---

## ⚠️ Риски и митигация

### Риск 1: Циклические импорты

**Описание:** Модули могут импортировать друг друга циклически, что вызовет ошибки.

**Вероятность:** Средняя

**Митигация:**
- Четкое определение зависимостей на этапе планирования
- Использование отложенных импортов (lazy imports) где необходимо
- Проверка циклических импортов на каждом этапе

**План действий при обнаружении:**
1. Определить цикл зависимостей
2. Вынести общие зависимости в отдельный модуль
3. Использовать отложенные импорты

---

### Риск 2: Нарушение работы приложения

**Описание:** После рефакторинга приложение может перестать работать.

**Вероятность:** Низкая (при соблюдении плана)

**Митигация:**
- Тестирование на каждом этапе
- Сохранение резервной копии
- Использование git для отслеживания изменений
- Откат к предыдущему этапу при проблемах

**План действий при обнаружении:**
1. Определить этап, на котором возникла проблема
2. Откатиться к предыдущему рабочему состоянию
3. Исправить проблему
4. Повторить тесты

---

### Риск 3: Проблемы со сборкой бинарника

**Описание:** PyInstaller может не найти все модули после рефакторинга.

**Вероятность:** Средняя

**Митигация:**
- Использование `.spec` файла с явными `hiddenimports`
- Тестирование сборки на каждом этапе
- Проверка размера и содержимого бинарника

**План действий при обнаружении:**
1. Проверить `.spec` файл на наличие всех модулей
2. Добавить отсутствующие модули в `hiddenimports`
3. Пересобрать бинарник
4. Проверить работу

---

### Риск 4: Увеличение размера бинарника

**Описание:** Размер бинарника может увеличиться из-за дублирования кода.

**Вероятность:** Низкая

**Митигация:**
- Проверка размера бинарника на каждом этапе
- Оптимизация импортов
- Использование `--exclude-module` для ненужных модулей

**План действий при обнаружении:**
1. Определить причину увеличения размера
2. Исключить ненужные модули
3. Оптимизировать импорты

---

### Риск 5: Проблемы с производительностью

**Описание:** Модульная структура может замедлить запуск приложения.

**Вероятность:** Очень низкая

**Митигация:**
- Использование отложенных импортов для тяжелых модулей
- Профилирование времени запуска
- Сравнение производительности до и после рефакторинга

**План действий при обнаружении:**
1. Измерить время запуска
2. Определить узкие места
3. Оптимизировать импорты
4. Использовать отложенные импорты

---

## 🎯 Контрольные точки

### Критические контрольные точки (обязательные)

1. **После Этапа 1 (Core модули)**
   - ✅ Приложение запускается
   - ✅ Логирование работает
   - ✅ Бинарник собирается

2. **После Этапа 3 (Handlers модули)**
   - ✅ Установка компонентов работает
   - ✅ Удаление компонентов работает
   - ✅ Проверка статусов работает

3. **После Этапа 10 (GUI Tabs)**
   - ✅ Все вкладки GUI работают
   - ✅ Переключение между вкладками работает

4. **После Этапа 12 (Финальный этап)**
   - ✅ Все функции работают
   - ✅ Бинарник работает на всех платформах
   - ✅ Размер файла FSA-AstraInstall.py ~200 строк

### Важные контрольные точки (рекомендуемые)

1. **После каждого этапа**
   - ✅ Синтаксис Python корректен
   - ✅ Импорты работают
   - ✅ Приложение запускается (хотя бы частично)

2. **После каждого этапа**
   - ✅ Коммит в git с описанием изменений

---

## 📅 Временные оценки

### Общая оценка времени

| Этап | Название | Время | Приоритет |
|------|----------|-------|-----------|
| 0 | Подготовка | 1 день | Высокий |
| 1 | Core модули | 2-3 дня | Высокий |
| 2 | Utils модули | 2 дня | Высокий |
| 3 | Handlers модули | 3-4 дня | Высокий |
| 4 | Managers модули | 2-3 дня | Высокий |
| 5 | Monitoring модули | 1-2 дня | Средний |
| 6 | Interactive модули | 1 день | Средний |
| 7 | Updater модуль | 1 день | Средний |
| 8 | Runtime модули | 1 день | Высокий |
| 9 | GUI Widgets | 1 день | Высокий |
| 10 | GUI Tabs | 3-4 дня | Высокий |
| 11 | GUI Main Window | 2-3 дня | Высокий |
| 12 | Финальный этап | 1 день | Высокий |
| 13 | Очистка и оптимизация | 1-2 дня | Низкий |
| **ИТОГО** | | **22-30 дней** | |

### Ускорение процесса

- ✅ **Параллельная работа** - можно работать над разными модулями одновременно (после Этапа 1)
- ✅ **Автоматизация** - использование скриптов для проверки импортов
- ✅ **Тестирование** - быстрые проверки на каждом этапе

---

## 📚 Дополнительные материалы

### Полезные команды

#### Проверка синтаксиса всех Python файлов:
```bash
find . -name "*.py" -exec python3 -m py_compile {} \;
```

#### Проверка импортов:
```bash
python3 -c "from Code.core import *; print('Core OK')"
python3 -c "from Code.handlers import *; print('Handlers OK')"
# ... и т.д.
```

#### Поиск циклических импортов:
```bash
python3 -c "import sys; sys.path.insert(0, '.'); from Code.core import *"
```

#### Статистика кода:
```bash
find . -name "*.py" -exec wc -l {} + | tail -1
```

---

## ✅ Заключение

Этот план обеспечивает:

1. **Постепенную миграцию** - разбиение на 13 этапов с проверками
2. **Сохранение функциональности** - весь существующий функционал сохраняется
3. **Тестирование на каждом этапе** - быстрая локализация проблем
4. **Гибкость** - возможность отката на любом этапе
5. **Документирование** - четкое описание каждого этапа

**Следующие шаги:**
1. Просмотреть и утвердить план
2. Создать ветку для рефакторинга
3. Начать с Этапа 0 (Подготовка)

---

**Дата создания:** 2025.12.23  
**Авторы:** @FoksSegr & AI Assistant (@LLM)  
**Версия документа:** 1.0.0
