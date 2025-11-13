# Версия: V2.5.124 (2025.11.13)

# АЛГОРИТМ ПОВЕДЕНИЯ СИСТЕМЫ УСТАНОВКИ/УДАЛЕНИЯ

## 🎯 ОСНОВНЫЕ ПРИНЦИПЫ

### 1. Последовательность выполнения
- **Все компоненты устанавливаются/удаляются ПОСЛЕДОВАТЕЛЬНО** (не параллельно!)
- Каждый компонент ждет завершения предыдущего
- Статус меняется синхронно с выполнением

### 2. Статусы компонентов ⚠️
- `missing` - компонент не установлен (по умолчанию) ✅ **Реализовано**
- `pending` - компонент выбран пользователем, ждет установки/удаления ❌ **НЕ используется**
- `installing` / `removing` - компонент в процессе установки/удаления ❌ **НЕ используется**
- `ok` - компонент успешно установлен ✅ **Реализовано** (через проверку файлов)
- `error` - ошибка установки/удаления ❌ **НЕ используется**

**ВНИМАНИЕ:** В текущей реализации `ComponentStatusManager` существует и имеет методы для работы со статусами, но они **НЕ вызываются** в процессе установки/удаления. `UniversalInstaller` не имеет доступа к `ComponentStatusManager` и не обновляет статусы во время установки.

### 3. Чекбоксы
- **Снимаются ТОЛЬКО с завершенных компонентов** (статус `ok` или `missing` после завершения операции)
- **НЕ снимаются** с компонентов в процессе (`pending`, `installing`, `removing`)
- **НЕ снимаются** с компонентов с ошибкой (`error`)

### 4. Кнопки
- **Блокируются** при запуске установки/удаления
- **Разблокируются** после завершения всех операций

---

## 📋 СЦЕНАРИЙ 1: УСТАНОВКА ОДНОГО РОДИТЕЛЬСКОГО КОМПОНЕНТА

**Пример:** Пользователь выбрал только `WINEPREFIX`

### Этап 1: Выбор компонента (пользователь)
1. Пользователь отмечает чекбокс `WINEPREFIX` → `☑`
2. Нажимает кнопку "Установить"

### Этап 2: Подготовка (run_wine_install)
1. Получаем список выбранных: `selected = ['wineprefix']` (ID компонентов)
2. Блокируем кнопки "Установить" и "Проверить"
3. Запускаем поток установки `_perform_wine_install(selected)`
4. **ВНИМАНИЕ:** В текущей реализации статус `pending` НЕ устанавливается перед установкой
5. Разрешение зависимостей происходит внутри `install_components()`:
   - Вызывается `resolve_dependencies(selected)`
   - `WINEPREFIX` зависит от `wine_astraregul`
   - Автоматически добавляется `wine_astraregul`
   - Финальный список для установки: `['wine_astraregul', 'wineprefix']`

### Этап 3: Выполнение установки (_perform_wine_install → install_components)
**Последовательность выполнения (ВАЖНО: ПОСЛЕДОВАТЕЛЬНО!):**

#### Компонент 1: `wine_astraregul` (зависимость)
1. Проверка `check_component_status('wine_astraregul')`: не установлен → начинаем установку
2. **Статус:** ⚠️ **НЕ обновляется** - остается `missing` (статус `installing` НЕ устанавливается!)
3. Выполнение `install_component('wine_astraregul')` → **ЖДЕМ завершения** (последовательно!)
4. Проверка результата:
   - ✅ Успех → статус определяется при следующей проверке как `ok`
   - ❌ Ошибка → статус определяется при следующей проверке как `missing`
5. Вызывается callback `UPDATE_COMPONENT:wine_astraregul` для обновления GUI
6. **Чекбокс:** НЕ меняется (не был выбран пользователем)

#### Компонент 2: `wineprefix` (выбранный пользователем)
1. Проверка `check_component_status('wineprefix')`: не установлен → начинаем установку
2. **Статус:** ⚠️ **НЕ обновляется** - остается `missing` (статус `installing` НЕ устанавливается!)
3. Выполнение `install_component('wineprefix')` → **ЖДЕМ завершения** (последовательно!)
4. Проверка результата:
   - ✅ Успех → статус определяется при следующей проверке как `ok`
   - ❌ Ошибка → статус определяется при следующей проверке как `missing`
5. Вызывается callback `UPDATE_COMPONENT:wineprefix` для обновления GUI
6. **Чекбокс:** После завершения и обновления GUI → автоматически снимается (статус `ok`)

### Этап 4: Завершение (_install_completed)
1. Останавливаем все фоновые процессы (таймеры, мониторинг)
2. Разблокируем кнопки
3. Обновляем GUI (все статусы)
4. Снимаем чекбоксы с завершенных компонентов

---

## 📋 СЦЕНАРИЙ 2: УСТАНОВКА ОДНОГО ДОЧЕРНЕГО КОМПОНЕНТА

**Пример:** Пользователь выбрал только `Wine Mono`

### Этап 1: Выбор компонента (пользователь)
1. Пользователь отмечает чекбокс `Wine Mono` → `☑`
2. Нажимает кнопку "Установить"

### Этап 2: Подготовка (run_wine_install)
1. Получаем список выбранных: `selected = ['wine-mono']`
2. **Разрешаем зависимости:**
   - `Wine Mono` зависит от `wineprefix`
   - `wineprefix` зависит от `wine_astraregul`
   - Добавляем оба автоматически
   - Финальный список: `['wine_astraregul', 'wineprefix', 'wine-mono']`
3. **Устанавливаем статусы:**
   - Только для ЯВНО выбранных: `wine-mono` → `pending`
   - Зависимости НЕ получают `pending`
4. Обновляем GUI
5. Блокируем кнопки
6. Запускаем поток установки

### Этап 3: Выполнение установки
**Последовательность (ПОСЛЕДОВАТЕЛЬНО!):**

#### Компонент 1: `wine_astraregul` (родительская зависимость)
1. `missing` → `installing` → выполняем → `ok` / `error`

#### Компонент 2: `wineprefix` (родительская зависимость)
1. `missing` → `installing` → выполняем → `ok` / `error`

#### Компонент 3: `wine-mono` (выбранный пользователем)
1. `pending` → `installing` → выполняем → `ok` / `error`
2. **Чекбокс:** После завершения автоматически снимается

### Этап 4: Завершение
- Все фоновые процессы остановлены
- Кнопки разблокированы
- Чекбоксы сняты с завершенных

---

## 📋 СЦЕНАРИЙ 3: УСТАНОВКА НЕСКОЛЬКИХ КОМПОНЕНТОВ

**Пример:** Пользователь выбрал `WINEPREFIX` и `Wine Mono`

### Этап 1: Выбор компонентов (пользователь)
1. Пользователь отмечает `WINEPREFIX` → `☑`
2. Пользователь отмечает `Wine Mono` → `☑`
3. Нажимает "Установить"

### Этап 2: Подготовка (run_wine_install)
1. Получаем список: `selected = ['wineprefix', 'wine-mono']`
2. **Разрешаем зависимости:**
   - `WINEPREFIX` → добавляет `wine_astraregul`
   - `Wine Mono` → добавляет `wineprefix` (уже есть, дубликат игнорируется)
   - Финальный список: `['wine_astraregul', 'wineprefix', 'wine-mono']`
3. **Устанавливаем статусы:**
   - Только для ЯВНО выбранных: `wineprefix` → `pending`, `wine-mono` → `pending`
4. Обновляем GUI
5. Блокируем кнопки
6. Запускаем поток

### Этап 3: Выполнение установки
**Последовательность (ПОСЛЕДОВАТЕЛЬНО!):**

#### Компонент 1: `wine_astraregul`
- `missing` → `installing` → выполняем → `ok` / `error`

#### Компонент 2: `wineprefix`
- `pending` → `installing` → выполняем → `ok` / `error`
- **Чекбокс:** После завершения снимается

#### Компонент 3: `wine-mono`
- `pending` → `installing` → выполняем → `ok` / `error`
- **Чекбокс:** После завершения снимается

---

## 📋 СЦЕНАРИЙ 4: УДАЛЕНИЕ КОМПОНЕНТОВ

**Пример:** Пользователь выбрал `Wine Mono` для удаления

### Этап 1: Выбор компонента (пользователь)
1. Пользователь отмечает `Wine Mono` → `☑`
2. Нажимает "Удалить"
3. Подтверждает удаление

### Этап 2: Подготовка (run_wine_uninstall)
1. Получаем список: `selected = ['wine-mono']`
2. **Находим дочерние компоненты:**
   - `Wine Mono` не имеет дочерних → список без изменений
   - Если бы удаляли `wineprefix` → добавились бы все winetricks компоненты
3. **Устанавливаем статусы:**
   - Только для ЯВНО выбранных: `wine-mono` → `pending`
4. Обновляем GUI
5. Блокируем кнопки
6. Запускаем поток удаления

### Этап 3: Выполнение удаления
**Последовательность (ПОСЛЕДОВАТЕЛЬНО!):**

#### Компонент 1: `wine-mono`
1. Проверка: установлен → начинаем удаление
2. **Статус:** `pending` → `removing`
3. Выполнение `uninstall_component('wine-mono')` → **ЖДЕМ завершения**
4. Проверка результата:
   - ✅ Успех → статус `missing`
   - ❌ Ошибка → статус `error`
5. **Чекбокс:** После завершения автоматически снимается (статус `missing`)

### Этап 4: Завершение (_uninstall_completed)
1. Останавливаем все фоновые процессы
2. Разблокируем кнопки
3. Обновляем GUI
4. Снимаем чекбоксы с завершенных

---

## 📋 СЦЕНАРИЙ 5: ОБНОВЛЕНИЕ GUI (_update_wine_status)

### Когда вызывается:
- При запуске приложения (первоначальная загрузка)
- После выбора компонентов (до начала установки)
- После завершения установки/удаления
- По требованию (например, после проверки)

### Алгоритм обновления (ТЕКУЩАЯ РЕАЛИЗАЦИЯ):

1. **Сохраняем состояние чекбоксов:**
   - Проходим по всем отмеченным чекбоксам из `self.wine_checkboxes`
   - Сохраняем имена компонентов в `current_selection` (set)
   - **ВНИМАНИЕ:** В текущей реализации сохраняются ВСЕ отмеченные чекбоксы, БЕЗ фильтрации по статусу

2. **Очищаем таблицу** (удаляем все строки и очищаем `wine_checkboxes`)

3. **Получаем все статусы** (`get_all_components_status()`)
   - Вызывается ПОСЛЕ сохранения чекбоксов

4. **Восстанавливаем таблицу:**
   - Проходим по всем компонентам из `COMPONENTS_CONFIG`
   - Группируем по категориям и сортируем по приоритету
   - Для каждого компонента:
     - Получаем статус из `all_status`
     - Создаем строку в таблице
     - Определяем чекбокс: `☐` для `gui_selectable`, пустое для остальных
     - Определяем символ для дочерних компонентов: `├─` или `└─` для winetricks

5. **Восстанавливаем состояние чекбоксов:**
   - Проходим по всем `item_id` в `wine_checkboxes`
   - Если `component_name` находится в `current_selection` → устанавливаем `☑`
   - **ВНИМАНИЕ:** Восстанавливаются ВСЕ компоненты из `current_selection`, БЕЗ проверки статуса

6. **Обновляем цвета** (согласно статусам через теги)

---

## 🔄 ПОСЛЕДОВАТЕЛЬНОСТЬ ВЫПОЛНЕНИЯ (КРИТИЧНО!)

### ❌ НЕПРАВИЛЬНО (параллельно):
```
install_component('wine_astraregul')  → запускаем и не ждем
install_component('wineprefix')      → запускаем сразу же
install_component('wine-mono')       → запускаем сразу же
```

### ✅ ПРАВИЛЬНО (последовательно):
```python
# install_components() - метод выполняет последовательно:
for component_id in all_components:
    status = 'pending' → 'installing'
    result = install_component(component_id)  # ЖДЕМ завершения!
    if result:
        status = 'installing' → 'ok'
    else:
        status = 'installing' → 'error'
```

**Каждый `install_component()` возвращает результат синхронно** - мы ждем его завершения перед переходом к следующему!

---

## 📊 СХЕМА СОСТОЯНИЙ ЧЕКБОКСОВ

```
┌─────────────┬──────────┬──────────┬──────────────┬─────────┬─────────┐
│   Статус    │ Чекбокс  │ Операция │  После обнов │ Снимаем? │ Сохраняем? │
├─────────────┼──────────┼──────────┼──────────────┼─────────┼─────────┤
│  missing    │    ☐     │    -     │      -       │    -    │    Нет  │
│  pending    │    ☑     │  Ждет    │   Восстан.  │   Нет   │   Да    │
│ installing  │    ☑     │  Работает│   Восстан.  │   Нет   │   Да    │
│ removing    │    ☑     │  Работает│   Восстан.  │   Нет   │   Да    │
│     ok      │    ☐     │ Завершено│   Снимаем    │   Да    │    Нет  │
│   error     │    ☑     │  Ошибка  │   Восстан.  │   Нет   │   Да    │
└─────────────┴──────────┴──────────┴──────────────┴─────────┴─────────┘
```

---

## ⚠️ КРИТИЧЕСКИЕ МОМЕНТЫ

### 1. Последовательность выполнения ✅
- **ВСЕ компоненты выполняются ПОСЛЕДОВАТЕЛЬНО** в цикле `for component_id in resolved_components:`
- Каждый `install_component()` блокирует выполнение до завершения
- Нет параллельного выполнения!

### 2. Статусы для зависимостей ❌ **НЕ РЕАЛИЗОВАНЫ**
- **В текущей реализации статусы НЕ устанавливаются вообще!**
- `UniversalInstaller` не имеет доступа к `ComponentStatusManager`
- В `install_components()` и `install_component()` НЕТ вызовов `update_component_status()`
- Статусы определяются только через проверку файлов после завершения установки
- Статусы `pending`, `installing`, `removing` НЕ используются в процессе установки/удаления

### 3. Чекбоксы для завершенных ⚠️
- **В текущей реализации:** Сохраняются ВСЕ отмеченные чекбоксы без фильтрации
- **В текущей реализации:** Восстанавливаются ВСЕ компоненты из `current_selection` без проверки статуса
- **ПРОБЛЕМА:** Чекбоксы остаются отмеченными для завершенных компонентов, пока не будет вызван `_update_wine_status()`

### 4. Обновление GUI
- Полное обновление таблицы происходит в `_update_wine_status()` после завершения
- Во время выполнения callback `UPDATE_COMPONENT:component_id` вызывается, но статусы НЕ обновляются
- Статусы в GUI показывают только результат проверки файлов (`ok`/`missing`), но НЕ процесс (`installing`/`pending`/`removing`)

---

## 🎬 ПОЛНЫЙ ЦИКЛ УСТАНОВКИ (пошагово)

```
1. [Пользователь] Выбирает компоненты → отмечает чекбоксы ☑
2. [Пользователь] Нажимает "Установить"
3. [GUI] run_wine_install()
   ├─ Получает выбранные компоненты (ID из чекбоксов)
   ├─ Блокирует кнопки
   └─ Запускает поток установки
4. [Поток] _perform_wine_install(selected)
   └─ Вызывает universal_installer.install_components(selected)
5. [UniversalInstaller] install_components(selected)
   ├─ Разрешает зависимости: resolve_dependencies(selected) → resolved_components
   └─ Последовательно устанавливает каждый компонент:
      ├─ for component_id in resolved_components:
      ├─ check_component_status() → если не установлен
      ├─ install_component() → выполнение установки (ЖДЕМ завершения!)
      ├─ ⚠️ Статусы НЕ обновляются! (pending/installing НЕ устанавливаются)
      ├─ callback("UPDATE_COMPONENT:component_id") → обновление GUI (но статус не меняется)
      └─ ...
6. [GUI] _install_completed(success)
   ├─ Разблокирует кнопки
   └─ Обновляет GUI (_update_wine_status) → снимает чекбоксы с завершенных
```

---

## ✅ ПРОВЕРКА ПРАВИЛЬНОСТИ РЕАЛИЗАЦИИ

### Вопросы для проверки:
1. ✅ Устанавливаются ли компоненты последовательно (не параллельно)? **ДА** - реализовано
2. ✅ Ждем ли мы завершения каждого `install_component()` перед следующим? **ДА** - реализовано
3. ❌ Статус `pending` устанавливается только для явно выбранных? **НЕТ** - статусы НЕ устанавливаются!
4. ⚠️ Чекбоксы снимаются только с завершенных (`ok`/`missing`)? **Частично** - снимаются, но без проверки статуса
5. ✅ Зависимости добавляются автоматически, но не получают `pending`? **ДА** - зависимости добавляются, статусы не используются
6. ✅ Дочерние компоненты НЕ добавляются автоматически? **ДА** - реализовано (только при удалении)

---

## 🔧 ЕСЛИ ЧТО-ТО НЕ РАБОТАЕТ

### Проблема: Все компоненты запускаются параллельно
**Решение:** Проверить, что `install_components()` использует цикл `for` с синхронными вызовами

### Проблема: Чекбоксы не снимаются после завершения установки
**Решение:** Добавить фильтрацию в `_update_wine_status()` - сохранять только НЕ завершенные компоненты в `current_selection`

### Проблема: Статусы не обновляются
**Решение:** Проверить, что `update_component_status()` вызывается в правильных местах

### Проблема: Статусы НЕ используются в процессе установки/удаления
**Решение:** 
1. Передать `ComponentStatusManager` в `UniversalInstaller` через конструктор
2. Вызывать `component_status_manager.update_component_status(component_id, 'installing')` перед установкой
3. Вызывать `component_status_manager.update_component_status(component_id, 'ok'/'error')` после установки
4. Устанавливать статус `pending` в `run_wine_install()` перед запуском потока

---

## 💡 ПРЕДЛОЖЕНИЯ ПО ПРАВИЛЬНОЙ СТРУКТУРЕ РАБОТЫ С ЧЕКБОКСАМИ И ЗАВИСИМОСТЯМИ

### 1. Улучшение логики сохранения чекбоксов в `_update_wine_status()`

**Текущая проблема:**
- Сохраняются ВСЕ отмеченные чекбоксы без фильтрации по статусу
- Восстанавливаются ВСЕ компоненты из `current_selection`, даже если операция завершена

**Предлагаемое решение:**
```python
# В методе _update_wine_status():

# 1. ПОЛУЧАЕМ статусы ПЕРЕД сохранением чекбоксов
all_status = self.component_status_manager.get_all_components_status()

# 2. Сохраняем ТОЛЬКО компоненты, которые НЕ завершены
current_selection = set()
for item, checked in self.wine_checkboxes.items():
    if checked:
        values = self.wine_tree.item(item, 'values')
        component_name = values[1]
        
        # Получаем статус компонента (через ID из COMPONENTS_CONFIG)
        component_id = self._get_component_id_by_name(component_name)
        status_tag = all_status.get(component_id, ('', 'missing'))[1]
        
        # Сохраняем ТОЛЬКО если операция НЕ завершена
        if status_tag not in ['ok', 'missing']:
            current_selection.add(component_name)
```

**Преимущества:**
- Чекбоксы автоматически снимаются с завершенных компонентов
- Чекбоксы остаются для компонентов в процессе (`pending`, `installing`, `removing`, `error`)
- Нет необходимости в дополнительных проверках при восстановлении

---

### 2. Добавление статуса 'pending' перед установкой

**Текущая проблема:**
- Статус `pending` НЕ устанавливается перед установкой
- Пользователь не видит, что компонент ждет установки

**Предлагаемое решение:**
```python
# В методе run_wine_install():

# После получения selected компонентов:
selected = self.get_selected_wine_components()

# Устанавливаем статус 'pending' для явно выбранных компонентов
for component_id in selected:
    self.component_status_manager.update_component_status(component_id, 'pending')

# Обновляем GUI для отображения статуса 'pending'
self._update_wine_status()

# Затем запускаем установку
```

**Преимущества:**
- Пользователь видит статус "Ожидание" перед установкой
- Явное разделение между выбранными и зависимостями
- Зависимости получают `installing` сразу (без `pending`)

---

### 3. Правильная обработка зависимостей

**Текущая реализация:**
- ✅ Зависимости добавляются автоматически через `resolve_dependencies()`
- ✅ Зависимости НЕ получают статус `pending`
- ✅ Установка выполняется последовательно

**Предлагаемое улучшение:**
```python
# В методе install_components():

# 1. Разрешаем зависимости
resolved_components = self.resolve_dependencies(component_ids)

# 2. Устанавливаем статус 'installing' для зависимостей (не pending!)
for component_id in resolved_components:
    if component_id not in component_ids:  # Это зависимость
        self.component_status_manager.update_component_status(component_id, 'installing')
        self._callback("UPDATE_COMPONENT:%s" % component_id)

# 3. Последовательно устанавливаем компоненты
for component_id in resolved_components:
    # Устанавливаем статус 'installing' если еще не установлен
    if component_id in component_ids:  # Это выбранный компонент
        current_status = self.component_status_manager.get_component_status(component_id)
        if current_status == 'pending':
            self.component_status_manager.update_component_status(component_id, 'installing')
            self._callback("UPDATE_COMPONENT:%s" % component_id)
    
    # Устанавливаем компонент
    if not self.check_component_status(component_id):
        if self.install_component(component_id):
            self.component_status_manager.update_component_status(component_id, 'ok')
        else:
            self.component_status_manager.update_component_status(component_id, 'error')
        self._callback("UPDATE_COMPONENT:%s" % component_id)
```

---

### 4. Улучшение восстановления чекбоксов

**Предлагаемое решение:**
```python
# В методе _update_wine_status(), при восстановлении чекбоксов:

# Восстанавливаем состояние чекбоксов
for item_id in self.wine_checkboxes:
    if item_id in self.wine_tree.get_children():
        values = self.wine_tree.item(item_id, 'values')
        component_name = values[1]
        
        # Получаем статус компонента
        component_id = self._get_component_id_by_name(component_name)
        status_tag = all_status.get(component_id, ('', 'missing'))[1]
        
        # Восстанавливаем чекбокс ТОЛЬКО если:
        # 1. Компонент был в current_selection (операция не завершена)
        # 2. Или статус указывает на незавершенную операцию
        if component_name in current_selection:
            self.wine_checkboxes[item_id] = True
            values = list(values)
            values[0] = '☑'
            self.wine_tree.item(item_id, values=values)
        elif status_tag in ['ok', 'missing']:
            # Операция завершена - явно снимаем чекбокс
            self.wine_checkboxes[item_id] = False
            values = list(values)
            values[0] = '☐'
            self.wine_tree.item(item_id, values=values)
```

---

### 5. Итоговая схема правильной работы

```
┌─────────────────────────────────────────────────────────────┐
│ 1. ПОЛЬЗОВАТЕЛЬ ВЫБИРАЕТ КОМПОНЕНТЫ                          │
│    - Отмечает чекбоксы ☑                                    │
│    - Нажимает "Установить"                                  │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. ПОДГОТОВКА (run_wine_install)                            │
│    - Получаем selected компонентов (ID)                     │
│    - Устанавливаем статус 'pending' для выбранных          │
│    - Обновляем GUI (_update_wine_status)                    │
│    - Блокируем кнопки                                       │
│    - Запускаем поток установки                              │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. ВЫПОЛНЕНИЕ (install_components)                          │
│    - Разрешаем зависимости (resolve_dependencies)           │
│    - Устанавливаем статус 'installing' для зависимостей     │
│    - Последовательно устанавливаем компоненты:             │
│      * missing/pending → installing → ok/error              │
│    - После каждого компонента: callback для GUI            │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. ЗАВЕРШЕНИЕ (_install_completed)                          │
│    - Разблокируем кнопки                                    │
│    - Обновляем GUI (_update_wine_status)                    │
│    - При обновлении:                                        │
│      * Сохраняем только НЕ завершенные чекбоксы            │
│      * Восстанавливаем чекбоксы из сохраненного списка      │
│      * Автоматически снимаем чекбоксы с завершенных         │
└─────────────────────────────────────────────────────────────┘
```

---

### 6. Ключевые принципы правильной реализации

1. **Статусы:**
   - `pending` → только для явно выбранных компонентов (до начала установки)
   - `installing` → для всех компонентов в процессе установки (выбранных и зависимостей)
   - `ok`/`error` → после завершения установки

2. **Чекбоксы:**
   - Сохраняются ТОЛЬКО для компонентов со статусом: `pending`, `installing`, `removing`, `error`
   - НЕ сохраняются для компонентов со статусом: `ok`, `missing` (после завершения)
   - Восстанавливаются ТОЛЬКО из сохраненного списка (который уже отфильтрован)

3. **Зависимости:**
   - Добавляются автоматически через `resolve_dependencies()`
   - НЕ получают статус `pending`
   - Получают статус `installing` сразу при начале установки

4. **Последовательность:**
   - Все компоненты устанавливаются ПОСЛЕДОВАТЕЛЬНО
   - Каждый `install_component()` блокирует выполнение до завершения
   - Нет параллельного выполнения!

---

### 7. Рекомендуемые изменения в коде

#### 🔴 КРИТИЧНО: Реализация статусов (сейчас НЕ реализовано!)

1. **В `UniversalInstaller.__init__()`:**
   ```python
   def __init__(self, logger=None, callback=None, status_manager=None):
       self.logger = logger
       self.callback = callback
       self.status_manager = status_manager  # Добавить!
   ```

2. **В `run_wine_install()`:**
   ```python
   # Получаем список выбранных компонентов
   selected = self.get_selected_wine_components()
   
   # Устанавливаем статус 'pending' для выбранных компонентов
   for component_id in selected:
       self.component_status_manager.update_component_status(component_id, 'pending')
   
   # Обновляем GUI для отображения статуса 'pending'
   self._update_wine_status()
   
   # Затем запускаем установку
   ```

3. **В `install_components()`:**
   ```python
   # Разрешаем зависимости
   resolved_components = self.resolve_dependencies(component_ids)
   
   # Устанавливаем статус 'installing' для зависимостей
   for component_id in resolved_components:
       if component_id not in component_ids:  # Это зависимость
           if self.status_manager:
               self.status_manager.update_component_status(component_id, 'installing')
   
   # Последовательно устанавливаем компоненты
   for component_id in resolved_components:
       # Устанавливаем статус 'installing' для выбранных компонентов
       if component_id in component_ids:  # Это выбранный компонент
           if self.status_manager:
               self.status_manager.update_component_status(component_id, 'installing')
       
       # Устанавливаем компонент
       if not self.check_component_status(component_id):
           result = self.install_component(component_id)
           
           # Обновляем статус после установки
           if self.status_manager:
               if result:
                   self.status_manager.update_component_status(component_id, 'ok')
               else:
                   self.status_manager.update_component_status(component_id, 'error')
           
           self._callback("UPDATE_COMPONENT:%s" % component_id)
   ```

4. **В `_update_wine_status()`:**
   ```python
   # 1. ПОЛУЧАЕМ статусы ДО сохранения чекбоксов
   all_status = self.component_status_manager.get_all_components_status()
   
   # 2. Сохраняем ТОЛЬКО компоненты, которые НЕ завершены
   current_selection = set()
   for item, checked in self.wine_checkboxes.items():
       if checked:
           values = self.wine_tree.item(item, 'values')
           component_name = values[1]
           
           # Получаем статус компонента
           component_id = self._get_component_id_by_name(component_name)
           status_tag = all_status.get(component_id, ('', 'missing'))[1]
           
           # Сохраняем ТОЛЬКО если операция НЕ завершена
           if status_tag not in ['ok', 'missing']:
               current_selection.add(component_name)
   
   # ... остальной код ...
   
   # 5. Восстанавливаем чекбоксы с проверкой статуса
   for item_id in self.wine_checkboxes:
       if item_id in self.wine_tree.get_children():
           values = self.wine_tree.item(item_id, 'values')
           component_name = values[1]
           
           # Получаем статус компонента
           component_id = self._get_component_id_by_name(component_name)
           status_tag = all_status.get(component_id, ('', 'missing'))[1]
           
           # Восстанавливаем ТОЛЬКО если компонент был сохранен И операция не завершена
           if component_name in current_selection:
               self.wine_checkboxes[item_id] = True
               values = list(values)
               values[0] = '☑'
               self.wine_tree.item(item_id, values=values)
           elif status_tag in ['ok', 'missing']:
               # Операция завершена - явно снимаем чекбокс
               self.wine_checkboxes[item_id] = False
               values = list(values)
               values[0] = '☐'
               self.wine_tree.item(item_id, values=values)
   ```

5. **В `AutomationGUI.__init__()`:**
   ```python
   # Передаем ComponentStatusManager в UniversalInstaller
   self.universal_installer = UniversalInstaller(
       callback=self._component_status_callback,
       status_manager=self.component_status_manager  # Добавить!
   )
   ```

**Эти изменения обеспечат правильную работу статусов и чекбоксов согласно описанному алгоритму.**
