# План рефакторинга системы файлового сканирования

**Версия документа:** 1.0.0  
**Проект:** FSA-AstraInstall  
**Компания:** ООО "НПА Вира-Реалтайм"  
**Текущая версия проекта:** V3.4.174 (2025.12.11)

## 📋 Оглавление

1. [Общая концепция](#общая-концепция)
2. [Текущее состояние системы](#текущее-состояние-системы)
3. [Цели и задачи рефакторинга](#цели-и-задачи-рефакторинга)
4. [Изменения в структуре данных](#изменения-в-структуре-данных)
5. [Параллельное сканирование](#параллельное-сканирование)
6. [UI изменения (вариант 2 - боковая панель)](#ui-изменения-вариант-2---боковая-панель)
7. [Управление директориями мониторинга](#управление-директориями-мониторинга)
8. [Система сохранения пользовательских настроек](#система-сохранения-пользовательских-настроек)
9. [Алгоритм работы с множественными снимками](#алгоритм-работы-с-множественными-снимками)
10. [Оценки производительности](#оценки-производительности)
11. [Пошаговый план реализации](#пошаговый-план-реализации)
12. [Риски и митигация](#риски-и-митигация)
13. [Проверка после рефакторинга](#проверка-после-рефакторинга)

---

## 🎯 Общая концепция

Рефакторинг направлен на:
- **Оптимизацию использования памяти** - упрощение структуры данных снимков
- **Ускорение создания снимков** - параллельное сканирование директорий
- **Улучшение UX** - добавление системы множественных контрольных точек (снимков)
- **Снижение нагрузки на систему** - создание только базового снимка при старте, мониторинг по требованию
- **Гибкое управление мониторингом** - возможность включать/выключать отдельные директории и добавлять пользовательские
- **Сохранение пользовательских настроек** - автоматическое сохранение всех настроек в скрытом конфигурационном файле

**Принцип:** Сохранить весь функционал, оптимизировать производительность, добавить возможность работы с несколькими снимками и гибкое управление настройками.

---

## 📊 Текущее состояние системы

### Классы и их функции:

#### 1. **`DirectorySnapshot`** (строки ~27523-27746)
**Назначение:** Создание снимка состояния директории

**Текущая структура данных:**
```python
self.files = {}  # {relative_path: (size, mtime, hash)}
self.directories = set()  # {relative_path1, relative_path2, ...}
```

**Параметры сканирования:**
- `max_depth=None` - без ограничения глубины
- `max_files=1000000` - очень большой лимит
- `calculate_hashes=False` - хеши не вычисляются
- `exclude_paths` - список исключённых путей

**Метрики производительности:**
- `scan_duration` - время сканирования
- `files_scanned` - количество файлов
- `directories_scanned` - количество директорий
- `memory_usage` - использование памяти

**Процесс сканирования:**
- Последовательный обход директорий через `os.walk()`
- `os.stat()` для каждого файла
- Пауза каждые 100 файлов (0.01 сек) для неблокирующей работы
- Исключение системных директорий (`/proc`, `/sys`, `/dev`, `/tmp`, и т.д.)

#### 2. **`DirectoryMonitor`** (строки ~27746-27990)
**Назначение:** Мониторинг изменений в директориях

**Текущая структура:**
- `baseline` - базовый снимок
- `last_snapshot` - последний снимок
- `monitoring` - флаг активности мониторинга

**Методы:**
- `start_monitoring()` - начать мониторинг
- `check_changes()` - проверить изменения
- `_compare_snapshots()` - сравнить два снимка

#### 3. **`AutomationGUI.create_filesystem_monitor_tab()`** (строки ~15835-15883)
**Назначение:** UI для мониторинга файловой системы

**Текущие элементы UI:**
- Кнопки управления: "Начать мониторинг", "Пауза", "Перезапуск", "Сбросить", "Очистить"
- Статистика: количество файлов, время работы, активные директории
- Информация о базовом снимке
- Вкладки представлений: "Структура снимка", "Все изменения", "По директориям", "По типам", "По времени"
- Прокручиваемая область с аккордеоном для отображения изменений

**Мониторируемые директории** (`_get_monitored_directories()`, строки ~15984-16028):
- `~/.cache/wine`
- `~/.cache/winetricks`
- `/opt/wine-9.0`
- `/opt/wine-astraregul`
- `/var/cache/apt`
- `/usr/local`
- `/opt`
- `/etc`
- `/usr/bin`
- `~/.wine-astraregul/drive_c`
- `~/.local/share/wineprefixes/*/drive_c`

**Текущий процесс запуска:**
- При старте приложения: `self.root.after(3000, self._create_filesystem_snapshot_only)` (строка ~13198)
- Создаётся только базовый снимок, мониторинг не запускается
- Мониторинг активируется вручную через кнопку "Начать мониторинг"

---

## 🎯 Цели и задачи рефакторинга

### Основные цели:

1. **Оптимизация памяти:**
   - Упростить структуру данных снимка
   - Хранить только путь и размер файла
   - Убрать ненужные данные (mtime, hash)

2. **Ускорение сканирования:**
   - Реализовать параллельное сканирование директорий
   - Использовать threading для одновременного сканирования нескольких директорий

3. **Система множественных снимков:**
   - Возможность создавать несколько контрольных точек
   - Сравнение любого снимка с любым другим
   - Управление снимками через UI

4. **Улучшение UX:**
   - Боковая панель со списком снимков (вариант 2)
   - Удобное сравнение снимков
   - Визуализация изменений между снимками
   - Исправление прокрутки аккордеона колесиком мыши (работает корректно во всём диапазоне)

---

## 🔧 Изменения в структуре данных

### Текущая структура:
```python
self.files[rel_path] = (stat.st_size, stat.st_mtime, file_hash)
# Размер: ~100-250 байт на файл
# Данные: размер, время модификации, хеш
```

### Новая структура:
```python
self.files[rel_path] = stat.st_size  # Только размер (int, 8 байт)
# Размер: ~50-150 байт на файл (путь + int)
# Данные: только размер файла
```

### Изменения в коде:

#### 1. **`DirectorySnapshot.__init__()`**
```python
# БЫЛО:
self.files[rel_path] = (stat.st_size, stat.st_mtime, file_hash)

# СТАНЕТ:
self.files[rel_path] = stat.st_size
```

#### 2. **`DirectorySnapshot._scan_directory()`**
```python
# БЫЛО:
stat = os.stat(file_path)
file_hash = 0
if self.calculate_hashes:
    file_hash = self._quick_hash(file_path)
self.files[rel_path] = (stat.st_size, stat.st_mtime, file_hash)

# СТАНЕТ:
stat = os.stat(file_path)
self.files[rel_path] = stat.st_size
# Убрать логику вычисления хешей (calculate_hashes больше не используется)
```

#### 3. **`DirectoryMonitor._compare_snapshots()`**
```python
# БЫЛО:
old_info = old_snapshot.files[file_path]  # (size, mtime, hash)
new_info = new_snapshot.files[file_path]  # (size, mtime, hash)
if old_info != new_info:
    changes['modified_files'].append(file_path)

# СТАНЕТ:
old_size = old_snapshot.files[file_path]  # int
new_size = new_snapshot.files[file_path]  # int
if old_size != new_size:
    changes['modified_files'].append(file_path)
```

#### 4. **Удаление неиспользуемого кода:**
- Параметр `calculate_hashes` можно оставить для обратной совместимости, но не использовать
- Метод `_quick_hash()` можно удалить или оставить для будущего использования
- Поле `hash_calculation_time` в метриках можно удалить

---

## ⚡ Параллельное сканирование

### Текущий процесс (последовательно):
```python
for dir_path in monitored_dirs:  # 8 директорий
    dir_snapshot = DirectorySnapshot(dir_path, ...)
    # Директория 1: 30 сек
    # Директория 2: 10 сек
    # Директория 3: 5 сек
    # Итого: 45 сек
```

### Новый процесс (параллельно):
```python
import threading

def scan_directory(dir_path, results_dict, lock):
    """Сканирование одной директории в отдельном потоке"""
    try:
        snapshot = DirectorySnapshot(dir_path, ...)
        with lock:
            results_dict[dir_path] = snapshot
    except Exception as e:
        print(f"[FilesystemMonitor] Ошибка сканирования {dir_path}: {e}")

# Создаём потоки для каждой директории
threads = []
results = {}
lock = threading.Lock()

for dir_path in monitored_dirs:
    thread = threading.Thread(
        target=scan_directory,
        args=(dir_path, results, lock),
        name=f"ScanThread-{os.path.basename(dir_path)}"
    )
    thread.daemon = True
    thread.start()
    threads.append(thread)

# Ждём завершения всех потоков
for thread in threads:
    thread.join()

# Объединяем результаты
all_files = {}
all_directories = set()
for dir_path, snapshot in results.items():
    # ... объединение снимков ...
```

### Изменения в коде:

#### 1. **`AutomationGUI._create_filesystem_snapshot_only()`**
```python
def _create_filesystem_snapshot_only(self):
    """Создание только базового снимка файловой системы без запуска мониторинга"""
    if hasattr(self, 'filesystem_baseline_snapshot') and self.filesystem_baseline_snapshot:
        return  # Снимок уже создан

    def _scan_in_background():
        try:
            monitored_dirs = self._get_monitored_directories()
            
            # ПАРАЛЛЕЛЬНОЕ СКАНИРОВАНИЕ
            import threading
            threads = []
            results = {}
            lock = threading.Lock()
            
            def scan_dir(dir_path):
                try:
                    snapshot = DirectorySnapshot(
                        dir_path,
                        max_depth=None,
                        max_files=1000000,
                        calculate_hashes=False
                    )
                    with lock:
                        results[dir_path] = snapshot
                except Exception as e:
                    print(f"[FilesystemMonitor] Ошибка сканирования {dir_path}: {e}", gui_log=True)
            
            # Запускаем потоки
            for dir_path in monitored_dirs:
                if os.path.exists(dir_path):
                    thread = threading.Thread(
                        target=scan_dir,
                        args=(dir_path,),
                        name=f"ScanThread-{os.path.basename(dir_path)}"
                    )
                    thread.daemon = True
                    thread.start()
                    threads.append(thread)
            
            # Ждём завершения
            for thread in threads:
                thread.join()
            
            # Объединяем результаты
            all_files = {}
            all_directories = set()
            total_files = 0
            
            for dir_path, dir_snapshot in results.items():
                for rel_path, file_size in dir_snapshot.files.items():
                    # ... формирование полного пути ...
                    all_files[prefixed_path] = file_size
                # ... объединение директорий ...
                total_files += dir_snapshot.files_scanned
            
            # Создаём объединённый снимок
            snapshot = DirectorySnapshot.__new__(DirectorySnapshot)
            snapshot.directory_path = "/"
            snapshot.timestamp = datetime.datetime.now()
            snapshot.files = all_files
            snapshot.directories = all_directories
            snapshot.files_scanned = total_files
            snapshot.scan_duration = max(s.get_performance_metrics().get('scan_duration', 0) 
                                        for s in results.values())
            
            self.filesystem_baseline_snapshot = snapshot
            
            # Создаём монитор (но НЕ запускаем мониторинг)
            if not hasattr(self, 'filesystem_monitor') or not self.filesystem_monitor:
                self.filesystem_monitor = DirectoryMonitor()
            self.filesystem_monitor.baseline = snapshot
            self.filesystem_monitor.last_snapshot = snapshot
            self.filesystem_monitor.monitoring = False
            
            print(f"[FilesystemMonitor] Базовый снимок создан: {snapshot.files_scanned} файлов (мониторинг не запущен)", gui_log=True)
        except Exception as e:
            print(f"[FilesystemMonitor] Ошибка при создании базового снимка: {e}", gui_log=True)
    
    snapshot_thread = threading.Thread(target=_scan_in_background, name="FilesystemSnapshotThread")
    snapshot_thread.daemon = True
    snapshot_thread.start()
```

#### 2. **Аналогичные изменения в `_start_filesystem_monitoring()`**
- Применить параллельное сканирование при создании снимков во время мониторинга

---

## 🎨 UI изменения (вариант 2 - боковая панель)

### Текущая структура UI:
```
┌─────────────────────────────────────────────────┐
│ [Кнопки управления]                             │
│ [Статистика] [Время] [Директории]               │
│ [Базовый снимок] [Нагрузка]                     │
│ [Вкладки представлений]                         │
│ ┌─────────────────────────────────────────────┐ │
│ │ [Прокручиваемая область с аккордеоном]      │ │
│ │                                               │ │
│ │                                               │ │
│ └─────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────┘
```

### Новая структура UI (вариант 2):
```
┌─────────────────────────────────────────────────┐
│ [Кнопки управления]                             │
│ [Статистика] [Время] [Директории]               │
│ [Базовый снимок]                                │
│ [Вкладки представлений]                         │
│ ┌──────────────────────┬──────────────────────┐ │
│ │ 📸 Создать снимок    │                      │ │
│ │ ──────────────────── │ [Прокручиваемая      │ │
│ │ Сравнить с: [▼]      │  область с           │ │
│ │ [Показать изменения] │  аккордеоном]        │ │
│ │                      │                      │ │
│ │ [📁 Управление       │                      │ │
│ │  директориями]       │                      │ │
│ │                      │                      │ │
│ │ ──────────────────── │                      │ │
│ │                      │                      │ │
│ │ Контрольные точки:   │                      │ │
│ │ ┌──────────────────┐ │                      │ │
│ │ │ 📸 Стартовый     │ │                      │ │
│ │ │   2025.12.03     │ │                      │ │
│ │ │   50,000 файлов   │ │                      │ │
│ │ ├──────────────────┤ │                      │ │
│ │ │ 📸 Снимок #1     │ │                      │ │
│ │ │   2025.12.03     │ │                      │ │
│ │ │   52,000 файлов   │ │                      │ │
│ │ └──────────────────┘ │                      │ │
│ └──────────────────────┴──────────────────────┘ │
└─────────────────────────────────────────────────┘
```

### Изменения в коде:

#### 1. **`AutomationGUI.create_filesystem_monitor_tab()`**

**Удаление статистики нагрузки CPU:**

```python
# БЫЛО (строки ~15903-15912):
# Строка 3: Информация о базовом снимке и нагрузке
row3_control = self.tk.Frame(control_frame)
row3_control.pack(fill=self.tk.X, pady=2)
self.fs_baseline_label = self.tk.Label(row3_control, text="Базовый снимок не создан", 
                                         font=('Arial', 8), fg='gray')
self.fs_baseline_label.pack(side=self.tk.LEFT)
self.tk.Label(row3_control, text="|", font=('Arial', 8), fg='gray').pack(side=self.tk.LEFT, padx=5)
self.fs_performance_label = self.tk.Label(row3_control, text="Нагрузка: -", 
                                           font=('Arial', 8), fg='gray')
self.fs_performance_label.pack(side=self.tk.LEFT)

# СТАНЕТ:
# Строка 3: Информация о базовом снимке (БЕЗ статистики нагрузки)
row3_control = self.tk.Frame(control_frame)
row3_control.pack(fill=self.tk.X, pady=2)
self.fs_baseline_label = self.tk.Label(row3_control, text="Базовый снимок не создан", 
                                         font=('Arial', 8), fg='gray')
self.fs_baseline_label.pack(side=self.tk.LEFT)
# УДАЛЕНО: разделитель и fs_performance_label
```

**Изменение структуры UI:**

```python
# БЫЛО:
canvas_frame = self.tk.Frame(self.filesystem_monitor_frame)
canvas_frame.pack(fill=self.tk.BOTH, expand=True, padx=10, pady=5)

# СТАНЕТ:
# Основной контейнер с двумя колонками
main_container = self.tk.Frame(self.filesystem_monitor_frame)
main_container.pack(fill=self.tk.BOTH, expand=True, padx=10, pady=5)

# Левая колонка: боковая панель со снимками
left_panel = self.tk.Frame(main_container, width=250, bg='#f0f0f0')
left_panel.pack(side=self.tk.LEFT, fill=self.tk.Y, padx=(0, 10))
left_panel.pack_propagate(False)  # Фиксированная ширина

# Правая колонка: прокручиваемая область с аккордеоном
right_frame = self.tk.Frame(main_container)
right_frame.pack(side=self.tk.RIGHT, fill=self.tk.BOTH, expand=True)

canvas_frame = self.tk.Frame(right_frame)
canvas_frame.pack(fill=self.tk.BOTH, expand=True)
# ... существующий код canvas ...

# Кнопка создания снимка
create_snapshot_btn = self.tk.Button(
    left_panel,
    text="📸 Создать снимок",
    command=self._create_manual_snapshot,
    width=25
)
create_snapshot_btn.pack(pady=10, padx=5)

# Разделитель
separator = self.tk.Frame(left_panel, height=2, bg='#ccc')
separator.pack(fill=self.tk.X, padx=5, pady=5)

# Выбор снимка для сравнения
compare_label = self.tk.Label(left_panel, text="Сравнить с:", font=('Arial', 9, 'bold'))
compare_label.pack(anchor='w', padx=5, pady=(5, 2))

self.fs_compare_var = self.tk.StringVar()
self.fs_compare_dropdown = self.ttk.Combobox(
    left_panel,
    textvariable=self.fs_compare_var,
    state='readonly',
    width=22
)
self.fs_compare_dropdown.pack(padx=5, pady=2)
self.fs_compare_dropdown.bind('<<ComboboxSelected>>', self._on_compare_snapshot_selected)

show_changes_btn = self.tk.Button(
    left_panel,
    text="Показать изменения",
    command=self._show_snapshot_changes,
    width=25
)
show_changes_btn.pack(pady=5, padx=5)

# Разделитель
separator2 = self.tk.Frame(left_panel, height=2, bg='#ccc')
separator2.pack(fill=self.tk.X, padx=5, pady=5)

# Кнопка управления директориями
manage_dirs_btn = self.tk.Button(
    left_panel,
    text="📁 Управление директориями",
    command=self._open_directories_manager,
    width=25
)
manage_dirs_btn.pack(pady=5, padx=5)

# Разделитель
separator3 = self.tk.Frame(left_panel, height=2, bg='#ccc')
separator3.pack(fill=self.tk.X, padx=5, pady=5)

# Список контрольных точек
snapshots_label = self.tk.Label(
    left_panel,
    text="Контрольные точки:",
    font=('Arial', 9, 'bold')
)
snapshots_label.pack(anchor='w', padx=5, pady=(5, 2))

# Прокручиваемый список снимков
snapshots_frame = self.tk.Frame(left_panel)
snapshots_frame.pack(fill=self.tk.BOTH, expand=True, padx=5, pady=5)

snapshots_scrollbar = self.ttk.Scrollbar(snapshots_frame)
snapshots_scrollbar.pack(side=self.tk.RIGHT, fill=self.tk.Y)

self.fs_snapshots_listbox = self.tk.Listbox(
    snapshots_frame,
    yscrollcommand=snapshots_scrollbar.set,
    font=('Arial', 8),
    selectmode=self.tk.SINGLE
)
self.fs_snapshots_listbox.pack(side=self.tk.LEFT, fill=self.tk.BOTH, expand=True)
snapshots_scrollbar.config(command=self.fs_snapshots_listbox.yview)
self.fs_snapshots_listbox.bind('<<ListboxSelect>>', self._on_snapshot_selected)
```

#### 2. **Новые методы для управления снимками:**

```python
def _create_manual_snapshot(self):
    """Создание снимка по требованию пользователя"""
    # Создаём снимок в фоне
    # Добавляем в список снимков
    # Обновляем UI

def _on_snapshot_selected(self, event):
    """Обработка выбора снимка из списка"""
    # Показываем информацию о выбранном снимке
    # Обновляем выпадающий список для сравнения

def _on_compare_snapshot_selected(self, event):
    """Обработка выбора снимка для сравнения"""
    # Подготавливаем сравнение

def _show_snapshot_changes(self):
    """Показать изменения между выбранными снимками"""
    # Получаем выбранные снимки
    # Выполняем сравнение
    # Отображаем результаты

def _update_snapshots_list(self):
    """Обновление списка снимков в UI"""
    # Очищаем список
    # Добавляем все снимки с форматированием
```

#### 2. **Удаление кода обновления статистики нагрузки CPU:**

```python
# БЫЛО (строки ~16472-16477):
# Обновляем метрики производительности
if self.filesystem_monitor:
    metrics = self.filesystem_monitor.get_performance_metrics()
    cpu_scan = metrics.get('last_scan_metrics', {}).get('scan_duration', 0) * 10  # Примерная нагрузка
    cpu_compare = metrics.get('compare_duration', 0) * 5
    self.fs_performance_label.config(
        text=f"Нагрузка: Сканирование {cpu_scan:.1f}% CPU | Сравнение {cpu_compare:.1f}% CPU")

# СТАНЕТ:
# УДАЛЕНО: весь блок обновления fs_performance_label
# (этот код находится в методе обновления UI файлового мониторинга)
```

#### 3. **Исправление прокрутки аккордеона колесиком мыши:**

**Проблема:** Текущая реализация использует `bind_all`, что привязывает прокрутку ко всему приложению. Это вызывает конфликты, когда курсор находится над другими элементами, и прокрутка работает некорректно.

**Решение:** Привязывать прокрутку только к canvas и его дочерним элементам, с правильной проверкой области курсора.

```python
# БЫЛО (строки ~15960-15972):
# Привязка прокрутки колесиком мыши
def _on_mousewheel(event):
    # Поддержка Windows и macOS
    if hasattr(event, 'delta'):
        self.fs_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
    # Поддержка Linux (Button-4 и Button-5)
    elif event.num == 4:
        self.fs_canvas.yview_scroll(-1, "units")
    elif event.num == 5:
        self.fs_canvas.yview_scroll(1, "units")
self.fs_canvas.bind_all("<MouseWheel>", _on_mousewheel)
self.fs_canvas.bind_all("<Button-4>", _on_mousewheel)  # Linux
self.fs_canvas.bind_all("<Button-5>", _on_mousewheel)  # Linux

# СТАНЕТ:
# Привязка прокрутки колесиком мыши (ИСПРАВЛЕНО)
def _on_mousewheel(event):
    """Обработка прокрутки колесиком мыши с проверкой области"""
    # Получаем виджет, над которым произошло событие
    widget = event.widget
    
    # Проверяем, что событие произошло над canvas или его содержимым
    # Используем winfo_containing для проверки, находится ли курсор над canvas
    x, y = self.fs_canvas.winfo_pointerxy()
    x -= self.fs_canvas.winfo_rootx()
    y -= self.fs_canvas.winfo_rooty()
    
    # Проверяем, что координаты находятся в пределах canvas
    if 0 <= x <= self.fs_canvas.winfo_width() and 0 <= y <= self.fs_canvas.winfo_height():
        # Поддержка Windows и macOS
        if hasattr(event, 'delta'):
            delta = int(-1 * (event.delta / 120))
            self.fs_canvas.yview_scroll(delta, "units")
        # Поддержка Linux (Button-4 и Button-5)
        elif event.num == 4:
            self.fs_canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self.fs_canvas.yview_scroll(1, "units")
        return "break"  # Предотвращаем дальнейшую обработку события

def _bind_mousewheel_to_widgets():
    """Привязка прокрутки к canvas и всем его дочерним элементам"""
    def bind_recursive(widget):
        """Рекурсивная привязка к виджету и его детям"""
        widget.bind("<MouseWheel>", _on_mousewheel)
        widget.bind("<Button-4>", _on_mousewheel)  # Linux
        widget.bind("<Button-5>", _on_mousewheel)  # Linux
        # Привязываем к дочерним элементам
        for child in widget.winfo_children():
            try:
                bind_recursive(child)
            except:
                pass  # Пропускаем виджеты, к которым нельзя привязаться
    
    # Привязываем к canvas
    bind_recursive(self.fs_canvas)
    # Привязываем к фрейму аккордеона
    if hasattr(self, 'fs_accordion_frame'):
        bind_recursive(self.fs_accordion_frame)

# Привязываем прокрутку после создания canvas
self.fs_canvas.bind("<Enter>", lambda e: _bind_mousewheel_to_widgets())
# Также привязываем при обновлении содержимого аккордеона
# (вызывать _bind_mousewheel_to_widgets() после каждого обновления аккордеона)
```

**Дополнительные улучшения:**

1. **Обновление scrollregion при изменении содержимого:**
```python
def _update_scrollregion(self):
    """Обновление области прокрутки canvas"""
    self.fs_canvas.update_idletasks()  # Обновляем размеры виджетов
    bbox = self.fs_canvas.bbox("all")
    if bbox:
        self.fs_canvas.configure(scrollregion=bbox)
    # Перепривязываем прокрутку к новым элементам
    _bind_mousewheel_to_widgets()
```

2. **Вызов обновления scrollregion:**
- После создания каждой секции аккордеона
- После сворачивания/разворачивания секций
- После обновления содержимого аккордеона

#### 3. **Хранение множественных снимков:**

```python
# В __init__ или create_filesystem_monitor_tab:
self.filesystem_snapshots = []  # Список всех снимков
# Формат: [
#     {
#         'id': 'baseline',
#         'name': 'Стартовый',
#         'timestamp': datetime,
#         'snapshot': DirectorySnapshot,
#         'files_count': int
#     },
#     ...
# ]
```

---

## 🗂️ Управление директориями мониторинга

### Текущее состояние:

Список директорий для мониторинга жёстко закодирован в методе `_get_monitored_directories()`. Все директории всегда включены, нельзя отключить отдельные или добавить новые.

### Новая функциональность:

#### 1. **Глобальная переменная для системных директорий:**

Вынести список системных директорий в глобальную переменную в начале файла (после `COMPONENTS_CONFIG`, строка ~1140) для удобной настройки:

```python
# ============================================================================
# КОНФИГУРАЦИЯ СИСТЕМНЫХ ДИРЕКТОРИЙ ДЛЯ МОНИТОРИНГА ФАЙЛОВОЙ СИСТЕМЫ
# ============================================================================

FILESYSTEM_MONITORING_DIRS = [
    {
        'path': '~/.cache/wine',
        'enabled': True,
        'type': 'system',
        'description': 'Кэш Wine'
    },
    {
        'path': '~/.cache/winetricks',
        'enabled': True,
        'type': 'system',
        'description': 'Кэш Winetricks'
    },
    {
        'path': '/opt/wine-9.0',
        'enabled': True,
        'type': 'system',
        'description': 'Wine 9.0'
    },
    {
        'path': '/opt/wine-astraregul',
        'enabled': True,
        'type': 'system',
        'description': 'Wine AstraRegul'
    },
    {
        'path': '/var/cache/apt',
        'enabled': True,
        'type': 'system',
        'description': 'Кэш APT'
    },
    {
        'path': '/usr/local',
        'enabled': True,
        'type': 'system',
        'description': 'Локальные установки'
    },
    {
        'path': '/opt',
        'enabled': True,
        'type': 'system',
        'description': 'Опциональные пакеты'
    },
    {
        'path': '/etc',
        'enabled': False,  # По умолчанию выключено
        'type': 'system',
        'description': 'Конфигурация системы'
    },
    {
        'path': '/usr/bin',
        'enabled': True,
        'type': 'system',
        'description': 'Системные бинарники'
    },
    # Динамические директории (wineprefix) добавляются автоматически в _init_monitored_directories()
    # на основе существующих путей
]

# Примечание: Пользовательские директории добавляются через UI и сохраняются в конфиге
```

**Преимущества:**
- Легко найти и изменить список директорий
- Не нужно искать по всему коду
- Централизованная настройка
- Понятная структура данных

#### 2. **Структура данных для директорий:**

```python
# В __init__ или create_filesystem_monitor_tab:
self.filesystem_monitored_dirs = [
    {
        'path': '~/.cache/wine',
        'enabled': True,
        'type': 'system',  # 'system' или 'user'
        'description': 'Кэш Wine'
    },
    {
        'path': '/opt/wine-9.0',
        'enabled': True,
        'type': 'system',
        'description': 'Wine установка'
    },
    # ... остальные системные директории
]

# Пользовательские директории добавляются с type='user'
```

#### 2. **UI для управления директориями:**

**В боковой панели (слева):**
- Кнопка `[📁 Управление директориями]` — открывает отдельное окно

**Отдельное окно "Управление директориями мониторинга":**

```
┌─────────────────────────────────────────────────────────┐
│ Управление директориями мониторинга              [×]   │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ Мониторируемые директории:                             │
│ ┌───────────────────────────────────────────────────┐ │
│ │ ☑ 🔧 ~/.cache/wine                                │ │
│ │ ☑ 🔧 /opt/wine-9.0                                │ │
│ │ ☐ 🔧 /usr/local                                   │ │
│ │ ☑ 🔧 /var/cache/apt                               │ │
│ │ ☑ 🔧 /opt                                         │ │
│ │ ☐ 🔧 /etc                                         │ │
│ │ ☑ 🔧 /usr/bin                                     │ │
│ │ ☑ 🔧 ~/.wine-astraregul/drive_c                   │ │
│ │ ☑ 📁 /custom/monitor (пользовательская)           │ │
│ │                                                    │ │
│ │ [Прокрутка списка]                                │ │
│ └───────────────────────────────────────────────────┘ │
│                                                         │
│ [+ Добавить директорию]                                │
│                                                         │
│ Примечание: Системные директории (🔧) нельзя удалить  │
│             Пользовательские (📁) можно удалить        │
│                                                         │
│ [Сохранить]  [Отмена]                                  │
└─────────────────────────────────────────────────────────┘
```

**Элементы окна:**
- Прокручиваемый список директорий с чекбоксами (Treeview или Listbox)
- Чекбокс = включена/выключена директория
- Иконка `🔧` = системная директория (нельзя удалить)
- Иконка `📁` = пользовательская директория (можно удалить)
- Кнопка `[+ Добавить директорию]` — открывает диалог выбора директории
- Правый клик на директории → контекстное меню: "Удалить" (только user), "Переименовать", "Отключить/Включить"
- Кнопки `[Сохранить]` и `[Отмена]` — сохранение изменений или отмена

#### 3. **Методы для управления:**

```python
def _get_monitored_directories(self):
    """Возвращает список включённых директорий для мониторинга"""
    return [
        os.path.expanduser(d['path']) if d['path'].startswith('~') else d['path']
        for d in self.filesystem_monitored_dirs
        if d['enabled'] and os.path.exists(os.path.expanduser(d['path']) if d['path'].startswith('~') else d['path'])
    ]

def _toggle_directory_monitoring(self, dir_path):
    """Включить/выключить мониторинг директории"""
    for dir_info in self.filesystem_monitored_dirs:
        if dir_info['path'] == dir_path:
            dir_info['enabled'] = not dir_info['enabled']
            self._save_user_config()  # Сохранить настройки
            self._update_directories_list()  # Обновить UI
            break

def _add_custom_directory(self, dir_path, description=None):
    """Добавить пользовательскую директорию для мониторинга"""
    # Проверяем, что директория существует
    expanded_path = os.path.expanduser(dir_path) if dir_path.startswith('~') else dir_path
    if not os.path.exists(expanded_path):
        return False
    
    # Проверяем, что директория ещё не добавлена
    for dir_info in self.filesystem_monitored_dirs:
        if dir_info['path'] == dir_path:
            return False  # Уже существует
    
    # Добавляем новую директорию
    self.filesystem_monitored_dirs.append({
        'path': dir_path,
        'enabled': True,
        'type': 'user',
        'description': description or os.path.basename(expanded_path)
    })
    
    self._save_user_config()  # Сохранить настройки
    self._update_directories_list()  # Обновить UI
    return True

def _remove_custom_directory(self, dir_path):
    """Удалить пользовательскую директорию (только type='user')"""
    for i, dir_info in enumerate(self.filesystem_monitored_dirs):
        if dir_info['path'] == dir_path and dir_info['type'] == 'user':
            del self.filesystem_monitored_dirs[i]
            self._save_user_config()  # Сохранить настройки
            self._update_directories_list()  # Обновить UI
            return True
    return False

def _open_directories_manager(self):
    """Открытие окна управления директориями"""
    # Создаём модальное окно
    dirs_window = self.tk.Toplevel(self.root)
    dirs_window.title("Управление директориями мониторинга")
    dirs_window.geometry("600x500")
    dirs_window.transient(self.root)  # Модальное окно
    dirs_window.grab_set()  # Блокируем взаимодействие с главным окном
    
    # Заголовок
    header_label = self.tk.Label(dirs_window, text="Мониторируемые директории:", 
                                  font=('Arial', 10, 'bold'))
    header_label.pack(pady=10, padx=10, anchor='w')
    
    # Прокручиваемый список директорий
    list_frame = self.tk.Frame(dirs_window)
    list_frame.pack(fill=self.tk.BOTH, expand=True, padx=10, pady=5)
    
    scrollbar = self.ttk.Scrollbar(list_frame)
    scrollbar.pack(side=self.tk.RIGHT, fill=self.tk.Y)
    
    # Используем Treeview для чекбоксов и иконок
    dirs_tree = self.ttk.Treeview(list_frame, yscrollcommand=scrollbar.set, 
                                   columns=('path', 'type'), show='tree headings', height=15)
    dirs_tree.heading('#0', text='')
    dirs_tree.heading('path', text='Путь')
    dirs_tree.heading('type', text='Тип')
    dirs_tree.column('#0', width=30)
    dirs_tree.column('path', width=400)
    dirs_tree.column('type', width=100)
    dirs_tree.pack(side=self.tk.LEFT, fill=self.tk.BOTH, expand=True)
    scrollbar.config(command=dirs_tree.yview)
    
    # Заполняем список
    for dir_info in self.filesystem_monitored_dirs:
        checkbox = '☑' if dir_info['enabled'] else '☐'
        type_icon = '🔧' if dir_info['type'] == 'system' else '📁'
        type_text = 'Системная' if dir_info['type'] == 'system' else 'Пользовательская'
        
        item_id = dirs_tree.insert('', 'end', 
                                   text=checkbox,
                                   values=(dir_info['path'], type_text),
                                   tags=(dir_info['type'],))
        
        # Цвет для системных директорий
        if dir_info['type'] == 'system':
            dirs_tree.set(item_id, 'path', f"{type_icon} {dir_info['path']}")
            dirs_tree.item(item_id, tags=('system',))
        else:
            dirs_tree.set(item_id, 'path', f"{type_icon} {dir_info['path']}")
            dirs_tree.item(item_id, tags=('user',))
    
    # Обработчик клика по чекбоксу
    def _on_tree_click(event):
        item = dirs_tree.selection()[0] if dirs_tree.selection() else None
        if item:
            # Переключаем чекбокс
            current_text = dirs_tree.item(item, 'text')
            new_text = '☐' if current_text == '☑' else '☑'
            dirs_tree.item(item, text=new_text)
    
    dirs_tree.bind('<Button-1>', _on_tree_click)
    
    # Кнопки управления
    buttons_frame = self.tk.Frame(dirs_window)
    buttons_frame.pack(fill=self.tk.X, padx=10, pady=10)
    
    add_btn = self.tk.Button(buttons_frame, text="+ Добавить директорию",
                             command=lambda: self._add_directory_dialog(dirs_tree))
    add_btn.pack(side=self.tk.LEFT, padx=5)
    
    # Примечание
    note_label = self.tk.Label(dirs_window, 
                               text="Примечание: Системные директории (🔧) нельзя удалить. Пользовательские (📁) можно удалить.",
                               font=('Arial', 8), fg='gray', justify='left')
    note_label.pack(pady=5, padx=10, anchor='w')
    
    # Кнопки сохранения
    save_frame = self.tk.Frame(dirs_window)
    save_frame.pack(fill=self.tk.X, padx=10, pady=10)
    
    def _save_directories():
        # Сохраняем изменения из treeview обратно в self.filesystem_monitored_dirs
        # ... логика сохранения ...
        self._save_user_config()
        dirs_window.destroy()
    
    save_btn = self.tk.Button(save_frame, text="Сохранить", command=_save_directories)
    save_btn.pack(side=self.tk.RIGHT, padx=5)
    
    cancel_btn = self.tk.Button(save_frame, text="Отмена", command=dirs_window.destroy)
    cancel_btn.pack(side=self.tk.RIGHT, padx=5)
```

#### 3. **Инициализация директорий:**

```python
def _init_monitored_directories(self):
    """Инициализация списка директорий (системные + загруженные из конфига)"""
    # Копируем системные директории из глобальной переменной
    import copy
    default_dirs = copy.deepcopy(FILESYSTEM_MONITORING_DIRS)
    
    # Добавляем динамические директории (wineprefix)
    wineprefix_main = os.path.expanduser('~/.wine-astraregul')
    drive_c_main = os.path.join(wineprefix_main, 'drive_c')
    if os.path.exists(drive_c_main):
        default_dirs.append({
            'path': drive_c_main,
            'enabled': True,
            'type': 'system',
            'description': 'WINEPREFIX основной'
        })
    
    # Добавляем drive_c для CONT wineprefix (CountPack)
    cont_wineprefix = os.path.expanduser('~/.local/share/wineprefixes/cont')
    drive_c_cont = os.path.join(cont_wineprefix, 'drive_c')
    if os.path.exists(drive_c_cont):
        default_dirs.append({
            'path': drive_c_cont,
            'enabled': True,
            'type': 'system',
            'description': 'WINEPREFIX CONT'
        })
    
    # Добавляем drive_c для всех остальных wineprefix'ов в ~/.local/share/wineprefixes
    wineprefixes_dir = os.path.expanduser('~/.local/share/wineprefixes')
    if os.path.exists(wineprefixes_dir):
        try:
            for item in os.listdir(wineprefixes_dir):
                wineprefix_path = os.path.join(wineprefixes_dir, item)
                if os.path.isdir(wineprefix_path):
                    drive_c_path = os.path.join(wineprefix_path, 'drive_c')
                    if os.path.exists(drive_c_path):
                        # Проверяем, что ещё не добавлено
                        if not any(d['path'] == drive_c_path for d in default_dirs):
                            default_dirs.append({
                                'path': drive_c_path,
                                'enabled': True,
                                'type': 'system',
                                'description': f'WINEPREFIX {item}'
                            })
        except (OSError, IOError):
            pass  # Пропускаем недоступные директории
    
    # Загружаем пользовательские настройки из конфига
    user_config = self._load_user_config()
    if user_config and 'monitored_directories' in user_config:
        # Объединяем системные директории с пользовательскими настройками
        user_dirs = user_config['monitored_directories']
        
        # Создаём словарь системных директорий по пути для быстрого поиска
        system_dirs_dict = {d['path']: d for d in default_dirs if d['type'] == 'system'}
        
        # Обновляем enabled для системных директорий из конфига
        for user_dir in user_dirs:
            if user_dir['path'] in system_dirs_dict:
                system_dirs_dict[user_dir['path']]['enabled'] = user_dir.get('enabled', True)
        
        # Добавляем пользовательские директории
        user_custom_dirs = [d for d in user_dirs if d['type'] == 'user']
        default_dirs.extend(user_custom_dirs)
    
    self.filesystem_monitored_dirs = default_dirs
```

---

## 💾 Система сохранения пользовательских настроек

### Концепция:

Сохранение всех пользовательских настроек в скрытом JSON-файле рядом с бинарником/скриптом. Файл создаётся автоматически при первом изменении настроек.

### Расположение конфигурационного файла:

```python
# Используем функцию _get_start_dir() для определения директории бинарника
CONFIG_FILE_NAME = '.fsa-astrainstall-config.json'
config_path = os.path.join(_get_start_dir(), CONFIG_FILE_NAME)

# Для скрытого файла на Linux/macOS имя начинается с точки
# На Windows файл будет скрыт через атрибуты
```

### Структура конфигурационного файла:

```json
{
    "version": "1.0.0",
    "last_updated": "2025.12.03T15:30:00",
    
    "window": {
        "width": 1400,
        "height": 900,
        "x": 100,
        "y": 50,
        "maximized": false
    },
    
    "filesystem_monitoring": {
        "monitored_directories": [
            {
                "path": "~/.cache/wine",
                "enabled": true,
                "type": "system",
                "description": "Кэш Wine"
            },
            {
                "path": "/custom/path/to/monitor",
                "enabled": true,
                "type": "user",
                "description": "Моя директория"
            }
        ],
        "auto_start_monitoring": false,
        "monitoring_interval": 5,
        "max_snapshots": 10
    },
    
    "ui": {
        "theme": "default",
        "font_size": 9,
        "show_tooltips": true,
        "auto_save_logs": true
    },
    
    "component_installation": {
        "default_install_path": "/opt",
        "auto_resolve_dependencies": true
    },
    
    "advanced": {
        "debug_mode": false,
        "log_level": "INFO",
        "performance_monitoring": false
    }
}
```

### Класс для работы с конфигурацией:

```python
import json
import os
from datetime import datetime

class UserConfigManager:
    """Менеджер пользовательских настроек"""
    
    def __init__(self, config_file_path):
        self.config_file_path = config_file_path
        self.config = {}
        self._load()
    
    def _load(self):
        """Загрузка конфигурации из файла"""
        if os.path.exists(self.config_file_path):
            try:
                with open(self.config_file_path, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"[ConfigManager] Ошибка загрузки конфига: {e}", gui_log=True)
                self.config = self._get_default_config()
        else:
            self.config = self._get_default_config()
    
    def _get_default_config(self):
        """Возвращает конфигурацию по умолчанию"""
        return {
            "version": "1.0.0",
            "last_updated": datetime.now().isoformat(),
            "window": {
                "width": 1400,
                "height": 900,
                "x": None,  # Центрировать
                "y": None,  # Центрировать
                "maximized": False
            },
            "filesystem_monitoring": {
                "monitored_directories": [],
                "auto_start_monitoring": False,
                "monitoring_interval": 5,
                "max_snapshots": 10
            },
            "ui": {
                "theme": "default",
                "font_size": 9,
                "show_tooltips": True,
                "auto_save_logs": True
            },
            "component_installation": {
                "default_install_path": "/opt",
                "auto_resolve_dependencies": True
            },
            "advanced": {
                "debug_mode": False,
                "log_level": "INFO",
                "performance_monitoring": False
            }
        }
    
    def save(self):
        """Сохранение конфигурации в файл"""
        try:
            # Обновляем время последнего изменения
            self.config['last_updated'] = datetime.now().isoformat()
            
            # Создаём директорию если не существует
            config_dir = os.path.dirname(self.config_file_path)
            if config_dir and not os.path.exists(config_dir):
                os.makedirs(config_dir, exist_ok=True)
            
            # Сохраняем в файл
            with open(self.config_file_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            
            # Делаем файл скрытым (на Windows)
            if platform.system() == 'Windows':
                try:
                    import ctypes
                    ctypes.windll.kernel32.SetFileAttributesW(
                        self.config_file_path,
                        0x02  # FILE_ATTRIBUTE_HIDDEN
                    )
                except:
                    pass
            
            return True
        except Exception as e:
            print(f"[ConfigManager] Ошибка сохранения конфига: {e}", gui_log=True)
            return False
    
    def get(self, key_path, default=None):
        """Получить значение по пути (например, 'window.width')"""
        keys = key_path.split('.')
        value = self.config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value
    
    def set(self, key_path, value):
        """Установить значение по пути"""
        keys = key_path.split('.')
        config = self.config
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        config[keys[-1]] = value
    
    def update_section(self, section, data):
        """Обновить целую секцию конфигурации"""
        if section not in self.config:
            self.config[section] = {}
        self.config[section].update(data)
```

### Интеграция в AutomationGUI:

```python
# В __init__:
from FSA_AstraInstall import _get_start_dir

config_file = os.path.join(_get_start_dir(), '.fsa-astrainstall-config.json')
self.user_config = UserConfigManager(config_file)

# Загрузка настроек окна
window_config = self.user_config.get('window', {})
if window_config.get('width') and window_config.get('height'):
    self.root.geometry(f"{window_config['width']}x{window_config['height']}")
    if window_config.get('x') and window_config.get('y'):
        self.root.geometry(f"+{window_config['x']}+{window_config['y']}")
    if window_config.get('maximized'):
        self.root.state('zoomed')  # Windows
        # или self.root.attributes('-zoomed', True)  # Linux

# Сохранение настроек окна при закрытии
def _on_window_close():
    # Сохраняем размер и положение окна
    if not self.root.state() == 'zoomed':  # Если не развёрнуто
        geometry = self.root.geometry()
        # Парсим geometry: "1400x900+100+50"
        parts = geometry.split('+')
        if len(parts) == 2:
            size = parts[0].split('x')
            pos = parts[1].split('+')
            self.user_config.update_section('window', {
                'width': int(size[0]),
                'height': int(size[1]),
                'x': int(pos[0]),
                'y': int(pos[1]),
                'maximized': False
            })
        else:
            self.user_config.update_section('window', {
                'maximized': True
            })
    else:
        self.user_config.update_section('window', {
            'maximized': True
        })
    
    self.user_config.save()
    self.root.destroy()

self.root.protocol("WM_DELETE_WINDOW", _on_window_close)
```

### Методы для сохранения настроек файлового мониторинга:

```python
def _save_user_config(self):
    """Сохранение настроек файлового мониторинга"""
    self.user_config.update_section('filesystem_monitoring', {
        'monitored_directories': self.filesystem_monitored_dirs,
        'max_snapshots': getattr(self, 'max_snapshots', 10)
    })
    self.user_config.save()

def _load_user_config(self):
    """Загрузка настроек файлового мониторинга"""
    return self.user_config.get('filesystem_monitoring', {})
```

### Что сохраняется:

1. **Окно:**
   - Размер (width, height)
   - Положение (x, y)
   - Состояние (maximized/normal)

2. **Файловый мониторинг:**
   - Список директорий с их состоянием (enabled/disabled)
   - Пользовательские директории
   - Максимальное количество снимков
   - Интервал мониторинга

3. **UI настройки:**
   - Тема оформления
   - Размер шрифта
   - Показ подсказок
   - Автосохранение логов

4. **Установка компонентов:**
   - Путь установки по умолчанию
   - Авторазрешение зависимостей

5. **Расширенные настройки:**
   - Режим отладки
   - Уровень логирования
   - Мониторинг производительности

### Безопасность:

- Файл создаётся с правами 0600 (только владелец может читать/писать)
- На Windows файл помечается как скрытый
- Пути с `~` автоматически расширяются при сохранении/загрузке
- Валидация путей перед сохранением

---

## 🔄 Алгоритм работы с множественными снимками

### 1. **Старт приложения:**
```
1. Через 3 секунды после запуска → _create_filesystem_snapshot_only()
2. Параллельное сканирование всех директорий (20-25 сек)
3. Создание объединённого снимка
4. Сохранение как "Стартовый" (id='baseline')
5. Добавление в список снимков
6. Мониторинг НЕ запускается
```

### 2. **Создание контрольной точки (кнопка "📸 Создать снимок"):**
```
1. Пользователь нажимает кнопку
2. Показываем индикатор прогресса
3. Параллельное сканирование всех директорий (20-25 сек)
4. Создание объединённого снимка
5. Генерация имени: "Снимок #N" (N = количество существующих снимков)
6. Добавление в список снимков
7. Обновление UI
8. Сохранение в памяти (self.filesystem_snapshots)
```

### 3. **Сравнение снимков:**
```
1. Пользователь выбирает снимок из списка (левый)
2. Пользователь выбирает снимок для сравнения из выпадающего списка (правый)
3. Нажимает "Показать изменения"
4. Вызывается DirectoryMonitor._compare_snapshots(old, new)
5. Результаты отображаются в основной области (аккордеон)
```

### 4. **Управление снимками:**
```
- Максимум снимков в памяти: 10 (настраиваемо)
- При превышении лимита: удалять самые старые (кроме baseline)
- Возможность удаления снимка (правый клик → "Удалить")
- Возможность переименования снимка (правый клик → "Переименовать")
```

### 5. **Мониторинг (опционально):**
```
1. Пользователь нажимает "Начать мониторинг"
2. Активируется периодическая проверка изменений
3. Сравнение с последним снимком (или baseline)
4. Отображение изменений в реальном времени
```

---

## 📈 Оценки производительности

### Память на один снимок:

**Текущая структура:**
- 50,000 файлов × 200 байт = ~10 МБ
- Overhead словаря: ~20-30% = +2-3 МБ
- **Итого: ~12-15 МБ на снимок**

**Новая структура (только путь + размер):**
- 50,000 файлов × 100 байт = ~5 МБ
- Overhead словаря: ~20-30% = +1 МБ
- **Итого: ~6 МБ на снимок** (экономия ~40%)

### Память для множественных снимков:

| Количество снимков | Текущая структура | Новая структура |
|-------------------|-------------------|-----------------|
| 1 (baseline)      | ~15 МБ            | ~6 МБ           |
| 5 снимков         | ~75 МБ            | ~30 МБ          |
| 10 снимков        | ~150 МБ           | ~60 МБ          |

**Рекомендация:** Ограничить максимум 10 снимков в памяти.

### Время создания снимка:

**Текущий процесс (последовательно):**
- 8 директорий сканируются по очереди
- Самая большая: `~/.wine-astraregul/drive_c` (~40,000 файлов) = ~20-25 сек
- Остальные 7 директорий: ~10,000 файлов = ~5-8 сек
- **Итого: ~25-33 секунды**

**Новый процесс (параллельно):**
- Все 8 директорий сканируются одновременно
- Время = время самой медленной директории = ~20-25 секунд
- **Ускорение: ~1.3-1.5 раза**
- **Итого: ~20-25 секунд**

### Сравнение снимков:

**Время сравнения:**
- 50,000 файлов в каждом снимке
- Операции: set difference, set intersection
- **Время: ~0.1-0.5 секунды** (очень быстро, всё в памяти)

---

## 📝 Пошаговый план реализации

### Этап 1: Упрощение структуры данных (1-2 часа)

1. **Изменение `DirectorySnapshot._scan_directory()`:**
   - Убрать сохранение `mtime` и `hash`
   - Сохранять только `stat.st_size`
   - Удалить логику вычисления хешей

2. **Изменение `DirectoryMonitor._compare_snapshots()`:**
   - Адаптировать сравнение для новой структуры (только размер)
   - Убрать проверку `mtime` и `hash`

3. **Тестирование:**
   - Проверить создание снимка
   - Проверить сравнение снимков
   - Проверить отображение изменений

### Этап 2: Параллельное сканирование (2-3 часа)

1. **Создание функции `_scan_directory_parallel()`:**
   - Реализовать многопоточное сканирование
   - Добавить синхронизацию через `threading.Lock()`
   - Обработка ошибок в каждом потоке

2. **Изменение `_create_filesystem_snapshot_only()`:**
   - Заменить последовательное сканирование на параллельное
   - Объединение результатов из всех потоков

3. **Изменение `_start_filesystem_monitoring()`:**
   - Применить параллельное сканирование при создании снимков

4. **Тестирование:**
   - Проверить время создания снимка (должно быть быстрее)
   - Проверить корректность объединения результатов
   - Проверить обработку ошибок

### Этап 3: Система множественных снимков (3-4 часа)

1. **Добавление структуры данных:**
   - `self.filesystem_snapshots = []` - список всех снимков
   - Формат записи снимка (id, name, timestamp, snapshot, files_count)

2. **Методы управления снимками:**
   - `_create_manual_snapshot()` - создание снимка по кнопке
   - `_update_snapshots_list()` - обновление списка в UI
   - `_on_snapshot_selected()` - обработка выбора
   - `_on_compare_snapshot_selected()` - обработка выбора для сравнения
   - `_show_snapshot_changes()` - показ изменений

3. **Интеграция с baseline:**
   - При создании baseline добавлять в список снимков как "Стартовый"
   - Обеспечить невозможность удаления baseline

4. **Тестирование:**
   - Создание нескольких снимков
   - Сравнение снимков между собой
   - Удаление снимков
   - Переименование снимков

### Этап 4: UI изменения (вариант 2 - боковая панель) (2-3 часа)

1. **Удаление статистики нагрузки CPU:**
   - Удалить `self.fs_performance_label` из строки 3 (row3_control)
   - Удалить разделитель "|" перед статистикой нагрузки
   - Удалить код обновления статистики (строки ~16472-16477)
   - Оставить только `self.fs_baseline_label` в строке 3

2. **Исправление прокрутки аккордеона колесиком мыши:**
   - Заменить `bind_all` на привязку только к canvas и его дочерним элементам
   - Добавить проверку координат курсора (находится ли над canvas)
   - Реализовать рекурсивную привязку прокрутки ко всем элементам аккордеона
   - Добавить метод `_update_scrollregion()` для обновления области прокрутки
   - Вызывать обновление scrollregion после каждого изменения содержимого аккордеона

3. **Изменение `create_filesystem_monitor_tab()`:**
   - Разделить на две колонки (левая - боковая панель, правая - основная область)
   - Добавить кнопку "📸 Создать снимок"
   - Добавить выпадающий список "Сравнить с:"
   - Добавить кнопку "Показать изменения"
   - Добавить список контрольных точек (Listbox)

4. **Стилизация боковой панели:**
   - Фиксированная ширина (250px)
   - Серый фон (#f0f0f0)
   - Разделители между секциями
   - Форматирование списка снимков (иконка, название, дата, количество файлов)

5. **Обработчики событий:**
   - Выбор снимка из списка
   - Выбор снимка для сравнения
   - Показ изменений

6. **Тестирование:**
   - Проверить, что статистика нагрузки CPU удалена из UI
   - Проверить прокрутку аккордеона колесиком мыши (работает во всём диапазоне, не "убегает")
   - Проверить, что прокрутка работает только над canvas, не конфликтует с другими элементами
   - Проверить прокрутку на разных платформах (Windows, Linux, macOS)
   - Проверить отображение всех элементов
   - Проверить работу кнопок
   - Проверить прокрутку списка снимков
   - Проверить адаптивность при изменении размера окна

### Этап 5: Система сохранения пользовательских настроек (2-3 часа)

1. **Создание класса `UserConfigManager`:**
   - Реализовать загрузку/сохранение JSON конфигурации
   - Методы `get()`, `set()`, `update_section()`
   - Обработка ошибок и значений по умолчанию
   - Скрытие файла на Windows (через ctypes)

2. **Интеграция в `AutomationGUI.__init__`:**
   - Инициализация `UserConfigManager` с путём к конфигу
   - Загрузка настроек окна (размер, положение, maximized)
   - Применение настроек при создании окна

3. **Сохранение настроек окна:**
   - Обработчик закрытия окна (`WM_DELETE_WINDOW`)
   - Сохранение размера, положения, состояния окна
   - Автоматическое сохранение при изменении

4. **Сохранение настроек файлового мониторинга:**
   - Методы `_save_user_config()` и `_load_user_config()`
   - Сохранение списка директорий и их состояния
   - Загрузка при инициализации вкладки мониторинга

5. **Тестирование:**
   - Проверить создание конфигурационного файла
   - Проверить сохранение/загрузку настроек окна
   - Проверить сохранение/загрузку настроек мониторинга
   - Проверить скрытие файла на Windows
   - Проверить права доступа к файлу (0600)

### Этап 6: Управление директориями мониторинга (2-3 часа)

1. **Создание глобальной переменной для системных директорий:**
   - Добавить глобальную переменную `FILESYSTEM_MONITORING_DIRS` в начале файла (после `COMPONENTS_CONFIG`, строка ~1140)
   - Структура: список словарей с полями `path`, `enabled`, `type`, `description`
   - Включить все системные директории, которые сейчас закодированы в `_get_monitored_directories()`
   - Добавить комментарий о том, что пользовательские директории добавляются через UI

2. **Изменение структуры данных:**
   - Заменить жёстко закодированный список на `self.filesystem_monitored_dirs`
   - Использовать `copy.deepcopy(FILESYSTEM_MONITORING_DIRS)` в `_init_monitored_directories()`
   - Формат: список словарей с полями `path`, `enabled`, `type`, `description`
   - Метод `_init_monitored_directories()` для инициализации с использованием глобальной переменной

3. **Изменение `_get_monitored_directories()`:**
   - Возвращать только включённые директории из `self.filesystem_monitored_dirs`
   - Фильтрация по `enabled=True`
   - Проверка существования директорий

4. **Методы управления директориями:**
   - `_toggle_directory_monitoring()` - включить/выключить
   - `_add_custom_directory()` - добавить пользовательскую
   - `_remove_custom_directory()` - удалить пользовательскую
   - `_open_directories_manager()` - открыть окно управления директориями
   - `_add_directory_dialog()` - диалог добавления директории

5. **UI для управления директориями:**
   - Добавить кнопку "📁 Управление директориями" в боковую панель (между "Показать изменения" и списком снимков)
   - Создать отдельное модальное окно `Toplevel` для управления директориями
   - Размер окна: 600x500
   - В окне: прокручиваемый список с чекбоксами (Treeview с колонками: чекбокс, путь, тип)
   - Иконки: 🔧 для системных, 📁 для пользовательских
   - Кнопка "+ Добавить директорию" с диалогом выбора (`askdirectory`)
   - Контекстное меню (правый клик): "Удалить" (только user), "Переименовать", "Отключить/Включить"
   - Кнопки "Сохранить" и "Отмена" в нижней части окна
   - Примечание о системных/пользовательских директориях

6. **Интеграция с сохранением настроек:**
   - Сохранение изменений при нажатии "Сохранить" в окне управления
   - Загрузка пользовательских директорий из конфига при старте
   - Объединение системных директорий с пользовательскими настройками (обновление `enabled` для системных)

6. **Тестирование:**
   - Открытие окна управления директориями по кнопке
   - Включение/выключение системных директорий через чекбоксы
   - Добавление пользовательских директорий через диалог
   - Удаление пользовательских директорий (системные нельзя удалить)
   - Сохранение/загрузка настроек директорий
   - Проверка работы мониторинга с изменённым списком
   - Модальность окна (блокировка главного окна)

### Этап 7: Оптимизация и доработка (1-2 часа)

1. **Ограничение количества снимков:**
   - Максимум 10 снимков в памяти
   - Автоматическое удаление старых (кроме baseline)

2. **Контекстное меню для снимков:**
   - Правый клик → "Удалить", "Переименовать", "Сделать baseline"

3. **Индикатор прогресса:**
   - Показывать прогресс при создании снимка
   - Блокировать UI во время сканирования

4. **Документация:**
   - Обновить комментарии в коде
   - Добавить docstrings для новых методов

### Этап 8: Финальное тестирование (1-2 часа)

1. **Функциональное тестирование:**
   - Создание baseline при старте
   - Создание нескольких снимков
   - Сравнение снимков
   - Удаление снимков
   - Мониторинг (если активирован)

2. **Производительность:**
   - Измерить время создания снимка (должно быть ~20-25 сек)
   - Измерить использование памяти (должно быть ~6 МБ на снимок)
   - Проверить время сравнения снимков

3. **UI/UX:**
   - Проверить удобство использования
   - Проверить отображение на разных разрешениях
   - Проверить работу с большим количеством снимков

---

## ⚠ Риски и митигация

### Риск 1: Проблемы с многопоточностью
**Описание:** Конфликты при одновременном доступе к общим данным  
**Вероятность:** Средняя  
**Влияние:** Высокое  
**Митигация:**
- Использовать `threading.Lock()` для синхронизации
- Изолировать данные каждого потока
- Объединять результаты только после завершения всех потоков

### Риск 2: Увеличение использования памяти
**Описание:** Множественные снимки могут занять много памяти  
**Вероятность:** Низкая  
**Влияние:** Среднее  
**Митигация:**
- Ограничить максимум 10 снимков
- Автоматически удалять старые снимки
- Мониторить использование памяти

### Риск 3: Проблемы с производительностью UI
**Описание:** Блокировка UI во время сканирования  
**Вероятность:** Низкая  
**Влияние:** Среднее  
**Митигация:**
- Сканирование выполняется в фоновом потоке
- Показывать индикатор прогресса
- Блокировать только кнопку создания снимка

### Риск 4: Ошибки при сравнении снимков
**Описание:** Неправильное сравнение из-за изменения структуры данных  
**Вероятность:** Низкая  
**Влияние:** Высокое  
**Митигация:**
- Тщательное тестирование метода `_compare_snapshots()`
- Проверка всех типов изменений (новые, удалённые, изменённые файлы)
- Проверка директорий

### Риск 5: Проблемы с обратной совместимостью
**Описание:** Старый код может ожидать старую структуру данных  
**Вероятность:** Низкая  
**Влияние:** Среднее  
**Митигация:**
- Проверить все места использования `DirectorySnapshot.files`
- Адаптировать код для новой структуры
- Тестирование всех функций, использующих снимки

### Риск 6: Проблемы с конфигурационным файлом
**Описание:** Ошибки чтения/записи конфига, повреждение данных  
**Вероятность:** Низкая  
**Влияние:** Среднее  
**Митигация:**
- Обработка ошибок JSON (try/except)
- Значения по умолчанию при ошибке загрузки
- Резервное копирование конфига перед изменением
- Валидация структуры конфига при загрузке

### Риск 7: Конфликты при изменении директорий во время сканирования
**Описание:** Пользователь изменяет список директорий во время создания снимка  
**Вероятность:** Низкая  
**Влияние:** Низкое  
**Митигация:**
- Блокировать изменение списка директорий во время сканирования
- Показывать индикатор "Сканирование..."
- Использовать копию списка директорий для текущего сканирования

---

## ✅ Проверка после рефакторинга

### Чек-лист функциональности:

**Снимки:**
- [ ] Baseline снимок создаётся при старте приложения
- [ ] Baseline снимок отображается в списке как "Стартовый"
- [ ] Кнопка "📸 Создать снимок" создаёт новый снимок
- [ ] Новый снимок добавляется в список с правильным именем
- [ ] Выбор снимка из списка работает корректно
- [ ] Выпадающий список "Сравнить с:" содержит все снимки
- [ ] Кнопка "Показать изменения" показывает различия между снимками
- [ ] Удаление снимка работает (кроме baseline)
- [ ] Переименование снимка работает
- [ ] Мониторинг работает (если активирован)
- [ ] Отображение изменений в аккордеоне работает корректно

**Управление директориями:**
- [ ] Глобальная переменная `FILESYSTEM_MONITORING_DIRS` определена в начале файла (после `COMPONENTS_CONFIG`)
- [ ] Список системных директорий легко найти и изменить в одном месте
- [ ] Кнопка "📁 Управление директориями" отображается в боковой панели
- [ ] Кнопка открывает отдельное модальное окно
- [ ] Окно блокирует взаимодействие с главным окном (модальное)
- [ ] Список директорий отображается в окне с чекбоксами
- [ ] Чекбоксы позволяют включать/выключать директории
- [ ] Системные директории помечены иконкой 🔧
- [ ] Пользовательские директории помечены иконкой 📁
- [ ] Кнопка "+ Добавить директорию" открывает диалог выбора
- [ ] Добавление пользовательской директории работает
- [ ] Удаление пользовательской директории работает (только user)
- [ ] Системные директории нельзя удалить
- [ ] Контекстное меню работает (правый клик)
- [ ] Кнопка "Сохранить" сохраняет изменения в конфиг
- [ ] Кнопка "Отмена" закрывает окно без сохранения

**Сохранение настроек:**
- [ ] Конфигурационный файл создаётся при первом изменении
- [ ] Файл скрыт на Windows (через атрибуты)
- [ ] Права доступа к файлу: 0600 (только владелец)
- [ ] Настройки окна сохраняются при закрытии
- [ ] Настройки окна загружаются при старте
- [ ] Настройки файлового мониторинга сохраняются
- [ ] Настройки файлового мониторинга загружаются
- [ ] Пользовательские директории сохраняются и загружаются
- [ ] Состояние включено/выключено директорий сохраняется

### Чек-лист производительности:

- [ ] Время создания снимка: ~20-25 секунд (параллельно)
- [ ] Память на снимок: ~6 МБ
- [ ] Время сравнения снимков: <1 секунда
- [ ] UI не блокируется во время сканирования
- [ ] Нет утечек памяти при создании/удалении снимков

### Чек-лист UI/UX:

- [ ] Статистика нагрузки CPU удалена из UI (строка 3 содержит только информацию о базовом снимке)
- [ ] Прокрутка аккордеона колесиком мыши работает корректно во всём диапазоне
- [ ] Прокрутка не "убегает" и не конфликтует с другими элементами интерфейса
- [ ] Прокрутка работает только когда курсор находится над canvas аккордеона
- [ ] Прокрутка работает на всех платформах (Windows, Linux, macOS)
- [ ] Область прокрутки (scrollregion) обновляется при изменении содержимого аккордеона
- [ ] Боковая панель отображается корректно
- [ ] Все элементы видны и доступны
- [ ] Список снимков прокручивается при большом количестве
- [ ] Форматирование снимков читаемое (иконка, название, дата, количество файлов)
- [ ] Кнопки имеют понятные названия и иконки
- [ ] Индикатор прогресса показывается при создании снимка

---

## 📚 Дополнительные заметки

### Будущие улучшения (не входят в текущий рефакторинг):

1. **Сохранение снимков на диск:**
   - Опциональное сохранение снимков в файлы (pickle)
   - Загрузка сохранённых снимков при старте

2. **Экспорт изменений:**
   - Экспорт списка изменений в CSV/JSON
   - Печать отчёта об изменениях

3. **Фильтрация изменений:**
   - Фильтр по типу изменения (новые/удалённые/изменённые)
   - Фильтр по размеру файла
   - Фильтр по пути

4. **Визуализация:**
   - График изменения количества файлов
   - График изменения размера директорий
   - Дерево директорий с подсветкой изменений

---

**Конец документа**
