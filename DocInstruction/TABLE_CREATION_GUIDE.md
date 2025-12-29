# Руководство по созданию новых таблиц (Treeview) в проекте FSA-AstraInstall

**Версия:** V3.7.208 (2025.12.29)  
**Компания:** ООО "НПА Вира-Реалтайм"  
**Разработчик:** @FoksSegr & AI Assistant (@LLM)

## 📋 Описание

Это руководство описывает пошаговый процесс создания новых таблиц (Treeview) в проекте FSA-AstraInstall с использованием системы управления размерами SizeManager. Все таблицы проекта должны использовать единый механизм сохранения и восстановления ширины колонок, позиций и выравнивания.

## 🎯 Цель

Обеспечить единообразие всех таблиц проекта и автоматическое сохранение/восстановление настроек пользователя (ширина колонок, выравнивание, порядок колонок).

## 📝 Пошаговая инструкция

### ШАГ 1: Создание Treeview с колонками

Создайте Treeview с указанием колонок:

```python
# Определяем колонки
columns = ('column1', 'column2', 'column3')

# Создаем Treeview
my_tree = self.ttk.Treeview(
    parent_frame,
    columns=columns,
    show='headings',  # Показывать только заголовки (без дерева)
    selectmode='extended'  # Мульти-выбор с Ctrl/Shift (или 'browse' для одиночного)
)
```

**Параметры:**
- `columns` - кортеж с именами колонок (используются как ключи)
- `show='headings'` - для обычных таблиц (без иерархии)
- `selectmode='extended'` - множественный выбор, `'browse'` - одиночный выбор

---

### ШАГ 2: Настройка заголовков колонок

Установите заголовки для каждой колонки:

```python
# Настраиваем заголовки колонок
my_tree.heading('column1', text='Колонка 1')
my_tree.heading('column2', text='Колонка 2')
my_tree.heading('column3', text='Колонка 3')
```

---

### ШАГ 3: Настройка через SizeManager

**КРИТИЧНО:** Все таблицы должны использовать SizeManager для автоматического управления размерами колонок.

```python
# Настраиваем таблицу через SizeManager (автоматическое сохранение/восстановление ширины колонок)
assert self.size_manager is not None, "SizeManager должен быть инициализирован"
self.size_manager.setup_tree(
    my_tree,
    'my_tree_key',  # Уникальный ключ таблицы (используется для сохранения настроек)
    auto_save=True,  # Автоматически сохранять при изменении ширины колонок
    enable_sorting=False,  # Сортировка не используется для этой таблицы (или True, если используется)
    enable_column_management=True,  # Включить управление порядком и видимостью колонок
    default_column_widths={
        'column1': {'width': 200, 'minwidth': 150},
        'column2': {'width': 180, 'minwidth': 150},
        'column3': {'width': 120, 'minwidth': 100, 'anchor': 'e'}  # 'e' = выравнивание по правому краю
    }
)
```

**Параметры `default_column_widths`:**
- `width` - ширина колонки по умолчанию (в пикселях)
- `minwidth` - минимальная ширина колонки (в пикселях)
- `anchor` - выравнивание текста:
  - `'w'` - по левому краю (west, по умолчанию)
  - `'e'` - по правому краю (east, для чисел)
  - `'center'` - по центру
  - `'n'` - сверху (north)
  - `'s'` - снизу (south)

**Параметры `setup_tree()`:**
- `tree` - объект Treeview
- `tree_key` - уникальный ключ таблицы (например, `'packages_tree'`, `'dialog_load_snapshot_tree'`)
- `auto_save=True` - автоматически сохранять изменения ширины колонок
- `enable_sorting=False` - включить сохранение сортировки (если используется)
- `enable_column_management=True` - включить управление порядком и видимостью колонок

---

### ШАГ 4: Добавление прокрутки

Добавьте Scrollbar для прокрутки таблицы:

```python
# Прокрутка
scrollbar = self.ttk.Scrollbar(parent_frame, orient=self.tk.VERTICAL, command=my_tree.yview)
my_tree.configure(yscrollcommand=scrollbar.set)

my_tree.pack(side=self.tk.LEFT, fill=self.tk.BOTH, expand=True)
scrollbar.pack(side=self.tk.RIGHT, fill=self.tk.Y)
```

---

### ШАГ 5: Добавление в min_sizes

**КРИТИЧНО:** Добавьте запись в словарь `min_sizes` в классе `SizeManager` (обычно около строки 14073):

```python
# В методе __init__ класса SizeManager, в словаре self.min_sizes:

# Колонки таблиц (минимальная ширина)
'packages_tree': 50,
'wine_tree': 50,
'processes_tree': 50,
'repos_tree': 50,
'installed_packages_tree': 50,
'available_packages_tree': 50,
'my_tree_key': 50,  # ← ДОБАВИТЬ ЗДЕСЬ
```

**Формат:** `'tree_key': 50,` где `50` - минимальная ширина колонок в пикселях (стандартное значение для всех таблиц).

---

### ШАГ 6: Добавление в defaults['tables']

**КРИТИЧНО:** Добавьте полную запись в словарь `self.defaults['tables']` в классе `SizeManager` (обычно около строки 14098):

```python
# В методе __init__ класса SizeManager, в словаре self.defaults['tables']:

'my_tree_key': {
    'column_widths': {'column1': 200, 'column2': 180, 'column3': 120},
    'column_anchors': {'column1': 'w', 'column2': 'w', 'column3': 'e'},
    'column_order': ['column1', 'column2', 'column3'],
    'column_visible': {'column1': True, 'column2': True, 'column3': True},
    'sort_column': None,
    'sort_direction': 'asc'
}
```

**Структура записи:**
- `column_widths` - словарь с ширинами колонок по умолчанию (должны совпадать с `default_column_widths` в `setup_tree()`)
- `column_anchors` - словарь с выравниванием колонок (должны совпадать с `anchor` в `default_column_widths`)
- `column_order` - список порядка колонок (все колонки должны быть перечислены)
- `column_visible` - словарь видимости колонок (обычно все `True`)
- `sort_column` - колонка сортировки по умолчанию (`None` если сортировка не используется)
- `sort_direction` - направление сортировки (`'asc'` или `'desc'`)

**ВАЖНО:** Значения в `defaults['tables']` должны точно соответствовать значениям в `default_column_widths` при вызове `setup_tree()`.

---

### ШАГ 7: Для диалоговых окон - сохранение ссылки на Treeview

**КРИТИЧНО:** Если таблица находится в диалоговом окне (Toplevel), сохраните ссылку на Treeview в окне:

```python
# Сохраняем ссылку на Treeview в окне для последующего доступа
dialog_window._my_tree = my_tree
```

Это необходимо для восстановления ширины колонок при повторном открытии окна.

---

### ШАГ 8: Для диалоговых окон - восстановление при повторном открытии

**КРИТИЧНО:** Если таблица находится в диалоговом окне, добавьте восстановление ширины колонок при повторном открытии окна:

```python
# В начале функции создания диалога, в блоке проверки существующего окна:

if existing_dialog and existing_dialog.winfo_exists():
    # ВОССТАНОВЛЕНИЕ ГЕОМЕТРИИ через SizeManager
    if self.size_manager is not None:
        saved_geometry = self.size_manager.get_saved_geometry('dialog_key')
        if saved_geometry:
            try:
                self.size_manager._restore_window_geometry(
                    existing_dialog, 
                    saved_geometry, 
                    'full',  # или 'position', 'width_and_position', 'min_height'
                    '900x600'  # default_size
                )
                existing_dialog.update_idletasks()
            except Exception as e:
                print(f"[WARNING] Не удалось восстановить геометрию окна: {e}", level='WARNING')
        
        # ВОССТАНОВЛЕНИЕ ШИРИНЫ КОЛОНОК Treeview
        if hasattr(existing_dialog, '_my_tree'):
            existing_tree = existing_dialog._my_tree
            try:
                self.size_manager._restore_tree_columns(
                    existing_tree,
                    'my_tree_key',
                    default_column_widths={
                        'column1': {'width': 200, 'minwidth': 150},
                        'column2': {'width': 180, 'minwidth': 150},
                        'column3': {'width': 120, 'minwidth': 100, 'anchor': 'e'}
                    }
                )
            except Exception as e:
                print(f"[WARNING] Не удалось восстановить ширину колонок таблицы: {e}", level='WARNING')
    
    # Окно уже открыто - поднимаем его на передний план
    existing_dialog.lift()
    existing_dialog.focus_set()
    return
```

**ВАЖНО:** Значения в `default_column_widths` при восстановлении должны точно совпадать с значениями при создании таблицы.

---

## 📋 Чек-лист создания новой таблицы

Используйте этот чек-лист, чтобы ничего не забыть:

- [ ] **ШАГ 1:** Создан Treeview с колонками (`columns`, `show='headings'`, `selectmode`)
- [ ] **ШАГ 2:** Настроены заголовки колонок (`tree.heading()`)
- [ ] **ШАГ 3:** Вызван `size_manager.setup_tree()` с правильными параметрами:
  - [ ] `auto_save=True`
  - [ ] `enable_sorting=False` (или `True` если используется)
  - [ ] `enable_column_management=True`
  - [ ] `default_column_widths` с указанием `width`, `minwidth` и `anchor`
- [ ] **ШАГ 4:** Добавлена прокрутка (Scrollbar)
- [ ] **ШАГ 5:** Добавлена запись в `min_sizes` (строка ~14073)
- [ ] **ШАГ 6:** Добавлена полная запись в `defaults['tables']` (строка ~14098):
  - [ ] `column_widths`
  - [ ] `column_anchors`
  - [ ] `column_order`
  - [ ] `column_visible`
  - [ ] `sort_column`
  - [ ] `sort_direction`
- [ ] **ШАГ 7 (для диалогов):** Сохранена ссылка на Treeview в окне (`dialog._my_tree = my_tree`)
- [ ] **ШАГ 8 (для диалогов):** Добавлено восстановление ширины колонок при повторном открытии

---

## 📝 Примеры из проекта

### Пример 1: Таблица в главном окне (repos_tree)

```python
# Создание таблицы
columns = ('status', 'type', 'uri', 'distribution', 'components')
self.repos_tree = self.ttk.Treeview(repos_list_frame, columns=columns, show='headings', height=12)

# Настройка заголовков
self.repos_tree.heading('status', text='Статус')
self.repos_tree.heading('type', text='Тип')
self.repos_tree.heading('uri', text='URI')
self.repos_tree.heading('distribution', text='Дистрибутив')
self.repos_tree.heading('components', text='Компоненты')

# Настройка через SizeManager
self.size_manager.setup_tree(
    self.repos_tree,
    'repos_tree',
    auto_save=True,
    enable_sorting=False,
    enable_column_management=True,
    default_column_widths={
        'status': {'width': 100},
        'type': {'width': 80, 'anchor': 'center'},
        'uri': {'width': 400},
        'distribution': {'width': 180, 'anchor': 'center'},
        'components': {'width': 250}
    }
)
```

### Пример 2: Таблица в диалоговом окне (dialog_load_snapshot_tree)

```python
# Создание таблицы
columns = ('snapshot', 'datetime', 'files')
snapshots_tree = self.ttk.Treeview(
    list_frame,
    columns=columns,
    show='headings',
    selectmode='extended'
)

# Настройка заголовков
snapshots_tree.heading('snapshot', text='Снимок')
snapshots_tree.heading('datetime', text='Дата и время')
snapshots_tree.heading('files', text='Файлов')

# Настройка через SizeManager
self.size_manager.setup_tree(
    snapshots_tree,
    'dialog_load_snapshot_tree',
    auto_save=True,
    enable_sorting=False,
    enable_column_management=True,
    default_column_widths={
        'snapshot': {'width': 200, 'minwidth': 150},
        'datetime': {'width': 180, 'minwidth': 150},
        'files': {'width': 120, 'minwidth': 100, 'anchor': 'e'}
    }
)

# Сохранение ссылки в окне
load_window._snapshots_tree = snapshots_tree

# В блоке проверки существующего окна:
if existing_dialog and existing_dialog.winfo_exists():
    # ... восстановление геометрии окна ...
    
    # ВОССТАНОВЛЕНИЕ ШИРИНЫ КОЛОНОК Treeview
    if hasattr(existing_dialog, '_snapshots_tree'):
        existing_tree = existing_dialog._snapshots_tree
        self.size_manager._restore_tree_columns(
            existing_tree,
            'dialog_load_snapshot_tree',
            default_column_widths={
                'snapshot': {'width': 200, 'minwidth': 150},
                'datetime': {'width': 180, 'minwidth': 150},
                'files': {'width': 120, 'minwidth': 100, 'anchor': 'e'}
            }
        )
```

---

## ⚠️ Важные замечания

### 1. Единообразие настроек

Все таблицы проекта должны использовать одинаковые параметры:
- `auto_save=True` - всегда включено
- `enable_column_management=True` - всегда включено (кроме особых случаев)
- `enable_sorting=False` - если сортировка не используется (с комментарием)

### 2. Соответствие значений

Значения в трех местах должны совпадать:
1. `default_column_widths` в `setup_tree()`
2. `default_column_widths` в `_restore_tree_columns()` (для диалогов)
3. `defaults['tables']['tree_key']` в конфигурации

### 3. Уникальность ключей

Ключ таблицы (`tree_key`) должен быть уникальным в рамках всего проекта. Используйте понятные имена:
- Для таблиц в главном окне: `'packages_tree'`, `'wine_tree'`, `'repos_tree'`
- Для таблиц в диалогах: `'dialog_load_snapshot_tree'`, `'dialog_package_info_tree'`

### 4. Выравнивание колонок

Используйте правильное выравнивание:
- `'w'` (west) - для текста (по умолчанию)
- `'e'` (east) - для чисел (количества, размеры)
- `'center'` - для статусов, флагов, иконок

### 5. Минимальные ширины

Всегда указывайте `minwidth` для каждой колонки, чтобы предотвратить слишком узкие колонки при изменении размера окна.

---

## 🔍 Проверка после создания

После создания новой таблицы проверьте:

1. ✅ Таблица отображается корректно
2. ✅ Ширина колонок сохраняется при изменении размера
3. ✅ Ширина колонок восстанавливается при перезапуске приложения
4. ✅ Для диалогов: ширина колонок восстанавливается при повторном открытии окна
5. ✅ Выравнивание колонок работает корректно
6. ✅ Нет ошибок в консоли при сохранении/восстановлении настроек

---

## 📚 Связанные документы

- `STARTUP_ALGORITHM.md` - алгоритм запуска приложения
- `ALGORITHM_BEHAVIOR.md` - алгоритм поведения системы
- Основной код: `FSA-AstraInstall.py` (класс `SizeManager`, строки ~14000-15000)

---

## 🔄 История изменений

| Дата | Изменение | Автор |
|------|-----------|-------|
| 2025.12.29 | Создано руководство по созданию таблиц | AI Assistant |

---

**Дата создания:** 2025.12.29  
**Дата последнего обновления:** 2025.12.29  
**Версия документа:** 1.0.0

