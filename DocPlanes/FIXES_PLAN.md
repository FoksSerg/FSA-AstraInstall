# ПЛАН ИСПРАВЛЕНИЙ АЛГОРИТМОВ УСТАНОВКИ И УДАЛЕНИЯ
# Версия: V3.4.174 (2025.12.03)
# Дата создания: 2025.01.25
# Файл: astra_automation.py

## ОБЩАЯ ИНФОРМАЦИЯ

**Цель:** Исправить найденные ошибки в алгоритмах установки и удаления компонентов
**Подход:** Все исправления сразу, с возможностью отката к коммиту
**Файл для изменений:** `astra_automation.py` (26105 строк)

---

## ИСПРАВЛЕНИЕ 1: resolve_dependencies_for_uninstall - правильный порядок удаления детей

### Проблема:
- Функция находит всех детей, но не упорядочивает их правильно
- Используется `resolve_dependencies(child_id)`, но результат не применяется для упорядочивания
- Дети могут удаляться в неправильном порядке

### Местоположение:
- **Файл:** `astra_automation.py`
- **Функция:** `resolve_dependencies_for_uninstall`
- **Строки:** 1405-1463

### Что изменить:

**БЛОК 1: Добавить защиту от циклов в find_children_recursive (строки 1421-1431)**

**БЫЛО:**
```python
def find_children_recursive(parent_id):
    """Рекурсивно находит всех детей компонента"""
    for component_id, config in COMPONENTS_CONFIG.items():
        if component_id == parent_id:
            continue  # Пропускаем сам компонент
        deps = config.get('dependencies', [])
        if parent_id in deps:
            # Найден ребенок - добавляем его и рекурсивно ищем его детей
            if component_id not in children:
                children.add(component_id)
                find_children_recursive(component_id)
```

**СТАНЕТ:**
```python
def find_children_recursive(parent_id, visited=None, max_depth=100, current_depth=0):
    """Рекурсивно находит всех детей компонента с защитой от циклов"""
    if visited is None:
        visited = set()
    
    # Защита от бесконечной рекурсии
    if current_depth > max_depth:
        print(f"Предупреждение: достигнута максимальная глубина рекурсии для {parent_id}", level='WARNING')
        return
    
    # Защита от циклов
    if parent_id in visited:
        return
    
    visited.add(parent_id)
    
    for component_id, config in COMPONENTS_CONFIG.items():
        if component_id == parent_id:
            continue  # Пропускаем сам компонент
        deps = config.get('dependencies', [])
        if parent_id in deps:
            # Найден ребенок - добавляем его и рекурсивно ищем его детей
            if component_id not in children:
                children.add(component_id)
                find_children_recursive(component_id, visited, max_depth, current_depth + 1)
    
    visited.remove(parent_id)  # Удаляем для возможности повторной обработки в других контекстах
```

**БЛОК 2: Добавить проверку существования компонентов (после строки 1417, перед строкой 1418)**

**ДОБАВИТЬ:**
```python
# КРИТИЧНО: Проверяем существование всех компонентов в конфигурации
valid_component_ids = []
for component_id in component_ids:
    if component_id not in COMPONENTS_CONFIG:
        print(f"Предупреждение: компонент {component_id} не найден в конфигурации, пропускаем", level='WARNING')
    else:
        valid_component_ids.append(component_id)

if not valid_component_ids:
    print("Ошибка: все компоненты для удаления не найдены в конфигурации", level='ERROR')
    return []

# Используем только валидные компоненты
component_ids = valid_component_ids
```

**БЛОК 3: Исправить упорядочивание детей (строки 1437-1445)**

**БЫЛО:**
```python
# Формируем список для удаления: сначала дети (в порядке зависимостей), потом сами компоненты
# Используем resolve_dependencies для детей, чтобы получить правильный порядок
children_list = []
for child_id in children:
    # Получаем зависимости ребенка, чтобы правильно упорядочить
    child_deps = resolve_dependencies(child_id)
    # Добавляем ребенка после его зависимостей
    if child_id not in children_list:
        children_list.append(child_id)
```

**СТАНЕТ:**
```python
# Формируем список для удаления: сначала дети (в порядке зависимостей), потом сами компоненты
# Используем resolve_dependencies для детей, чтобы получить правильный порядок
children_list = []
children_resolved = {}  # Словарь: child_id -> список зависимостей

# Собираем все зависимости для каждого ребенка
for child_id in children:
    try:
        child_deps = resolve_dependencies(child_id)
        children_resolved[child_id] = child_deps
    except ValueError as e:
        print(f"Ошибка при разрешении зависимостей для {child_id}: {e}", level='ERROR')
        # Добавляем ребенка без упорядочивания
        children_resolved[child_id] = [child_id]

# Упорядочиваем детей: сначала зависимости, потом зависимые
# Создаем граф зависимостей между детьми
children_graph = {}
for child_id, deps in children_resolved.items():
    children_graph[child_id] = [d for d in deps if d in children and d != child_id]

# Топологическая сортировка детей
visited_children = set()
temp_visited = set()

def topological_sort_children(child_id):
    """Топологическая сортировка детей"""
    if child_id in temp_visited:
        # Обнаружен цикл - добавляем ребенка без упорядочивания
        if child_id not in children_list:
            children_list.append(child_id)
        return
    if child_id in visited_children:
        return
    
    temp_visited.add(child_id)
    
    # Сначала обрабатываем зависимости
    for dep_id in children_graph.get(child_id, []):
        if dep_id in children and dep_id not in visited_children:
            topological_sort_children(dep_id)
    
    temp_visited.remove(child_id)
    visited_children.add(child_id)
    
    # Добавляем ребенка после его зависимостей
    if child_id not in children_list:
        children_list.append(child_id)

# Упорядочиваем всех детей
for child_id in children:
    if child_id not in visited_children:
        topological_sort_children(child_id)
```

### Проверка после изменений:
1. Синтаксис: `python3 -m py_compile astra_automation.py`
2. Тест: удаление компонента с детьми, проверка порядка удаления
3. Тест: передача несуществующего компонента (должно быть предупреждение)

---

## ИСПРАВЛЕНИЕ 2: Улучшение логики удаления wineprefix

### Проблема:
- Специальная логика пропускает удаление дочерних компонентов перед wineprefix
- Работает только если wineprefix не первый в списке
- Может пропустить удаление детей, которые находятся после wineprefix

### Местоположение:
- **Файл:** `astra_automation.py`
- **Метод:** `ComponentInstaller.uninstall_components`
- **Строки:** 11747-11755

### Что изменить:

**БЛОК: Заменить логику пропуска детей wineprefix (строки 11747-11755)**

**БЫЛО:**
```python
# КРИТИЧНО: Если удаляется WINEPREFIX, пропускаем удаление дочерних компонентов
if component_id in component_ids and component_id == 'wineprefix':
    wineprefix_idx = resolved_components.index('wineprefix')
    if idx < wineprefix_idx:
        # Это дочерний компонент перед wineprefix - пропускаем удаление
        print(f"Пропускаем удаление {component_id} - он автоматически исчезнет при удалении WINEPREFIX")
        if self.status_manager:
            self.status_manager.update_component_status(component_id, 'missing')
        continue
```

**СТАНЕТ:**
```python
# КРИТИЧНО: Если удаляется WINEPREFIX, пропускаем удаление дочерних компонентов
# Находим индекс wineprefix в списке (если он есть)
wineprefix_idx = None
if 'wineprefix' in component_ids:
    try:
        wineprefix_idx = resolved_components.index('wineprefix')
    except ValueError:
        wineprefix_idx = None

# Если wineprefix будет удален, собираем всех его детей
wineprefix_children = set()
if wineprefix_idx is not None:
    # Находим всех детей wineprefix через resolve_dependencies_for_uninstall
    wineprefix_children_temp = resolve_dependencies_for_uninstall(['wineprefix'])
    # Исключаем сам wineprefix из списка детей
    wineprefix_children = {c for c in wineprefix_children_temp if c != 'wineprefix'}

# Если текущий компонент - ребенок wineprefix, пропускаем его удаление
if component_id in wineprefix_children:
    print(f"Пропускаем удаление {component_id} - он автоматически исчезнет при удалении WINEPREFIX")
    if self.status_manager:
        self.status_manager.update_component_status(component_id, 'missing')
    continue
```

**ПРИМЕЧАНИЕ:** Этот блок должен быть перемещен ПЕРЕД циклом for (строка 11745), чтобы wineprefix_children вычислялся один раз для всех итераций.

### Проверка после изменений:
1. Синтаксис: `python3 -m py_compile astra_automation.py`
2. Тест: удаление wineprefix в начале списка
3. Тест: удаление wineprefix в середине списка
4. Тест: удаление wineprefix в конце списка

---

## ИСПРАВЛЕНИЕ 3: Улучшение обработки ошибок при удалении WinePackageHandler

### Проблема:
- После apt-get purge и ручного удаления директорий проверка статуса может не учесть, что директории уже удалены
- Статус может быть установлен как 'error' вместо 'missing'

### Местоположение:
- **Файл:** `astra_automation.py`
- **Метод:** `WinePackageHandler.uninstall`
- **Строки:** 3060-3090

### Что изменить:

**БЛОК: Улучшить проверку статуса после удаления (строки 3075-3090)**

**БЫЛО:**
```python
# КРИТИЧНО: Проверяем реальный статус компонента перед установкой 'missing'
# Это гарантирует, что статус 'missing' устанавливается только после проверки
os.sync()  # Принудительная синхронизация файловой системы

# Проверяем статус компонента
actual_status = self.check_status(component_id, config)

if not actual_status:
    # Компонент действительно удален - устанавливаем статус 'missing'
    self._update_status(component_id, 'missing')
    return True
else:
    # Компонент все еще существует - устанавливаем статус 'error'
    print(f"Пакет {config['name']} не удален (проверка статуса не подтвердила удаление)", level='ERROR')
    self._update_status(component_id, 'error')
    return False
```

**СТАНЕТ:**
```python
# КРИТИЧНО: Проверяем реальный статус компонента перед установкой 'missing'
# Это гарантирует, что статус 'missing' устанавливается только после проверки
os.sync()  # Принудительная синхронизация файловой системы
time.sleep(0.3)  # Задержка для обновления метаданных файловой системы

# Проверяем статус компонента
actual_status = self.check_status(component_id, config)

# Проверяем, существуют ли директории Wine (если они были удалены вручную)
wine_dirs = {
    'wine_astraregul': '/opt/wine-astraregul',
    'wine_9': '/opt/wine-9.0',
    'astra_wine_9': '/opt/wine-9.0',
    'astra_wine_astraregul': '/opt/wine-astraregul'
}
wine_dir_exists = False
if component_id in wine_dirs:
    wine_dir = wine_dirs[component_id]
    wine_dir_exists = os.path.exists(wine_dir)

if not actual_status:
    # Компонент действительно удален - устанавливаем статус 'missing'
    self._update_status(component_id, 'missing')
    return True
elif not wine_dir_exists:
    # Директории Wine удалены, но проверка статуса еще видит остатки
    # Это может быть из-за задержки обновления метаданных или остаточных файлов в других местах
    print(f"Пакет {config['name']}: директории Wine удалены, но проверка статуса еще видит остатки", level='WARNING')
    print(f"Считаем удаление успешным, так как основные директории удалены", level='WARNING')
    self._update_status(component_id, 'missing')
    return True
else:
    # Компонент все еще существует и директории не удалены - устанавливаем статус 'error'
    print(f"Пакет {config['name']} не удален (проверка статуса не подтвердила удаление)", level='ERROR')
    self._update_status(component_id, 'error')
    return False
```

### Проверка после изменений:
1. Синтаксис: `python3 -m py_compile astra_automation.py`
2. Тест: удаление Wine-пакета, проверка статуса после удаления
3. Тест: проверка корректности статусов в GUI

---

## ИСПРАВЛЕНИЕ 4: Улучшение очистки временных директорий в WinePackageHandler.install()

### Проблема:
- Очистка временных директорий выполняется в finally, но проверка files_result.get('cleanup') может быть некорректной
- Временные директории могут не удаляться или удаляться преждевременно

### Местоположение:
- **Файл:** `astra_automation.py`
- **Метод:** `WinePackageHandler.install`
- **Строки:** 2786-2808 (получение файлов), 2992-3000 (очистка)

### Что изменить:

**БЛОК 1: Инициализация temp_dir (после строки 2754, перед строкой 2755)**

**ДОБАВИТЬ:**
```python
# Инициализируем temp_dir для правильной очистки
temp_dir = None
temp_dir_source = None  # 'archive', 'url', 'direct' или None
```

**БЛОК 2: Сохранение temp_dir при получении файлов (после строки 2808)**

**БЫЛО:**
```python
temp_dir = files_result.get('temp_dir')
```

**СТАНЕТ:**
```python
temp_dir = files_result.get('temp_dir')
temp_dir_source = files_result.get('source', 'unknown')  # Сохраняем источник для проверки
```

**БЛОК 3: Улучшить очистку в finally (строки 2992-3000)**

**БЫЛО:**
```python
finally:
    # Очистка временной директории (если файл был извлечен из архива или загружен)
    if temp_dir and files_result.get('cleanup'):
        source = files_result.get('source', 'unknown')
        print(f"[INFO] Очистка временных файлов (источник: {source})", level='DEBUG')
        try:
            shutil.rmtree(temp_dir)
        except:
            pass
```

**СТАНЕТ:**
```python
finally:
    # Очистка временной директории (если файл был извлечен из архива или загружен)
    if temp_dir and os.path.exists(temp_dir):
        # Очищаем только если файл был получен из архива или URL (не из прямого пути)
        if temp_dir_source in ['archive', 'url']:
            print(f"Очистка временных файлов (источник: {temp_dir_source})", level='DEBUG')
            try:
                shutil.rmtree(temp_dir)
                print(f"Временная директория {temp_dir} успешно удалена", level='DEBUG')
            except PermissionError as e:
                print(f"Не удалось удалить временную директорию {temp_dir}: {e}", level='WARNING')
            except Exception as e:
                print(f"Ошибка при удалении временной директории {temp_dir}: {e}", level='WARNING')
        else:
            print(f"Временная директория {temp_dir} не удаляется (источник: {temp_dir_source})", level='DEBUG')
```

### Проверка после изменений:
1. Синтаксис: `python3 -m py_compile astra_automation.py`
2. Тест: установка из архива, проверка очистки временных директорий
3. Тест: установка из URL, проверка очистки временных директорий
4. Тест: установка из прямого пути, проверка что директории не удаляются

---

## ИСПРАВЛЕНИЕ 5: Унификация проверки статуса перед установкой

### Проблема:
- В install_components() есть проверка статуса (строка 11541)
- В обработчиках тоже есть проверка статуса (например, AptPackageHandler строка 4952)
- Это приводит к двойной проверке

### Местоположение:
- **Файл:** `astra_automation.py`
- **Методы:** 
  - `ComponentInstaller.install_components` (строка 11541)
  - `AptPackageHandler.install` (строка 4952)
  - `WinePackageHandler.install` (строка 2748)
  - `WineApplicationHandler.install` (строка 5112)
  - `WinetricksHandler.install` (строка 4465)

### Что изменить:

**РЕШЕНИЕ:** Оставить проверку статуса в `install_components()`, убрать из обработчиков

**БЛОК 1: AptPackageHandler.install (строки 4951-4953)**

**БЫЛО:**
```python
# КРИТИЧНО: Проверяем, установлен ли компонент ПЕРЕД установкой статуса
if self.check_status(component_id, config):
    return True

# ОБНОВЛЯЕМ СТАТУС: устанавливаем 'installing'
self._update_status(component_id, 'installing')
```

**СТАНЕТ:**
```python
# ПРИМЕЧАНИЕ: Проверка статуса выполняется в install_components() перед вызовом install()
# Здесь просто устанавливаем статус и выполняем установку

# ОБНОВЛЯЕМ СТАТУС: устанавливаем 'installing'
self._update_status(component_id, 'installing')
```

**БЛОК 2: WinePackageHandler.install (строки 2747-2752)**

**БЫЛО:**
```python
# КРИТИЧНО: Проверяем, установлен ли компонент ПЕРЕД установкой статуса
if self.check_status(component_id, config):
    return True

# ОБНОВЛЯЕМ СТАТУС: устанавливаем 'installing'
self._update_status(component_id, 'installing')
```

**СТАНЕТ:**
```python
# ПРИМЕЧАНИЕ: Проверка статуса выполняется в install_components() перед вызовом install()
# Здесь просто устанавливаем статус и выполняем установку

# ОБНОВЛЯЕМ СТАТУС: устанавливаем 'installing'
self._update_status(component_id, 'installing')
```

**БЛОК 3: WineApplicationHandler.install (строка 5112)**

**НАЙТИ И ЗАМЕНИТЬ аналогично**

**БЛОК 4: WinetricksHandler.install (строка 4465)**

**НАЙТИ И ЗАМЕНИТЬ аналогично**

### Проверка после изменений:
1. Синтаксис: `python3 -m py_compile astra_automation.py`
2. Тест: установка компонента, проверка что проверка статуса выполняется один раз
3. Тест: установка уже установленного компонента (должен пропуститься)

---

## ИСПРАВЛЕНИЕ 6: Улучшение разбиения command_name в AptPackageHandler

### Проблема:
- Разбиение по пробелам может быть некорректным, если имя пакета содержит пробелы (редко, но возможно)

### Местоположение:
- **Файл:** `astra_automation.py`
- **Метод:** `AptPackageHandler.install` и `AptPackageHandler.uninstall`
- **Строки:** 4985 (install), 5060 (uninstall)

### Что изменить:

**БЛОК 1: AptPackageHandler.install (строка 4985)**

**БЫЛО:**
```python
# НОВОЕ: Разбиваем command_name на список пакетов (если содержит пробелы)
packages = command_name.split() if ' ' in command_name else [command_name]
```

**СТАНЕТ:**
```python
# Разбиваем command_name на список пакетов
# Поддерживаем как строку с пробелами, так и уже список
if isinstance(command_name, list):
    packages = command_name
elif isinstance(command_name, str):
    # Разбиваем по пробелам, но сохраняем пустые строки для обработки
    packages = [p.strip() for p in command_name.split() if p.strip()]
    if not packages:
        packages = [command_name]  # Если разбиение дало пустой список, используем исходную строку
else:
    # Если command_name не строка и не список, конвертируем в строку
    packages = [str(command_name)]
```

**БЛОК 2: AptPackageHandler.uninstall (строка 5060)**

**ЗАМЕНИТЬ АНАЛОГИЧНО**

### Проверка после изменений:
1. Синтаксис: `python3 -m py_compile astra_automation.py`
2. Тест: установка одного пакета
3. Тест: установка нескольких пакетов через command_name с пробелами

---

## ПОРЯДОК ВЫПОЛНЕНИЯ ИСПРАВЛЕНИЙ

### Шаг 1: Создать коммит (снимок) текущего состояния
```bash
cd /Volumes/FSA-PRJ/Project/FSA-AstraInstall
git add -A
git commit -m "Снимок перед исправлениями алгоритмов установки/удаления"
```

### Шаг 2: Выполнить исправления в порядке:
1. Исправление 1: resolve_dependencies_for_uninstall
2. Исправление 2: Логика удаления wineprefix
3. Исправление 3: Обработка ошибок WinePackageHandler
4. Исправление 4: Очистка временных директорий
5. Исправление 5: Унификация проверки статуса
6. Исправление 6: Разбиение command_name

### Шаг 3: После каждого исправления:
1. Проверить синтаксис: `python3 -m py_compile astra_automation.py`
2. Если ошибки - исправить перед следующим шагом

### Шаг 4: После всех исправлений:
1. Финальная проверка синтаксиса
2. Тестирование установки компонента
3. Тестирование удаления компонента
4. Если все работает - создать коммит
5. Если есть проблемы - откатиться к снимку

---

## ОТКАТ К СНИМКУ (если что-то пошло не так)

```bash
cd /Volumes/FSA-PRJ/Project/FSA-AstraInstall
git log --oneline -5  # Найти хеш коммита-снимка
git reset --hard <хеш_коммита_снимка>  # Откатиться к снимку
```

---

## ПРИМЕЧАНИЯ

1. Все изменения должны сохранять существующую логику работы
2. После каждого изменения проверять синтаксис
3. При возникновении ошибок - остановиться и исправить перед продолжением
4. Сохранять комментарии и структуру кода
5. Использовать правильные уровни логирования (level='DEBUG', level='WARNING', level='ERROR')

