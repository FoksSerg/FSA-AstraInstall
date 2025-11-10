# Версия проекта: V2.4.106 (2025.11.07)

# ПЛАН УДАЛЕНИЯ UniversalInstaller И ПЕРЕНОСА ФУНКЦИОНАЛЬНОСТИ

## ЦЕЛЬ
Полностью удалить класс `UniversalInstaller` и перенести всю его функциональность в соответствующие классы:
- Методы управления процессами Wine → в `ComponentHandler`
- Координация установки/удаления → в `AutomationGUI`
- Handlers → создавать напрямую в `AutomationGUI`

---

## ЭТАП 1: ПЕРЕНОС МЕТОДОВ УПРАВЛЕНИЯ ПРОЦЕССАМИ WINE В ComponentHandler

### 1.1. Перенести методы из UniversalInstaller в ComponentHandler

**Методы для переноса (строки 6071-6267):**

1. **`_check_wine_processes_running()` (6071-6117)**
   - Перенести в `ComponentHandler` после метода `_stop_processes()` (строка ~810)
   - Изменить: заменить `[UniversalInstaller]` на `[ComponentHandler]` в сообщениях
   - Использовать `self.wineprefix` из `ComponentHandler` (уже есть)

2. **`_wait_for_all_processes_terminated()` (6119-6156)**
   - Перенести в `ComponentHandler` после `_check_wine_processes_running()`
   - Изменить: заменить `[UniversalInstaller]` на `[ComponentHandler]` в сообщениях
   - Использовать `self._check_wine_processes_running()` (уже будет в `ComponentHandler`)

3. **`_force_terminate_wine_processes()` (6158-6200)**
   - Перенести в `ComponentHandler` после `_wait_for_all_processes_terminated()`
   - Изменить: заменить `[UniversalInstaller]` на `[ComponentHandler]` в сообщениях

4. **`_terminate_wineserver()` (6202-6237)**
   - Перенести в `ComponentHandler` после `_force_terminate_wine_processes()`
   - Изменить: заменить `[UniversalInstaller]` на `[ComponentHandler]` в сообщениях
   - Использовать `self.wineprefix` из `ComponentHandler`

5. **`_ensure_no_conflicting_processes()` (6239-6267)**
   - Перенести в `ComponentHandler` после `_terminate_wineserver()`
   - Изменить: заменить `[UniversalInstaller]` на `[ComponentHandler]` в сообщениях
   - Использовать `self._check_wine_processes_running()` и `self._wait_for_all_processes_terminated()`

**Местоположение в ComponentHandler:**
- После метода `_stop_processes()` (строка ~810)
- Все методы будут доступны всем handlers, так как они наследуются от `ComponentHandler`

---

## ЭТАП 2: ПЕРЕНОС КООРДИНАЦИИ УСТАНОВКИ/УДАЛЕНИЯ В AutomationGUI

### 2.1. Перенести методы координации из UniversalInstaller в AutomationGUI

**Методы для переноса:**

1. **`install_components()` (6497-6602)**
   - Перенести в `AutomationGUI._install_components()`
   - Изменения:
     - Заменить `self.handlers` на `self.component_handlers`
     - Заменить `self._check_wine_processes_running()` на `handler._check_wine_processes_running()` (любой handler)
     - Заменить `self._wait_for_all_processes_terminated()` на `handler._wait_for_all_processes_terminated()`
     - Заменить `self._terminate_wineserver()` на `handler._terminate_wineserver()`
     - Заменить `self._ensure_no_conflicting_processes()` на `handler._ensure_no_conflicting_processes()`
     - Заменить `self.resolve_dependencies()` на `resolve_dependencies_for_install()` (глобальная функция)
     - Заменить `self.check_component_status()` на `check_component_status(component_id, wineprefix_path=self._get_wineprefix())`
     - Заменить `self.status_manager` на `self.component_status_manager`
     - Заменить `self.install_component()` на `self._install_component()`

2. **`uninstall_components()` (6605-6755)**
   - Перенести в `AutomationGUI._uninstall_components()`
   - Изменения:
     - Заменить `self.handlers` на `self.component_handlers`
     - Заменить `self._check_wine_processes_running()` на `handler._check_wine_processes_running()`
     - Заменить `self._wait_for_all_processes_terminated()` на `handler._wait_for_all_processes_terminated()`
     - Заменить `self._terminate_wineserver()` на `handler._terminate_wineserver()`
     - Заменить `self._ensure_no_conflicting_processes()` на `handler._ensure_no_conflicting_processes()`
     - Заменить `resolve_dependencies_for_uninstall()` (уже глобальная функция)
     - Заменить `self.check_component_status()` на `check_component_status(component_id, wineprefix_path=self._get_wineprefix())`
     - Заменить `self.status_manager` на `self.component_status_manager`
     - Заменить `self.uninstall_component()` на `self._uninstall_component()`

3. **`install_component()` (6345-6418)**
   - Перенести в `AutomationGUI._install_component()`
   - Изменения:
     - Удалить старую логику (строки 6392-6418) - оставить только логику с handlers
     - Заменить `self.handlers` на `self.component_handlers`
     - Заменить `self.status_manager` на `self.component_status_manager`

4. **`uninstall_component()` (6421-6494)**
   - Перенести в `AutomationGUI._uninstall_component()`
   - Изменения:
     - Удалить старую логику (строки 6468-6494) - оставить только логику с handlers
     - Заменить `self.handlers` на `self.component_handlers`
     - Заменить `self.status_manager` на `self.component_status_manager`

### 2.2. Перенести регистрацию handlers в AutomationGUI

**Метод `_register_handlers()` (6041-6069) → `AutomationGUI._register_component_handlers()`**

**Изменения:**
- Создать `self.component_handlers = {}` в `AutomationGUI.__init__()` (после строки 8148)
- Использовать `self.component_status_manager` вместо `self.status_manager`
- Использовать `self.component_progress_manager` вместо `self.progress_manager`
- Использовать `self.universal_runner` вместо `self.universal_runner`
- Использовать `self._get_astrapack_dir()` для получения пути к AstraPack
- Использовать `self._get_wineprefix()` для получения пути к WINEPREFIX

**Код метода:**
```python
def _register_component_handlers(self):
    """Регистрация всех обработчиков компонентов"""
    if not self.component_status_manager:
        print("ComponentStatusManager не передан, статусы не будут обновляться", level='WARNING')
    
    # Общие параметры для всех handlers
    common_params = {
        'astrapack_dir': self._get_astrapack_dir(),
        'logger': None,  # Не используется в новой архитектуре
        'callback': self._component_status_callback,
        'universal_runner': self.universal_runner,
        'progress_manager': self.component_progress_manager,
        'dual_logger': globals().get('_global_dual_logger') if '_global_dual_logger' in globals() else None,
        'status_manager': self.component_status_manager  # КРИТИЧНО
    }
    
    # Регистрируем handlers
    self.component_handlers['wine_packages'] = WinePackageHandler(**common_params)
    self.component_handlers['wine_environment'] = WineEnvironmentHandler(**common_params)
    self.component_handlers['winetricks'] = WinetricksHandler(
        use_minimal=self.use_minimal_winetricks.get() if hasattr(self, 'use_minimal_winetricks') else True,
        **common_params
    )
    self.component_handlers['system_config'] = SystemConfigHandler(**common_params)
    self.component_handlers['application'] = ApplicationHandler(**common_params)
    self.component_handlers['apt_packages'] = AptPackageHandler(**common_params)
    self.component_handlers['wine_application'] = WineApplicationHandler(**common_params)
    
    print("Handlers зарегистрированы: %s" % ', '.join(self.component_handlers.keys()))
```

---

## ЭТАП 3: ИЗМЕНЕНИЕ ИСПОЛЬЗОВАНИЯ В AutomationGUI

### 3.1. Заменить создание UniversalInstaller (строки 8150-8161)

**Было:**
```python
# Создаем UniversalInstaller с handlers
# ВАЖНО: component_progress_manager будет создан позже в create_widgets()
# поэтому передаем None, а затем обновим после создания
self.universal_installer = UniversalInstaller(
    callback=self._component_status_callback,
    use_handlers=True,  # Включаем новую архитектуру
    use_minimal_winetricks=self.use_minimal_winetricks.get() if hasattr(self, 'use_minimal_winetricks') else True,
    universal_runner=None,  # Будет установлен позже
    progress_manager=None,  # Будет установлен позже (component_progress_manager)
    dual_logger=globals().get('_global_dual_logger') if '_global_dual_logger' in globals() else None,
    status_manager=self.component_status_manager  # КРИТИЧНО: ComponentStatusManager
)
```

**Станет:**
```python
# Создаем handlers напрямую (будет зарегистрировано позже в create_widgets())
self.component_handlers = {}
# Регистрация handlers будет выполнена в create_widgets() после создания component_progress_manager
```

### 3.2. Заменить использование методов (строки 9324-9330)

**Было:**
```python
# НОВОЕ: Обновляем universal_installer с правильными параметрами
self.universal_installer.universal_runner = self.universal_runner
self.universal_installer.progress_manager = self.component_progress_manager
self.universal_installer.dual_logger = globals().get('_global_dual_logger') if '_global_dual_logger' in globals() else None
# Перерегистрируем handlers с правильными параметрами
if self.universal_installer.use_handlers:
    self.universal_installer._register_handlers()
```

**Станет:**
```python
# Регистрируем handlers с правильными параметрами
self._register_component_handlers()
```

### 3.3. Заменить вызовы методов установки/удаления

**Строка 11815:**
```python
# Было:
success = self.universal_installer.install_components(selected)

# Станет:
success = self._install_components(selected)
```

**Строка 12564:**
```python
# Было:
success = self.universal_installer.uninstall_components(components_to_remove)

# Станет:
success = self._uninstall_components(components_to_remove)
```

**Строка 12627:**
```python
# Было:
success = self.universal_installer.uninstall_components(selected_ids)

# Станет:
success = self._uninstall_components(selected_ids)
```

### 3.4. Заменить вызовы методов разрешения зависимостей и проверки статуса

**Строка 11781:**
```python
# Было:
resolved_components = self.universal_installer.resolve_dependencies(selected)

# Станет:
resolved_components = resolve_dependencies_for_install(selected)
```

**Строка 11787:**
```python
# Было:
is_installed = self.universal_installer.check_component_status(component_id)

# Станет:
is_installed = check_component_status(component_id, wineprefix_path=self._get_wineprefix())
```

**Строка 12479:**
```python
# Было:
is_installed = self.universal_installer.check_component_status(component_id)

# Станет:
is_installed = check_component_status(component_id, wineprefix_path=self._get_wineprefix())
```

### 3.5. Заменить доступ к методам управления процессами

**Строка 8543:**
```python
# Было:
if not hasattr(self, 'universal_installer') or not self.universal_installer:
    return wine_processes

try:
    # Получаем процессы Wine через UniversalInstaller
    running_processes = self.universal_installer._check_wine_processes_running()

# Станет:
if not self.component_handlers:
    return wine_processes

try:
    # Используем любой handler для доступа к методам управления процессами
    handler = list(self.component_handlers.values())[0]
    running_processes = handler._check_wine_processes_running()
```

### 3.6. Заменить доступ к status_manager

**Строки 8422-8427:**
```python
# Было:
# Проверяем наличие активных операций в UniversalInstaller
if hasattr(self, 'universal_installer') and self.universal_installer:
    status_manager = getattr(self.universal_installer, 'status_manager', None)
    if status_manager:
        installing = getattr(status_manager, 'installing', set())
        removing = getattr(status_manager, 'removing', set())

# Станет:
# Проверяем наличие активных операций через ComponentStatusManager
if hasattr(self, 'component_status_manager') and self.component_status_manager:
    status_manager = self.component_status_manager
    if status_manager:
        installing = getattr(status_manager, 'installing', set())
        removing = getattr(status_manager, 'removing', set())
```

**Строки 10632-10637:**
```python
# Было:
if hasattr(self, 'universal_installer') and self.universal_installer:
    status_manager = getattr(self.universal_installer, 'status_manager', None)
    if status_manager:
        # Получаем компоненты в процессе установки/удаления
        installing = getattr(status_manager, 'installing', set())
        removing = getattr(status_manager, 'removing', set())

# Станет:
if hasattr(self, 'component_status_manager') and self.component_status_manager:
    status_manager = self.component_status_manager
    if status_manager:
        # Получаем компоненты в процессе установки/удаления
        installing = getattr(status_manager, 'installing', set())
        removing = getattr(status_manager, 'removing', set())
```

---

## ЭТАП 4: УДАЛЕНИЕ СТАРОГО КОДА

### 4.1. Удалить класс UniversalInstaller полностью (строки 5970-6755)

**Удалить весь класс `UniversalInstaller`:**
- Строки 5970-6755: весь класс `UniversalInstaller`
- Включая:
  - `__init__()` (5978-6039)
  - `_register_handlers()` (6041-6069)
  - Все методы управления процессами (6071-6267) - **УЖЕ ПЕРЕНЕСЕНЫ**
  - `_log()` (6269-6291) - **НЕ НУЖЕН** (используется `print()`)
  - `resolve_dependencies()` (6293-6304) - **НЕ НУЖЕН** (используется глобальная функция)
  - `find_all_children()` (6306-6327) - **ПРОВЕРИТЬ ИСПОЛЬЗОВАНИЕ**
  - `check_component_status()` (6329-6342) - **НЕ НУЖЕН** (используется глобальная функция)
  - `install_component()` (6345-6418) - **УЖЕ ПЕРЕНЕСЕН**
  - `uninstall_component()` (6421-6494) - **УЖЕ ПЕРЕНЕСЕН**
  - `install_components()` (6497-6602) - **УЖЕ ПЕРЕНЕСЕН**
  - `uninstall_components()` (6605-6755) - **УЖЕ ПЕРЕНЕСЕН**

**Проверить использование `find_all_children()`:**
- Найти все места использования `find_all_children()`
- Если используется - перенести в `AutomationGUI` или использовать глобальную функцию

### 4.2. Удалить старую логику установки/удаления (если осталась)

- Проверить строки 6392-6418 (старая логика `install_component`) - **УЖЕ УДАЛЕНА** (оставлена только логика с handlers)
- Проверить строки 6468-6494 (старая логика `uninstall_component`) - **УЖЕ УДАЛЕНА** (оставлена только логика с handlers)

---

## ЭТАП 5: ДОБАВИТЬ ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ В AutomationGUI

### 5.1. Добавить метод `_get_wineprefix()`

**Местоположение:** В классе `AutomationGUI`, после метода `__init__()` или в начале класса

**Код:**
```python
def _get_wineprefix(self):
    """Получить путь к WINEPREFIX"""
    real_user = os.environ.get('SUDO_USER')
    if real_user and real_user != 'root':
        import pwd
        home = pwd.getpwnam(real_user).pw_dir
    else:
        home = os.path.expanduser("~")
    return os.path.join(home, ".wine-astraregul")
```

### 5.2. Добавить метод `_get_astrapack_dir()`

**Местоположение:** В классе `AutomationGUI`, после метода `_get_wineprefix()`

**Код:**
```python
def _get_astrapack_dir(self):
    """Получить путь к директории AstraPack"""
    import sys
    if os.path.isabs(sys.argv[0]):
        script_path = sys.argv[0]
    else:
        script_path = os.path.join(os.getcwd(), sys.argv[0])
    script_dir = os.path.dirname(os.path.abspath(script_path))
    return os.path.join(script_dir, "AstraPack")
```

---

## ИТОГОВАЯ СТРУКТУРА

```
ComponentHandler (базовый класс)
├─ Методы управления процессами Wine (перенесены из UniversalInstaller)
│  ├─ _check_wine_processes_running()
│  ├─ _wait_for_all_processes_terminated()
│  ├─ _force_terminate_wine_processes()
│  ├─ _terminate_wineserver()
│  └─ _ensure_no_conflicting_processes()
└─ Все handlers наследуются от ComponentHandler

AutomationGUI
├─ self.component_handlers = {} (создаются напрямую)
├─ _register_component_handlers() (регистрация handlers)
├─ _install_components() (координация установки)
├─ _uninstall_components() (координация удаления)
├─ _install_component() (вызов handler.install())
├─ _uninstall_component() (вызов handler.uninstall())
├─ _get_wineprefix() (вспомогательный метод)
└─ _get_astrapack_dir() (вспомогательный метод)
```

---

## ПОРЯДОК ВЫПОЛНЕНИЯ

1. **Этап 1:** Перенести методы управления процессами в `ComponentHandler`
2. **Этап 2:** Перенести координацию установки/удаления в `AutomationGUI`
3. **Этап 3:** Изменить использование в `AutomationGUI`
4. **Этап 4:** Удалить класс `UniversalInstaller`
5. **Этап 5:** Добавить вспомогательные методы в `AutomationGUI`

---

## ПРОВЕРКА ИСПОЛЬЗОВАНИЯ

### Проверить использование следующих методов/атрибутов:

1. **`find_all_children()`** - найти все места использования
2. **`self.universal_installer`** - найти все места использования
3. **`UniversalInstaller`** - найти все упоминания класса

### Команды для проверки:

```bash
# Найти все использования universal_installer
grep -n "universal_installer" astra_automation.py

# Найти все упоминания UniversalInstaller
grep -n "UniversalInstaller" astra_automation.py

# Найти все использования find_all_children
grep -n "find_all_children" astra_automation.py
```

---

## ВАЖНЫЕ ЗАМЕЧАНИЯ

1. **Методы управления процессами** должны быть доступны через любой handler, так как все handlers наследуются от `ComponentHandler`
2. **Глобальные функции** `resolve_dependencies_for_install()`, `resolve_dependencies_for_uninstall()`, `check_component_status()` уже существуют и должны использоваться напрямую
3. **ComponentStatusManager** уже создается в `AutomationGUI.__init__()` как `self.component_status_manager`
4. **ComponentProgressManager** создается в `AutomationGUI.create_widgets()` как `self.component_progress_manager`
5. **Handlers** должны регистрироваться после создания `component_progress_manager` в `create_widgets()`

---

## ДАТА СОЗДАНИЯ ПЛАНА
2025-01-XX

## СТАТУС
⏳ Ожидает реализации

