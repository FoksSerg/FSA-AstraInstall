# План реализации универсального WineConfigHandler

**Версия документа:** 1.0.0  
**Дата создания:** 2025.12.18  
**Проект:** FSA-AstraInstall  
**Компания:** ООО "НПА Вира-Реалтайм"  
**Текущая версия проекта:** V3.4.188 (2025.12.17)

## 📋 Оглавление

1. [Цель реализации](#цель-реализации)
2. [Текущая проблема](#текущая-проблема)
3. [Архитектура решения](#архитектура-решения)
4. [Типы операций](#типы-операций)
5. [Пошаговый план реализации](#пошаговый-план-реализации)
6. [Детальные изменения](#детальные-изменения)
7. [Примеры использования](#примеры-использования)
8. [Тестирование](#тестирование)
9. [Риски и митигация](#риски-и-митигация)

---

## 🎯 Цель реализации

Создать универсальный обработчик настроек Wine (`WineConfigHandler`), который:

- ✅ Управляет различными настройками Wine через единый интерфейс
- ✅ Работает через конфигурацию компонентов (без жестко закодированных проверок)
- ✅ Поддерживает расширение без изменения кода handler'а
- ✅ Интегрируется в существующую архитектуру ComponentInstaller
- ✅ Решает проблему DXVK на Intel HD Graphics
- ✅ Позволяет добавлять новые типы настроек Wine в будущем

---

## 🔍 Текущая проблема

### Проблема 1: DXVK не работает на Intel HD Graphics

**Симптомы:**
- Astra.IDE падает с ошибкой `dxvk::DxvkError`
- Ошибка: `DXVK: No adapters found`
- Intel HD Graphics 530 не поддерживает необходимые функции Vulkan для DXVK

**Текущее решение:**
- Ручной скрипт `fix_dxvk_intel.sh` для отключения DXVK
- Требует ручного запуска
- Не интегрирован в GUI

### Проблема 2: Отсутствие универсального механизма управления настройками Wine

**Текущее состояние:**
- Нет единого способа управления настройками Wine
- Каждая настройка требует отдельного кода
- Нет возможности легко добавлять новые типы настроек

**Примеры будущих потребностей:**
- Управление DLL overrides
- Настройки реестра Wine
- Переменные окружения Wine
- Версионирование DXVK
- Оптимизация производительности

---

## 🏗️ Архитектура решения

### 1. Базовый класс WineConfigHandler

```python
class WineConfigHandler(ComponentHandler):
    """
    Универсальный обработчик настроек Wine
    
    Поддерживает различные типы операций через конфигурацию компонентов:
    - dxvk_toggle: Включение/отключение DXVK
    - dll_override: Управление DLL overrides
    - registry_setting: Настройки реестра Wine
    - wine_env_var: Переменные окружения Wine
    """
    
    def get_category(self) -> str:
        return 'wine_config'
    
    def install(self, component_id: str, config: dict) -> bool:
        """Установка настройки Wine (применение изменения)"""
        
    def uninstall(self, component_id: str, config: dict) -> bool:
        """Удаление настройки Wine (откат изменения)"""
        
    def check_status(self, component_id: str, config: dict) -> bool:
        """Проверка статуса настройки"""
```

### 2. Диспетчеризация операций

Handler определяет тип операции из конфигурации компонента и вызывает соответствующий метод:

```python
operation_type = config.get('operation_type')
if operation_type == 'dxvk_toggle':
    return self._handle_dxvk_toggle(component_id, config, enable=False)
elif operation_type == 'dll_override':
    return self._handle_dll_override(component_id, config, apply=True)
# ... и т.д.
```

### 3. Структура компонентов в COMPONENTS_CONFIG

Каждый компонент настройки Wine имеет:
- `operation_type`: Тип операции
- `wineprefix_path`: Путь к WINEPREFIX
- Специфичные параметры для типа операции

---

## 🔧 Типы операций

### 1. `dxvk_toggle` - Управление DXVK

**Назначение:** Включение/отключение DXVK DLL

**Параметры конфигурации:**
```python
{
    'operation_type': 'dxvk_toggle',
    'operation_mode': 'disable',  # 'disable' или 'enable'
    'wineprefix_path': '~/.wine-astraregul',
    'dxvk_dlls': ['d3d9.dll', 'd3d11.dll', 'dxgi.dll'],  # Список DLL
    'backup_dir': 'dxvk_backup',  # Имя подпапки для резервных копий
    'auto_detect_gpu': False,  # Автоопределение видеокарты
    'gpu_whitelist': ['Intel'],  # Для каких GPU применять
    'gpu_blacklist': [],  # Для каких GPU не применять
}
```

**Логика работы:**
- `install()` с `operation_mode='disable'`: Отключает DXVK (переименовывает DLL)
- `uninstall()`: Включает DXVK (восстанавливает DLL из резервной копии)
- `check_status()`: Проверяет наличие `.dll.dxvk_disabled` файлов

### 2. `dll_override` - Управление DLL Overrides

**Назначение:** Управление DLL overrides в реестре Wine

**Параметры конфигурации:**
```python
{
    'operation_type': 'dll_override',
    'wineprefix_path': '~/.wine-astraregul',
    'dll_overrides': {
        'd3d9': 'native',
        'd3d11': 'builtin',
        'dxgi': 'native',
    },
    'backup_registry': True,  # Создавать резервную копию реестра
}
```

**Логика работы:**
- `install()`: Применяет DLL overrides через `wine reg add`
- `uninstall()`: Удаляет DLL overrides
- `check_status()`: Проверяет наличие overrides в реестре

### 3. `registry_setting` - Настройки реестра

**Назначение:** Изменение значений в реестре Wine

**Параметры конфигурации:**
```python
{
    'operation_type': 'registry_setting',
    'wineprefix_path': '~/.wine-astraregul',
    'registry_path': 'HKEY_CURRENT_USER\\Software\\Wine',
    'registry_key': 'Direct3D',
    'registry_value': 'DirectDrawRenderer',
    'registry_data': 'gdi',  # 'gdi', 'opengl', 'vulkan'
    'registry_type': 'REG_SZ',  # Тип значения
    'backup_registry': True,
}
```

**Логика работы:**
- `install()`: Устанавливает значение в реестре
- `uninstall()`: Восстанавливает предыдущее значение
- `check_status()`: Проверяет текущее значение в реестре

### 4. `wine_env_var` - Переменные окружения

**Назначение:** Управление переменными окружения Wine

**Параметры конфигурации:**
```python
{
    'operation_type': 'wine_env_var',
    'wineprefix_path': '~/.wine-astraregul',
    'env_vars': {
        'WINEDEBUG': '+d3d9,+err',
        'WINEDLLOVERRIDES': 'd3d9=n',
    },
    'config_file': 'wine_env.conf',  # Файл для сохранения настроек
}
```

**Логика работы:**
- `install()`: Сохраняет переменные в конфигурационный файл
- `uninstall()`: Удаляет переменные из конфигурации
- `check_status()`: Проверяет наличие конфигурационного файла

---

## 📝 Пошаговый план реализации

### Этап 1: Создание базового класса WineConfigHandler

**Задачи:**
1. Создать класс `WineConfigHandler(ComponentHandler)`
2. Реализовать `get_category()` → `'wine_config'`
3. Реализовать базовые методы: `install()`, `uninstall()`, `check_status()`
4. Добавить диспетчеризацию по `operation_type`
5. Реализовать вспомогательные методы:
   - `_get_wineprefix_path(config)` - получение пути к WINEPREFIX
   - `_create_backup(component_id, config)` - создание резервной копии
   - `_restore_backup(component_id, config)` - восстановление из резервной копии

**Местоположение:** После класса `SystemConfigHandler` (примерно строка 5400)

**Оценка:** 2-3 часа

### Этап 2: Реализация операции `dxvk_toggle`

**Задачи:**
1. Реализовать `_handle_dxvk_toggle(component_id, config, enable)`
2. Реализовать `_check_dxvk_status(component_id, config)`
3. Добавить автоопределение видеокарты (опционально)
4. Добавить проверку размера DLL для определения DXVK
5. Реализовать резервное копирование DLL

**Оценка:** 2-3 часа

### Этап 3: Добавление компонента в COMPONENTS_CONFIG

**Задачи:**
1. Добавить компонент `'dxvk_disable_intel'` в `COMPONENTS_CONFIG`
2. Настроить зависимости (зависит от `astra_wineprefix`)
3. Настроить параметры конфигурации
4. Добавить описание и sort_order

**Местоположение:** В секции `COMPONENTS_CONFIG` (примерно строка 1382)

**Оценка:** 30 минут

### Этап 4: Регистрация Handler в ComponentInstaller

**Задачи:**
1. Создать экземпляр `WineConfigHandler` в `AutomationGUI.__init__()`
2. Добавить в словарь `component_handlers['wine_config'] = ...`
3. Проверить, что handler правильно вызывается

**Местоположение:** В `AutomationGUI.__init__()` (примерно строка 13665)

**Оценка:** 30 минут

### Этап 5: Интеграция в GUI

**Задачи:**
1. Проверить, что компонент появляется в списке компонентов Wine
2. Проверить отображение статуса
3. Проверить работу установки/удаления
4. Добавить информационные сообщения

**Оценка:** 1 час

### Этап 6: Тестирование

**Задачи:**
1. Тестирование на системе с Intel HD Graphics
2. Тестирование на системе с NVIDIA
3. Тестирование отката изменений
4. Тестирование резервного копирования

**Оценка:** 2 часа

### Этап 7: Документация

**Задачи:**
1. Добавить комментарии в код
2. Обновить документацию компонентов
3. Добавить примеры использования

**Оценка:** 1 час

**Общая оценка:** 9-11 часов

---

## 🔨 Детальные изменения

### Изменение 1: Добавление класса WineConfigHandler

**Местоположение:** После `SystemConfigHandler` (примерно строка 5400)

**Код:**
```python
class WineConfigHandler(ComponentHandler):
# ============================================================================
# УНИВЕРСАЛЬНЫЙ ОБРАБОТЧИК НАСТРОЕК WINE
# ============================================================================
    """
    Универсальный обработчик настроек Wine
    
    Поддерживает различные типы операций через конфигурацию компонентов:
    - dxvk_toggle: Включение/отключение DXVK
    - dll_override: Управление DLL overrides
    - registry_setting: Настройки реестра Wine
    - wine_env_var: Переменные окружения Wine
    
    Все операции настраиваются через COMPONENTS_CONFIG без изменения кода handler'а.
    """
    
    def get_category(self) -> str:
        return 'wine_config'
    
    def __init__(self, status_manager=None, progress_manager=None, 
                 universal_runner=None, dual_logger=None, home=None):
        """
        Инициализация WineConfigHandler
        
        Args:
            status_manager: ComponentStatusManager для управления статусами
            progress_manager: UniversalProgressManager для прогресса
            universal_runner: UniversalProcessRunner для логирования
            dual_logger: DualStreamLogger для логирования
            home: Домашняя директория пользователя
        """
        self.status_manager = status_manager
        self.progress_manager = progress_manager
        self.universal_runner = universal_runner
        self.dual_logger = dual_logger
        self.home = home or os.path.expanduser("~")
    
    @track_class_activity('WineConfigHandler')
    def install(self, component_id: str, config: dict) -> bool:
        """
        Установка настройки Wine (применение изменения)
        
        Args:
            component_id: ID компонента
            config: Конфигурация компонента
            
        Returns:
            bool: True если установка успешна
        """
        # Проверяем статус перед установкой
        if self.check_status(component_id, config):
            return True
        
        # Устанавливаем статус 'installing'
        self._update_status(component_id, 'installing')
        
        operation_type = config.get('operation_type')
        if not operation_type:
            print(f"Ошибка: компонент {component_id} не имеет operation_type", level='ERROR')
            self._update_status(component_id, 'error')
            return False
        
        # Диспетчеризация по типу операции
        if operation_type == 'dxvk_toggle':
            return self._handle_dxvk_toggle(component_id, config, enable=False)
        elif operation_type == 'dll_override':
            return self._handle_dll_override(component_id, config, apply=True)
        elif operation_type == 'registry_setting':
            return self._handle_registry_setting(component_id, config, apply=True)
        elif operation_type == 'wine_env_var':
            return self._handle_wine_env_var(component_id, config, apply=True)
        else:
            print(f"Неизвестный тип операции: {operation_type}", level='ERROR')
            self._update_status(component_id, 'error')
            return False
    
    @track_class_activity('WineConfigHandler')
    def uninstall(self, component_id: str, config: dict) -> bool:
        """
        Удаление настройки Wine (откат изменения)
        
        Args:
            component_id: ID компонента
            config: Конфигурация компонента
            
        Returns:
            bool: True если удаление успешно
        """
        # Устанавливаем статус 'removing'
        self._update_status(component_id, 'removing')
        
        operation_type = config.get('operation_type')
        if not operation_type:
            print(f"Ошибка: компонент {component_id} не имеет operation_type", level='ERROR')
            self._update_status(component_id, 'error')
            return False
        
        # Обратная операция
        if operation_type == 'dxvk_toggle':
            return self._handle_dxvk_toggle(component_id, config, enable=True)
        elif operation_type == 'dll_override':
            return self._handle_dll_override(component_id, config, apply=False)
        elif operation_type == 'registry_setting':
            return self._handle_registry_setting(component_id, config, apply=False)
        elif operation_type == 'wine_env_var':
            return self._handle_wine_env_var(component_id, config, apply=False)
        else:
            print(f"Неизвестный тип операции: {operation_type}", level='ERROR')
            self._update_status(component_id, 'error')
            return False
    
    def check_status(self, component_id: str, config: dict) -> bool:
        """
        Проверка статуса настройки Wine
        
        Args:
            component_id: ID компонента
            config: Конфигурация компонента
            
        Returns:
            bool: True если настройка применена, False если нет
        """
        operation_type = config.get('operation_type')
        if not operation_type:
            return False
        
        if operation_type == 'dxvk_toggle':
            return self._check_dxvk_status(component_id, config)
        elif operation_type == 'dll_override':
            return self._check_dll_override_status(component_id, config)
        elif operation_type == 'registry_setting':
            return self._check_registry_setting_status(component_id, config)
        elif operation_type == 'wine_env_var':
            return self._check_wine_env_var_status(component_id, config)
        else:
            return False
    
    # ========================================================================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # ========================================================================
    
    def _get_wineprefix_path(self, config: dict) -> str:
        """
        Получить путь к WINEPREFIX из конфигурации
        
        Args:
            config: Конфигурация компонента
            
        Returns:
            str: Полный путь к WINEPREFIX
        """
        wineprefix_path = config.get('wineprefix_path', '~/.wine-astraregul')
        return expand_user_path(wineprefix_path)
    
    def _create_backup_dir(self, component_id: str, config: dict) -> str:
        """
        Создать директорию для резервных копий
        
        Args:
            component_id: ID компонента
            config: Конфигурация компонента
            
        Returns:
            str: Путь к директории резервных копий
        """
        wineprefix = self._get_wineprefix_path(config)
        backup_dir_name = config.get('backup_dir', f'{component_id}_backup')
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = os.path.join(wineprefix, f"{backup_dir_name}_{timestamp}")
        os.makedirs(backup_dir, exist_ok=True)
        return backup_dir
    
    def _update_status(self, component_id: str, status: str):
        """Обновить статус компонента"""
        if self.status_manager:
            self.status_manager.update_component_status(component_id, status)
    
    # ========================================================================
    # МЕТОДЫ ДЛЯ ОПЕРАЦИИ dxvk_toggle
    # ========================================================================
    
    def _handle_dxvk_toggle(self, component_id: str, config: dict, enable: bool) -> bool:
        """
        Управление DXVK (включение/отключение)
        
        Args:
            component_id: ID компонента
            config: Конфигурация компонента
            enable: True для включения, False для отключения
            
        Returns:
            bool: True если операция успешна
        """
        wineprefix = self._get_wineprefix_path(config)
        system32_dir = os.path.join(wineprefix, 'drive_c/windows/system32')
        
        dxvk_dlls = config.get('dxvk_dlls', ['d3d9.dll', 'd3d11.dll', 'dxgi.dll'])
        
        if enable:
            # Включение DXVK: восстановление из резервной копии
            return self._restore_dxvk_dlls(component_id, config, system32_dir, dxvk_dlls)
        else:
            # Отключение DXVK: переименование DLL
            return self._disable_dxvk_dlls(component_id, config, system32_dir, dxvk_dlls)
    
    def _disable_dxvk_dlls(self, component_id: str, config: dict, 
                           system32_dir: str, dxvk_dlls: list) -> bool:
        """Отключение DXVK DLL"""
        backup_dir = self._create_backup_dir(component_id, config)
        disabled_count = 0
        
        for dll_name in dxvk_dlls:
            dll_path = os.path.join(system32_dir, dll_name)
            disabled_path = f"{dll_path}.dxvk_disabled"
            
            if os.path.exists(dll_path):
                # Проверяем, что это DXVK (обычно больше 1MB)
                try:
                    size = os.path.getsize(dll_path)
                    if size > 1048576:  # Больше 1MB
                        # Создаем резервную копию
                        backup_path = os.path.join(backup_dir, dll_name)
                        shutil.copy2(dll_path, backup_path)
                        
                        # Переименовываем
                        os.rename(dll_path, disabled_path)
                        disabled_count += 1
                        print(f"DXVK DLL отключен: {dll_name}", gui_log=True)
                except Exception as e:
                    print(f"Ошибка при отключении {dll_name}: {e}", level='ERROR')
        
        if disabled_count > 0:
            self._update_status(component_id, 'ok')
            return True
        else:
            print("DXVK DLL не найдены для отключения", level='WARNING')
            self._update_status(component_id, 'missing')
            return False
    
    def _restore_dxvk_dlls(self, component_id: str, config: dict,
                           system32_dir: str, dxvk_dlls: list) -> bool:
        """Восстановление DXVK DLL из резервной копии"""
        wineprefix = self._get_wineprefix_path(config)
        backup_dir_name = config.get('backup_dir', f'{component_id}_backup')
        
        # Ищем последнюю резервную копию
        backup_dirs = []
        for item in os.listdir(wineprefix):
            if item.startswith(backup_dir_name) and os.path.isdir(os.path.join(wineprefix, item)):
                backup_dirs.append(item)
        
        if not backup_dirs:
            print("Резервные копии DXVK не найдены", level='ERROR')
            self._update_status(component_id, 'error')
            return False
        
        # Используем последнюю резервную копию
        latest_backup = sorted(backup_dirs)[-1]
        backup_dir = os.path.join(wineprefix, latest_backup)
        
        restored_count = 0
        for dll_name in dxvk_dlls:
            disabled_path = os.path.join(system32_dir, f"{dll_name}.dxvk_disabled")
            backup_path = os.path.join(backup_dir, dll_name)
            dll_path = os.path.join(system32_dir, dll_name)
            
            if os.path.exists(disabled_path) and os.path.exists(backup_path):
                try:
                    # Восстанавливаем из резервной копии
                    shutil.copy2(backup_path, dll_path)
                    os.remove(disabled_path)
                    restored_count += 1
                    print(f"DXVK DLL восстановлен: {dll_name}", gui_log=True)
                except Exception as e:
                    print(f"Ошибка при восстановлении {dll_name}: {e}", level='ERROR')
        
        if restored_count > 0:
            self._update_status(component_id, 'missing')
            return True
        else:
            self._update_status(component_id, 'error')
            return False
    
    def _check_dxvk_status(self, component_id: str, config: dict) -> bool:
        """
        Проверка статуса DXVK (отключен ли)
        
        Returns:
            bool: True если DXVK отключен (есть .dxvk_disabled файлы)
        """
        wineprefix = self._get_wineprefix_path(config)
        system32_dir = os.path.join(wineprefix, 'drive_c/windows/system32')
        dxvk_dlls = config.get('dxvk_dlls', ['d3d9.dll', 'd3d11.dll', 'dxgi.dll'])
        
        # Проверяем наличие .dxvk_disabled файлов
        disabled_count = 0
        for dll_name in dxvk_dlls:
            disabled_path = os.path.join(system32_dir, f"{dll_name}.dxvk_disabled")
            if os.path.exists(disabled_path):
                disabled_count += 1
        
        # Если хотя бы один DLL отключен - считаем, что DXVK отключен
        return disabled_count > 0
    
    # ========================================================================
    # МЕТОДЫ ДЛЯ ДРУГИХ ОПЕРАЦИЙ (заглушки для будущей реализации)
    # ========================================================================
    
    def _handle_dll_override(self, component_id: str, config: dict, apply: bool) -> bool:
        """Управление DLL overrides (будущая реализация)"""
        print(f"DLL override операция пока не реализована для {component_id}", level='WARNING')
        self._update_status(component_id, 'error')
        return False
    
    def _handle_registry_setting(self, component_id: str, config: dict, apply: bool) -> bool:
        """Управление настройками реестра (будущая реализация)"""
        print(f"Registry setting операция пока не реализована для {component_id}", level='WARNING')
        self._update_status(component_id, 'error')
        return False
    
    def _handle_wine_env_var(self, component_id: str, config: dict, apply: bool) -> bool:
        """Управление переменными окружения (будущая реализация)"""
        print(f"Wine env var операция пока не реализована для {component_id}", level='WARNING')
        self._update_status(component_id, 'error')
        return False
    
    def _check_dll_override_status(self, component_id: str, config: dict) -> bool:
        """Проверка статуса DLL overrides"""
        return False
    
    def _check_registry_setting_status(self, component_id: str, config: dict) -> bool:
        """Проверка статуса настроек реестра"""
        return False
    
    def _check_wine_env_var_status(self, component_id: str, config: dict) -> bool:
        """Проверка статуса переменных окружения"""
        return False
```

### Изменение 2: Добавление компонента в COMPONENTS_CONFIG

**Местоположение:** После компонента `'astra_desktop_shortcut'` (примерно строка 1382)

**Код:**
```python
    'dxvk_disable_intel': {
        'name': 'Отключение DXVK для Intel',
        'category': 'wine_config',
        'dependencies': ['astra_wineprefix'],
        'wineprefix_path': '~/.wine-astraregul',
        'operation_type': 'dxvk_toggle',
        'operation_mode': 'disable',
        'dxvk_dlls': ['d3d9.dll', 'd3d11.dll', 'dxgi.dll'],
        'backup_dir': 'dxvk_backup',
        'auto_detect_gpu': True,  # Автоопределение видеокарты
        'gpu_whitelist': ['Intel'],  # Для каких GPU применять
        'gui_selectable': True,
        'description': 'Отключение DXVK для Intel HD Graphics (решает проблему запуска Astra.IDE)',
        'sort_order': 13,
        'check_method': 'dxvk_status',
        'check_paths': ['drive_c/windows/system32/d3d9.dll.dxvk_disabled']
    },
```

### Изменение 3: Регистрация Handler в AutomationGUI

**Местоположение:** В `AutomationGUI.__init__()` (примерно строка 13665)

**Код:**
```python
# Создаем handlers для разных категорий компонентов
component_handlers = {
    'wine_packages': WinePackageHandler(...),
    'wine_environment': WineEnvironmentHandler(...),
    'wine_application': WineApplicationHandler(...),
    'wine_config': WineConfigHandler(  # НОВЫЙ
        status_manager=status_manager,
        progress_manager=progress_manager,
        universal_runner=universal_runner,
        dual_logger=dual_logger,
        home=home
    ),
    'system_config': SystemConfigHandler(...),
    'desktop_shortcut': DesktopShortcutHandler(...),
    'winetricks': WinetricksHandler(...),
}
```

---

## 💡 Примеры использования

### Пример 1: Отключение DXVK для Intel

**Компонент:**
```python
'dxvk_disable_intel': {
    'name': 'Отключение DXVK для Intel',
    'category': 'wine_config',
    'operation_type': 'dxvk_toggle',
    'operation_mode': 'disable',
    'dxvk_dlls': ['d3d9.dll', 'd3d11.dll', 'dxgi.dll'],
}
```

**Использование:**
- Пользователь выбирает компонент в GUI
- Нажимает "Установить"
- Handler отключает DXVK DLL
- Astra.IDE запускается без ошибок

### Пример 2: Включение DXVK для NVIDIA (будущее)

**Компонент:**
```python
'dxvk_enable_nvidia': {
    'name': 'Включение DXVK для NVIDIA',
    'category': 'wine_config',
    'operation_type': 'dxvk_toggle',
    'operation_mode': 'enable',
    'gpu_whitelist': ['NVIDIA', 'AMD'],
}
```

### Пример 3: DLL Overrides (будущее)

**Компонент:**
```python
'dll_overrides_optimization': {
    'name': 'Оптимизация DLL Overrides',
    'category': 'wine_config',
    'operation_type': 'dll_override',
    'dll_overrides': {
        'd3d9': 'native',
        'd3d11': 'native',
    },
}
```

---

## 🧪 Тестирование

### Тест 1: Отключение DXVK

**Шаги:**
1. Убедиться, что DXVK установлен (есть d3d9.dll в system32)
2. Установить компонент `dxvk_disable_intel`
3. Проверить, что DLL переименованы в `.dxvk_disabled`
4. Проверить наличие резервной копии
5. Запустить Astra.IDE - должно работать без ошибок

**Ожидаемый результат:**
- DXVK отключен
- Резервная копия создана
- Astra.IDE запускается успешно

### Тест 2: Включение DXVK (откат)

**Шаги:**
1. Убедиться, что DXVK отключен
2. Удалить компонент `dxvk_disable_intel`
3. Проверить, что DLL восстановлены из резервной копии
4. Проверить, что `.dxvk_disabled` файлы удалены

**Ожидаемый результат:**
- DXVK восстановлен
- Статус компонента: `[MISSING]`

### Тест 3: Проверка статуса

**Шаги:**
1. Проверить статус компонента когда DXVK включен
2. Проверить статус компонента когда DXVK отключен

**Ожидаемый результат:**
- DXVK включен → статус `[MISSING]`
- DXVK отключен → статус `[OK]`

### Тест 4: Множественные установки

**Шаги:**
1. Установить компонент дважды
2. Проверить, что не создаются дубликаты резервных копий

**Ожидаемый результат:**
- Компонент не устанавливается повторно
- Статус остается `[OK]`

---

## ⚠️ Риски и митигация

### Риск 1: Потеря резервных копий

**Проблема:** Резервные копии могут быть удалены пользователем

**Митигация:**
- Хранить несколько последних резервных копий
- Добавить проверку наличия резервной копии перед восстановлением
- Предупреждать пользователя при удалении резервных копий

### Риск 2: Конфликт с другими настройками Wine

**Проблема:** Другие инструменты могут изменять те же DLL

**Митигация:**
- Проверять состояние перед изменением
- Логировать все изменения
- Предупреждать о возможных конфликтах

### Риск 3: Неправильное определение DXVK DLL

**Проблема:** Может переименовать не DXVK DLL

**Митигация:**
- Проверять размер DLL (DXVK обычно > 1MB)
- Проверять наличие в winetricks.log
- Добавить опцию ручного указания DLL

### Риск 4: Проблемы с правами доступа

**Проблема:** Нет прав для изменения DLL в system32

**Митигация:**
- Проверять права доступа перед операцией
- Использовать правильного владельца файлов
- Логировать ошибки прав доступа

---

## 📊 Преимущества универсального подхода

### 1. Расширяемость

**Без изменения кода handler'а можно добавить:**
- Новые типы операций через конфигурацию
- Новые компоненты настроек Wine
- Специфичные параметры для каждого компонента

### 2. Единый интерфейс

**Все настройки Wine:**
- Управляются через один handler
- Имеют одинаковый интерфейс (install/uninstall/check_status)
- Интегрируются в GUI одинаково

### 3. Переиспользование кода

**Общие методы:**
- Резервное копирование
- Проверка WINEPREFIX
- Логирование
- Управление статусами

### 4. Простота поддержки

**Преимущества:**
- Один класс для всех настроек Wine
- Легко найти и исправить ошибки
- Единый стиль кода

---

## 🔮 Будущие возможности

### 1. Автоопределение видеокарты

**Реализация:**
- Определение GPU через `lspci` или `/proc/driver/nvidia/version`
- Автоматическое предложение настроек
- Условная установка компонентов

### 2. Версионирование DXVK

**Реализация:**
- Выбор версии DXVK (1.x, 2.x)
- Установка конкретной версии
- Откат к предыдущей версии

### 3. Оптимизация производительности

**Реализация:**
- Настройки реестра для оптимизации
- DLL overrides для лучшей производительности
- Профили для разных видеокарт

### 4. Экспорт/импорт настроек

**Реализация:**
- Сохранение конфигурации Wine
- Восстановление из файла
- Миграция между системами

---

## 📝 Примечания

- Handler реализуется поэтапно, начиная с `dxvk_toggle`
- Другие типы операций добавляются по мере необходимости
- Все изменения логируются через UniversalProcessRunner
- Резервные копии хранятся в WINEPREFIX для удобства

---

**Дата создания:** 2025.12.18  
**Версия документа:** 1.0.0  
**Статус:** 📝 ПЛАН ГОТОВ К РЕАЛИЗАЦИИ

