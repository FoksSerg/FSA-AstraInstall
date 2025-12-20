# План реализации реактивного управления состоянием кнопок GUI

**Версия документа:** 1.0.0  
**Дата создания:** 2025.12.20  
**Проект:** FSA-AstraInstall  
**Компания:** ООО "НПА Вира-Реалтайм"  
**Текущая версия проекта:** V3.4.189 (2025.12.20)

## 📋 Оглавление

1. [Проблема и цель](#проблема-и-цель)
2. [Текущая архитектура](#текущая-архитектура)
3. [Реактивный подход](#реактивный-подход)
4. [Детальный план реализации](#детальный-план-реализации)
5. [Структура кода](#структура-кода)
6. [Миграция существующего кода](#миграция-существующего-кода)
7. [Тестирование](#тестирование)
8. [Риски и митигация](#риски-и-митигация)

---

## 🎯 Проблема и цель

### Текущие проблемы

1. **Дублирование кода блокировки кнопок** - явная блокировка/разблокировка в каждом методе (`run_wine_install()`, `run_wine_uninstall()`, и т.д.)
2. **Риск забыть обновить кнопки** - при добавлении новых процессов легко пропустить блокировку
3. **Неконсистентность** - кнопка отмены блокируется при обновлении системы, хотя должна быть активна
4. **Разблокировка при клике на чекбоксы** - `_update_wine_buttons()` не проверяет `PROCESS_STATE`
5. **Сложность поддержки** - изменения логики блокировки требуют правок в множестве мест

### Цель

Реализовать реактивную систему управления состоянием кнопок, где:
- Все кнопки автоматически реагируют на изменения `PROCESS_STATE`
- Единая точка управления через `set_process_state()`
- Минимум явных вызовов блокировки/разблокировки
- Сохранение локальной логики для сложных кнопок (например, "Создать Образ")

---

## 🏗️ Текущая архитектура

### Глобальные переменные состояния

```python
PROCESS_STATE = 'idle'  # 'idle', 'installing', 'uninstalling', 'updating', 'automation'
PROCESS_PAUSED = False  # Флаг паузы
```

### Функция установки состояния

```python
def set_process_state(state: str, paused: bool = False):
    global PROCESS_STATE, PROCESS_PAUSED
    PROCESS_STATE = state
    PROCESS_PAUSED = paused
    # ... управление progress_manager ...
    _update_buttons_state()  # Уже вызывает обновление кнопок!
```

### Текущая функция обновления кнопок

```python
def _update_buttons_state():
    """Обновляет состояние кнопок в GUI на основе текущего состояния процесса"""
    global PROCESS_STATE, PROCESS_PAUSED
    # ... обновление ограниченного набора кнопок ...
```

**Проблема:** Обновляет только часть кнопок, не учитывает все вкладки и таблицы.

---

## ⚡ Реактивный подход

### Концепция

1. **Регистрация кнопок** - при инициализации GUI регистрируем все кнопки с правилами их состояния
2. **Автоматическое обновление** - при изменении `PROCESS_STATE` все зарегистрированные кнопки обновляются автоматически
3. **Локальная логика** - для кнопок с особыми проверками (категория, статус компонента) вызываются отдельные методы

### Преимущества

- ✅ Единая точка управления - все через `set_process_state()`
- ✅ Автоматическая синхронизация - кнопки всегда соответствуют состоянию
- ✅ Меньше кода - не нужно явно блокировать/разблокировать
- ✅ Проще поддерживать - правила в одном месте
- ✅ Меньше ошибок - невозможно забыть обновить кнопки

---

## 📝 Детальный план реализации

### Этап 1: Регистрация кнопок

**Файл:** `FSA-AstraInstall.py`  
**Класс:** `AutomationGUI`  
**Метод:** `__init__()` или новый метод `_register_reactive_buttons()`

**Действия:**
1. Добавить словарь `self.reactive_buttons` для хранения правил
2. Зарегистрировать все кнопки с их правилами состояния
3. Разделить кнопки на категории:
   - `blocked_on_any_process` - блокируются при любом процессе
   - `special_rules` - кнопки с особыми правилами (отмена, остановка)
   - `local_logic` - кнопки с локальной логикой (создать образ)

**Код:**
```python
def _register_reactive_buttons(self):
    """Регистрация кнопок для реактивного обновления на основе PROCESS_STATE"""
    self.reactive_buttons = {
        # Кнопки, которые блокируются при любом процессе (is_running = True)
        'blocked_on_any_process': [
            'sync_time_button',
            'start_button',
            'check_wine_button',
            'install_wine_button',
            'uninstall_wine_button',
            'run_checks_button',
            'load_repos_button',
            'check_repos_button2',
            'auto_check_repos_button',
            'update_repos_button',
            'refresh_button',
        ],
        
        # Кнопки с особыми правилами (словарь с enabled_states/disabled_states)
        'special_rules': {
            'cancel_operation_button': {
                'enabled_states': ['installing', 'uninstalling', 'updating'],
                'disabled_states': ['idle', 'automation']
            },
            'stop_button': {
                'enabled_states': ['automation'],
                'disabled_states': ['idle', 'installing', 'uninstalling', 'updating']
            }
        },
        
        # Кнопки с локальной логикой (обновляются через отдельные методы)
        'local_logic': [
            'create_template_button',  # Обновляется через _update_create_template_button_state()
        ]
    }
```

**Вызов:** В `__init__()` после создания всех виджетов:
```python
# После создания всех виджетов
self._register_reactive_buttons()
```

---

### Этап 2: Улучшение функции `_update_buttons_state()`

**Файл:** `FSA-AstraInstall.py`  
**Функция:** `_update_buttons_state()` (строка 26849)

**Действия:**
1. Использовать зарегистрированные правила из `self.reactive_buttons`
2. Блокировать кнопки из `blocked_on_any_process` при `is_running = True`
3. Применять особые правила для кнопок из `special_rules`
4. Вызывать локальные методы обновления для кнопок из `local_logic`
5. Блокировать/разблокировать таблицы (wine_tree, repos_tree)

**Код:**
```python
def _update_buttons_state():
    """Реактивное обновление состояния кнопок на основе PROCESS_STATE"""
    global PROCESS_STATE, PROCESS_PAUSED
    
    if not hasattr(sys, '_gui_instance') or not sys._gui_instance:
        return
    
    gui = sys._gui_instance
    is_running = PROCESS_STATE != 'idle'
    
    try:
        # Проверяем наличие зарегистрированных правил
        if not hasattr(gui, 'reactive_buttons'):
            # Fallback на старую логику если правила не зарегистрированы
            _update_buttons_state_legacy()
            return
        
        # 1. БЛОКИРУЕМ кнопки при любом процессе
        blocked_buttons = gui.reactive_buttons.get('blocked_on_any_process', [])
        for button_name in blocked_buttons:
            if hasattr(gui, button_name):
                button = getattr(gui, button_name)
                button.config(state=gui.tk.DISABLED if is_running else gui.tk.NORMAL)
        
        # 2. ОСОБЫЕ ПРАВИЛА для специфичных кнопок
        special_rules = gui.reactive_buttons.get('special_rules', {})
        for button_name, rule in special_rules.items():
            if hasattr(gui, button_name):
                button = getattr(gui, button_name)
                enabled = PROCESS_STATE in rule.get('enabled_states', [])
                button.config(state=gui.tk.NORMAL if enabled else gui.tk.DISABLED)
        
        # 3. КНОПКИ С ЛОКАЛЬНОЙ ЛОГИКОЙ (вызываем их методы обновления)
        if not is_running:  # Только когда процесс не активен
            # Обновляем кнопки Wine с проверкой выбранных компонентов
            if hasattr(gui, '_update_wine_buttons'):
                gui._update_wine_buttons()
            
            # Обновляем кнопку "Создать Образ" с локальными проверками
            if hasattr(gui, '_update_create_template_button_state'):
                gui._update_create_template_button_state()
        
        # 4. БЛОКИРОВКА ТАБЛИЦ (отключение обработчиков кликов)
        if hasattr(gui, 'wine_tree'):
            if is_running:
                # Отключаем обработчики кликов
                gui.wine_tree.unbind('<Button-1>')
                gui.wine_tree.unbind('<Double-Button-1>')
            else:
                # Включаем обработчики кликов
                gui.wine_tree.bind('<Button-1>', gui.on_wine_tree_click)
                gui.wine_tree.bind('<Double-Button-1>', gui.on_wine_tree_double_click)
        
        if hasattr(gui, 'repos_tree'):
            if is_running:
                gui.repos_tree.unbind('<Button-3>')
                gui.repos_tree.unbind('<Double-1>')
            else:
                gui.repos_tree.bind('<Button-3>', gui.show_repo_context_menu)
                gui.repos_tree.bind('<Double-1>', gui.show_repo_details)
        
    except Exception as e:
        print(f"[ERROR] Ошибка реактивного обновления кнопок: {e}", level='ERROR')
```

---

### Этап 3: Исправление `_update_wine_buttons()`

**Файл:** `FSA-AstraInstall.py`  
**Метод:** `_update_wine_buttons()` (строка 21763)

**Проблема:** Не проверяет `PROCESS_STATE` перед разблокировкой кнопок

**Исправление:**
```python
def _update_wine_buttons(self):
    """Обновление состояния кнопок установки/удаления"""
    # КРИТИЧНО: Проверяем состояние процесса - не разблокируем кнопки во время выполнения
    global PROCESS_STATE
    is_running = PROCESS_STATE != 'idle'
    
    if is_running:
        # Во время процесса кнопки должны быть заблокированы
        return
    
    selected_count = sum(1 for checked in self.wine_checkboxes.values() if checked)
    
    if selected_count > 0:
        self.install_wine_button.config(state=self.tk.NORMAL)
        self.uninstall_wine_button.config(state=self.tk.NORMAL)
    else:
        self.install_wine_button.config(state=self.tk.DISABLED)
        self.uninstall_wine_button.config(state=self.tk.DISABLED)
```

---

### Этап 4: Удаление явных блокировок из методов

**Файлы и методы:**
1. `run_wine_install()` (строка 20899) - удалить явные блокировки
2. `run_wine_uninstall()` (строка 21817) - удалить явные блокировки
3. `_install_completed()` (строка 21074) - удалить явные разблокировки, добавить вызов `_update_create_template_button_state()`
4. `_wine_uninstall_completed()` (строка 22545) - удалить явные разблокировки, добавить вызов `_update_create_template_button_state()`

**Пример для `run_wine_install()`:**

**Было:**
```python
def run_wine_install(self):
    # ... код ...
    
    # Устанавливаем состояние процесса
    set_process_state('installing', paused=False)
    
    # Блокируем кнопки во время установки
    self.install_wine_button.config(state=self.tk.DISABLED)
    self.uninstall_wine_button.config(state=self.tk.DISABLED)
    self.check_wine_button.config(state=self.tk.DISABLED)
    # Активируем кнопку отмены
    self.cancel_operation_button.config(state=self.tk.NORMAL)
    # ... остальной код ...
```

**Станет:**
```python
def run_wine_install(self):
    # ... код ...
    
    # Устанавливаем состояние процесса - ВСЕ кнопки обновятся автоматически!
    set_process_state('installing', paused=False)
    
    # ... остальной код (явные блокировки удалены) ...
```

**Пример для `_install_completed()`:**

**Было:**
```python
def _install_completed(self, success):
    # Сбрасываем состояние процесса
    set_process_state('idle', paused=False)
    
    # Разблокируем кнопки
    self.install_wine_button.config(state=self.tk.NORMAL)
    self.uninstall_wine_button.config(state=self.tk.NORMAL)
    self.check_wine_button.config(state=self.tk.NORMAL)
    # Деактивируем кнопку отмены
    self.cancel_operation_button.config(state=self.tk.DISABLED)
    # ... остальной код ...
```

**Станет:**
```python
def _install_completed(self, success):
    # Сбрасываем состояние процесса - ВСЕ кнопки обновятся автоматически!
    set_process_state('idle', paused=False)
    
    # Обновляем кнопку "Создать Образ" с локальными проверками
    self._update_create_template_button_state()
    
    # ... остальной код (явные разблокировки удалены) ...
```

---

### Этап 5: Исправление кнопки отмены при обновлении системы

**Проблема:** Кнопка отмены блокируется при `PROCESS_STATE == 'updating'`, хотя должна быть активна

**Решение:** Уже исправлено в `special_rules` - кнопка отмены активна при `['installing', 'uninstalling', 'updating']`

---

### Этап 6: Блокировка чекбоксов (опционально)

**Текущее состояние:** Чекбоксы не блокируются явно, но таблица `wine_tree` блокируется (отключаются обработчики кликов)

**Решение:** Блокировка таблицы уже реализована в этапе 2. Чекбоксы в таблице автоматически становятся недоступными для кликов.

---

## 📐 Структура кода

### Иерархия вызовов

```
set_process_state('installing')
    ↓
_update_buttons_state()
    ↓
    ├─ Блокировка кнопок из 'blocked_on_any_process'
    ├─ Применение правил из 'special_rules'
    ├─ Вызов локальных методов для 'local_logic' (если is_running = False)
    └─ Блокировка/разблокировка таблиц
```

### Зависимости

- `set_process_state()` → вызывает `_update_buttons_state()`
- `_update_buttons_state()` → использует `gui.reactive_buttons`
- `_update_wine_buttons()` → вызывается из `_update_buttons_state()` при `is_running = False`
- `_update_create_template_button_state()` → вызывается из `_update_buttons_state()` при `is_running = False`

---

## 🔄 Миграция существующего кода

### Шаг 1: Добавить регистрацию кнопок

**Место:** `AutomationGUI.__init__()` после создания всех виджетов

### Шаг 2: Обновить `_update_buttons_state()`

**Место:** Функция `_update_buttons_state()` (строка 26849)

### Шаг 3: Исправить `_update_wine_buttons()`

**Место:** Метод `_update_wine_buttons()` (строка 21763)

### Шаг 4: Удалить явные блокировки

**Места:**
- `run_wine_install()` - строки 20980-20985
- `run_wine_uninstall()` - строки 21892-21897
- `_install_completed()` - строки 21079-21084
- `_wine_uninstall_completed()` - строки 22567-22569

### Шаг 5: Добавить вызовы локальных методов

**Места:**
- `_install_completed()` - после `set_process_state('idle')`
- `_wine_uninstall_completed()` - после `set_process_state('idle')`

---

## ✅ Тестирование

### Сценарии тестирования

1. **Установка компонентов:**
   - Нажать "Установить выбранные"
   - Проверить: все кнопки заблокированы, кнопка отмены активна
   - Проверить: таблица wine_tree не реагирует на клики
   - После завершения: все кнопки разблокированы, кнопка отмены неактивна

2. **Удаление компонентов:**
   - Нажать "Удалить выбранные"
   - Проверить: все кнопки заблокированы, кнопка отмены активна
   - После завершения: все кнопки разблокированы

3. **Обновление системы:**
   - Нажать "Запустить" на вкладке "Обновление ОС"
   - Проверить: все кнопки заблокированы, кнопка отмены активна
   - После завершения: все кнопки разблокированы

4. **Клик на чекбоксы во время процесса:**
   - Запустить установку
   - Попытаться кликнуть на чекбокс в таблице
   - Проверить: чекбокс не меняется (таблица заблокирована)

5. **Кнопка "Создать Образ":**
   - Выбрать один компонент с категорией `wine_environment` и статусом `ok`
   - Проверить: кнопка активна
   - Выбрать другой компонент
   - Проверить: кнопка неактивна (локальная логика работает)

---

## ⚠️ Риски и митигация

### Риск 1: Кнопки не обновляются при прямом изменении PROCESS_STATE

**Митигация:** Всегда использовать `set_process_state()`, не изменять `PROCESS_STATE` напрямую

### Риск 2: Локальная логика не вызывается

**Митигация:** В `_update_buttons_state()` явно вызывать локальные методы при `is_running = False`

### Риск 3: Кнопка не зарегистрирована

**Митигация:** Fallback на старую логику в `_update_buttons_state()` если правила не зарегистрированы

### Риск 4: Ошибка при обновлении кнопки

**Митигация:** Try-except блок в `_update_buttons_state()` для обработки ошибок

---

## 📊 Итоговая структура

### Новые методы/функции

1. `AutomationGUI._register_reactive_buttons()` - регистрация кнопок
2. `_update_buttons_state()` - улучшенная версия с реактивной логикой
3. `_update_buttons_state_legacy()` - fallback на старую логику (опционально)

### Измененные методы

1. `AutomationGUI._update_wine_buttons()` - добавлена проверка `PROCESS_STATE`
2. `AutomationGUI.run_wine_install()` - удалены явные блокировки
3. `AutomationGUI.run_wine_uninstall()` - удалены явные блокировки
4. `AutomationGUI._install_completed()` - удалены явные разблокировки, добавлен вызов локального метода
5. `AutomationGUI._wine_uninstall_completed()` - удалены явные разблокировки, добавлен вызов локального метода

### Удаленный код

- Явные `button.config(state=...)` из методов установки/удаления
- Дублирующие блокировки кнопок

---

## 🎯 Результат

После реализации:
- ✅ Все кнопки автоматически реагируют на изменения `PROCESS_STATE`
- ✅ Единая точка управления через `set_process_state()`
- ✅ Меньше кода - нет явных блокировок/разблокировок
- ✅ Проще поддерживать - правила в одном месте
- ✅ Меньше ошибок - невозможно забыть обновить кнопки
- ✅ Сохранена локальная логика для сложных кнопок

---

**Дата создания:** 2025.12.20  
**Версия документа:** 1.0.0  
**Статус:** 📝 ПЛАН ГОТОВ К РЕАЛИЗАЦИИ
