# План модульного рефакторинга FSA-AstraInstall

**Версия документа:** 1.6.0  
**Дата создания:** 2025.12.23  
**Дата обновления:** 2026.01.01  
**Проект:** FSA-AstraInstall  
**Компания:** ООО "НПА Вира-Реалтайм"  
**Текущая версия проекта:** V3.7.211 (2025.12.31)  
**Статус:** 📋 ПЛАН (ОБНОВЛЕН)  
**Авторы:** @FoksSegr & AI Assistant (@LLM)  
**Изменения v1.1.0:** Добавлены пропущенные компоненты (CredentialManager, SizeManager, process_utils), обновлены все номера строк согласно актуальному коду (43,342 строки)  
**Изменения v1.2.0:** Добавлен Этап 15 - обновление DockerManager и процесса сборки бинарников для работы с модульной структурой  
**Изменения v1.3.0:** Добавлен Этап 1 - обновление COMMIT_RULES.md для работы с модульной структурой (критически важно, выполняется до начала миграции)  
**Изменения v1.4.0:** Переработан подход к рефакторингу - постепенное уменьшение основного файла с сборкой бинарника на каждом этапе. Добавлен Этап 0 - перенос исходного файла в Code/Run/. Обновление DockerManager перенесено на Этап 2 для возможности сборки бинарников с самого начала рефакторинга  
**Изменения v1.5.0:** КРИТИЧЕСКОЕ ИЗМЕНЕНИЕ - исходный файл `FSA-AstraInstall.py` в корне проекта НЕ ТРОГАЕТСЯ. Вся работа по рефакторингу ведется с копией `Code/Run/FSA-AstraInstall.py`. Это обеспечивает полную независимость процессов: можно продолжать разработку по старой схеме параллельно с рефакторингом. Создаются отдельные правила коммитов для рефакторинга  
**Изменения v1.6.0:** Уточнена структура проекта - рабочая копия размещается в `Code/Run/FSA-AstraInstall.py` (вместо `Code/legacy/`). После рефакторинга `Code/Run/FSA-AstraInstall.py` становится основным файлом для разработки и обновления версий проекта. Исходный файл в корне остается как резерв/история. Все файлы проекта находятся в `Code/` для сборки бинарника на Linux

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
10. [Этапы начала тестирования и сборки](#-этапы-начала-тестирования-и-сборки)
11. [Контрольные точки](#контрольные-точки)

---

## 🎯 Общая концепция

### Принципы рефакторинга

1. **Сохранение функциональности** - весь существующий функционал сохраняется без изменений
2. **Постепенная миграция** - разбиение на этапы с проверкой работоспособности на каждом этапе
3. **Постепенное уменьшение рабочей копии** - код выносится в модули, а в `Code/Run/FSA-AstraInstall.py` (рабочая копия) заменяется на импорты. Файл уменьшается: 43,342 → 40,000 → 35,000 → ... → 200 строк. **КРИТИЧЕСКИ ВАЖНО:** Исходный файл `FSA-AstraInstall.py` в корне проекта НЕ ТРОГАЕТСЯ и продолжает работать по старой схеме независимо
4. **Сборка бинарника на каждом этапе** - после каждого этапа переноса кода собирается бинарник и тестируется для гарантии работоспособности
5. **Независимость от исходного файла** - исходный файл `FSA-AstraInstall.py` в корне проекта НЕ ТРОГАЕТСЯ. Работа ведется с копией `Code/Run/FSA-AstraInstall.py`. Это позволяет продолжать разработку по старой схеме параллельно с рефакторингом
6. **Отдельные правила коммитов** - создаются отдельные правила коммитов для рефакторинга, чтобы процессы были полностью независимыми
6. **Минимизация изменений** - изменяются только пути импортов и структура, логика кода остается неизменной
7. **Тестирование на каждом этапе** - после каждого этапа проверяется работа скрипта и сборка бинарника

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
| **Размер основного файла** | 43,342 строки кода |
| **Количество классов** | 36 классов |
| **Количество функций** | ~45 функций верхнего уровня |
| **Размер бинарника** | 13-16 MB |
| **Архитектура** | Монолитный файл |
| **Сборка** | PyInstaller onefile |

### Проблемы текущей структуры

1. **Монолитный файл** - 43,342 строки затрудняют навигацию
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

- ✅ Модульная структура из 50 файлов вместо 1 монолитного
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
├── 📄 FSA-AstraInstall.py          # ИСХОДНЫЙ ФАЙЛ - НЕ ТРОГАЕМ (43,342 строки, резерв/история)
│
├── 📁 Code/                         # Все модули приложения (независимая структура для рефакторинга)
│   │
│   ├── 📁 Run/                      # Папка для запуска проекта
│   │   └── FSA-AstraInstall.py      # РАБОЧАЯ КОПИЯ для рефакторинга (постепенно уменьшается: 43,342 → 200 строк)
│   │                                # ТОЧКА ВХОДА для модульной версии
│   │                                # После рефакторинга: основной файл для разработки и обновления версий
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
│   ├── 📁 gui/                      # Графический интерфейс (12 модулей, ~18,000 строк)
│   │   ├── __init__.py
│   │   ├── main_window.py           # AutomationGUI (основной класс)
│   │   ├── widgets/
│   │   │   ├── __init__.py
│   │   │   ├── tooltip.py           # ToolTip
│   │   │   ├── terminal_redirector.py # TerminalRedirector
│   │   │   └── size_manager.py      # SizeManager
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
│   ├── 📁 utils/                    # Вспомогательные утилиты (10 модулей, ~3,500 строк)
│   │   ├── __init__.py
│   │   ├── path_utils.py            # Работа с путями
│   │   ├── file_utils.py            # Работа с файлами/архивами
│   │   ├── permission_utils.py      # Управление правами доступа
│   │   ├── component_utils.py       # Утилиты для компонентов
│   │   ├── system_utils.py          # SystemStats, RepoChecker
│   │   ├── platform_utils.py        # Определение платформы
│   │   ├── ntp_utils.py             # Синхронизация времени NTP
│   │   ├── text_utils.py            # Текстовые утилиты
│   │   ├── process_utils.py         # Утилиты для работы с процессами
│   │   └── security_utils.py        # CredentialManager, безопасность
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
├── 📁 DockerManager/                # (требует обновления на Этапе 2 - КРИТИЧЕСКИ ВАЖНО)
│   ├── scripts/docker_build.sh      # Обновить для работы с модулями (Этап 2)
│   ├── file_manager.py              # Обновить для загрузки Code/ (Этап 2)
│   └── config.py                    # Проверить и обновить при необходимости
├── 📁 CommitManager/                # (без изменений)
└── 📁 ... (остальные директории без изменений)
```

---

## 📝 Детальное распределение кода

### Core модули

#### `core/logging.py` (строки 921-1589)
**Классы и функции:**
- `DualStreamLogger` (класс) - управление двумя потоками логирования
- `universal_print()` (функция) - универсальная функция вывода (строки 1590-1673)
- `_init_logging_early()` (функция) - ранняя инициализация логирования (строки 1793-1931)
- `create_default_logger()` (функция) - создание логгера по умолчанию

**Зависимости:**
- Стандартная библиотека: `os`, `sys`, `datetime`, `threading`, `queue`

#### `core/process_runner.py` (строки 11942-12800)
**Классы и функции:**
- `UniversalProcessRunner` (класс) - универсальный обработчик процессов
- `get_global_universal_runner()` (функция) - получение глобального экземпляра

**Зависимости:**
- `Code.core.logging` - DualStreamLogger
- Стандартная библиотека: `subprocess`, `threading`, `queue`

#### `core/progress.py` (строки 36010-36519)
**Классы и функции:**
- `UniversalProgressManager` (класс) - менеджер прогресса
- `get_global_progress_manager()` (функция)
- `set_global_progress_manager()` (функция)
- `set_process_state()` (функция) - установка состояния процесса
- `get_process_state()` (функция) - получение состояния процесса
- `is_process_running()` (функция) - проверка запущенности процесса

**Зависимости:**
- Стандартная библиотека: `threading`, `time`

#### `core/activity.py` (строки 2861-2942)
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

#### `handlers/base.py` (строки 3068-6338)
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

#### `handlers/wine.py` (строки 6339-8707)
**Классы:**
- `WinePackageHandler` - обработчик Wine пакетов (wine_astraregul, wine_9)
- `WineConfigHandler` - обработчик конфигурации Wine
- `WineEnvironmentHandler` - обработчик Wine окружения (WINEPREFIX)

**Зависимости:**
- `Code.handlers.base` - ComponentHandler
- `Code.utils.file_utils` - работа с файлами
- `Code.utils.component_utils` - утилиты компонентов

#### `handlers/winetricks.py` (строки 8708-9155)
**Классы:**
- `WinetricksHandler` - обработчик winetricks компонентов

**Зависимости:**
- `Code.handlers.base` - ComponentHandler
- `Code.managers.winetricks_manager` - WinetricksManager

#### `handlers/apt.py` (строки 9156-9409)
**Классы:**
- `AptPackageHandler` - обработчик APT пакетов Linux

**Зависимости:**
- `Code.handlers.base` - ComponentHandler

#### `handlers/application.py` (строки 9410-10684)
**Классы:**
- `WineApplicationHandler` - обработчик Wine приложений Windows
- `ApplicationHandler` - обработчик приложений (Astra.IDE, CONT-Designer)

**Зависимости:**
- `Code.handlers.base` - ComponentHandler
- `Code.managers.wine_instance` - WineApplicationInstanceManager

#### `handlers/shortcut.py` (строки 11292-11726)
**Классы:**
- `DesktopShortcutHandler` - обработчик ярлыков рабочего стола

**Зависимости:**
- `Code.handlers.base` - ComponentHandler

#### `handlers/system.py` (строки 6845-7331)
**Классы:**
- `SystemConfigHandler` - обработчик системных настроек

**Зависимости:**
- `Code.handlers.base` - ComponentHandler

---

### Managers модули

#### `managers/component_status.py` (строки 14272-14489)
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

#### `managers/component_installer.py` (строки 14490-15651)
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

#### `managers/wine_instance.py` (строки 2943-3067)
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

#### `Code/managers/system_updater.py` (строки 36669-37789, 37790-39239)
**Классы:**
- `SystemUpdateParser` - парсер обновлений системы
- `SystemUpdater` - обновление Linux пакетов

**Зависимости:**
- `Code.core.process_runner` - UniversalProcessRunner
- `Code.core.logging` - DualStreamLogger
- `Code.utils.system_utils` - RepoChecker

#### `managers/winetricks_manager.py` (строки 13575-14271)
**Классы:**
- `WinetricksManager` - управление winetricks

**Зависимости:**
- `Code.core.process_runner` - UniversalProcessRunner
- `Code.core.logging` - логирование

---

### GUI модули

#### `gui/main_window.py` (строки 17796-35863)
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

#### `gui/widgets/tooltip.py` (строки 15652-15744)
**Классы:**
- `ToolTip` - всплывающие подсказки

**Зависимости:**
- Стандартная библиотека: `tkinter`

#### `gui/widgets/terminal_redirector.py` (строки 15745-15775)
**Классы:**
- `TerminalRedirector` - перенаправление sys.stdout/stderr

**Зависимости:**
- `Code.core.logging` - universal_print

#### `gui/widgets/size_manager.py` (строки 15776-17795)
**Классы:**
- `SizeManager` - универсальный менеджер размеров и настроек отображения

**Методы:**
- `__init__()` - инициализация менеджера размеров
- `setup_window()` - настройка окна с сохранением геометрии
- `setup_tree()` - настройка таблицы с сохранением ширины колонок
- `setup_paned()` - настройка панели с сохранением позиции разделителя
- `setup_notebook()` - настройка вкладок с сохранением активной вкладки
- `reset_window()` - сброс геометрии окна к значениям по умолчанию
- `reset_tree()` - сброс настроек таблицы к значениям по умолчанию
- `reset_paned()` - сброс позиции разделителя к значениям по умолчанию
- `reset_notebook()` - сброс активной вкладки к значениям по умолчанию
- `reset_element()` - универсальный метод сброса настроек элемента
- `reset_all()` - сброс всех настроек

**Зависимости:**
- Стандартная библиотека: `os`, `json`, `tkinter`

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

#### `Code/utils/path_utils.py` (строки 522-561)
**Функции:**
- `_get_start_dir()` - получение стартовой директории бинарника/скрипта
- `START_DIR` (глобальная переменная)

**Зависимости:**
- Стандартная библиотека: `os`, `sys`, `platform`

#### `Code/utils/file_utils.py` (строки 2048-2376)
**Функции:**
- `extract_archive()` - извлечение архива с прогрессом

**Зависимости:**
- Стандартная библиотека: `tarfile`, `os`, `shutil`

#### `Code/utils/permission_utils.py` (строки 1674-1994)
**Функции:**
- `fix_permissions()` - исправление прав доступа к файлам
- `fix_permissions_async()` - асинхронное исправление прав

**Зависимости:**
- Стандартная библиотека: `os`, `stat`, `threading`

#### `Code/utils/component_utils.py` (строки 2020-2820)
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

#### `Code/utils/system_utils.py` (строки 12801-13042)
**Классы:**
- `RepoChecker` - проверка репозиториев
- `SystemStats` - анализ статистики системы

**Зависимости:**
- Стандартная библиотека: `subprocess`, `re`

#### `Code/utils/platform_utils.py` (строки 40935-41072)
**Функции:**
- `detect_astra_version()` - определение версии Astra Linux
- `_init_current_platform()` - инициализация текущей платформы
- `_is_astra_1_7()` - проверка Astra Linux 1.7
- `CURRENT_PLATFORM` (глобальная переменная)

**Зависимости:**
- Стандартная библиотека: `os`, `subprocess`, `platform`

#### `Code/utils/ntp_utils.py` (строки 39240-39410)
**Функции:**
- `_get_ntp_servers_list()` - получение списка NTP серверов
- `sync_system_time()` - синхронизация системного времени
- `sync_system_time_async()` - асинхронная синхронизация времени

**Зависимости:**
- Стандартная библиотека: `subprocess`, `threading`

#### `Code/utils/text_utils.py` (строки 1932-1994)
**Функции:**
- `get_source_description()` - получение описания источника
- `expand_user_path()` - расширение пути пользователя
- `_remove_emoji()` - удаление emoji из текста

**Зависимости:**
- Стандартная библиотека: `os`, `pwd`, `re`

#### `Code/utils/process_utils.py` (строки 1756-1788)
**Функции:**
- `cleanup_temp_dirs()` - безопасная очистка временных директорий
- `terminate_process()` - безопасное завершение процесса с таймаутом

**Зависимости:**
- Стандартная библиотека: `os`, `shutil`, `subprocess`

#### `Code/utils/security_utils.py` (строки 562-905)
**Классы:**
- `CredentialManager` - управление учетными данными удаленных источников

**Методы:**
- `__init__()` - инициализация менеджера учетных данных
- `_ensure_credentials_file()` - создание файла учетных данных
- `_get_encryption_key()` - генерация ключа шифрования
- `encrypt_password()` - шифрование пароля
- `decrypt_password()` - расшифровка пароля
- `normalize_source_url()` - нормализация URL источника
- `load_credentials()` - загрузка всех учетных данных
- `save_credentials()` - сохранение всех учетных данных
- `get_credentials_for_source()` - получение учетных данных для источника
- `save_credentials_for_source()` - сохранение учетных данных для источника

**Функции:**
- `get_global_credential_manager()` - получение глобального экземпляра (строки 909-919)

**Зависимости:**
- Опционально: `cryptography` (Fernet, PBKDF2HMAC)
- Стандартная библиотека: `os`, `json`, `base64`, `hashlib`, `socket`, `urllib.parse`

**Примечание:** При отсутствии библиотеки `cryptography` используется fallback на base64 (небезопасно, но работает). Рекомендуется исправить в будущем.

---

### Monitoring модули

#### `monitoring/process_monitor.py` (строки 13234-13329)
**Классы:**
- `ProcessMonitor` - мониторинг процессов приложения

**Зависимости:**
- `Code.core.process_runner` - UniversalProcessRunner
- Опционально: `psutil`

#### `monitoring/installation_monitor.py` (строки 13330-13574)
**Классы:**
- `InstallationMonitor` - мониторинг установки

**Зависимости:**
- `Code.core.process_runner` - UniversalProcessRunner
- `Code.core.progress` - UniversalProgressManager

#### `monitoring/filesystem_monitor.py` (строки 39819-40774)
**Классы:**
- `DirectorySnapshot` - снимок состояния директории (строки 39819-40442)
- `DirectoryMonitor` - мониторинг изменений в директории (строки 40443-40774)

**Зависимости:**
- `Code.monitoring.filesystem_filter` - FilesystemFilter
- Стандартная библиотека: `os`, `time`

#### `monitoring/filesystem_filter.py` (строки 39741-39818)
**Классы:**
- `FilesystemFilter` - фильтр файловой системы

**Зависимости:**
- Стандартная библиотека: `fnmatch`, `os`

---

### Interactive модули

#### `interactive/handler.py` (строки 35864-36009)
**Классы:**
- `InteractiveHandler` - обработка интерактивных запросов

**Зависимости:**
- `Code.interactive.config` - InteractiveConfig
- `Code.core.process_runner` - UniversalProcessRunner

#### `interactive/config.py` (строки 11872-11941)
**Классы:**
- `InteractiveConfig` - конфигурация интерактивных запросов

**Зависимости:**
- Стандартная библиотека: `re`

#### `interactive/replay.py` (строки 11727-11871)
**Классы:**
- `LogReplaySimulator` - симулятор воспроизведения логов

**Зависимости:**
- `Code.interactive.config` - InteractiveConfig

---

### Updater модуль

#### `Code/updater/self_updater.py` (строки 41127-42396)
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

#### `runtime/startup.py` (строки 40775-41126)
**Функции:**
- `find_running_instance()` - поиск запущенного экземпляра программы
- `activate_existing_window()` - активация существующего окна
- `ensure_correct_binary_name()` - проверка и исправление имени бинарника
- `restart_with_path()` - перезапуск с новым путем

**Зависимости:**
- Стандартная библиотека: `os`, `subprocess`, `psutil`
- Опционально: `wmctrl`

#### `runtime/tcl_tk_loader.py` (строки 42655-42778)
**Функции:**
- `_load_tcl_tk_libraries()` - загрузка библиотек Tcl/Tk для PyInstaller

**Зависимости:**
- Стандартная библиотека: `os`, `ctypes`, `sys`

#### `runtime/main_functions.py` (строки 39411-39732)
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

#### `Code/Run/FSA-AstraInstall.py` - Точка входа модульной версии

**КРИТИЧЕСКИ ВАЖНО:** 
- Исходный файл `FSA-AstraInstall.py` в корне проекта НЕ ТРОГАЕТСЯ и продолжает работать по старой схеме
- Рабочая копия для рефакторинга находится в `Code/Run/FSA-AstraInstall.py`
- Эта копия постепенно уменьшается от 43,342 до ~200 строк
- После рефакторинга становится основным файлом для разработки и обновления версий

**Содержимое `Code/Run/FSA-AstraInstall.py`:**
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

**Размер:** ~200 строк (вместо 43,342)

---

## 🔄 Поэтапный план миграции

### Этап 0: Подготовка и создание рабочей копии

**КРИТИЧЕСКИ ВАЖНО:** Исходный файл `FSA-AstraInstall.py` в корне проекта НЕ ТРОГАЕМ. Он продолжает работать по старой схеме независимо от рефакторинга.

#### Задачи:
1. ✅ Создать резервную копию проекта
2. ✅ Инициализировать git репозиторий (если еще не инициализирован)
3. ✅ Создать ветку для рефакторинга: `git checkout -b refactoring/modular-structure`
4. ✅ Подготовить структуру директорий:
   - Создать папку `Code/` (независимая структура для рефакторинга)
   - Создать папку `Code/Run/` для рабочей копии файла запуска
   - Создать все подпапки внутри `Code/` (core, handlers, managers, gui, utils, monitoring, interactive, updater, runtime)
   - Создать подпапки gui/widgets и gui/tabs
5. ✅ Создать все `__init__.py` файлы (пока пустые) во всех папках
6. ✅ **Создать рабочую копию исходного файла в Code/Run/**
   - Скопировать `FSA-AstraInstall.py` (из корня) в `Code/Run/FSA-AstraInstall.py`
   - Это рабочая копия для рефакторинга (43,342 строки)
   - Исходный файл в корне остается нетронутым и продолжает работать
   - После рефакторинга `Code/Run/FSA-AstraInstall.py` станет основным файлом для разработки и обновления версий
7. ✅ **Создать отдельные правила коммитов для рефакторинга**
   - Создать `Code/COMMIT_RULES.md` или обновить основной `COMMIT_RULES.md` с условиями для работы с `Code/`
   - Убедиться, что коммиты рефакторинга не затрагивают исходный файл в корне

#### Контрольная точка:
- ✅ Все директории созданы (включая `Code/Run/`)
- ✅ Все `__init__.py` файлы на месте (включая `Code/Run/__init__.py`)
- ✅ Рабочая копия создана: `Code/Run/FSA-AstraInstall.py` (43,342 строки)
- ✅ Исходный файл `FSA-AstraInstall.py` в корне проекта НЕ ТРОНУТ (43,342 строки)
- ✅ Исходный файл продолжает работать по старой схеме независимо
- ✅ Отдельные правила коммитов для рефакторинга созданы
- ✅ Проверены зависимости между модулями (граф зависимостей)
- ✅ Выявлены и устранены потенциальные циклические зависимости

---

### Этап 1: Обновление COMMIT_RULES.md для модульной структуры

**КРИТИЧЕСКИ ВАЖНО:** Этот этап должен быть выполнен ДО начала миграции кода, так как коммиты будут создаваться с самого начала рефакторинга. Правила должны обеспечивать независимость рефакторинга от исходного файла в корне.

#### Задачи:

1. **Обновить шаг 3 (Определение измененных файлов)**
   - Добавить обработку файлов в `Code/` директории
   - Убедиться, что `Code/` не исключается из проверки изменений
   - **КРИТИЧНО:** Исходный `FSA-AstraInstall.py` в корне НЕ должен попадать в коммиты рефакторинга
   - Обновить проверку для `Code/Run/FSA-AstraInstall.py` (точка входа модульной версии, постепенно уменьшается)
   - Добавить проверку изменений в модулях `Code/**/*.py`
   - Убедиться, что изменения в корневом `FSA-AstraInstall.py` обрабатываются отдельно (для старой схемы разработки)

2. **Обновить шаг 5 (Определение текущей версии)**
   - Добавить поиск версий в файлах `Code/**/*.py`
   - Убедиться, что версии в модулях учитываются при определении `CURRENT_VERSION`
   - Обновить паттерн поиска: `head -20 "$file" | grep "V[0-9]\+\.[0-9]\+\.[0-9]\+"` должен работать для всех `.py` файлов в `Code/`

3. **Обновить шаг 7 (Сбор подробной информации об изменениях)**
   - Добавить обработку файлов в `Code/` для анализа изменений
   - Обновить проверку для `FSA-AstraInstall.py` (теперь это точка входа)
   - Добавить обработку новых модулей в `Code/` (как новых файлов)
   - Убедиться, что статистика изменений корректно собирается для модулей

4. **Обновить шаг 12 (Обновление дат релиза и версий)**
   - Добавить обновление дат/версий в файлах `Code/**/*.py`
   - Убедиться, что все модули в `Code/` получают обновленные даты релиза
   - Обновить версии в модулях при необходимости

5. **Обновить шаг 14 (Обновление версий проекта в ключевых файлах)**
   - Решить, нужно ли добавлять некоторые модули `Code/` в ключевые файлы
   - Возможно, добавить `Code/core/config.py` в ключевые файлы (содержит глобальные константы)
   - Обновить список ключевых файлов при необходимости

6. **Обновить шаг 17 (Добавление файлов в индекс)**
   - Убедиться, что `Code/` директория корректно добавляется в индекс
   - Обновить проверку для исключения `FSA-AstraInstall.py` (теперь это точка входа)
   - Добавить явную проверку наличия `Code/` перед добавлением в индекс

7. **Обновить примеры и комментарии**
   - Обновить все примеры путей к файлам для учета `Code/`
   - Добавить комментарии о работе с модульной структурой
   - Обновить документацию по обработке файлов

#### Детали изменений:

**Шаг 3 - Определение измененных файлов:**
```bash
# Добавить после определения CHANGED_FILES:
# Проверка изменений в Code/ директории
CODE_CHANGED=$(git diff --name-only HEAD | grep "^Code/" || echo "")
if [ ! -z "$CODE_CHANGED" ]; then
    CHANGED_FILES="$CHANGED_FILES $CODE_CHANGED"
fi
```

**Шаг 5 - Определение текущей версии:**
```bash
# Обновить поиск версий для включения Code/:
ALL_FILES_TO_CHECK="$CHANGED_FILES $NEW_FILES"
echo "$ALL_FILES_TO_CHECK" | tr ' ' '\n' | while read file; do
    [ ! -z "$file" ] || continue
    # Включаем файлы из Code/ в проверку версий
    if [[ "$file" =~ \.(py|sh|md)$ ]] && [ -f "$file" ]; then
        head -20 "$file" | grep "V[0-9]\+\.[0-9]\+\.[0-9]\+" >> "$VERSION_TEMP" 2>/dev/null || true
    fi
done
```

**Шаг 7 - Сбор информации об изменениях:**
```bash
# Добавить обработку файлов из Code/:
CHANGED_FILES_FOR_ANALYSIS=$(echo "$CHANGED_FILES" | tr ' ' '\n' | grep -v -E "^(FSA-AstraInstall-1-7|FSA-AstraInstall-1-8)$" | tr '\n' ' ')
echo "$CHANGED_FILES_FOR_ANALYSIS" | tr ' ' '\n' | while read file; do
    [ ! -z "$file" ] || continue
    # Обрабатываем файлы из Code/ так же, как и остальные
    if [[ "$file" =~ ^Code/ ]]; then
        # Для файлов из Code/ используем git diff
        git diff --stat HEAD "$file" > "$STAT_TEMP" 2>/dev/null || true
        git diff HEAD "$file" > "$DIFF_TEMP" 2>/dev/null
        # ... остальная обработка
    fi
done
```

**Шаг 12 - Обновление дат релиза и версий:**
```bash
# Убедиться, что файлы из Code/ обновляются:
ALL_FILES_TO_UPDATE="$CHANGED_FILES $NEW_FILES"
echo "$ALL_FILES_TO_UPDATE" | tr ' ' '\n' | while read file; do
    [ ! -z "$file" ] || continue
    # Включаем файлы из Code/ в обновление
    if [[ "$file" =~ \.(py|sh|md)$ ]] && [ -f "$file" ]; then
        # Обновление дат и версий для всех файлов, включая Code/
        sed -i '' "1,20s/([0-9]\{4\}\.[0-9]\{2\}\.[0-9]\{2\})/($TODAY)/g" "$file" 2>/dev/null || true
        # ... остальное обновление
    fi
done
```

**Шаг 17 - Добавление файлов в индекс:**
```bash
# Убедиться, что Code/ добавляется корректно:
# Проверка наличия Code/ директории
if [ -d "Code" ]; then
    # Добавляем Code/ если есть изменения
    git add Code/ 2>/dev/null && echo "✓ Добавлена директория Code/" || true
fi
```

#### Тестирование:
- ✅ Проверка определения измененных файлов в `Code/`
- ✅ Проверка поиска версий в модулях `Code/`
- ✅ Проверка обновления дат/версий в модулях
- ✅ Проверка добавления `Code/` в индекс
- ✅ Тестовый коммит с изменениями в `Code/` (после Этапа 2)

#### Контрольная точка:
- ✅ `COMMIT_RULES.md` обновлен для работы с модульной структурой
- ✅ Все шаги алгоритма учитывают `Code/` директорию
- ✅ Тестовый коммит успешно создан с изменениями в `Code/`
- ✅ Версии и даты корректно обновляются в модулях

---

### Этап 2: Обновление DockerManager и процесса сборки бинарников

**КРИТИЧЕСКИ ВАЖНО:** Этот этап должен быть выполнен ДО начала переноса кода, чтобы можно было собирать бинарники на каждом этапе рефакторинга.

#### Задачи:

1. **Создать `.spec` файл для PyInstaller**
   - Создать `FSA-AstraInstall.spec` в корне проекта
   - Настроить все `hiddenimports` для модулей из `Code/` (пока пустые, будут заполняться по мере переноса)
   - Настроить `datas` для включения `AstraPack/`, `Icons/`, `README.md`, `HELPME.md`
   - Настроить `binaries` для Tcl/Tk библиотек, wmctrl
   - Настроить `runtime_hooks` для предзагрузки libBLT
   - Использовать `.spec` файл вместо прямой команды `pyinstaller`

2. **Обновить `DockerManager/scripts/docker_build.sh`**
   - Убрать вызов `fix_future_imports.py` (больше не нужен для модульной структуры)
   - Изменить команду сборки: использовать `pyinstaller FSA-AstraInstall.spec` вместо прямой команды
   - Убедиться, что `Code/` директория доступна в контейнере
   - Обновить проверки наличия файлов (проверять `Code/` структуру)
   - Сохранить всю логику работы с Tcl/Tk библиотеками
   - Сохранить логику работы с иконками и документацией
   - Добавить поддержку работы с одним файлом (для начальных этапов рефакторинга)

3. **Обновить `DockerManager/file_manager.py`**
   - Добавить `Code/` в список обязательных директорий для загрузки
   - Убедиться, что все `__init__.py` файлы включены в загрузку
   - Обновить функцию `should_exclude()` для корректной обработки `Code/`
   - Добавить проверку наличия `Code/` директории перед загрузкой
   - Убедиться, что `Code/Run/` корректно загружается (содержит точку входа)

4. **Обновить `DockerManager/config.py` (если нужно)**
   - Проверить, нужно ли обновить конфигурацию проекта
   - **КРИТИЧНО:** Убедиться, что `input_file` указывает на `Code/Run/FSA-AstraInstall.py` (точка входа модульной версии)
   - Исходный файл в корне не используется для сборки модульной версии

5. **Обновить `DockerManager/scripts/fix_future_imports.py` (опционально)**
   - Либо удалить (если не нужен для модульной структуры)
   - Либо обновить для работы с модулями (если все еще нужен)
   - Проверить, нужен ли он вообще для модульной структуры

6. **Обновить Dockerfile (если нужно)**
   - Проверить, что все зависимости для модульной структуры установлены
   - Убедиться, что PyInstaller корректно работает с модулями

#### Детали изменений:

**`FSA-AstraInstall.spec` (новый файл в корне проекта):**
- Базовый `.spec` файл с поддержкой модулей из `Code/`
- **КРИТИЧНО:** Точка входа - `Code/Run/FSA-AstraInstall.py` (не исходный файл в корне)
- `hiddenimports` будут добавляться по мере переноса кода
- Начальная структура с поддержкой одного файла и модулей

**Изменения в `docker_build.sh`:**
- Убрать строки с `fix_future_imports.py`
- Изменить команду сборки: использовать `pyinstaller FSA-AstraInstall.spec`
- **КРИТИЧНО:** Убедиться, что `.spec` файл указывает на `Code/Run/FSA-AstraInstall.py` как точку входа
- Добавить проверку наличия `Code/` директории
- Добавить проверку наличия `Code/Run/FSA-AstraInstall.py` (рабочая копия)
- Добавить проверку наличия `FSA-AstraInstall.spec`

**Изменения в `file_manager.py`:**
- В функции `should_exclude()` добавить проверку: не исключать `Code/` директорию, включая `Code/Run/`
- Добавить явную проверку наличия `Code/` перед загрузкой
- Убедиться, что все поддиректории `Code/` копируются

#### Тестирование:
- ✅ Проверка загрузки `Code/` директории на сервер
- ✅ Проверка наличия всех `__init__.py` файлов
- ✅ **ТЕСТОВАЯ СБОРКА БИНАРНИКА** через DockerManager с использованием `.spec` файла (на текущем монолитном файле)
- ✅ Проверка работы бинарника на целевых платформах (astra-1.7, astra-1.8)
- ✅ Проверка размера бинарника (должен остаться 13-16 MB)

#### Контрольная точка:
- ✅ `.spec` файл создан и настроен
- ✅ `docker_build.sh` обновлен для работы с модулями и одним файлом
- ✅ `file_manager.py` обновлен для загрузки `Code/`
- ✅ Бинарник собирается успешно через DockerManager (на текущем монолитном файле)
- ✅ Бинарник работает на всех целевых платформах
- ✅ **Готовность к сборке бинарников на каждом этапе рефакторинга**

---

### Этап 3: Core модули

#### Задачи:
1. **`Code/core/config.py`**
   - Перенести все глобальные константы (строки 12-1071)
   - Создать `__init__.py` с экспортом констант
   - **Заменить код в `Code/Run/FSA-AstraInstall.py` на импорты** (удалить строки 12-1071, добавить `from Code.core.config import *`)

2. **`Code/core/logging.py`**
   - Перенести `DualStreamLogger` (строки 921-1589)
   - Перенести `universal_print()` (строки 1590-1673)
   - Перенести `_init_logging_early()` (строки 1793-1931)
   - Перенести `create_default_logger()` (если есть)
   - **Заменить код в `Code/Run/FSA-AstraInstall.py` на импорты** (удалить строки 921-1931, добавить импорты)

3. **`Code/core/process_runner.py`**
   - Перенести `UniversalProcessRunner` (строки 11942-12800)
   - Перенести `get_global_universal_runner()` (строки 12793-12800)
   - **Заменить код в `Code/Run/FSA-AstraInstall.py` на импорты** (удалить строки 11942-12800, добавить импорты)

4. **`Code/core/progress.py`**
   - Перенести `UniversalProgressManager` (строки 36010-36519)
   - Перенести `get_global_progress_manager()` (строки 36520-36529)
   - Перенести `set_global_progress_manager()` (строки 36530-36534)
   - Перенести `set_process_state()` (строки 36535-36561)
   - Перенести `get_process_state()` (строки 36562-36566)
   - Перенести `is_process_running()` (строки 36567-36571)
   - Перенести `_update_buttons_state()` (строки 36572-36668)
   - **Заменить код в `Code/Run/FSA-AstraInstall.py` на импорты** (удалить строки 36010-36668, добавить импорты)

5. **`Code/core/activity.py`**
   - Перенести `ActivityTracker` (строки 2861-2923)
   - Перенести `track_class_activity()` (строки 2924-2942)
   - **Заменить код в `Code/Run/FSA-AstraInstall.py` на импорты** (удалить строки 2861-2942, добавить импорты)

6. **Обновить `.spec` файл**
   - Добавить `hiddenimports` для всех core модулей:
     - `Code.core.config`
     - `Code.core.logging`
     - `Code.core.process_runner`
     - `Code.core.progress`
     - `Code.core.activity`

7. **Фиксация уменьшения размера файла**
   - Зафиксировать размер `Code/Run/FSA-AstraInstall.py` после замены кода на импорты
   - Ожидаемое уменьшение: ~43,342 → ~40,000 строк (примерно)

#### Тестирование:
- ✅ Проверка импортов всех модулей
- ✅ Проверка работы `universal_print()`
- ✅ Проверка работы `UniversalProcessRunner`
- ✅ Запуск приложения в режиме скрипта
- ✅ **СБОРКА БИНАРНИКА через DockerManager** с использованием `.spec` файла
- ✅ Проверка работы бинарника на целевых платформах
- ✅ Проверка размера бинарника (должен остаться 13-16 MB)

#### Контрольная точка:
- ✅ Все core модули перенесены
- ✅ Код в `Code/Run/FSA-AstraInstall.py` заменен на импорты
- ✅ Размер `Code/Run/FSA-AstraInstall.py` уменьшился (зафиксировать точное значение)
- ✅ Все импорты обновлены
- ✅ Приложение запускается
- ✅ Бинарник собирается через DockerManager и работает

---

### Этап 4: Utils модули

#### Задачи:
1. **`Code/utils/path_utils.py`**
   - Перенести `_get_start_dir()` (строки 522-561)
   - Перенести глобальную переменную `START_DIR` (если есть)
   - **Заменить код в `Code/Run/FSA-AstraInstall.py` на импорты** (удалить строки 522-561, добавить импорты)

2. **`Code/utils/text_utils.py`**
   - Перенести `get_source_description()`, `expand_user_path()`, `_remove_emoji()` (строки 1932-1994)
   - **Заменить код в `Code/Run/FSA-AstraInstall.py` на импорты** (удалить строки 1932-1994, добавить импорты)

3. **`Code/utils/permission_utils.py`**
   - Перенести `fix_permissions()`, `fix_permissions_async()` (строки 1674-1994)
   - **Заменить код в `Code/Run/FSA-AstraInstall.py` на импорты** (удалить строки 1674-1994, добавить импорты)

4. **`Code/utils/component_utils.py`**
   - Перенести все функции работы с компонентами (строки 2020-2820)
   - **Заменить код в `Code/Run/FSA-AstraInstall.py` на импорты** (удалить строки 2020-2820, добавить импорты)

5. **`Code/utils/file_utils.py`**
   - Перенести `extract_archive()` (строки 2048-2376)
   - **Заменить код в `Code/Run/FSA-AstraInstall.py` на импорты** (удалить строки 2048-2376, добавить импорты)

6. **`Code/utils/system_utils.py`**
   - Перенести `RepoChecker`, `SystemStats` (строки 12801-13042)
   - **Заменить код в `Code/Run/FSA-AstraInstall.py` на импорты** (удалить строки 12801-13042, добавить импорты)

7. **`Code/utils/platform_utils.py`**
   - Перенести функции определения платформы (строки 40935-41072)
   - **Заменить код в `Code/Run/FSA-AstraInstall.py` на импорты** (удалить строки 40935-41072, добавить импорты)

8. **`Code/utils/ntp_utils.py`**
   - Перенести функции синхронизации времени (строки 39240-39410)
   - **Заменить код в `Code/Run/FSA-AstraInstall.py` на импорты** (удалить строки 39240-39410, добавить импорты)

9. **`Code/utils/process_utils.py`**
   - Перенести `cleanup_temp_dirs()` (строки 1756-1768)
   - Перенести `terminate_process()` (строки 1769-1788)
   - **Заменить код в `Code/Run/FSA-AstraInstall.py` на импорты** (удалить строки 1756-1788, добавить импорты)

10. **`Code/utils/security_utils.py`**
    - Перенести `CredentialManager` (строки 562-905)
    - Перенести `get_global_credential_manager()` (строки 909-919)
    - **Заменить код в `Code/Run/FSA-AstraInstall.py` на импорты** (удалить строки 562-919, добавить импорты)

11. **Обновить `.spec` файл**
    - Добавить `hiddenimports` для всех utils модулей:
      - `Code.utils.path_utils`
      - `Code.utils.text_utils`
      - `Code.utils.permission_utils`
      - `Code.utils.component_utils`
      - `Code.utils.file_utils`
      - `Code.utils.system_utils`
      - `Code.utils.platform_utils`
      - `Code.utils.ntp_utils`
      - `Code.utils.process_utils`
      - `Code.utils.security_utils`

12. **Фиксация уменьшения размера файла**
    - Зафиксировать размер `Code/Run/FSA-AstraInstall.py` после замены кода на импорты
    - Ожидаемое уменьшение: ~40,000 → ~37,000 строк (примерно)

#### Тестирование:
- ✅ Проверка всех утилит
- ✅ Проверка работы с путями
- ✅ Проверка работы с компонентами
- ✅ Проверка работы `CredentialManager` (загрузка/сохранение учетных данных)
- ✅ Проверка работы `terminate_process()` и `cleanup_temp_dirs()`
- ✅ Запуск приложения
- ✅ **СБОРКА БИНАРНИКА через DockerManager** с использованием `.spec` файла
- ✅ Проверка работы бинарника на целевых платформах
- ✅ Проверка размера бинарника (должен остаться 13-16 MB)

#### Контрольная точка:
- ✅ Все utils модули перенесены
- ✅ Код в `Code/Run/FSA-AstraInstall.py` заменен на импорты
- ✅ Размер `Code/Run/FSA-AstraInstall.py` уменьшился (зафиксировать точное значение)
- ✅ Все импорты обновлены
- ✅ Приложение запускается
- ✅ Бинарник собирается через DockerManager и работает

---

### Этап 5: Handlers модули

#### Задачи:
1. **`Code/handlers/base.py`**
   - Перенести `ComponentHandler` (ABC) (строки 3068-6338)
   - Перенести общие методы: `_log()`, `_get_source_dir()`, `_resolve_single_file()` и т.д.
   - **Заменить код в `Code/Run/FSA-AstraInstall.py` на импорты** (удалить строки 3068-6338, добавить импорты)

2. **`Code/handlers/wine.py`**
   - Перенести `WinePackageHandler`, `WineConfigHandler`, `WineEnvironmentHandler` (строки 6339-8707)
   - **Заменить код в `Code/Run/FSA-AstraInstall.py` на импорты** (удалить строки 6339-8707, добавить импорты)

3. **`Code/handlers/winetricks.py`**
   - Перенести `WinetricksHandler` (строки 8708-9155)
   - **Заменить код в `Code/Run/FSA-AstraInstall.py` на импорты** (удалить строки 8708-9155, добавить импорты)

4. **`Code/handlers/apt.py`**
   - Перенести `AptPackageHandler` (строки 9156-9409)
   - **Заменить код в `Code/Run/FSA-AstraInstall.py` на импорты** (удалить строки 9156-9409, добавить импорты)

5. **`Code/handlers/application.py`**
   - Перенести `WineApplicationHandler`, `ApplicationHandler` (строки 9410-10684)
   - **Заменить код в `Code/Run/FSA-AstraInstall.py` на импорты** (удалить строки 9410-10684, добавить импорты)

6. **`Code/handlers/shortcut.py`**
   - Перенести `DesktopShortcutHandler` (строки 11292-11726)
   - **Заменить код в `Code/Run/FSA-AstraInstall.py` на импорты** (удалить строки 11292-11726, добавить импорты)

7. **`Code/handlers/system.py`**
   - Перенести `SystemConfigHandler` (строки 6845-7331)
   - **Заменить код в `Code/Run/FSA-AstraInstall.py` на импорты** (удалить строки 6845-7331, добавить импорты)

8. **Обновить `.spec` файл**
   - Добавить `hiddenimports` для всех handlers модулей:
     - `Code.handlers.base`
     - `Code.handlers.wine`
     - `Code.handlers.winetricks`
     - `Code.handlers.apt`
     - `Code.handlers.application`
     - `Code.handlers.shortcut`
     - `Code.handlers.system`

9. **Фиксация уменьшения размера файла**
   - Зафиксировать размер `Code/Run/FSA-AstraInstall.py` после замены кода на импорты
   - Ожидаемое уменьшение: ~37,000 → ~32,000 строк (примерно)

#### Тестирование:
- ✅ Проверка установки каждого типа компонента
- ✅ Проверка удаления компонентов
- ✅ Проверка статусов компонентов
- ✅ Запуск приложения
- ✅ **СБОРКА БИНАРНИКА через DockerManager** с использованием `.spec` файла
- ✅ Проверка работы бинарника на целевых платформах
- ✅ Проверка размера бинарника (должен остаться 13-16 MB)

#### Контрольная точка:
- ✅ Все handlers модули перенесены
- ✅ Код в `Code/Run/FSA-AstraInstall.py` заменен на импорты
- ✅ Размер `Code/Run/FSA-AstraInstall.py` уменьшился (зафиксировать точное значение)
- ✅ Все импорты обновлены
- ✅ Установка/удаление компонентов работает
- ✅ Бинарник собирается через DockerManager и работает

---

### Этап 6: Managers модули

#### Задачи:
1. **`Code/managers/wine_instance.py`**
   - Перенести `WineApplicationInstanceManager` (строки 2943-3067)
   - **Заменить код в `Code/Run/FSA-AstraInstall.py` на импорты** (удалить строки 2943-3067, добавить импорты)

2. **`Code/managers/component_status.py`**
   - Перенести `ComponentStatusManager` (строки 14272-14489)
   - **Заменить код в `Code/Run/FSA-AstraInstall.py` на импорты** (удалить строки 14272-14489, добавить импорты)

3. **`Code/managers/component_installer.py`**
   - Перенести `ComponentInstaller` (строки 14490-15651)
   - **Заменить код в `Code/Run/FSA-AstraInstall.py` на импорты** (удалить строки 14490-15651, добавить импорты)

4. **`Code/managers/winetricks_manager.py`**
   - Перенести `WinetricksManager` (строки 13575-14271)
   - **Заменить код в `Code/Run/FSA-AstraInstall.py` на импорты** (удалить строки 13575-14271, добавить импорты)

5. **`Code/managers/system_updater.py`**
   - Перенести `SystemUpdateParser` (строки 36669-37789)
   - Перенести `SystemUpdater` (строки 37790-39239)
   - **Заменить код в `Code/Run/FSA-AstraInstall.py` на импорты** (удалить строки 36669-39239, добавить импорты)

6. **Обновить `.spec` файл**
   - Добавить `hiddenimports` для всех managers модулей:
     - `Code.managers.wine_instance`
     - `Code.managers.component_status`
     - `Code.managers.component_installer`
     - `Code.managers.winetricks_manager`
     - `Code.managers.system_updater`

7. **Фиксация уменьшения размера файла**
   - Зафиксировать размер `Code/Run/FSA-AstraInstall.py` после замены кода на импорты
   - Ожидаемое уменьшение: ~32,000 → ~28,000 строк (примерно)

#### Тестирование:
- ✅ Проверка работы всех менеджеров
- ✅ Проверка установки компонентов через ComponentInstaller
- ✅ Проверка обновления системы
- ✅ Запуск приложения
- ✅ **СБОРКА БИНАРНИКА через DockerManager** с использованием `.spec` файла
- ✅ Проверка работы бинарника на целевых платформах
- ✅ Проверка размера бинарника (должен остаться 13-16 MB)

#### Контрольная точка:
- ✅ Все managers модули перенесены
- ✅ Код в `Code/Run/FSA-AstraInstall.py` заменен на импорты
- ✅ Размер `Code/Run/FSA-AstraInstall.py` уменьшился (зафиксировать точное значение)
- ✅ Все импорты обновлены
- ✅ Менеджеры работают корректно
- ✅ Бинарник собирается через DockerManager и работает

---

### Этап 7: Monitoring модули

#### Задачи:
1. **`Code/monitoring/filesystem_filter.py`**
   - Перенести `FilesystemFilter` (строки 39741-39818)
   - **Заменить код в `Code/Run/FSA-AstraInstall.py` на импорты** (удалить строки 39741-39818, добавить импорты)

2. **`Code/monitoring/filesystem_monitor.py`**
   - Перенести `DirectorySnapshot` (строки 39819-40442)
   - Перенести `DirectoryMonitor` (строки 40443-40774)
   - **Заменить код в `Code/Run/FSA-AstraInstall.py` на импорты** (удалить строки 39819-40774, добавить импорты)

3. **`Code/monitoring/process_monitor.py`**
   - Перенести `ProcessMonitor` (строки 13234-13329)
   - **Заменить код в `Code/Run/FSA-AstraInstall.py` на импорты** (удалить строки 13234-13329, добавить импорты)

4. **`Code/monitoring/installation_monitor.py`**
   - Перенести `InstallationMonitor` (строки 13330-13574)
   - **Заменить код в `Code/Run/FSA-AstraInstall.py` на импорты** (удалить строки 13330-13574, добавить импорты)

5. **Обновить `.spec` файл**
   - Добавить `hiddenimports` для всех monitoring модулей:
     - `Code.monitoring.filesystem_filter`
     - `Code.monitoring.filesystem_monitor`
     - `Code.monitoring.process_monitor`
     - `Code.monitoring.installation_monitor`

6. **Фиксация уменьшения размера файла**
   - Зафиксировать размер `Code/Run/FSA-AstraInstall.py` после замены кода на импорты
   - Ожидаемое уменьшение: ~28,000 → ~27,000 строк (примерно)

#### Тестирование:
- ✅ Проверка мониторинга файловой системы
- ✅ Проверка мониторинга процессов
- ✅ Проверка мониторинга установки
- ✅ Запуск приложения
- ✅ **СБОРКА БИНАРНИКА через DockerManager** с использованием `.spec` файла
- ✅ Проверка работы бинарника на целевых платформах
- ✅ Проверка размера бинарника (должен остаться 13-16 MB)

#### Контрольная точка:
- ✅ Все monitoring модули перенесены
- ✅ Код в `Code/Run/FSA-AstraInstall.py` заменен на импорты
- ✅ Размер `Code/Run/FSA-AstraInstall.py` уменьшился (зафиксировать точное значение)
- ✅ Все импорты обновлены
- ✅ Мониторинг работает корректно
- ✅ Бинарник собирается через DockerManager и работает

---

### Этап 8: Interactive модули

#### Задачи:
1. **`Code/interactive/config.py`**
   - Перенести `InteractiveConfig` (строки 11872-11941)
   - **Заменить код в `Code/Run/FSA-AstraInstall.py` на импорты** (удалить строки 11872-11941, добавить импорты)

2. **`Code/interactive/replay.py`**
   - Перенести `LogReplaySimulator` (строки 11727-11871)
   - **Заменить код в `Code/Run/FSA-AstraInstall.py` на импорты** (удалить строки 11727-11871, добавить импорты)

3. **`Code/interactive/handler.py`**
   - Перенести `InteractiveHandler` (строки 35864-36009)
   - **Заменить код в `Code/Run/FSA-AstraInstall.py` на импорты** (удалить строки 35864-36009, добавить импорты)

4. **Обновить `.spec` файл**
   - Добавить `hiddenimports` для всех interactive модулей:
     - `Code.interactive.config`
     - `Code.interactive.replay`
     - `Code.interactive.handler`

5. **Фиксация уменьшения размера файла**
   - Зафиксировать размер `Code/Run/FSA-AstraInstall.py` после замены кода на импорты
   - Ожидаемое уменьшение: ~27,000 → ~26,500 строк (примерно)

#### Тестирование:
- ✅ Проверка обработки интерактивных запросов
- ✅ Проверка симуляции логов
- ✅ Запуск приложения
- ✅ **СБОРКА БИНАРНИКА через DockerManager** с использованием `.spec` файла
- ✅ Проверка работы бинарника на целевых платформах
- ✅ Проверка размера бинарника (должен остаться 13-16 MB)

#### Контрольная точка:
- ✅ Все interactive модули перенесены
- ✅ Код в `Code/Run/FSA-AstraInstall.py` заменен на импорты
- ✅ Размер `Code/Run/FSA-AstraInstall.py` уменьшился (зафиксировать точное значение)
- ✅ Все импорты обновлены
- ✅ Интерактивные системы работают
- ✅ Бинарник собирается через DockerManager и работает

---

### Этап 9: Updater модуль

#### Задачи:
1. **`Code/updater/self_updater.py`**
   - Перенести `SelfUpdater` (строки 41127-42396)
   - **Заменить код в `Code/Run/FSA-AstraInstall.py` на импорты** (удалить строки 41127-42396, добавить импорты)

2. **Обновить `.spec` файл**
   - Добавить `hiddenimports` для updater модуля:
     - `Code.updater.self_updater`

3. **Фиксация уменьшения размера файла**
   - Зафиксировать размер `Code/Run/FSA-AstraInstall.py` после замены кода на импорты
   - Ожидаемое уменьшение: ~26,500 → ~25,000 строк (примерно)

#### Тестирование:
- ✅ Проверка проверки обновлений
- ✅ Проверка загрузки обновлений (в тестовом режиме)
- ✅ Запуск приложения
- ✅ **СБОРКА БИНАРНИКА через DockerManager** с использованием `.spec` файла
- ✅ Проверка работы бинарника на целевых платформах
- ✅ Проверка размера бинарника (должен остаться 13-16 MB)

#### Контрольная точка:
- ✅ Updater модуль перенесен
- ✅ Код в `Code/Run/FSA-AstraInstall.py` заменен на импорты
- ✅ Размер `Code/Run/FSA-AstraInstall.py` уменьшился (зафиксировать точное значение)
- ✅ Все импорты обновлены
- ✅ Система обновлений работает
- ✅ Бинарник собирается через DockerManager и работает

---

### Этап 10: Runtime модули

#### Задачи:
1. **`Code/runtime/startup.py`**
   - Перенести `find_running_instance()` (строки 40775-40854)
   - Перенести `activate_existing_window()` (строки 40855-40934)
   - Перенести `detect_astra_version()` (строки 40935-41005)
   - Перенести `_init_current_platform()` (строки 41006-41022)
   - Перенести `_is_astra_1_7()` (строки 41023-41032)
   - Перенести `_remove_emoji()` (строки 41033-41060)
   - Перенести `restart_with_path()` (строки 41061-41072)
   - Перенести `ensure_correct_binary_name()` (строки 41073-41126)
   - **Заменить код в `Code/Run/FSA-AstraInstall.py` на импорты** (удалить строки 40775-41126, добавить импорты)

2. **`Code/runtime/tcl_tk_loader.py`**
   - Перенести `_load_tcl_tk_libraries()` (строки 42655-42778)
   - **Заменить код в `Code/Run/FSA-AstraInstall.py` на импорты** (удалить строки 42655-42778, добавить импорты)

3. **`Code/runtime/main_functions.py`**
   - Перенести `run_repo_checker()` (строки 39411-39463)
   - Перенести `run_system_stats()` (строки 39464-39503)
   - Перенести `run_interactive_handler()` (строки 39504-39525)
   - Перенести `run_system_updater()` (строки 39526-39560)
   - Перенести `run_gui_monitor()` (строки 39561-39732)
   - Перенести `cleanup_temp_files()` (строки 39733-39740)
   - **Заменить код в `Code/Run/FSA-AstraInstall.py` на импорты** (удалить строки 39411-39740, добавить импорты)

4. **Обновить `.spec` файл**
   - Добавить `hiddenimports` для всех runtime модулей:
     - `Code.runtime.startup`
     - `Code.runtime.tcl_tk_loader`
     - `Code.runtime.main_functions`

5. **Фиксация уменьшения размера файла**
   - Зафиксировать размер `Code/Run/FSA-AstraInstall.py` после замены кода на импорты
   - Ожидаемое уменьшение: ~25,000 → ~23,000 строк (примерно)

#### Тестирование:
- ✅ Проверка запуска приложения
- ✅ Проверка загрузки Tcl/Tk для бинарника
- ✅ Запуск приложения
- ✅ **СБОРКА БИНАРНИКА через DockerManager** с использованием `.spec` файла
- ✅ Проверка работы бинарника на целевых платформах
- ✅ Проверка размера бинарника (должен остаться 13-16 MB)

#### Контрольная точка:
- ✅ Все runtime модули перенесены
- ✅ Код в `Code/Run/FSA-AstraInstall.py` заменен на импорты
- ✅ Размер `Code/Run/FSA-AstraInstall.py` уменьшился (зафиксировать точное значение)
- ✅ Все импорты обновлены
- ✅ Приложение запускается корректно
- ✅ Бинарник собирается через DockerManager и работает

---

### Этап 11: GUI модули - часть 1 (Widgets)

#### Задачи:
1. **`Code/gui/widgets/tooltip.py`**
   - Перенести `ToolTip` (строки 15652-15744)
   - **Заменить код в `Code/Run/FSA-AstraInstall.py` на импорты** (удалить строки 15652-15744, добавить импорты)

2. **`Code/gui/widgets/terminal_redirector.py`**
   - Перенести `TerminalRedirector` (строки 15745-15775)
   - **Заменить код в `Code/Run/FSA-AstraInstall.py` на импорты** (удалить строки 15745-15775, добавить импорты)

3. **`Code/gui/widgets/size_manager.py`**
   - Перенести `SizeManager` (строки 15776-17795)
   - **Заменить код в `Code/Run/FSA-AstraInstall.py` на импорты** (удалить строки 15776-17795, добавить импорты)

4. **Обновить `.spec` файл**
   - Добавить `hiddenimports` для всех widgets модулей:
     - `Code.gui.widgets.tooltip`
     - `Code.gui.widgets.terminal_redirector`
     - `Code.gui.widgets.size_manager`

5. **Фиксация уменьшения размера файла**
   - Зафиксировать размер `Code/Run/FSA-AstraInstall.py` после замены кода на импорты
   - Ожидаемое уменьшение: ~23,000 → ~20,000 строк (примерно)

#### Тестирование:
- ✅ Проверка работы подсказок
- ✅ Проверка перенаправления терминала
- ✅ Проверка работы `SizeManager` (сохранение/восстановление геометрии окон и таблиц)
- ✅ Запуск приложения
- ✅ **СБОРКА БИНАРНИКА через DockerManager** с использованием `.spec` файла
- ✅ Проверка работы бинарника на целевых платформах
- ✅ Проверка размера бинарника (должен остаться 13-16 MB)

#### Контрольная точка:
- ✅ Все widgets модули перенесены
- ✅ Код в `Code/Run/FSA-AstraInstall.py` заменен на импорты
- ✅ Размер `Code/Run/FSA-AstraInstall.py` уменьшился (зафиксировать точное значение)
- ✅ Все импорты обновлены
- ✅ Виджеты работают корректно
- ✅ Бинарник собирается через DockerManager и работает

---

### Этап 12: GUI модули - часть 2 (Tabs)

#### Задачи:
1. **`Code/gui/tabs/main_tab.py`**
   - Перенести создание вкладки "Обновление ОС" (строки из AutomationGUI.create_main_tab)
   - **Заменить код в `Code/Run/FSA-AstraInstall.py` на импорты** (удалить соответствующие строки, добавить импорты)

2. **`Code/gui/tabs/repos_tab.py`**
   - Перенести создание вкладки "Репозитории" (строки из AutomationGUI.create_repos_tab)
   - **Заменить код в `Code/Run/FSA-AstraInstall.py` на импорты** (удалить соответствующие строки, добавить импорты)

3. **`Code/gui/tabs/terminal_tab.py`**
   - Перенести создание вкладки "Терминал" (строки из AutomationGUI.create_terminal_tab)
   - **Заменить код в `Code/Run/FSA-AstraInstall.py` на импорты** (удалить соответствующие строки, добавить импорты)

4. **`Code/gui/tabs/wine_tab.py`**
   - Перенести создание вкладки "Установка Программ" (строки из AutomationGUI.create_wine_tab)
   - **Заменить код в `Code/Run/FSA-AstraInstall.py` на импорты** (удалить соответствующие строки, добавить импорты)

5. **`Code/gui/tabs/system_tab.py`**
   - Перенести создание вкладки "О системе" (строки из AutomationGUI.create_system_info_tab)
   - **Заменить код в `Code/Run/FSA-AstraInstall.py` на импорты** (удалить соответствующие строки, добавить импорты)

6. **`Code/gui/tabs/filesystem_tab.py`**
   - Перенести создание вкладки "Файловая система" (строки из AutomationGUI.create_filesystem_monitor_tab)
   - **Заменить код в `Code/Run/FSA-AstraInstall.py` на импорты** (удалить соответствующие строки, добавить импорты)

7. **`Code/gui/tabs/processes_tab.py`**
   - Перенести создание вкладки "Мониторинг" (строки из AutomationGUI.create_processes_monitor_tab)
   - **Заменить код в `Code/Run/FSA-AstraInstall.py` на импорты** (удалить соответствующие строки, добавить импорты)

8. **`Code/gui/tabs/packages_tab.py`**
   - Перенести создание вкладки "Пакеты" (строки из AutomationGUI.create_packages_tab)
   - **Заменить код в `Code/Run/FSA-AstraInstall.py` на импорты** (удалить соответствующие строки, добавить импорты)

9. **Обновить `.spec` файл**
   - Добавить `hiddenimports` для всех tabs модулей:
     - `Code.gui.tabs.main_tab`
     - `Code.gui.tabs.repos_tab`
     - `Code.gui.tabs.terminal_tab`
     - `Code.gui.tabs.wine_tab`
     - `Code.gui.tabs.system_tab`
     - `Code.gui.tabs.filesystem_tab`
     - `Code.gui.tabs.processes_tab`
     - `Code.gui.tabs.packages_tab`

10. **Фиксация уменьшения размера файла**
    - Зафиксировать размер `Code/Run/FSA-AstraInstall.py` после замены кода на импорты
    - Ожидаемое уменьшение: ~20,000 → ~15,000 строк (примерно)

#### Тестирование:
- ✅ Проверка каждой вкладки отдельно
- ✅ Проверка переключения между вкладками
- ✅ Проверка всех функций в каждой вкладке
- ✅ Запуск приложения
- ✅ **СБОРКА БИНАРНИКА через DockerManager** с использованием `.spec` файла
- ✅ Проверка работы бинарника на целевых платформах
- ✅ Проверка размера бинарника (должен остаться 13-16 MB)

#### Контрольная точка:
- ✅ Все tabs модули перенесены
- ✅ Код в `Code/Run/FSA-AstraInstall.py` заменен на импорты
- ✅ Размер `Code/Run/FSA-AstraInstall.py` уменьшился (зафиксировать точное значение)
- ✅ Все импорты обновлены
- ✅ Все вкладки работают корректно
- ✅ Бинарник собирается через DockerManager и работает

---

### Этап 13: GUI модули - часть 3 (Main Window)

#### Задачи:
1. **`Code/gui/main_window.py`**
   - Перенести `AutomationGUI` (строки 17796-35863)
   - Разбить большой класс на логические методы
   - Обновить все вызовы вкладок на импорты из модулей
   - Обновить использование `SizeManager` на импорт из `Code.gui.widgets.size_manager`
   - **Заменить код в `Code/Run/FSA-AstraInstall.py` на импорты** (удалить строки 17796-35863, добавить импорты)

2. **Обновить `.spec` файл**
   - Добавить `hiddenimports` для main_window модуля:
     - `Code.gui.main_window`

3. **Фиксация уменьшения размера файла**
   - Зафиксировать размер `Code/Run/FSA-AstraInstall.py` после замены кода на импорты
   - Ожидаемое уменьшение: ~15,000 → ~500 строк (примерно)

#### Тестирование:
- ✅ Проверка создания главного окна
- ✅ Проверка всех методов GUI
- ✅ Проверка работы всех вкладок
- ✅ Запуск приложения
- ✅ **СБОРКА БИНАРНИКА через DockerManager** с использованием `.spec` файла
- ✅ Проверка работы бинарника на целевых платформах
- ✅ Проверка размера бинарника (должен остаться 13-16 MB)

#### Контрольная точка:
- ✅ Main window модуль перенесен
- ✅ Код в `Code/Run/FSA-AstraInstall.py` заменен на импорты
- ✅ Размер `Code/Run/FSA-AstraInstall.py` уменьшился (зафиксировать точное значение)
- ✅ Все импорты обновлены
- ✅ GUI работает полностью
- ✅ Бинарник собирается через DockerManager и работает

---

### Этап 14: Финальный этап - Точка входа

#### Задачи:
1. **`Code/Run/FSA-AstraInstall.py`** (рабочая копия для рефакторинга)
   - Обновить все импорты
   - Оставить только функцию `main()` и блок `if __name__ == '__main__':`
   - Удалить весь перенесенный код
   - Проверить, что файл стал ~200 строк
   - Убедиться, что все импорты корректны
   - **КРИТИЧНО:** Исходный файл `FSA-AstraInstall.py` в корне проекта остается нетронутым (резерв/история)

2. **Фиксация финального размера файла**
   - Зафиксировать финальный размер `Code/Run/FSA-AstraInstall.py`
   - Ожидаемый размер: ~200 строк
   - Исходный файл в корне остается 43,342 строки (резерв/история)
   - **После рефакторинга:** `Code/Run/FSA-AstraInstall.py` становится основным файлом для разработки и обновления версий проекта

#### Тестирование:
- ✅ **ПОЛНОЕ ФУНКЦИОНАЛЬНОЕ ТЕСТИРОВАНИЕ** - все модули перенесены
- ✅ Проверка всех функций приложения
- ✅ Проверка работы в режиме скрипта
- ✅ Проверка работы GUI
- ✅ **СБОРКА БИНАРНИКА через DockerManager** с использованием `.spec` файла
- ✅ Проверка работы бинарника на целевых платформах (astra-1.7, astra-1.8)
- ✅ Проверка размера бинарника (должен остаться 13-16 MB)

#### Контрольная точка:
- ✅ Файл `Code/Run/FSA-AstraInstall.py` обновлен
- ✅ Размер файла ~200 строк (зафиксировать точное значение)
- ✅ Исходный файл `FSA-AstraInstall.py` в корне проекта остался нетронутым
- ✅ Все функции работают
- ✅ Бинарник собирается через DockerManager и работает на всех платформах
- ✅ **РЕФАКТОРИНГ ЗАВЕРШЕН**

---

### Этап 15: Очистка и оптимизация

#### Задачи:
1. Удалить неиспользуемые импорты из всех модулей
2. Оптимизировать `__init__.py` файлы
3. Проверить все циклические импорты
4. Добавить docstrings в новые модули
5. Проверить соответствие PEP 8
6. Рефакторинг глобальных переменных (опционально):
   - Создать класс `ApplicationState` для управления состоянием
   - Заменить глобальные переменные на методы класса
   - Использовать dependency injection вместо глобальных экземпляров
7. Улучшение обработки исключений (опционально):
   - Заменить bare `except:` на конкретные исключения
   - Заменить широкие `except Exception:` на специфичные
   - Добавить логирование всех исключений
8. Улучшение безопасности (опционально):
   - Исправить `CredentialManager`: убрать fallback на base64
   - Требовать обязательное наличие `cryptography`
   - Улучшить генерацию ключа шифрования

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

1. **DockerManager** - загружает исходники на удаленный сервер
2. **Docker контейнер** - собирает бинарник в изолированной среде
3. **PyInstaller onefile** - упаковывает один файл `FSA-AstraInstall.py`
4. **Результат** - автономный бинарник 13-16 MB для целевой платформы (astra-1.7 или astra-1.8)

### После рефакторинга

#### Преимущества:
- ✅ **Кэширование** - PyInstaller кэширует изменения отдельных модулей
- ✅ **Инкрементальные сборки** - пересборка только измененных модулей
- ✅ **Отладка** - проще локализовать проблемы в конкретном модуле
- ✅ **Управление через .spec** - централизованная конфигурация сборки
- ✅ **Явные зависимости** - все модули явно указаны в hiddenimports

#### Возможные проблемы:
- ⚠️ **Скрытые импорты** - PyInstaller может пропустить динамические импорты
- **Решение:** Использовать `hiddenimports` в .spec файле (уже добавлено)
- ⚠️ **Загрузка модулей** - DockerManager должен загружать `Code/` директорию
- **Решение:** Обновить `file_manager.py` для включения `Code/` (Этап 2)
- ⚠️ **Структура проекта** - PyInstaller должен найти все модули
- **Решение:** Использовать `.spec` файл с явными путями (Этап 2)

#### Рекомендации для PyInstaller:

**КРИТИЧНО:** DockerManager обновляется на Этапе 2 (до начала переноса кода):
1. Создать `.spec` файл (см. Этап 2)
2. Обновить `docker_build.sh` для использования `.spec` файла
3. Обновить `file_manager.py` для загрузки `Code/` директории

**Создать `.spec` файл:**
```python
# FSA-AstraInstall.spec
a = Analysis(
    ['Code/Run/FSA-AstraInstall.py'],  # КРИТИЧНО: рабочая копия для рефакторинга
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
        'Code.gui.widgets.size_manager',
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
        'Code.utils.process_utils',
        'Code.utils.security_utils',
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

## 🧪 Этапы начала тестирования и сборки

### Частичное тестирование (можно начинать раньше)

**После Этапа 2 (Core модули):**
- ✅ Можно тестировать базовую функциональность (логирование, процесс-раннер, прогресс)
- ✅ Можно проверять импорты модулей
- ✅ Можно запускать приложение в режиме скрипта (частично)
- ⚠️ **НЕ рекомендуется** собирать бинарник на этом этапе (не все зависимости готовы)

**После Этапа 3 (Utils модули):**
- ✅ Можно тестировать утилиты (пути, файлы, компоненты, безопасность)
- ✅ Можно проверять работу CredentialManager
- ✅ Можно тестировать работу с процессами
- ⚠️ **НЕ рекомендуется** собирать бинарник на этом этапе (GUI еще не готов)

**После Этапа 4 (Handlers модули):**
- ✅ Можно тестировать установку/удаление компонентов
- ✅ Можно проверять статусы компонентов
- ✅ Можно тестировать обработчики изолированно
- ⚠️ **НЕ рекомендуется** собирать бинарник на этом этапе (GUI еще не готов)

**После Этапа 5 (Managers модули):**
- ✅ Можно тестировать менеджеры компонентов
- ✅ Можно тестировать обновление системы
- ✅ Можно тестировать WinetricksManager
- ⚠️ **НЕ рекомендуется** собирать бинарник на этом этапе (GUI еще не готов)

**После Этапа 12 (GUI Main Window):**
- ✅ Можно тестировать полный GUI
- ✅ Можно тестировать все функции приложения
- ✅ Можно пробовать собирать бинарник вручную (через PyInstaller напрямую)
- ⚠️ **НЕ рекомендуется** использовать DockerManager для сборки (еще не обновлен)

### Полное тестирование и сборка

**После Этапа 2 (Обновление DockerManager):**
- ✅ DockerManager обновлен для работы с модулями
- ✅ `.spec` файл создан и настроен
- ✅ Можно собирать бинарники через DockerManager на каждом этапе переноса кода
- ✅ Бинарники собираются и тестируются после каждого этапа (3-14)

**После Этапа 14 (Финальный этап - Точка входа):**
- ✅ **ПОЛНОЕ ТЕСТИРОВАНИЕ** - все модули перенесены, точка входа обновлена
- ✅ Можно тестировать все функции приложения
- ✅ **ПОЛНАЯ СБОРКА ЧЕРЕЗ DOCKERMANAGER** - все готово для автоматической сборки
- ✅ Можно собирать бинарники через DockerManager для всех платформ (astra-1.7, astra-1.8)
- ✅ Можно тестировать бинарники на целевых платформах
- ✅ Можно использовать в production

### Рекомендации по тестированию

1. **Поэтапное тестирование:**
   - После каждого этапа (2-12) тестировать перенесенные модули изолированно
   - Проверять импорты и базовую функциональность
   - НЕ собирать бинарник до Этапа 13

2. **Интеграционное тестирование:**
   - После Этапа 2 - DockerManager обновлен, можно собирать бинарники на каждом этапе
   - После каждого этапа (3-14) - сборка бинарника через DockerManager для проверки работоспособности
   - Тестирование на целевых платформах после каждого этапа

3. **Production тестирование:**
   - После Этапа 14 - полное тестирование всех функций
   - Сборка через DockerManager для всех платформ
   - Тестирование на всех целевых платформах
   - Проверка всех функций в бинарнике

---

## 🎯 Контрольные точки

### Критические контрольные точки (обязательные)

1. **После Этапа 1 (Обновление COMMIT_RULES.md)**
   - ✅ COMMIT_RULES.md обновлен для работы с модульной структурой
   - ✅ Тестовый коммит успешно создан с изменениями в Code/
   - ✅ Версии и даты корректно обновляются в модулях

2. **После Этапа 2 (Core модули)**
   - ✅ Приложение запускается частично (без GUI)
   - ✅ Логирование работает
   - ✅ Базовые функции работают
   - ⚠️ Бинарник НЕ рекомендуется собирать (GUI и другие модули еще не готовы)
   - ✅ Коммит с Core модулями успешно создан

3. **После Этапа 4 (Handlers модули)**
   - ✅ Установка компонентов работает
   - ✅ Удаление компонентов работает
   - ✅ Проверка статусов работает

4. **После Этапа 11 (GUI Tabs)**
   - ✅ Все вкладки GUI работают
   - ✅ Переключение между вкладками работает

5. **После Этапа 2 (Обновление DockerManager)**
   - ✅ DockerManager обновлен для работы с модулями
   - ✅ `.spec` файл создан и настроен
   - ✅ Можно собирать бинарники через DockerManager на каждом этапе переноса кода
   - ✅ Бинарники собираются и тестируются после каждого этапа (3-14)

6. **После Этапа 14 (Финальный этап - Точка входа)**
   - ✅ Все функции работают
   - ✅ Размер файла `Code/Run/FSA-AstraInstall.py` ~200 строк
   - ✅ Исходный файл `FSA-AstraInstall.py` в корне остался нетронутым (43,342 строки)
   - ✅ **ПОЛНАЯ СБОРКА ЧЕРЕЗ DOCKERMANAGER** - все готово для автоматической сборки
   - ✅ Бинарник собирается через DockerManager для всех платформ (astra-1.7, astra-1.8)
   - ✅ Бинарник работает на всех целевых платформах
   - ✅ Все функции приложения работают в бинарнике
   - ✅ Размер бинарника в пределах нормы (13-16 MB)
   - ✅ **PRODUCTION-READY** - можно использовать в production

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
| 1 | Обновление COMMIT_RULES.md | 1 день | **КРИТИЧЕСКИЙ** |
| 2 | Core модули | 2-3 дня | Высокий |
| 3 | Utils модули | 2-3 дня | Высокий |
| 4 | Handlers модули | 3-4 дня | Высокий |
| 5 | Managers модули | 2-3 дня | Высокий |
| 6 | Monitoring модули | 1-2 дня | Средний |
| 7 | Interactive модули | 1 день | Средний |
| 8 | Updater модуль | 1 день | Средний |
| 9 | Runtime модули | 1 день | Высокий |
| 10 | GUI Widgets | 1-2 дня | Высокий |
| 11 | GUI Tabs | 3-4 дня | Высокий |
| 12 | GUI Main Window | 2-3 дня | Высокий |
| 13 | Финальный этап | 1 день | Высокий |
| 14 | Очистка и оптимизация | 2-3 дня | Низкий |
| **ИТОГО** | | **27-37 дней** | |

**Примечание:** Обновление DockerManager выполняется на Этапе 2 (до начала переноса кода), чтобы можно было собирать бинарники на каждом этапе рефакторинга.

### Ускорение процесса

- ✅ **Параллельная работа** - можно работать над разными модулями одновременно (после Этапа 2)
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

1. **Постепенную миграцию** - разбиение на 16 этапов с проверками
2. **Учет всех компонентов** - включены все классы и функции, включая CredentialManager, SizeManager, process_utils
3. **Сохранение функциональности** - весь существующий функционал сохраняется
4. **Тестирование на каждом этапе** - быстрая локализация проблем
5. **Гибкость** - возможность отката на любом этапе
6. **Документирование** - четкое описание каждого этапа
7. **Актуальные данные** - все номера строк обновлены согласно текущему коду (43,342 строки)
8. **Обновление процесса сборки** - обновление DockerManager перенесено на Этап 2 (до начала переноса кода) для возможности сборки бинарников на каждом этапе

### 📝 Основные изменения в версии 1.1.0:

1. ✅ **Добавлен CredentialManager** - модуль `Code/utils/security_utils.py` (строки 562-905)
2. ✅ **Добавлен SizeManager** - модуль `Code/gui/widgets/size_manager.py` (строки 15776-17795)
3. ✅ **Добавлен process_utils** - модуль `Code/utils/process_utils.py` (строки 1756-1788)
4. ✅ **Обновлены все номера строк** - согласно актуальному размеру файла (43,342 строки вместо 37,726)
5. ✅ **Обновлена структура проекта** - добавлены новые модули в дерево директорий
6. ✅ **Обновлен .spec файл** - добавлены hiddenimports для новых модулей
7. ✅ **Добавлены задачи по улучшению** - безопасность, обработка исключений, глобальные переменные (Этап 14)
8. ✅ **Обновлены временные оценки** - с учетом новых модулей (27-37 дней вместо 22-30)
9. ✅ **Обновление DockerManager перенесено на Этап 2** - обновление DockerManager и процесса сборки бинарников выполняется до начала переноса кода для возможности сборки бинарников на каждом этапе
10. ✅ **Добавлен .spec файл** - конфигурация PyInstaller с явными hiddenimports для всех модулей (создается на Этапе 2)
11. ✅ **Добавлен Этап 1** - обновление COMMIT_RULES.md для работы с модульной структурой (критически важно, выполняется до начала миграции)

**Следующие шаги:**
1. Просмотреть и утвердить план
2. Создать ветку для рефакторинга
3. Начать с Этапа 0 (Подготовка)
4. **КРИТИЧЕСКИ ВАЖНО:** Выполнить Этап 1 (Обновление COMMIT_RULES.md) ДО начала миграции кода, так как коммиты будут создаваться с самого начала рефакторинга
5. **КРИТИЧЕСКИ ВАЖНО:** Выполнить Этап 2 (Обновление DockerManager) ДО начала переноса кода, чтобы можно было собирать бинарники на каждом этапе рефакторинга

---

**Дата создания:** 2025.12.23  
**Дата обновления:** 2025.12.31  
**Авторы:** @FoksSegr & AI Assistant (@LLM)  
**Версия документа:** 1.3.0  
**Изменения v1.1.0:** Добавлены пропущенные компоненты (CredentialManager, SizeManager, process_utils), обновлены все номера строк согласно актуальному коду (43,342 строки)  
**Изменения v1.2.0:** Добавлен Этап 15 - обновление DockerManager и процесса сборки бинарников для работы с модульной структурой  
**Изменения v1.3.0:** Добавлен Этап 1 - обновление COMMIT_RULES.md для работы с модульной структурой (критически важно, выполняется до начала миграции)
