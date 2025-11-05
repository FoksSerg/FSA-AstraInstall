# 📋 ДЕТАЛЬНЫЙ ПЛАН РЕФАКТОРИНГА: МИГРАЦИЯ НА АРХИТЕКТУРУ COMPONENT HANDLERS
**Версия: V2.4.102 (2025.11.05)**
**Компания: ООО "НПА Вира-Реалтайм"**

# Статус: ДЕТАЛЬНЫЙ ПЛАН РЕАЛИЗАЦИИ

## 🎯 ЦЕЛИ И ЗАДАЧИ РЕФАКТОРИНГА

### Основные цели:
1. **Универсальный инструмент** - установка ЛЮБЫХ компонентов и приложений на Linux
2. **Расширяемость** - легко добавлять новые типы компонентов через handlers
3. **Упрощение кода** - удаление дублирующей логики (~2037 строк)
4. **Унификация** - единая точка входа для всех компонентов через handlers
5. **Интеграция** - использование всей инфраструктуры (логирование, прогресс-бары, процессы, мониторинг)
6. **Визуализация** - дерево зависимостей в таблице компонентов
7. **Мониторинг** - отслеживание процессов в реальном времени (диск, сеть, CPU, время)
8. **Безопасность** - миграция без ломки существующего функционала

### Критерии успеха:
- ✅ Существующий функционал продолжает работать
- ✅ Новые компоненты устанавливаются/удаляются через handlers
- ✅ Логирование работает через все каналы (файл, терминал, GUI)
- ✅ Прогресс-бары отображаются корректно для всех процессов
- ✅ Статусы компонентов обновляются в реальном времени
- ✅ Зависимости визуализируются в таблице
- ✅ Мониторинг работает для всех процессов
- ✅ Код стал проще и понятнее

---

## 🏗️ АРХИТЕКТУРНАЯ СХЕМА

### Полная архитектура системы:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         AUTOMATIONGUI (GUI)                              │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐      │
│  │ Вкладка "Управление"│  │ Вкладка "Wine & IDE"│  │ Вкладка "Терминал"│ │
│  │                   │  │                   │  │                   │ │
│  │ [Обновление системы]│  │ [Таблица компонентов]│  │ [Лог операций]    │ │
│  │                   │  │                   │  │                   │ │
│  │ Прогресс-бары:    │  │ Дерево компонентов:│  │ Вывод:           │ │
│  │ - Загрузка        │  │ - Статусы         │  │ - RAW поток       │ │
│  │ - Распаковка      │  │ - Зависимости     │  │ - ANALYSIS поток │ │
│  │ - Конфигурация    │  │ - Прогресс        │  │                   │ │
│  │                   │  │                   │  │                   │ │
│  │ Мониторинг:       │  │ Мониторинг:       │  │                   │ │
│  │ - Время           │  │ - Время           │  │                   │ │
│  │ - Диск            │  │ - Диск            │  │                   │ │
│  │ - Сеть            │  │ - Сеть            │  │                   │ │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
                              │              │
                              ▼              ▼
        ┌─────────────────────────────────────────────┐
        │     UniversalProcessRunner (глобальный)      │
        │  - Запуск процессов (subprocess.run)         │
        │  - Логирование (log_info/log_error)         │
        │  - Перехват print() и subprocess             │
        └─────────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────────────┐
        │       DualStreamLogger (глобальный)          │
        │  - RAW поток (необработанный вывод)        │
        │  - ANALYSIS поток (парсинг, аналитика)      │
        │  - Буферы в памяти + файловая запись        │
        └─────────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────────────┐
        │    UniversalProgressManager (глобальный)     │
        │  - Универсальный прогресс для ВСЕХ процессов │
        │  - process_type: 'system_update' | 'wine_install' │
        │  - Отправка обновлений в GUI                │
        └─────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│  SystemUpdater   │  │ UniversalInstaller│  │  (другие модули)  │
│                  │  │                  │  │                  │
│ Обновление системы│  │ Установка компонентов│  │                  │
│ (apt-get)        │  │ (Wine, winetricks)│  │                  │
│                  │  │                  │  │                  │
│ Использует:      │  │ Использует:      │  │                  │
│ - SystemUpdateParser│  │ - ComponentStatusManager│ │                  │
│   (парсит apt-get)│  │   (статусы компонентов)│ │                  │
│                  │  │                  │  │                  │
│ Прогресс через:  │  │ Прогресс через:  │  │                  │
│ UniversalProgressMgr│  │ UniversalProgressMgr│  │                  │
│ process_type:    │  │ process_type:    │  │                  │
│ 'system_update'  │  │ 'wine_install'   │  │                  │
│                  │  │                  │  │                  │
│ Мониторинг:       │  │ Мониторинг:       │  │                  │
│ - Время           │  │ - Время           │  │                  │
│ - Диск            │  │ - Диск            │  │                  │
│ - Сеть (через парсер)│ │ - Сеть (через монитор)│ │                  │
└──────────────────┘  └──────────────────┘  └──────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────────────┐
        │    ComponentStatusManager (ОТДЕЛЬНЫЙ!)        │
        │  - Управление статусами компонентов         │
        │  - pending → installing → ok/error          │
        │  - НЕ используется для обновления системы!  │
        │                                             │
        │  Методы:                                    │
        │  - update_component_status(id, status)       │
        │  - get_all_components_status()              │
        │  - sync_with_wine_checker()                 │
        │                                             │
        │  Область: ТОЛЬКО компоненты из COMPONENTS_CONFIG│
        └─────────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────────────┐
        │        UniversalInstaller                    │
        │  ┌──────────────────────────────────────┐   │
        │  │  Реестр handlers:                     │   │
        │  │  - WinePackageHandler                  │   │
        │  │  - WineEnvironmentHandler              │   │
        │  │  - WinetricksHandler                   │   │
        │  │  - SystemConfigHandler                 │   │
        │  │  - ApplicationHandler                 │   │
        │  └──────────────────────────────────────┘   │
        │                                             │
        │  Использует ComponentStatusManager для:     │
        │  - Обновления статусов во время установки   │
        │  - Отображения прогресса в GUI              │
        └─────────────────────────────────────────────┘
```

### Ключевые принципы разделения ответственности:

#### 1. ComponentStatusManager (ОТДЕЛЬНЫЙ КЛАСС)
**Назначение:** Управление статусами компонентов из COMPONENTS_CONFIG
- **Статусы:** `pending`, `installing`, `removing`, `ok`, `error`
- **Используется:** Только UniversalInstaller и handlers
- **НЕ используется:** SystemUpdater (обновление системы)
- **Область:** ТОЛЬКО компоненты из COMPONENTS_CONFIG

#### 2. UniversalProgressManager (ОБЩИЙ КЛАСС)
**Назначение:** Универсальный прогресс для ВСЕХ процессов
- **Типы процессов:** `system_update`, `wine_install`, `general`
- **Используется:** SystemUpdater, UniversalInstaller, handlers
- **Область:** ВСЕ процессы в системе

#### 3. Разделение потоков данных:
```
SystemUpdater → SystemUpdateParser → UniversalProgressManager → GUI
    (process_type='system_update')

UniversalInstaller → Handler → ComponentStatusManager → GUI
                    ↓
              UniversalProgressManager → GUI
    (process_type='wine_install')
```

---

## 📊 ТЕКУЩЕЕ СОСТОЯНИЕ

### Существующие классы:

#### 1. Классы, которые БУДУТ УДАЛЕНЫ:
- **`WineInstaller`** (строки 2342-3815, ~1550 строк)
  - Методы: `install_wine_packages()`, `setup_wine_environment()`, `_ensure_wineprefix_architecture()`, `install_winetricks_components()`, `install_astra_ide()`, `create_start_script()`, `create_desktop_shortcut()`
  
- **`WineUninstaller`** (строки 4358-4759, ~487 строк)
  - Методы: `remove_wine_packages()`, `remove_wineprefix()`, `remove_ide()`, `remove_all_wine_data()`

#### 2. Классы, которые ОСТАНУТСЯ (без изменений):
- **`WinetricksManager`** - используется handlers
- **`MinimalWinetricks`** - используется WinetricksManager
- **`WineComponentsChecker`** - проверка компонентов (остается)
- **`UniversalProcessRunner`** - используется handlers
- **`DualStreamLogger`** - используется handlers
- **`SystemUpdater`** - обновление системы (остается без изменений)
- **`SystemUpdateParser`** - парсинг apt-get (остается без изменений)

#### 3. Классы, которые БУДУТ МОДИФИЦИРОВАНЫ:
- **`UniversalInstaller`** - добавление handlers, интеграция ComponentStatusManager
- **`ComponentStatusManager`** - уже существует, нужно интегрировать в UniversalInstaller
- **`UniversalProgressManager`** - уже существует, используется для всех процессов
- **`AutomationGUI`** - улучшение таблицы компонентов, визуализация зависимостей

#### 4. Классы, которые БУДУТ ДОБАВЛЕНЫ:
- **`ComponentHandler`** - базовый абстрактный класс
- **`WinePackageHandler`** - обработчик Wine пакетов
- **`WineEnvironmentHandler`** - обработчик Wine окружения
- **`WinetricksHandler`** - обработчик winetricks компонентов
- **`SystemConfigHandler`** - обработчик системных настроек
- **`ApplicationHandler`** - обработчик приложений (Astra.IDE)
- **`UniversalMonitor`** - универсальный мониторинг (опционально)

---

## 🔍 ДЕТАЛЬНАЯ ПРОРАБОТКА КОМПОНЕНТОВ

### 1. ComponentStatusManager (СУЩЕСТВУЕТ, НУЖНА ИНТЕГРАЦИЯ)

**Текущее состояние:**
- Создан в GUI: `self.component_status_manager = ComponentStatusManager(callback=self._component_status_callback)`
- Используется в GUI: `_update_wine_status()` вызывает `get_all_components_status()`
- НЕ используется в UniversalInstaller

**Что нужно сделать:**
1. Передать ComponentStatusManager в UniversalInstaller
2. Обновлять статусы в handlers:
   - `pending` - перед установкой (когда компонент выбран)
   - `installing` - во время установки
   - `ok`/`error` - после завершения
3. Обновлять статусы зависимостей автоматически

**Интерфейс ComponentStatusManager:**
```python
class ComponentStatusManager:
    def update_component_status(self, component_id, status):
        # status: 'pending', 'installing', 'removing', 'ok', 'error'
        # Обновляет внутренние состояния и вызывает callback
    
    def get_all_components_status(self):
        # Возвращает dict: {component_id: (status_text, status_tag)}
        # status_text: '[OK]', '[Ожидание]', '[Установка]', '[---]'
        # status_tag: 'ok', 'pending', 'installing', 'missing'
    
    def sync_with_wine_checker(self, wine_checker):
        # Синхронизация с WineComponentsChecker
```

### 2. UniversalProgressManager (СУЩЕСТВУЕТ, ИСПОЛЬЗУЕТСЯ)

**Текущее состояние:**
- Создан в SystemUpdater: `self.universal_progress_manager = UniversalProgressManager(...)`
- Используется для обновления системы: `process_type='system_update'`
- НЕ используется в UniversalInstaller для установки компонентов

**Что нужно сделать:**
1. Создать UniversalProgressManager в GUI или передать из GUI
2. Передать в UniversalInstaller
3. Использовать в handlers с `process_type='wine_install'`
4. Различать процессы по `process_type`:
   - `'system_update'` - обновление системы (SystemUpdater)
   - `'wine_install'` - установка компонентов (UniversalInstaller)

**Интерфейс UniversalProgressManager:**
```python
class UniversalProgressManager:
    def update_progress(self, process_type, stage_name, stage_progress, global_progress, details="", **kwargs):
        # process_type: 'system_update' | 'wine_install' | 'general'
        # Отправляет обновление в GUI через callback
```

### 3. ComponentHandler (НОВЫЙ БАЗОВЫЙ КЛАСС)

**Назначение:** Базовый класс для всех handlers компонентов

**Интерфейс:**
```python
class ComponentHandler(ABC):
    def __init__(self, 
                 astrapack_dir=None,
                 logger=None,
                 callback=None,
                 universal_runner=None,
                 progress_manager=None,
                 dual_logger=None,
                 status_manager=None):  # НОВОЕ: ComponentStatusManager
    
    @abstractmethod
    def install(self, component_id: str, config: dict) -> bool:
        """Установка компонента"""
        # Должен обновлять статусы через status_manager:
        # 1. status_manager.update_component_status(component_id, 'installing')
        # 2. Выполнить установку
        # 3. status_manager.update_component_status(component_id, 'ok' или 'error')
    
    @abstractmethod
    def uninstall(self, component_id: str, config: dict) -> bool:
        """Удаление компонента"""
        # Аналогично install, но с 'removing' и 'missing'
    
    @abstractmethod
    def check_status(self, component_id: str, config: dict) -> bool:
        """Проверка статуса компонента"""
    
    @abstractmethod
    def get_category(self) -> str:
        """Возвращает категорию компонентов"""
```

**Методы базового класса:**
- `_log()` - логирование через UniversalProcessRunner и DualStreamLogger
  - ВАЖНО: handlers также могут использовать прямой `print()` - он работает через `universal_print` → DualStreamLogger
- `_update_progress()` - обновление прогресса через UniversalProgressManager
- `_run_process()` - запуск процессов через UniversalProcessRunner
- `_update_status()` - обновление статуса через ComponentStatusManager (НОВОЕ)

**ВАЖНО: Инфраструктура логирования сохраняется:**
- `print()` переопределен через `builtins.print = universal_print` (строка 794)
- `universal_print()` использует DualStreamLogger для всех сообщений
- UniversalProcessRunner.log_info/log_error используют DualStreamLogger
- Все логирование идет через DualStreamLogger (RAW и ANALYSIS потоки)

### 4. UniversalInstaller (МОДИФИЦИРУЕТСЯ)

**Текущее состояние:**
- Создан в GUI: `self.universal_installer = UniversalInstaller(callback=self._component_status_callback)`
- Использует старую логику через `install_method`
- НЕ использует ComponentStatusManager
- НЕ использует UniversalProgressManager

**Что нужно сделать:**
1. Добавить параметры в `__init__()`:
   - `status_manager` - ComponentStatusManager
   - `progress_manager` - UniversalProgressManager
   - `use_handlers` - флаг включения handlers
2. Создать реестр handlers
3. Модифицировать `install_component()` и `uninstall_component()` для использования handlers
4. Интегрировать обновление статусов через ComponentStatusManager

### 5. AutomationGUI (МОДИФИЦИРУЕТСЯ)

**Текущее состояние:**
- ComponentStatusManager создан: `self.component_status_manager = ComponentStatusManager(...)`
- UniversalInstaller создан: `self.universal_installer = UniversalInstaller(...)`
- SystemUpdater создан: `self.system_updater = SystemUpdater(...)`
- SystemUpdater имеет свой UniversalProgressManager

**Что нужно сделать:**
1. Создать отдельный UniversalProgressManager для UniversalInstaller
   - Или использовать общий (но с разными `process_type`)
2. Передать ComponentStatusManager и UniversalProgressManager в UniversalInstaller
3. Улучшить таблицу компонентов:
   - Визуализация дерева зависимостей
   - Отображение статусов в реальном времени
   - Показ прогресса установки

---

## 📝 ПОШАГОВЫЙ ПЛАН РЕАЛИЗАЦИИ

### ЭТАП 0: ПОДГОТОВКА И АНАЛИЗ (Приоритет: КРИТИЧЕСКИЙ)

#### Шаг 0.1: Бэкап текущего состояния
**Действия:**
1. Создать git ветку: `git checkout -b refactoring/component-handlers`
2. Сделать коммит: `git commit -am "Текущее состояние перед рефакторингом"`
3. Проверить, что все тесты проходят

**Чеклист:**
- [ ] Ветка создана
- [ ] Коммит сделан
- [ ] Тесты проходят

#### Шаг 0.2: Анализ зависимостей
**Действия:**
1. Найти все использования `WineInstaller`:
   ```bash
   grep -n "WineInstaller" astra_automation.py
   ```
2. Найти все использования `WineUninstaller`:
   ```bash
   grep -n "WineUninstaller" astra_automation.py
   ```
3. Проверить, что ComponentStatusManager не используется в SystemUpdater
4. Проверить, что UniversalProgressManager используется правильно

**Чеклист:**
- [ ] Все использования WineInstaller найдены
- [ ] Все использования WineUninstaller найдены
- [ ] Подтверждено разделение ComponentStatusManager и UniversalProgressManager

#### Шаг 0.3: Добавление компонента ptrace_scope в COMPONENTS_CONFIG
**Местоположение:** После строки 68 (после `wine_9`)

**Код для вставки:**
```python
    # Системные настройки
    'ptrace_scope': {
        'name': 'Настройка ptrace_scope',
        'category': 'system_config',
        'dependencies': [],
        'check_paths': ['/proc/sys/kernel/yama/ptrace_scope'],
        'install_method': 'system_config',
        'uninstall_method': 'system_config',
        'gui_selectable': False,  # Скрыт от пользователя, устанавливается автоматически
        'description': 'Настройка ptrace_scope для Wine',
        'priority': 3  # После wine пакетов, перед wineprefix
    },
```

**Чеклист:**
- [ ] Компонент добавлен в COMPONENTS_CONFIG
- [ ] Приоритеты обновлены (ptrace_scope=3, wineprefix=4)
- [ ] Проверка синтаксиса: `python3 -m py_compile astra_automation.py`

---

### ЭТАП 1: СОЗДАНИЕ БАЗОВОГО КЛАССА (Приоритет: ВЫСОКИЙ)

#### Шаг 1.1: Создание абстрактного класса ComponentHandler
**Местоположение:** После строки 221 (после `COMPONENTS_CONFIG`)

**Детальная проработка:**

**1. Импорты:**
```python
from abc import ABC, abstractmethod
```

**2. Класс ComponentHandler:**

```python
# ============================================================================
# БАЗОВЫЙ КЛАСС ДЛЯ ОБРАБОТЧИКОВ КОМПОНЕНТОВ
# ============================================================================
class ComponentHandler(ABC):
    """Базовый класс для обработчиков компонентов с интеграцией всех систем"""
    
    def __init__(self, 
                 astrapack_dir=None,
                 logger=None,
                 callback=None,
                 universal_runner=None,
                 progress_manager=None,
                 dual_logger=None,
                 status_manager=None):
        """
        Инициализация обработчика компонентов
        
        Args:
            astrapack_dir: Путь к директории AstraPack
            logger: Экземпляр Logger для записи в файл
            callback: Функция для обновления статуса в GUI
            universal_runner: UniversalProcessRunner для запуска процессов
            progress_manager: UniversalProgressManager для прогресса
            dual_logger: DualStreamLogger для двойных потоков логирования
            status_manager: ComponentStatusManager для управления статусами
        """
        self.astrapack_dir = astrapack_dir
        self.logger = logger
        self.callback = callback
        self.universal_runner = universal_runner or get_global_universal_runner()
        self.progress_manager = progress_manager
        self.dual_logger = dual_logger or (globals().get('_global_dual_logger') if '_global_dual_logger' in globals() else None)
        self.status_manager = status_manager  # КРИТИЧНО: для обновления статусов
        
        # Определяем домашнюю директорию РЕАЛЬНОГО пользователя
        real_user = os.environ.get('SUDO_USER')
        if real_user and real_user != 'root':
            import pwd
            self.home = pwd.getpwnam(real_user).pw_dir
        else:
            self.home = os.path.expanduser("~")
        
        self.wineprefix = os.path.join(self.home, ".wine-astraregul")
    
    def _log(self, message, level="INFO"):
        """
        Универсальное логирование через все системы
        
        ВАЖНО: Вся инфраструктура логирования сохраняется:
        - print() продолжает работать везде (переопределен через builtins.print = universal_print)
        - universal_print использует DualStreamLogger для логирования
        - UniversalProcessRunner.log_info/log_error также используют DualStreamLogger
        
        Метод _log() - удобная обертка, но handlers могут использовать и прямой print()
        """
        # Логирование через UniversalProcessRunner
        # (UniversalProcessRunner.log_info/log_error внутри используют DualStreamLogger)
        if self.universal_runner:
            if level == "ERROR":
                self.universal_runner.log_error(message)
            elif level == "WARNING":
                self.universal_runner.log_warning(message)
            else:
                self.universal_runner.log_info(message)
        
        # Дополнительное логирование через DualStreamLogger напрямую (если есть)
        # (обычно это уже делается через UniversalProcessRunner, но для надежности)
        if self.dual_logger:
            if level == "ERROR":
                self.dual_logger.write_analysis(f"[ERROR] {message}")
            elif level == "WARNING":
                self.dual_logger.write_analysis(f"[WARNING] {message}")
            else:
                self.dual_logger.write_analysis(f"[INFO] {message}")
        
        # Callback в GUI
        if self.callback:
            self.callback(message)
        
        # ПРИМЕЧАНИЕ: handlers также могут использовать прямой print():
        # print(f"[INFO] {message}")  # Работает через universal_print → DualStreamLogger
    
    def _update_progress(self, stage_name, stage_progress, global_progress, details=""):
        """Обновление прогресса через UniversalProgressManager"""
        if self.progress_manager:
            self.progress_manager.update_progress(
                process_type='wine_install',  # КРИТИЧНО: для различения от system_update
                stage_name=stage_name,
                stage_progress=stage_progress,
                global_progress=global_progress,
                details=details
            )
    
    def _update_status(self, component_id, status):
        """Обновление статуса компонента через ComponentStatusManager"""
        if self.status_manager:
            self.status_manager.update_component_status(component_id, status)
    
    def _run_process(self, command, process_type="install", channels=["file", "terminal"]):
        """Запуск процесса через UniversalProcessRunner"""
        if self.universal_runner:
            return self.universal_runner.run_process(
                command=command,
                process_type=process_type,
                channels=channels
            )
        return -1
    
    @abstractmethod
    def install(self, component_id: str, config: dict) -> bool:
        """
        Установка компонента
        
        Args:
            component_id: ID компонента из COMPONENTS_CONFIG
            config: Конфигурация компонента из COMPONENTS_CONFIG
            
        Returns:
            bool: True если установка успешна, False если ошибка
            
        Обязательные действия:
        1. self._update_status(component_id, 'installing')
        2. Выполнить установку
        3. self._update_status(component_id, 'ok' или 'error')
        """
        pass
    
    @abstractmethod
    def uninstall(self, component_id: str, config: dict) -> bool:
        """
        Удаление компонента
        
        Args:
            component_id: ID компонента из COMPONENTS_CONFIG
            config: Конфигурация компонента из COMPONENTS_CONFIG
            
        Returns:
            bool: True если удаление успешно, False если ошибка
            
        Обязательные действия:
        1. self._update_status(component_id, 'removing')
        2. Выполнить удаление
        3. self._update_status(component_id, 'missing' или 'error')
        """
        pass
    
    @abstractmethod
    def check_status(self, component_id: str, config: dict) -> bool:
        """
        Проверка статуса компонента
        
        Args:
            component_id: ID компонента из COMPONENTS_CONFIG
            config: Конфигурация компонента из COMPONENTS_CONFIG
            
        Returns:
            bool: True если компонент установлен, False если нет
        """
        pass
    
    @abstractmethod
    def get_category(self) -> str:
        """
        Возвращает категорию компонентов
        
        Returns:
            str: Категория ('wine_packages', 'wine_environment', 'winetricks', 'system_config', 'application')
        """
        pass
```

**Чеклист:**
- [ ] Импорт `ABC, abstractmethod` добавлен в начало файла
- [ ] Класс ComponentHandler создан после COMPONENTS_CONFIG
- [ ] Метод `_update_status()` добавлен для работы с ComponentStatusManager
- [ ] `process_type='wine_install'` используется в `_update_progress()`
- [ ] Код проверен на синтаксис: `python3 -m py_compile astra_automation.py`

---

### ЭТАП 2: СОЗДАНИЕ HANDLERS (Приоритет: ВЫСОКИЙ)

#### Шаг 2.1: Создание WinePackageHandler
**Местоположение:** После класса `ComponentHandler`

**Детальная проработка:**

**1. Изучить существующие методы:**
- `UniversalInstaller._install_package_manager()` (строка ~5043)
- `UniversalInstaller._uninstall_package_manager()` (строка ~5083)

**2. Класс WinePackageHandler:**

```python
# ============================================================================
# ОБРАБОТЧИК WINE ПАКЕТОВ
# ============================================================================
class WinePackageHandler(ComponentHandler):
    """Обработчик Wine пакетов (wine_astraregul, wine_9)"""
    
    def get_category(self) -> str:
        return 'wine_packages'
    
    def install(self, component_id: str, config: dict) -> bool:
        """Установка Wine пакета через apt"""
        # ОБНОВЛЯЕМ СТАТУС: устанавливаем 'installing'
        self._update_status(component_id, 'installing')
        
        self._log(f"Установка компонента: {config['name']}")
        
        # Обновляем прогресс
        self._update_progress(
            stage_name=f"Установка {config['name']}",
            stage_progress=0,
            global_progress=0,
            details=f"Подготовка к установке {component_id}"
        )
        
        # Определяем имя .deb файла из component_id
        deb_files = {
            'wine_astraregul': 'wine-astraregul_10.0-rc6-3_amd64.deb',
            'wine_9': 'wine_9.0-1_amd64.deb'
        }
        
        if component_id not in deb_files:
            self._log(f"ОШИБКА: Неизвестный пакет: {component_id}", "ERROR")
            self._update_status(component_id, 'error')
            return False
        
        deb_name = deb_files[component_id]
        package_path = os.path.join(self.astrapack_dir, deb_name)
        
        if not os.path.exists(package_path):
            self._log(f"ОШИБКА: Файл пакета не найден: {package_path}", "ERROR")
            self._update_status(component_id, 'error')
            return False
        
        # Обновляем прогресс
        self._update_progress(
            stage_name=f"Установка {config['name']}",
            stage_progress=50,
            global_progress=50,
            details="Установка через apt..."
        )
        
        # Используем UniversalProcessRunner
        return_code = self._run_process(
            ['apt', 'install', '-y', package_path],
            process_type="install",
            channels=["file", "terminal", "gui"]
        )
        
        if return_code == 0:
            self._log(f"Пакет {config['name']} установлен успешно")
            self._update_progress(
                stage_name=f"Установка {config['name']}",
                stage_progress=100,
                global_progress=100,
                details=f"{config['name']} установлен успешно"
            )
            # ОБНОВЛЯЕМ СТАТУС: устанавливаем 'ok'
            self._update_status(component_id, 'ok')
            return True
        else:
            self._log(f"ОШИБКА установки пакета {config['name']} (код: {return_code})", "ERROR")
            # ОБНОВЛЯЕМ СТАТУС: устанавливаем 'error'
            self._update_status(component_id, 'error')
            return False
    
    def uninstall(self, component_id: str, config: dict) -> bool:
        """Удаление Wine пакета через apt-get purge"""
        # ОБНОВЛЯЕМ СТАТУС: устанавливаем 'removing'
        self._update_status(component_id, 'removing')
        
        self._log(f"Удаление компонента: {config['name']}")
        
        package_names = {
            'wine_astraregul': 'wine-astraregul',
            'wine_9': 'wine-9.0'
        }
        
        if component_id not in package_names:
            self._log(f"ОШИБКА: Неизвестный пакет для удаления: {component_id}", "ERROR")
            self._update_status(component_id, 'error')
            return False
        
        package_name = package_names[component_id]
        
        # Останавливаем Wine процессы перед удалением
        self._run_process(['pkill', '-9', 'wine'], process_type="remove")
        self._run_process(['pkill', '-9', 'wineserver'], process_type="remove")
        self._run_process(['pkill', '-9', 'wineboot'], process_type="remove")
        
        import time
        time.sleep(1)
        
        # Удаляем пакет через apt-get purge
        return_code = self._run_process(
            ['apt-get', 'purge', '-y', package_name],
            process_type="remove",
            channels=["file", "terminal"]
        )
        
        if return_code == 0:
            self._log(f"Пакет {config['name']} удален успешно")
            # Удаляем директории Wine вручную
            wine_dirs = {
                'wine_astraregul': '/opt/wine-astraregul',
                'wine_9': '/opt/wine-9.0'
            }
            if component_id in wine_dirs:
                wine_dir = wine_dirs[component_id]
                if os.path.exists(wine_dir):
                    import shutil
                    shutil.rmtree(wine_dir)
                    self._log(f"  Удалена директория: {wine_dir}")
            # ОБНОВЛЯЕМ СТАТУС: устанавливаем 'missing'
            self._update_status(component_id, 'missing')
            return True
        else:
            self._log(f"ОШИБКА удаления пакета {config['name']}", "ERROR")
            # ОБНОВЛЯЕМ СТАТУС: устанавливаем 'error'
            self._update_status(component_id, 'error')
            return False
    
    def check_status(self, component_id: str, config: dict) -> bool:
        """Проверка статуса Wine пакета"""
        check_paths = config.get('check_paths', [])
        for path in check_paths:
            if os.path.exists(path):
                return True
        return False
```

**Чеклист:**
- [ ] Класс создан и наследуется от `ComponentHandler`
- [ ] Метод `install()` обновляет статусы через `_update_status()`
- [ ] Метод `uninstall()` обновляет статусы через `_update_status()`
- [ ] Используется `_run_process()` вместо прямого `subprocess.run()`
- [ ] Используется `_log()` для логирования
- [ ] Используется `_update_progress()` для прогресса
- [ ] Код проверен на синтаксис

**ПРИМЕЧАНИЕ:** Остальные handlers (WineEnvironmentHandler, WinetricksHandler, SystemConfigHandler, ApplicationHandler) создаются аналогично с обязательным обновлением статусов через `_update_status()`.

---

### ЭТАП 3: ИНТЕГРАЦИЯ HANDLERS В UNIVERSALINSTALLER (Приоритет: КРИТИЧЕСКИЙ)

#### Шаг 3.1: Модификация __init__() UniversalInstaller
**Местоположение:** Метод `__init__()` класса `UniversalInstaller` (строка 4866)

**Детальная проработка:**

**Текущий код:**
```python
def __init__(self, logger=None, callback=None):
```

**Новый код:**
```python
def __init__(self, 
             logger=None, 
             callback=None,
             use_handlers=False,  # НОВЫЙ ПАРАМЕТР
             use_minimal_winetricks=True,  # НОВЫЙ ПАРАМЕТР
             universal_runner=None,  # НОВЫЙ ПАРАМЕТР
             progress_manager=None,  # НОВЫЙ ПАРАМЕТР
             dual_logger=None,  # НОВЫЙ ПАРАМЕТР
             status_manager=None):  # НОВЫЙ ПАРАМЕТР: ComponentStatusManager
    """
    Инициализация универсального установщика
    
    Args:
        logger: Экземпляр класса Logger для логирования
        callback: Функция для обновления статуса в GUI (опционально)
        use_handlers: Использовать новую архитектуру handlers (по умолчанию False)
        use_minimal_winetricks: Использовать минимальный winetricks (по умолчанию True)
        universal_runner: UniversalProcessRunner для запуска процессов
        progress_manager: UniversalProgressManager для прогресса
        dual_logger: DualStreamLogger для двойных потоков логирования
        status_manager: ComponentStatusManager для управления статусами
    """
   
    self.logger = logger
    self.callback = callback
    self.use_handlers = use_handlers
    self.use_minimal_winetricks = use_minimal_winetricks
    
    # Получаем абсолютный путь к директории скрипта
    import sys
    if os.path.isabs(sys.argv[0]):
        script_path = sys.argv[0]
    else:
        script_path = os.path.join(os.getcwd(), sys.argv[0])
    
    script_dir = os.path.dirname(os.path.abspath(script_path))
    self.astrapack_dir = os.path.join(script_dir, "AstraPack")
    
    # Определяем домашнюю директорию РЕАЛЬНОГО пользователя
    real_user = os.environ.get('SUDO_USER')
    if real_user and real_user != 'root':
        import pwd
        self.home = pwd.getpwnam(real_user).pw_dir
    else:
        self.home = os.path.expanduser("~")
    
    self.wineprefix = os.path.join(self.home, ".wine-astraregul")
    
    # Инициализируем специализированные установщики (для совместимости)
    self.wine_installer = None
    self.winetricks_manager = WinetricksManager(self.astrapack_dir, use_minimal=self.use_minimal_winetricks)

    # Инфраструктура
    self.universal_runner = universal_runner or get_global_universal_runner()
    self.progress_manager = progress_manager  # Может быть None, если не передан
    self.dual_logger = dual_logger or (globals().get('_global_dual_logger') if '_global_dual_logger' in globals() else None)
    self.status_manager = status_manager  # КРИТИЧНО: ComponentStatusManager
    
    # Реестр обработчиков компонентов
    self.handlers = {}
    if self.use_handlers:
        self._register_handlers()
```

**Чеклист:**
- [ ] Параметры добавлены в `__init__()`
- [ ] Параметры сохранены в `self`
- [ ] `_register_handlers()` вызывается если `use_handlers=True`
- [ ] Код проверен на синтаксис

#### Шаг 3.2: Регистрация handlers
**Местоположение:** После `__init__()` класса `UniversalInstaller`

**Код для вставки:**
```python
def _register_handlers(self):
    """Регистрация всех обработчиков компонентов"""
    if not self.status_manager:
        self._log("ВНИМАНИЕ: ComponentStatusManager не передан, статусы не будут обновляться", "WARNING")
    
    # Общие параметры для всех handlers
    common_params = {
        'astrapack_dir': self.astrapack_dir,
        'logger': self.logger,
        'callback': self.callback,
        'universal_runner': self.universal_runner,
        'progress_manager': self.progress_manager,
        'dual_logger': self.dual_logger,
        'status_manager': self.status_manager  # КРИТИЧНО
    }
    
    # Регистрируем handlers
    self.handlers['wine_packages'] = WinePackageHandler(**common_params)
    self.handlers['wine_environment'] = WineEnvironmentHandler(**common_params)
    self.handlers['winetricks'] = WinetricksHandler(
        use_minimal=self.use_minimal_winetricks,
        **common_params
    )
    self.handlers['system_config'] = SystemConfigHandler(**common_params)
    self.handlers['application'] = ApplicationHandler(**common_params)
    
    self._log("Handlers зарегистрированы: %s" % ', '.join(self.handlers.keys()))
```

**Чеклист:**
- [ ] Метод `_register_handlers()` создан
- [ ] Все handlers зарегистрированы
- [ ] ComponentStatusManager передается во все handlers
- [ ] UniversalProgressManager передается во все handlers
- [ ] Код проверен на синтаксис

#### Шаг 3.3: Модификация метода install_component()
**Местоположение:** Метод `install_component()` класса `UniversalInstaller` (строка 5022)

**Детальная проработка:**

**Текущий код (примерно):**
```python
def install_component(self, component_id):
    if component_id not in COMPONENTS_CONFIG:
        self._log("Ошибка: компонент '%s' не найден в конфигурации" % component_id, "ERROR")
        return False
    
    config = COMPONENTS_CONFIG[component_id]
    install_method = config['install_method']
    
    # ... старая логика через install_method ...
```

**Новый код:**
```python
def install_component(self, component_id):
    """
    Установка одного компонента
    
    Args:
        component_id: ID компонента
        
    Returns:
        bool: True если установка успешна, False если ошибка
    """
    if component_id not in COMPONENTS_CONFIG:
        self._log("Ошибка: компонент '%s' не найден в конфигурации" % component_id, "ERROR")
        return False
    
    config = COMPONENTS_CONFIG[component_id]
    
    # НОВАЯ ЛОГИКА: Используем handlers если включен флаг
    if self.use_handlers:
        category = config.get('category')
        if not category:
            self._log("Ошибка: компонент '%s' не имеет категории" % component_id, "ERROR")
            return False
        
        if category in self.handlers:
            handler = self.handlers[category]
            # Устанавливаем статус 'pending' перед установкой (если есть status_manager)
            if self.status_manager:
                self.status_manager.update_component_status(component_id, 'pending')
            # Вызываем handler
            result = handler.install(component_id, config)
            return result
        else:
            self._log("Ошибка: неизвестная категория '%s' для компонента '%s'" % (category, component_id), "ERROR")
            if self.status_manager:
                self.status_manager.update_component_status(component_id, 'error')
            return False
    
    # СТАРАЯ ЛОГИКА: Используем install_method (оставляем для совместимости)
    install_method = config['install_method']
    
    self._log("Установка компонента: %s (метод: %s)" % (config['name'], install_method))
    
    try:
        if install_method == 'package_manager':
            return self._install_package_manager(component_id, config)
        elif install_method == 'system_config':
            return self._install_system_config(component_id, config)
        elif install_method == 'wine_init':
            return self._install_wine_init(component_id, config)
        elif install_method == 'winetricks':
            return self._install_winetricks(component_id, config)
        elif install_method == 'wine_executable':
            return self._install_wine_executable(component_id, config)
        elif install_method == 'script_creation':
            return self._install_script_creation(component_id, config)
        elif install_method == 'desktop_shortcut':
            return self._install_desktop_shortcut(component_id, config)
        else:
            self._log("Неизвестный метод установки: %s" % install_method, "ERROR")
            return False
    except Exception as e:
        self._log("Ошибка установки компонента %s: %s" % (component_id, str(e)), "ERROR")
        return False
```

**Чеклист:**
- [ ] Проверка `use_handlers` добавлена
- [ ] Новая логика использует handlers
- [ ] Статус 'pending' устанавливается перед установкой
- [ ] Старая логика сохранена и работает
- [ ] Обработка ошибок работает для обоих путей
- [ ] Код проверен на синтаксис

#### Шаг 3.4: Модификация метода uninstall_component()
**Местоположение:** Метод `uninstall_component()` класса `UniversalInstaller` (строка 5063)

**Что делать:** Аналогично `install_component()`, но с использованием `handler.uninstall()`

**Чеклист:**
- [ ] Аналогично шагу 3.3
- [ ] Статус 'removing' устанавливается перед удалением

#### Шаг 3.5: Модификация метода install_components()
**Местоположение:** Метод `install_components()` класса `UniversalInstaller` (строка ~5104)

**Что делать:**
1. Добавить обновление статусов 'pending' для выбранных компонентов перед установкой
2. Убедиться, что статусы обновляются через ComponentStatusManager

**Код для модификации:**
```python
def install_components(self, component_ids):
    """
    Установка компонентов с учетом зависимостей
    
    Args:
        component_ids: Список ID компонентов для установки
        
    Returns:
        bool: True если все компоненты установлены успешно, False если есть ошибки
    """
    self._log("Начало установки компонентов: %s" % ', '.join(component_ids))
    
    # Разрешаем зависимости
    resolved_components = self.resolve_dependencies(component_ids)
    self._log("Компоненты с учетом зависимостей: %s" % ', '.join(resolved_components))
    
    # НОВОЕ: Устанавливаем статус 'pending' для выбранных компонентов
    if self.status_manager:
        for component_id in component_ids:
            if component_id in COMPONENTS_CONFIG:
                self.status_manager.update_component_status(component_id, 'pending')
    
    success = True
    for component_id in resolved_components:
        if not self.check_component_status(component_id):
            if not self.install_component(component_id):
                success = False
                # Компонент уже установил свой статус через handler
        else:
            self._log("Компонент '%s' уже установлен, пропускаем" % component_id)
    
    if success:
        self._log("Все компоненты установлены успешно")
    else:
        self._log("Некоторые компоненты не установлены", "ERROR")
    
    return success
```

**Чеклист:**
- [ ] Статус 'pending' устанавливается для выбранных компонентов
- [ ] Зависимости разрешаются правильно
- [ ] Статусы обновляются через handlers

---

### ЭТАП 4: ИНТЕГРАЦИЯ В GUI (Приоритет: ВЫСОКИЙ)

#### Шаг 4.1: Создание UniversalProgressManager для UniversalInstaller
**Местоположение:** Метод `__init__()` класса `AutomationGUI` (после строки 7356)

**Детальная проработка:**

**Проблема:** SystemUpdater имеет свой UniversalProgressManager с `process_type='system_update'`. Нужен отдельный для UniversalInstaller с `process_type='wine_install'`.

**Решение:** Создать отдельный UniversalProgressManager для UniversalInstaller или использовать общий (но с разными `process_type`).

**Код для вставки:**
```python
# Создаем SystemUpdater ПОСЛЕ создания universal_runner
self.system_updater = SystemUpdater(self.universal_runner)
self.system_updater.gui_instance = self  # Передаем ссылку на GUI

# Устанавливаем парсер в UniversalProcessRunner после создания SystemUpdater
self.universal_runner.parser = self.system_updater.system_update_parser

# Передаем ссылки на детальные бары для прямого обновления
self.system_updater.download_progress = self.download_progress
self.system_updater.unpack_progress = self.unpack_progress
self.system_updater.config_progress = self.config_progress
self.system_updater.download_label = self.download_label
self.system_updater.unpack_label = self.unpack_label
self.system_updater.config_label = self.config_label

# НОВОЕ: Создаем UniversalProgressManager для UniversalInstaller
def send_component_progress_to_gui(progress_data):
    """Отправка обновления прогресса установки компонентов в GUI"""
    try:
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
        
        # Формируем данные для GUI
        gui_data = {
            'stage_name': progress_data.get('stage_name', 'Неизвестно'),
            'stage_progress': progress_data.get('stage_progress', 0),
            'global_progress': progress_data.get('global_progress', 0),
            'details': progress_data.get('details', ''),
            'timestamp': timestamp
        }
        
        # Отправляем через universal_runner
        if hasattr(self, 'universal_runner') and self.universal_runner:
            if hasattr(self.universal_runner, 'gui_log_callback') and self.universal_runner.gui_log_callback:
                try:
                    self.universal_runner.gui_log_callback("[COMPONENT_PROGRESS] " + str(gui_data))
                except Exception as e:
                    print(f"[ERROR] Ошибка вызова gui_log_callback: {e}")
    except Exception as e:
        print(f"[ERROR] Ошибка в send_component_progress_to_gui: {e}")

# Создаем UniversalProgressManager для компонентов
self.component_progress_manager = UniversalProgressManager(
    universal_runner=self.universal_runner,
    gui_callback=send_component_progress_to_gui
)
```

**Чеклист:**
- [ ] UniversalProgressManager создан для компонентов
- [ ] Callback настроен для отправки в GUI
- [ ] Код проверен на синтаксис

#### Шаг 4.2: Обновление создания UniversalInstaller в GUI
**Местоположение:** Метод `__init__()` класса `AutomationGUI` (строка 6542)

**Текущий код:**
```python
self.universal_installer = UniversalInstaller(callback=self._component_status_callback)
```

**Новый код:**
```python
# Инициализируем новую универсальную архитектуру
self.component_status_manager = ComponentStatusManager(callback=self._component_status_callback)

# Создаем UniversalInstaller с handlers
self.universal_installer = UniversalInstaller(
    callback=self._component_status_callback,
    use_handlers=True,  # Включаем новую архитектуру
    use_minimal_winetricks=self.use_minimal_winetricks.get(),
    universal_runner=self.universal_runner,
    progress_manager=self.component_progress_manager,  # НОВОЕ: UniversalProgressManager для компонентов
    dual_logger=_global_dual_logger if '_global_dual_logger' in globals() else None,
    status_manager=self.component_status_manager  # КРИТИЧНО: ComponentStatusManager
)
```

**Чеклист:**
- [ ] ComponentStatusManager создан перед UniversalInstaller
- [ ] UniversalInstaller создан с `use_handlers=True`
- [ ] ComponentStatusManager передан в UniversalInstaller
- [ ] UniversalProgressManager передан в UniversalInstaller
- [ ] dual_logger передан из глобальной переменной
- [ ] Код проверен на синтаксис

#### Шаг 4.3: Улучшение таблицы компонентов (визуализация зависимостей)
**Местоположение:** Метод `_update_wine_status()` класса `AutomationGUI` (строка 9106)

**Детальная проработка:**

**Что нужно сделать:**
1. Отображать компоненты в виде дерева зависимостей
2. Использовать символы `├─`, `└─`, `│` для визуализации
3. Показывать статусы зависимостей (родительские/дочерние)
4. Раскрашивать зависимости по статусу

**Пример структуры:**
```
☐ Wine Astraregul          [OK]    /opt/wine-astraregul/bin/wine
☐ WINEPREFIX               [OK]    ~/.wine-astraregul
  ├─ Wine Mono             [OK]    drive_c/windows/mono/...
  ├─ .NET Framework 4.8    [INSTALL] Установка... 45%
  └─ Visual C++ 2013        [PENDING] Ожидание...
☐ Astra.IDE                [OK]    drive_c/Program Files/...
  ├─ Скрипт запуска        [OK]    ~/start-astraide.sh
  └─ Ярлык рабочего стола   [OK]    ~/Desktop/AstraRegul.desktop
```

**Код для модификации:**

```python
def _update_wine_status(self):
    """Обновление статуса в GUI с использованием универсальной архитектуры"""
    # ... существующий код сохранения чекбоксов ...
    
    # Используем новую универсальную архитектуру для получения статусов
    all_status = self.component_status_manager.get_all_components_status()
    
    # НОВОЕ: Строим дерево зависимостей
    def build_dependency_tree():
        """Строит дерево зависимостей компонентов"""
        tree = {}
        # Первый проход: создаем узлы
        for component_id, config in COMPONENTS_CONFIG.items():
            tree[component_id] = {
                'config': config,
                'children': [],
                'parent': None
            }
        
        # Второй проход: связываем зависимости
        for component_id, node in tree.items():
            dependencies = node['config'].get('dependencies', [])
            for dep_id in dependencies:
                if dep_id in tree:
                    tree[dep_id]['children'].append(component_id)
                    node['parent'] = dep_id
        
        return tree
    
    # Строим дерево
    dependency_tree = build_dependency_tree()
    
    # НОВОЕ: Функция для отображения компонента с учетом дерева
    def render_component(component_id, indent=0, is_last=False, prefix=""):
        """Отображает компонент с учетом дерева зависимостей"""
        if component_id not in COMPONENTS_CONFIG:
            return
        
        config = COMPONENTS_CONFIG[component_id]
        status_text, status_tag = all_status.get(component_id, ('[---]', 'missing'))
        
        # Определяем путь для отображения
        check_paths = config['check_paths']
        display_path = check_paths[0] if check_paths else 'N/A'
        
        # Определяем, есть ли чекбокс
        has_checkbox = config.get('gui_selectable', False)
        checkbox = '☐' if has_checkbox else '  '
        
        # Определяем символ для дерева
        if indent == 0:
            component_display_name = config['name']
        else:
            symbol = '└─' if is_last else '├─'
            component_display_name = f"  {prefix}{symbol} {config['name']}"
        
        # Добавляем компонент в таблицу
        item_id = self.wine_tree.insert('', self.tk.END, values=(
            checkbox,
            component_display_name,
            status_text,
            display_path
        ))
        
        if has_checkbox:
            self.wine_checkboxes[item_id] = False
        
        # Цветовое выделение
        self.wine_tree.item(item_id, tags=(status_tag))
        
        # Рекурсивно отображаем дочерние компоненты
        children = dependency_tree[component_id]['children']
        new_prefix = prefix + ('   ' if is_last else '│  ')
        for i, child_id in enumerate(children):
            is_last_child = (i == len(children) - 1)
            render_component(child_id, indent + 1, is_last_child, new_prefix)
    
    # Отображаем компоненты по категориям (корневые узлы)
    root_components = []
    for component_id, node in dependency_tree.items():
        if node['parent'] is None:  # Корневой узел
            root_components.append((component_id, node['config'].get('priority', 999)))
    
    # Сортируем по приоритету
    root_components.sort(key=lambda x: x[1])
    
    # Отображаем корневые компоненты и их дочерние
    for i, (component_id, _) in enumerate(root_components):
        is_last = (i == len(root_components) - 1)
        render_component(component_id, indent=0, is_last=is_last, prefix="")
    
    # ... остальной существующий код ...
```

**Чеклист:**
- [ ] Функция `build_dependency_tree()` создана
- [ ] Функция `render_component()` создана
- [ ] Компоненты отображаются в виде дерева
- [ ] Символы `├─`, `└─`, `│` используются правильно
- [ ] Статусы отображаются корректно
- [ ] Код проверен на синтаксис

---

### ЭТАП 5: ТЕСТИРОВАНИЕ (Приоритет: КРИТИЧЕСКИЙ)

#### Шаг 5.1: Тестирование каждого handler по отдельности
(См. оригинальный план, детализация аналогична)

#### Шаг 5.2: Интеграционное тестирование
(См. оригинальный план, детализация аналогична)

#### Шаг 5.3: Тестирование статусов
**Новое тестирование:**

**Проверка обновления статусов:**
- [ ] Статус 'pending' устанавливается при выборе компонента
- [ ] Статус 'installing' устанавливается во время установки
- [ ] Статус 'ok' устанавливается после успешной установки
- [ ] Статус 'error' устанавливается при ошибке
- [ ] Статус 'removing' устанавливается во время удаления
- [ ] Статус 'missing' устанавливается после успешного удаления
- [ ] GUI обновляется в реальном времени при изменении статусов

**Проверка разделения процессов:**
- [ ] SystemUpdater использует `process_type='system_update'`
- [ ] UniversalInstaller использует `process_type='wine_install'`
- [ ] GUI различает процессы по `process_type`
- [ ] Прогресс-бары обновляются независимо для разных процессов

---

### ЭТАП 6: МИГРАЦИЯ НА НОВУЮ АРХИТЕКТУРУ (Приоритет: СРЕДНИЙ)
(См. оригинальный план, детализация аналогична)

---

### ЭТАП 7: УДАЛЕНИЕ СТАРОГО КОДА (Приоритет: НИЗКИЙ)
(См. оригинальный план, детализация аналогична)

---

### ЭТАП 8: ФИНАЛИЗАЦИЯ (Приоритет: СРЕДНИЙ)
(См. оригинальный план, детализация аналогична)

---

## 🔍 КРИТЕРИИ УСПЕХА

### Функциональные критерии:
- ✅ Все существующие компоненты устанавливаются/удаляются корректно
- ✅ Новые компоненты можно добавлять только через handlers
- ✅ Логирование работает через все каналы (файл, терминал, GUI)
- ✅ Прогресс-бары отображаются для всех операций
- ✅ Статусы компонентов обновляются в реальном времени
- ✅ Зависимости визуализируются в таблице
- ✅ Мониторинг работает для всех процессов
- ✅ Зависимости разрешаются автоматически

### Технические критерии:
- ✅ Код стал короче (удалено ~2037 строк дублирующего кода)
- ✅ Код стал понятнее (логика инкапсулирована в handlers)
- ✅ Код стал расширяемее (новый handler = новый тип компонентов)
- ✅ Нет дублирования логики между handlers
- ✅ ComponentStatusManager и UniversalProgressManager разделены правильно

### Качественные критерии:
- ✅ Все тесты проходят
- ✅ Нет регрессий в функционале
- ✅ Код задокументирован
- ✅ Комментарии понятны новому разработчику

---

## ⚠️ РИСКИ И СПОСОБЫ ИХ МИНИМИЗАЦИИ

### Риск 1: Поломка существующего функционала
**Минимизация:**
- Использовать флаг `use_handlers` для постепенного переключения
- Сохранить старую логику до полного тестирования
- Регрессионное тестирование на каждом этапе

### Риск 2: Путаница между ComponentStatusManager и UniversalProgressManager
**Минимизация:**
- Четкое разделение: ComponentStatusManager - только компоненты, UniversalProgressManager - все процессы
- Использование `process_type` для различения процессов
- Детальная документация разделения ответственности

### Риск 3: Потеря логирования или прогресса
**Минимизация:**
- Каждый handler использует инфраструктуру через базовый класс
- Тестировать логирование и прогресс для каждого handler
- Проверять все каналы вывода

### Риск 4: Ошибки в handlers
**Минимизация:**
- Пошаговое тестирование каждого handler
- Unit-тесты для критических методов
- Интеграционные тесты для полного цикла

### Риск 5: Проблемы с миграцией
**Минимизация:**
- Поэтапная миграция (один handler за раз)
- Возможность отката через `use_handlers=False`
- Детальное логирование всех операций

---

## 📚 СПРАВОЧНАЯ ИНФОРМАЦИЯ

### Связь компонентов:
```
COMPONENTS_CONFIG['category']
    ↓
UniversalInstaller.handlers['category']
    ↓
ComponentHandler.install/uninstall
    ├─→ ComponentStatusManager (статусы компонентов)
    ├─→ UniversalProgressManager (прогресс, process_type='wine_install')
    ├─→ UniversalProcessRunner (процессы)
    │   └─→ DualStreamLogger (логирование через log_info/log_error)
    └─→ print() / universal_print() → DualStreamLogger (прямое логирование)
    
ВАЖНО: Вся инфраструктура логирования сохраняется:
- print() переопределен через builtins.print = universal_print (строка 794)
- universal_print() → DualStreamLogger (RAW и ANALYSIS потоки)
- UniversalProcessRunner.log_info/log_error → DualStreamLogger
- Handlers могут использовать как _log(), так и прямой print()
```

### Разделение процессов:
```
SystemUpdater
    └─→ UniversalProgressManager (process_type='system_update')
    
UniversalInstaller
    └─→ UniversalProgressManager (process_type='wine_install')
    └─→ ComponentStatusManager (статусы компонентов)
```

### Порядок установки компонентов:
1. `wine_packages` (Wine пакеты)
2. `system_config` (ptrace_scope)
3. `wine_environment` (WINEPREFIX)
4. `winetricks` (winetricks компоненты)
5. `application` (Astra.IDE + скрипты + ярлыки)

### Порядок удаления компонентов:
1. `application` (приложение + скрипты + ярлыки)
2. `winetricks` (winetricks компоненты)
3. `wine_environment` (WINEPREFIX)
4. `system_config` (откат настроек)
5. `wine_packages` (Wine пакеты)

---

## 📝 ЗАМЕТКИ ДЛЯ РАЗРАБОТЧИКА

### Важные моменты:
1. **Всегда тестируй после каждого шага** - не переходи к следующему этапу без проверки
2. **Используй git** - коммить после каждого успешного шага
3. **Документируй проблемы** - если что-то не работает, зафиксируй в комментариях
4. **Не торопись** - лучше медленно, но правильно, чем быстро с ошибками
5. **Помни о разделении** - ComponentStatusManager для компонентов, UniversalProgressManager для всех процессов
6. **Инфраструктура логирования сохраняется** - print() переопределен везде, DualStreamLogger используется для всех логов

### Команды для проверки:
```bash
# Проверка синтаксиса
python3 -m py_compile astra_automation.py

# Поиск использования класса
grep -n "WineInstaller" astra_automation.py
grep -n "ComponentStatusManager" astra_automation.py
grep -n "UniversalProgressManager" astra_automation.py

# Запуск тестов (если есть)
./test-environment/test_all_components.sh
```

---

## ✅ ЧЕКЛИСТ ФИНАЛЬНОЙ ПРОВЕРКИ

Перед завершением рефакторинга проверить:
- [ ] Все handlers реализованы и работают
- [ ] Все тесты проходят
- [ ] Статусы обновляются в реальном времени
- [ ] Зависимости визуализируются в таблице
- [ ] ComponentStatusManager и UniversalProgressManager разделены правильно
- [ ] Старый код удален
- [ ] Документация обновлена
- [ ] Нет дублирования кода
- [ ] Логирование работает
- [ ] Прогресс-бары работают
- [ ] GUI работает корректно
- [ ] Коммит создан с описанием изменений
- [ ] Ветка слита в основную

---

**КОНЕЦ ПЛАНА РЕФАКТОРИНГА**

Дата создания плана: 2025-11-05
Версия плана: 2.5.0
Статус: ДЕТАЛЬНЫЙ ПЛАН ГОТОВ К РЕАЛИЗАЦИИ
