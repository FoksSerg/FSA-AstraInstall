# План удаления класса MinimalWinetricks и переноса функционала

## Цель
Удалить класс `MinimalWinetricks` и перенести весь его функционал в класс `WinetricksManager` для упрощения архитектуры и консолидации логики работы с winetricks.

## Анализ текущего состояния

### Класс MinimalWinetricks
- **Расположение**: `astra_automation.py`, строки 9863-10468 (≈605 строк)
- **Назначение**: Python-реализация минимального winetricks для установки 6 компонентов
- **Методы**:
  - `__init__(astrapack_dir)` - инициализация
  - `install_components(components, wineprefix, callback)` - публичный метод установки
  - `_download(url, dest_path, expected_sha256, ...)` - скачивание файлов
  - `_sha256(path)` - вычисление SHA256
  - `_run_wine_process_with_raw_logging(cmd, env, timeout)` - запуск wine процессов
  - `_ensure_prefix(wineprefix)` - инициализация WINEPREFIX
  - `_env(wineprefix)` - настройка окружения Wine
  - `_copy(src, dst)` - копирование файлов
  - `_install_component(component_id, wineprefix)` - универсальный метод установки
  - `_install_msi_component(...)` - установка MSI
  - `_install_exe_single_component(...)` - установка одного EXE
  - `_install_exe_dual_x86x64_component(...)` - установка двух EXE (x86/x64)
  - `_install_dll_dual_3264_component(...)` - установка DLL (32/64)
  - `_install_tar_gz_component(...)` - установка TAR.GZ

### Точки использования MinimalWinetricks

#### 1. WinetricksManager (строка 9747)
- **Создание экземпляра**: `self._minimal = MinimalWinetricks(astrapack_dir=self.astrapack_dir)`
- **Использование**: `self._minimal.install_components()` (строка 9777)
- **Контекст**: Метод `install_wine_packages()` использует минимальный winetricks при `use_minimal=True`

#### 2. WinetricksHandler (строки 3572-3606)
- **Использование**: Динамический импорт через Python-команду в строке 3586
- **Контекст**: Установка winetricks компонентов через `su` от имени пользователя
- **Код**: 
  ```python
  from astra_automation import MinimalWinetricks; 
  m = MinimalWinetricks(astrapack_dir='...'); 
  m.install_components(['...'], wineprefix='...')
  ```

#### 3. WineApplicationHandler (строки 5804-5829)
- **Создание экземпляра**: `minimal_winetricks = MinimalWinetricks(astrapack_dir=self.astrapack_dir)` (строка 5805)
- **Использование**: `minimal_winetricks._download(...)` (строка 5823)
- **Контекст**: Скачивание установщиков для Wine приложений

### Зависимости от флагов и настроек

#### Флаг `use_minimal` используется в:
1. `WinetricksManager.__init__()` - параметр конструктора (строка 9728)
2. `WinetricksManager._check_winetricks_availability()` - проверка доступности (строка 9751)
3. `WinetricksManager.install_wine_packages()` - выбор реализации (строка 9775)
4. `WinetricksManager.set_use_minimal()` - переключение режима (строка 9808)
5. `WinetricksManager.get_available_components()` - список компонентов (строка 9827)
6. `WinetricksHandler.__init__()` - параметр конструктора (строка 3134)
7. `WinetricksHandler.set_use_minimal()` - переключение режима (строка 3439)
8. `WinetricksHandler.install()` - выбор реализации (строка 3572)

#### GUI переменная `use_minimal_winetricks`:
1. Определение: `self.use_minimal_winetricks = tk.BooleanVar(value=False)` (строка 11567)
2. Чекбокс в интерфейсе: строка 13815
3. Обработчик изменения: строки 17285-17287
4. Передача в обработчики: строки 11726, 11744, 22687, 22703

#### Параметр `use_minimal_winetricks` в ComponentInstaller:
- Определение: строка 10828
- Использование: строка 10845

## План реализации

### ЭТАП 1: Перенос методов из MinimalWinetricks в WinetricksManager

#### 1.1. Обновление `__init__()` WinetricksManager
**Файл**: `astra_automation.py`  
**Строки**: 9728-9747

**Действия**:
1. Удалить параметр `use_minimal` из конструктора
2. Удалить создание `self._minimal = MinimalWinetricks(...)` (строка 9747)
3. Добавить инициализацию `self.cache_dir = os.path.join(os.path.expanduser('~'), '.cache', 'winetricks')`
4. Создать директорию кэша с правильными правами: `os.makedirs(self.cache_dir, exist_ok=True)` и `fix_dir_permissions(self.cache_dir)`
5. Удалить атрибут `self.use_minimal`

**Код после изменений**:
```python
def __init__(self, astrapack_dir):
    """
    Инициализация менеджера winetricks
    
    Args:
        astrapack_dir: Путь к директории AstraPack
    """
    self.astrapack_dir = astrapack_dir
    
    # Путь к winetricks скрипту в кэше пользователя
    self.original_winetricks = os.path.expanduser('~/.cache/winetricks/winetricks')
    
    # Директория кэша для скачивания файлов
    self.cache_dir = os.path.join(os.path.expanduser('~'), '.cache', 'winetricks')
    try:
        os.makedirs(self.cache_dir, exist_ok=True)
        fix_dir_permissions(self.cache_dir)
    except Exception:
        pass
    
    # Проверяем доступность оригинального winetricks
    self._check_winetricks_availability()
```

#### 1.2. Обновление `_check_winetricks_availability()`
**Файл**: `astra_automation.py`  
**Строки**: 9749-9758

**Действия**:
1. Удалить проверку `if not self.use_minimal:`
2. Упростить метод - только проверка оригинального winetricks
3. Если оригинальный winetricks не найден - вывести предупреждение, но не падать

**Код после изменений**:
```python
def _check_winetricks_availability(self):
    """Проверка доступности winetricks скрипта"""
    if not os.path.exists(self.original_winetricks):
        print(f"Оригинальный winetricks не найден: {self.original_winetricks}", level='WARNING')
        print("Будет использована встроенная Python-реализация", level='WARNING')
    elif not os.access(self.original_winetricks, os.X_OK):
        os.chmod(self.original_winetricks, 0o755)
```

#### 1.3. Перенос вспомогательных методов
**Файл**: `astra_automation.py`  
**Расположение**: После метода `_check_winetricks_availability()`, перед `install_wine_packages()`

**Методы для переноса** (в порядке зависимостей):

1. **`_sha256(path)`** - вычисление SHA256 хеша
   - Из: `MinimalWinetricks._sha256()` (строки 10024-10029)
   - Зависимости: `hashlib`
   - Изменения: Заменить префикс `[MinimalWinetricks]` на `[WinetricksManager]` в логах (если есть)

2. **`_download(url, dest_path, expected_sha256, component_id, filename)`** - скачивание файлов
   - Из: `MinimalWinetricks._download()` (строки 9903-10022)
   - Зависимости: `_sha256()`, `REQUESTS_AVAILABLE`, `requests`, `urllib.request`, `ssl`, `fix_dir_permissions`
   - Изменения: 
     - Заменить все префиксы `[MinimalWinetricks]` на `[WinetricksManager]`
     - Убедиться, что используется `self.cache_dir` и `self.astrapack_dir`

3. **`_run_wine_process_with_raw_logging(cmd, env, timeout)`** - запуск wine процессов
   - Из: `MinimalWinetricks._run_wine_process_with_raw_logging()` (строки 10029-10092)
   - Зависимости: `subprocess`, `threading`, `_global_dual_logger`
   - Изменения: Заменить префиксы `[MinimalWinetricks]` на `[WinetricksManager]`

4. **`_env(wineprefix)`** - настройка окружения Wine
   - Из: `MinimalWinetricks._env()` (строки 10123-10138)
   - Зависимости: `os.environ`
   - Изменения: Нет

5. **`_ensure_prefix(wineprefix)`** - инициализация WINEPREFIX
   - Из: `MinimalWinetricks._ensure_prefix()` (строки 10096-10121)
   - Зависимости: `_env()`, `subprocess`, `os`
   - Изменения: Нет

6. **`_copy(src, dst)`** - копирование файлов
   - Из: `MinimalWinetricks._copy()` (строки 10140-10142)
   - Зависимости: `os`, `shutil`
   - Изменения: Нет

#### 1.4. Перенос методов установки компонентов
**Файл**: `astra_automation.py`  
**Расположение**: После вспомогательных методов

**Методы для переноса**:

1. **`_install_component(component_id, wineprefix)`** - универсальный метод
   - Из: `MinimalWinetricks._install_component()` (строки 10144-10230)
   - Зависимости: `get_component_field()`, все методы установки
   - Изменения: Заменить префиксы `[MinimalWinetricks]` на `[WinetricksManager]`

2. **`_install_msi_component(component_id, wineprefix, url, sha, filename)`**
   - Из: `MinimalWinetricks._install_msi_component()` (строки 10232-10259)
   - Зависимости: `_download()`, `_env()`, `_run_wine_process_with_raw_logging()`, `fix_dir_permissions`
   - Изменения: Заменить префиксы

3. **`_install_exe_single_component(component_id, wineprefix, url, sha, filename)`**
   - Из: `MinimalWinetricks._install_exe_single_component()` (строки 10261-10288)
   - Зависимости: `_download()`, `_env()`, `_run_wine_process_with_raw_logging()`, `fix_dir_permissions`
   - Изменения: Заменить префиксы

4. **`_install_exe_dual_x86x64_component(...)`**
   - Из: `MinimalWinetricks._install_exe_dual_x86x64_component()` (строки 10290-10341)
   - Зависимости: `_download()`, `_env()`, `_run_wine_process_with_raw_logging()`, `fix_dir_permissions`
   - Изменения: Заменить префиксы

5. **`_install_dll_dual_3264_component(...)`**
   - Из: `MinimalWinetricks._install_dll_dual_3264_component()` (строки 10343-10370)
   - Зависимости: `_download()`, `_copy()`, `os`
   - Изменения: Заменить префиксы

6. **`_install_tar_gz_component(component_id, wineprefix, url, sha, filename)`**
   - Из: `MinimalWinetricks._install_tar_gz_component()` (строки 10372-10412)
   - Зависимости: `_download()`, `_copy()`, `tarfile`
   - Изменения: Заменить префиксы

#### 1.5. Перенос публичного метода `install_components()`
**Файл**: `astra_automation.py`  
**Расположение**: После методов установки компонентов

**Метод**: `install_components(components, wineprefix, callback=None)`
- Из: `MinimalWinetricks.install_components()` (строки 10414-10468)
- Зависимости: `_ensure_prefix()`, `_install_component()`
- Изменения: 
  - Заменить все префиксы `[MinimalWinetricks]` на `[WinetricksManager]`
  - Заменить `MinimalWinetricks.install_components()` на `WinetricksManager.install_components()` в логах

### ЭТАП 2: Обновление WinetricksManager.install_wine_packages()

**Файл**: `astra_automation.py`  
**Строки**: 9760-9806

**Действия**:
1. Удалить проверку `if self.use_minimal:`
2. Удалить блок с использованием `self._minimal.install_components()`
3. Сначала попробовать использовать встроенную Python-реализацию (`self.install_components()`)
4. Если компонент не поддерживается (возврат `False`), использовать оригинальный winetricks
5. Упростить логику - убрать флаг `use_minimal`

**Код после изменений**:
```python
def install_wine_packages(self, components, wineprefix=None, callback=None):
    """
    Установка Wine пакетов через winetricks
    
    Args:
        components: Список компонентов для установки
        wineprefix: Путь к WINEPREFIX (опционально)
        callback: Функция обратного вызова для обновления статуса (опционально)
    
    Returns:
        bool: True если установка успешна, False в противном случае
    """
    if not components:
        return True
    
    # Сначала пробуем использовать встроенную Python-реализацию
    result = self.install_components(components, wineprefix=wineprefix, callback=callback)
    
    # Если встроенная реализация вернула False (компонент не поддерживается),
    # используем оригинальный winetricks
    if result is False:
        print(f"[WinetricksManager] Компонент требует оригинальный winetricks, используем его")
        return self._install_via_original_winetricks(components, wineprefix, callback)
    
    return result

def _install_via_original_winetricks(self, components, wineprefix=None, callback=None):
    """Установка через оригинальный bash winetricks"""
    winetricks_script = self.original_winetricks
    if not os.path.exists(winetricks_script):
        print(f"[WinetricksManager] Оригинальный winetricks не найден: {winetricks_script}", level='ERROR')
        return False
    
    cmd = [winetricks_script] + components
    env = os.environ.copy()
    if wineprefix:
        env['WINEPREFIX'] = wineprefix
    try:
        result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=1800)
        if result.returncode == 0:
            if callback:
                callback(f"Установлены компоненты: {', '.join(components)}")
            return True
        if callback:
            callback(f"Ошибка установки компонентов: {result.stderr.strip()}")
        return False
    except Exception as e:
        if callback:
            callback(f"Исключение при установке компонентов: {e}")
        return False
```

### ЭТАП 3: Удаление методов, связанных с use_minimal

#### 3.1. Удаление `set_use_minimal()`
**Файл**: `astra_automation.py`  
**Строки**: 9808-9818

**Действия**: Полностью удалить метод

#### 3.2. Обновление `get_available_components()`
**Файл**: `astra_automation.py`  
**Строки**: 9820-9849

**Действия**:
1. Удалить проверку `if self.use_minimal:`
2. Всегда возвращать список компонентов из оригинального winetricks
3. Если оригинальный winetricks недоступен, вернуть список поддерживаемых компонентов встроенной реализации

**Код после изменений**:
```python
def get_available_components(self):
    """
    Получение списка доступных компонентов
    
    Returns:
        list: Список доступных компонентов
    """
    # Пробуем получить список из оригинального winetricks
    if os.path.exists(self.original_winetricks):
        try:
            result = subprocess.run(
                [self.original_winetricks, '--list'],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                # Парсим список компонентов из вывода
                components = []
                for line in result.stdout.split('\n'):
                    if line.strip() and not line.startswith('winetricks'):
                        components.append(line.strip())
                return components
        except:
            pass
    
    # Fallback: возвращаем список компонентов, поддерживаемых встроенной реализацией
    return ['wine_mono', 'dotnet48', 'vcrun2013', 'vcrun2022', 'd3dcompiler_43', 'd3dcompiler_47', 'dxvk']
```

### ЭТАП 4: Обновление WinetricksHandler

#### 4.1. Обновление `__init__()`
**Файл**: `astra_automation.py`  
**Строки**: 3131-3190

**Действия**:
1. Удалить параметр `use_minimal` из конструктора
2. Удалить атрибут `self.use_minimal`
3. Обновить создание `WinetricksManager` - убрать параметр `use_minimal`

**Код после изменений**:
```python
def __init__(self, **kwargs):
    """
    Инициализация обработчика winetricks
    
    Args:
        **kwargs: Параметры для ComponentHandler
    """
    super().__init__(**kwargs)
    # Инициализируем WinetricksManager (ленивая инициализация)
    self._winetricks_manager = None
```

#### 4.2. Обновление метода `install()`
**Файл**: `astra_automation.py`  
**Строки**: 3451-3606

**Действия**:
1. Удалить блок `if self.use_minimal:` (строки 3572-3606)
2. Использовать только `WinetricksManager` через `su`
3. Удалить динамический импорт `from astra_automation import MinimalWinetricks`

**Код после изменений**:
```python
# Используем WinetricksManager через su для запуска от пользователя
# WinetricksManager сам решает использовать встроенную реализацию или оригинальный winetricks
script_path = os.path.abspath(sys.argv[0] if hasattr(sys, 'argv') else __file__)
cmd_string = textwrap.dedent(f"""
    cd {self.astrapack_dir} &&
    export WINEPREFIX="$HOME"/.wine-astraregul &&
    export WINEDEBUG="-all" &&
    export WINE=/opt/wine-9.0/bin/wine &&
    export PATH="/opt/wine-9.0/bin:$PATH" &&
    python3 -c "import sys; \\
        sys.path.insert(0, '{os.path.dirname(script_path)}'); \\
        from astra_automation import WinetricksManager; \\
        m = WinetricksManager(astrapack_dir='{self.astrapack_dir}'); \\
        m.install_wine_packages(['{winetricks_component}'], wineprefix='$HOME/.wine-astraregul')"
""").strip()

bash_cmd = f"bash -c {shlex.quote(cmd_string)}"
return_code = self._run_process(
    ['su', '-', real_user, '-c', bash_cmd],
    process_type="install",
    channels=["file", "terminal"],
    timeout=600
)
```

#### 4.3. Удаление `set_use_minimal()`
**Файл**: `astra_automation.py`  
**Строки**: 3439-3449

**Действия**: Полностью удалить метод

### ЭТАП 5: Обновление WineApplicationHandler

#### 5.1. Обновление метода `_install_wine_executable()`
**Файл**: `astra_automation.py`  
**Строки**: 5765-5829

**Действия**:
1. Удалить создание `minimal_winetricks = MinimalWinetricks(...)` (строка 5805)
2. Заменить `minimal_winetricks._download()` на вызов метода из `WinetricksManager`
3. Варианты решения:
   - **Вариант А**: Создать экземпляр `WinetricksManager` и использовать его метод `_download()`
   - **Вариант Б**: Вынести `_download()` в отдельную утилиту (функцию модуля)
   - **Вариант В**: Сделать `_download()` статическим методом или методом класса

**Рекомендация**: Вариант А - создать экземпляр `WinetricksManager` (он легковесный, только инициализирует пути)

**Код после изменений**:
```python
# Создаем WinetricksManager для скачивания файлов
winetricks_manager = WinetricksManager(astrapack_dir=self.astrapack_dir)

# Скачиваем установщик
try:
    winetricks_manager._download(
        download_url,
        installer_path,
        expected_sha256=download_sha256,
        component_id=component_id,
        filename=download_filename
    )
except Exception as e:
    print(f"Ошибка скачивания установщика: {e}", level='ERROR')
    self._update_status(component_id, 'error')
    return False
```

### ЭТАП 6: Обновление GUI и настроек

#### 6.1. Удаление переменной `use_minimal_winetricks` из GUI
**Файл**: `astra_automation.py`  
**Строки**: 11567

**Действия**: Удалить строку `self.use_minimal_winetricks = tk.BooleanVar(value=False)`

#### 6.2. Удаление чекбокса из интерфейса
**Файл**: `astra_automation.py`  
**Строки**: 13815

**Действия**: Найти и удалить создание чекбокса для выбора режима winetricks

#### 6.3. Удаление обработчика изменения режима
**Файл**: `astra_automation.py`  
**Строки**: 17285-17287

**Действия**: Удалить обработчик изменения `use_minimal_winetricks`

#### 6.4. Обновление передачи параметров в обработчики
**Файл**: `astra_automation.py`  
**Строки**: 11726, 11744, 22687, 22703

**Действия**: 
1. Найти все места, где передается `use_minimal=...` или `use_minimal_winetricks=...`
2. Удалить эти параметры из вызовов конструкторов

#### 6.5. Обновление ComponentInstaller
**Файл**: `astra_automation.py`  
**Строки**: 10816-10845

**Действия**:
1. Удалить параметр `use_minimal_winetricks` из `__init__()`
2. Удалить атрибут `self.use_minimal_winetricks`
3. Обновить создание `WinetricksHandler` - убрать передачу `use_minimal`

### ЭТАП 7: Удаление класса MinimalWinetricks

**Файл**: `astra_automation.py`  
**Строки**: 9863-10468

**Действия**: 
1. Удалить весь класс `MinimalWinetricks` со всеми методами
2. Удалить комментарий-разделитель перед классом

### ЭТАП 8: Очистка комментариев и логов

**Действия**:
1. Найти все комментарии, упоминающие "минимальный winetricks" или "MinimalWinetricks"
2. Обновить или удалить их
3. Проверить логи с префиксом `[MinimalWinetricks]` - должны быть заменены на `[WinetricksManager]`

### ЭТАП 9: Обновление документации

#### 9.1. README.md
**Файл**: `README.md`  
**Строка**: 383

**Действия**: Удалить строку `- ✅ Реализован MinimalWinetricks - встроенный минимальный winetricks на Python`

#### 9.2. PROJECT_ANALYSIS.md
**Файл**: `PROJECT_ANALYSIS.md`  
**Строки**: 184, 187, 454

**Действия**: 
1. Удалить упоминания о `MinimalWinetricks`
2. Обновить описание `WinetricksManager` - указать, что он включает встроенную Python-реализацию

### ЭТАП 10: Проверка зависимостей и импортов

**Действия**:
1. Проверить, что все необходимые импорты присутствуют в начале файла:
   - `hashlib` (для `_sha256`)
   - `requests` (для `_download`, если `REQUESTS_AVAILABLE`)
   - `urllib.request`, `ssl` (для `_download`)
   - `subprocess`, `threading` (для `_run_wine_process_with_raw_logging`)
   - `tarfile` (для `_install_tar_gz_component`)
   - `shutil` (для `_copy`)
   - `os`, `sys` (базовые)
2. Убедиться, что `fix_dir_permissions()` доступна
3. Убедиться, что `get_component_field()` доступна
4. Убедиться, что `_global_dual_logger` доступна (для `_run_wine_process_with_raw_logging`)

## Порядок выполнения этапов

1. **ЭТАП 1** - Перенос методов (самый большой, но независимый)
2. **ЭТАП 2** - Обновление `install_wine_packages()` (зависит от этапа 1)
3. **ЭТАП 3** - Удаление методов `use_minimal` (независимый)
4. **ЭТАП 4** - Обновление `WinetricksHandler` (зависит от этапов 1-3)
5. **ЭТАП 5** - Обновление `WineApplicationHandler` (зависит от этапа 1)
6. **ЭТАП 6** - Обновление GUI (независимый)
7. **ЭТАП 7** - Удаление класса (после всех переносов)
8. **ЭТАП 8** - Очистка комментариев (после удаления класса)
9. **ЭТАП 9** - Обновление документации (независимый)
10. **ЭТАП 10** - Финальная проверка (после всех изменений)

## Риски и замечания

### Критические моменты:

1. **Метод `_download()` используется в двух местах**:
   - В `WinetricksManager` (в методах установки)
   - В `WineApplicationHandler` (для скачивания установщиков)
   - **Решение**: Сделать публичным методом `WinetricksManager` или вынести в утилиту

2. **Автоматическое переключение на оригинальный winetricks**:
   - Если компонент не поддерживается встроенной реализацией, должен использоваться оригинальный winetricks
   - **Решение**: Метод `install_components()` возвращает `False`, если компонент не поддерживается

3. **Обратная совместимость**:
   - Если есть сохраненные настройки с `use_minimal=True`, их нужно обработать
   - **Решение**: При загрузке настроек игнорировать этот параметр

4. **Зависимость от `_global_dual_logger`**:
   - Метод `_run_wine_process_with_raw_logging()` использует глобальную переменную
   - **Решение**: Проверить доступность перед использованием

## Оценка объема изменений

- **Перенос кода**: ~600 строк (методы из `MinimalWinetricks`)
- **Модификация кода**: ~200-300 строк (обновление использований)
- **Удаление кода**: ~650 строк (класс + флаги + GUI элементы)
- **Обновление документации**: ~5-10 строк
- **Итого**: ~1450-1560 строк изменений

## Критерии успешного завершения

1. ✅ Класс `MinimalWinetricks` полностью удален
2. ✅ Все методы перенесены в `WinetricksManager`
3. ✅ Все использования обновлены
4. ✅ Флаги `use_minimal` удалены
5. ✅ GUI элементы удалены
6. ✅ Документация обновлена
7. ✅ Код компилируется без ошибок
8. ✅ Линтер не выдает ошибок
9. ✅ Функциональность сохранена (установка компонентов работает)

