# План оптимизации производительности мониторинга

**Версия документа:** 1.0.0  
**Дата создания:** 2025.12.25  
**Проект:** FSA-AstraInstall  
**Компания:** ООО "НПА Вира-Реалтайм"  
**Текущая версия проекта:** V3.6.205 (2025.12.25)

## 📋 Оглавление

1. [Проблема и цель](#проблема-и-цель)
2. [Анализ проблемы](#анализ-проблемы)
3. [Архитектура решения](#архитектура-решения)
4. [Детальный план реализации](#детальный-план-реализации)
5. [Структура изменений](#структура-изменений)
6. [Тестирование](#тестирование)
7. [Риски и митигация](#риски-и-митигация)
8. [Критерии успеха](#критерии-успеха)

---

## 🎯 Проблема и цель

### Текущие проблемы

1. **Медленное обновление системы при включенном автообновлении** - процесс обновления занимает значительно больше времени, чем при выключенном автообновлении
2. **Перегрузка GUI-потока** - слишком частые обновления (каждые 100мс) блокируют главный поток интерфейса
3. **Полная перерисовка виджетов** - терминал и таблицы полностью пересоздаются при каждом обновлении вместо инкрементального обновления
4. **Накопление задач в очереди** - `terminal_update_callback` вызывается при каждой записи, создавая множество задач в очереди GUI
5. **Отсутствие отслеживания активной вкладки** - все вкладки обновляются с одинаковой частотой независимо от видимости
6. **Косвенное влияние на процесс APT** - перегруженный GUI может замедлить чтение stdout процесса, что приводит к заполнению буфера и блокировке APT

### Цель

Оптимизировать систему мониторинга так, чтобы:
- ✅ Обновление системы работало одинаково быстро при включенном и выключенном автообновлении
- ✅ GUI оставался отзывчивым во время активных операций
- ✅ Обновления происходили только для активных вкладок с высокой частотой
- ✅ Неактивные вкладки обновлялись редко (1-2 секунды) для актуальности данных
- ✅ Процесс APT не блокировался из-за перегрузки GUI

---

## 🔍 Анализ проблемы

### Как работает процесс APT

1. **Запуск процесса** (строка 10650):
   - `subprocess.Popen` с `stdout=subprocess.PIPE`, `bufsize=1` (построчный режим)
   - Процесс APT работает в отдельном процессе, независимо от Python

2. **Чтение вывода** (строка 10761):
   - `process.stdout.readline()` в цикле `run_process()`
   - Блокирующая операция: ждет новую строку от процесса

3. **Запись в буфер** (строка 10826):
   - `_global_dual_logger.write_raw(line_clean)` с блокировкой `_raw_lock`
   - Блокировка быстрая (добавление в deque)

4. **Callback обновления** (строки 210-214, 34306):
   - При каждой записи вызывается `terminal_update_callback()`
   - Ставит задачу в очередь GUI через `root.after(0, gui._update_terminal_display)`
   - Не блокирует запись напрямую, но создает очередь задач

### Проблемные места

#### 1. `process_terminal_queue()` - вызывается каждые 100мс
- **Местоположение:** строка 29903
- **Проблема:** Слишком частые вызовы, полная перерисовка терминала
- **Влияние:** Блокирует GUI-поток, накапливает задачи в очереди

#### 2. `_update_terminal_display()` - полная перерисовка
- **Местоположение:** строка 29567
- **Проблема:** Удаляет все содержимое терминала и создает заново все сообщения
- **Влияние:** При большом буфере (тысячи строк) занимает много времени

#### 3. `update_packages_table()` - вызывается каждые 500мс
- **Местоположение:** строка 22400
- **Проблема:** Полностью удаляет все строки таблицы и создает их заново
- **Влияние:** При большом количестве пакетов (сотни) занимает много времени

#### 4. `_refresh_processes_monitor()` - вызывается каждые 500мс
- **Местоположение:** строка 22267
- **Проблема:** Полностью удаляет все строки и создает их заново
- **Влияние:** Сбор информации о всех процессах каждый раз занимает время

#### 5. `terminal_update_callback` - вызывается при каждой записи
- **Местоположение:** строки 210-214
- **Проблема:** При быстром выводе APT создает множество задач в очереди GUI
- **Влияние:** Накопление задач, перегрузка GUI-потока

#### 6. `parse_from_buffer()` - обрабатывает все строки за раз
- **Местоположение:** строка 31607
- **Проблема:** При большом потоке данных обрабатывает все сразу
- **Влияние:** Может занимать много времени в GUI-потоке

### Косвенное влияние на процесс APT

**Механизм блокировки:**
1. Буфер stdout процесса ограничен (обычно 64KB)
2. Если буфер заполняется, процесс APT блокируется при попытке записи в stdout
3. Если `readline()` вызывается редко из-за перегрузки GUI, буфер может заполниться
4. Процесс APT приостанавливается, ожидая освобождения буфера

**Вывод:** GUI-обновления могут косвенно влиять на процесс APT через буфер stdout.

---

## 🏗️ Архитектура решения

### Принципы оптимизации

1. **Отслеживание активной вкладки** - обновлять только видимые компоненты с высокой частотой
2. **Адаптивные интервалы** - увеличивать интервалы при активной установке и неактивных вкладках
3. **Инкрементальные обновления** - обновлять только измененные элементы, не перерисовывать все
4. **Ограничение обработки** - обрабатывать данные порциями, не все сразу
5. **Кэширование состояний** - сравнивать с предыдущим состоянием, обновлять только изменения
6. **Оптимизация callback** - не вызывать при каждой записи, использовать флаги/счетчики

### Структура изменений

```
Этап 1: Отслеживание активной вкладки (фундамент)
  └─> Этап 2: Оптимизация терминала (критично)
      └─> Этап 5: Оптимизация парсинга буфера
          └─> Этап 6: Оптимизация process_terminal_queue
  └─> Этап 3: Оптимизация таблицы пакетов
  └─> Этап 4: Оптимизация мониторинга процессов
```

---

## 📝 Детальный план реализации

### Этап 1: Отслеживание активной вкладки (фундамент)

**Приоритет:** Высокий  
**Время:** 30-40 минут  
**Риск:** Низкий  
**Зависимости:** Нет

#### Задачи

1. Добавить переменные для хранения индексов вкладок
2. Сохранять индексы при создании вкладок
3. Добавить обработчик события переключения вкладок
4. Создать метод проверки активности вкладки

#### Изменения в коде

**Файл:** `FSA-AstraInstall.py`  
**Класс:** `AutomationGUI`  
**Метод:** `__init__()` или после создания notebook

**ДОБАВИТЬ в `__init__()` после создания notebook:**

```python
# Индексы вкладок для отслеживания активности
self.terminal_tab_index = None
self.packages_tab_index = None
self.monitoring_tab_index = None
self.current_active_tab_index = 0

# Привязываем обработчик переключения вкладок
if hasattr(self, 'notebook'):
    self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)
```

**ДОБАВИТЬ метод проверки активности:**

```python
def on_tab_changed(self, event=None):
    """Обработчик переключения вкладок"""
    try:
        self.current_active_tab_index = self.notebook.index(self.notebook.select())
    except Exception:
        pass

def is_tab_active(self, tab_index):
    """Проверяет, активна ли указанная вкладка"""
    if tab_index is None:
        return False
    try:
        return self.current_active_tab_index == tab_index
    except Exception:
        return False
```

**ИЗМЕНИТЬ при создании вкладок (сохранять индексы):**

```python
# При создании вкладки терминала (найти место создания terminal_frame)
self.terminal_tab_index = self.notebook.index(self.terminal_frame)

# При создании вкладки пакетов (найти место создания packages_frame)
self.packages_tab_index = self.notebook.index(self.packages_frame)

# При создании вкладки мониторинга (найти место создания processes_monitor_tab_index)
self.monitoring_tab_index = self.notebook.index(self.processes_monitor_tab_index)
```

#### Критерии успеха

- ✅ При переключении вкладок обновляется `current_active_tab_index`
- ✅ Метод `is_tab_active()` корректно определяет активность
- ✅ Индексы вкладок сохраняются при создании

---

### Этап 2: Оптимизация терминала

**Приоритет:** Критичный  
**Время:** 1-1.5 часа  
**Риск:** Средний  
**Зависимости:** Этап 1

#### Задачи

1. Адаптивные интервалы обновления в `process_terminal_queue()`
2. Инкрементальное обновление в `_update_terminal_display()`
3. Оптимизация `terminal_update_callback` в `DualStreamLogger`
4. Ограничение обработки строк

#### Изменения в коде

**Файл:** `FSA-AstraInstall.py`  
**Класс:** `AutomationGUI`  
**Метод:** `process_terminal_queue()`

**ИЗМЕНИТЬ строки 29852-29903:**

```python
def process_terminal_queue(self):
    """Обработка очереди специальных сообщений и обновление терминала из буферов"""
    try:
        # Проверяем, активна ли вкладка терминала
        is_terminal_active = self.is_tab_active(self.terminal_tab_index)
        
        # Проверяем, идет ли активная установка/обновление
        is_active_installation = False
        if hasattr(self, 'system_updater') and self.system_updater:
            parser = getattr(self.system_updater, 'system_update_parser', None)
            if parser and not parser.is_finished:
                is_active_installation = True
        
        # Обрабатываем очередь UniversalProcessRunner
        if hasattr(self, 'universal_runner') and self.universal_runner:
            self.universal_runner.process_queue()
        
        # Парсер читает из RAW-буфера (только если идет установка)
        if is_active_installation and hasattr(self, 'system_updater') and self.system_updater:
            if hasattr(self.system_updater, 'system_update_parser'):
                parser = self.system_updater.system_update_parser
                if parser and hasattr(parser, 'parse_from_buffer'):
                    try:
                        # Ограничиваем количество обрабатываемых строк за раз
                        max_lines_per_update = 50
                        initial_index = parser._last_processed_buffer_index
                        parser.parse_from_buffer()
                        processed = parser._last_processed_buffer_index - initial_index
                        
                        # Если обработано слишком много строк - увеличиваем интервал
                        if processed > max_lines_per_update:
                            update_interval = 500  # 500мс при большой нагрузке
                        else:
                            # Нормальная нагрузка
                            update_interval = 200 if is_active_installation else 300
                    except Exception as e:
                        print(f"[PARSER_ERROR] Ошибка parse_from_buffer: {e}")
                        update_interval = 300
                else:
                    update_interval = 300
            else:
                update_interval = 300
        else:
            update_interval = 300
        
        # Обрабатываем очередь сообщений (ограничиваем количество)
        processed_count = 0
        while hasattr(self, 'terminal_queue') and not self.terminal_queue.empty() and processed_count < 10:
            try:
                message = self.terminal_queue.get_nowait()
                processed_count += 1
                
                if message.startswith("[UNIVERSAL_PROGRESS]"):
                    self.handle_universal_progress(message)
                elif message.startswith("[REAL_TIME_PROGRESS]"):
                    self.handle_real_time_progress(message)
                elif message.startswith("[ADVANCED_PROGRESS]"):
                    self.handle_advanced_progress(message)
                elif message.startswith("[PROGRESS]"):
                    self.handle_apt_progress(message)
                elif message.startswith("[STAGE]"):
                    self.handle_stage_update(message)
                    
            except Exception as e:
                break
        
        # Обновляем терминал из буферов (только если нужно)
        # При активной установке обновляем реже, если вкладка неактивна
        should_update_terminal = True
        if is_active_installation and not is_terminal_active:
            # Проверяем, прошло ли достаточно времени с последнего обновления
            if hasattr(self, '_last_terminal_update_time'):
                time_since_update = time.time() - self._last_terminal_update_time
                if time_since_update < 1.0:  # Минимум 1 секунда между обновлениями
                    should_update_terminal = False
        
        if should_update_terminal:
            self._update_terminal_display()
            if not hasattr(self, '_last_terminal_update_time'):
                self._last_terminal_update_time = 0
            self._last_terminal_update_time = time.time()
                
    except Exception as e:
        print(f"[ERROR] Ошибка process_terminal_queue: {e}")
    finally:
        # Динамический интервал в зависимости от активности
        if is_terminal_active:
            # Вкладка активна - обновляем чаще
            if is_active_installation:
                next_interval = 200  # 200мс при активной установке
            else:
                next_interval = 300  # 300мс в обычном режиме
        else:
            # Вкладка неактивна - обновляем реже
            next_interval = 2000  # 2 секунды
        
        self.root.after(next_interval, self.process_terminal_queue)
```

**ИЗМЕНИТЬ метод `_update_terminal_display()` (строки 29567-29677):**

Добавить инкрементальное обновление вместо полной перерисовки:

```python
def _update_terminal_display(self):
    """Обновление терминала из буферов DualStreamLogger (инкрементальное)"""
    try:
        # ЗАЩИТА ОТ РЕКУРСИИ
        if hasattr(self, '_updating_terminal') and self._updating_terminal:
            return
        self._updating_terminal = True
        
        # Получаем dual_logger
        dual_logger = None
        if hasattr(self, 'universal_runner') and self.universal_runner:
            dual_logger = getattr(self.universal_runner, 'dual_logger', None)
        
        if not dual_logger:
            if '_global_dual_logger' in globals() and globals()['_global_dual_logger']:
                dual_logger = globals()['_global_dual_logger']
        
        if not dual_logger:
            self._updating_terminal = False
            return
        
        # Режим отображения
        mode = getattr(self, 'terminal_stream_mode', None)
        mode_value = mode.get() if mode else "analysis"
        
        # Поисковый фильтр
        search_text = self.terminal_search_var.get().lower()
        
        # Проверяем размер буфера
        if mode_value == "raw":
            current_buffer_size = dual_logger.get_raw_buffer_size()
        elif mode_value == "analysis":
            current_buffer_size = dual_logger.get_analysis_buffer_size()
        elif mode_value == "both":
            current_buffer_size = dual_logger.get_raw_buffer_size() + dual_logger.get_analysis_buffer_size()
        else:
            current_buffer_size = 0
        
        # Проверяем изменения
        buffer_changed = current_buffer_size != getattr(self, '_last_terminal_buffer_size', 0)
        mode_changed = mode_value != getattr(self, '_last_terminal_mode', None)
        search_changed = search_text != getattr(self, '_last_terminal_search', "")
        force_update = getattr(self, '_force_terminal_update', False)
        
        # Если ничего не изменилось - пропускаем
        if not buffer_changed and not mode_changed and not search_changed and not force_update:
            self._updating_terminal = False
            return
        
        # Сохраняем текущее состояние
        self._last_terminal_buffer_size = current_buffer_size
        self._last_terminal_mode = mode_value
        self._last_terminal_search = search_text
        self._force_terminal_update = False
        
        # ИНКРЕМЕНТАЛЬНОЕ ОБНОВЛЕНИЕ: добавляем только новые строки
        if buffer_changed and not mode_changed and not search_changed:
            # Только новые данные, режим и фильтр не изменились
            # Получаем только новые строки
            last_size = getattr(self, '_last_terminal_buffer_size', 0)
            
            if mode_value == "raw":
                all_messages = dual_logger.get_raw_buffer()
                new_messages = list(all_messages)[last_size:]
            elif mode_value == "analysis":
                all_messages = dual_logger.get_analysis_buffer()
                new_messages = list(all_messages)[last_size:]
            elif mode_value == "both":
                raw_messages = dual_logger.get_raw_buffer()
                analysis_messages = dual_logger.get_analysis_buffer()
                all_messages = list(raw_messages) + list(analysis_messages)
                all_messages.sort(key=lambda x: self._extract_timestamp(x))
                new_messages = all_messages[last_size:]
            else:
                new_messages = []
            
            # Применяем поисковый фильтр
            if search_text:
                new_messages = [msg for msg in new_messages if search_text in msg.lower()]
            
            # Добавляем только новые сообщения
            self.terminal_text.config(state=self.tk.NORMAL)
            for message in new_messages:
                display_message = message
                if not self.terminal_timestamp_enabled.get():
                    display_message = re.sub(r'^\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}\]\s*', '', display_message)
                
                self.terminal_text.insert(self.tk.END, display_message + "\n")
            
            # Прокрутка в конец (если автопрокрутка включена)
            if self.terminal_autoscroll_enabled.get():
                self.terminal_text.see(self.tk.END)
            
            self.terminal_text.config(state=self.tk.DISABLED)
        else:
            # Режим или фильтр изменились - полная перерисовка
            # ... существующий код полной перерисовки ...
            pass
        
        self._updating_terminal = False
        
    except Exception as e:
        print(f"Ошибка обновления терминала: {e}", level='ERROR', gui_log=True)
        if hasattr(self, '_updating_terminal'):
            self._updating_terminal = False
```

**ИЗМЕНИТЬ `DualStreamLogger.write_raw()` (строки 193-214):**

Оптимизировать callback - не вызывать при каждой записи:

```python
def write_raw(self, message):
    """Записать сообщение в RAW-поток (всегда с меткой времени)"""
    timestamp_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    formatted_message = "[%s] %s" % (timestamp_str, message)
    
    with self._raw_lock:
        self._raw_buffer.append(formatted_message)
    
    # Увеличиваем счетчик полученных сообщений
    with self._stats_lock:
        self._messages_received_raw += 1
    
    # Асинхронная запись в файл (если включено)
    if self._file_writer_running and self._raw_log_path:
        self._file_queue.put(('raw', formatted_message))
    
    # ОПТИМИЗАЦИЯ: Вызываем callback не при каждой записи, а с задержкой
    # Используем счетчик изменений
    if self.terminal_update_callback:
        if not hasattr(self, '_terminal_update_pending'):
            self._terminal_update_pending = False
        
        if not self._terminal_update_pending:
            self._terminal_update_pending = True
            # Вызываем callback с небольшой задержкой (накопление изменений)
            try:
                # Используем threading.Timer для неблокирующей задержки
                import threading
                def delayed_callback():
                    try:
                        if self.terminal_update_callback:
                            self.terminal_update_callback()
                    except Exception:
                        pass
                    finally:
                        self._terminal_update_pending = False
                
                timer = threading.Timer(0.1, delayed_callback)  # 100мс задержка
                timer.daemon = True
                timer.start()
            except Exception:
                # Fallback: вызываем сразу, если threading недоступен
                try:
                    self.terminal_update_callback()
                    self._terminal_update_pending = False
                except Exception:
                    pass
```

#### Критерии успеха

- ✅ Терминал обновляется с адаптивными интервалами
- ✅ Инкрементальное обновление работает (добавляются только новые строки)
- ✅ Callback не вызывается при каждой записи
- ✅ При неактивной вкладке обновления происходят реже

---

### Этап 3: Оптимизация таблицы пакетов

**Приоритет:** Высокий  
**Время:** 1-1.5 часа  
**Риск:** Средний  
**Зависимости:** Этап 1

#### Задачи

1. Адаптивные интервалы обновления
2. Кэширование состояния таблицы
3. Инкрементальное обновление строк
4. Проверка изменений перед обновлением

#### Изменения в коде

**Файл:** `FSA-AstraInstall.py`  
**Класс:** `AutomationGUI`  
**Метод:** `start_packages_table_update()` и `update_packages_table()`

**ИЗМЕНИТЬ строки 22395-22480:**

```python
def start_packages_table_update(self):
    """Запуск периодического обновления таблицы пакетов"""
    if hasattr(self, 'packages_tree'):
        self.update_packages_table()
        
        # Адаптивные интервалы в зависимости от активности вкладки
        is_packages_active = self.is_tab_active(self.packages_tab_index)
        
        if is_packages_active:
            # Вкладка активна - обновляем каждые 500мс-1 сек
            update_interval = 500
        else:
            # Вкладка неактивна - обновляем каждые 2-3 секунды
            update_interval = 2000
        
        self.root.after(update_interval, self.start_packages_table_update)

def update_packages_table(self):
    """Обновление таблицы пакетов из парсера (инкрементальное)"""
    try:
        # Получаем таблицу пакетов из парсера
        if not hasattr(self, 'system_updater') or not self.system_updater:
            return
        
        parser = getattr(self.system_updater, 'system_update_parser', None)
        if not parser or not hasattr(parser, 'packages_table'):
            return
        
        packages_table = parser.packages_table
        if not packages_table:
            return
        
        # ИНКРЕМЕНТАЛЬНОЕ ОБНОВЛЕНИЕ: сравниваем с кэшем
        if not hasattr(self, '_packages_table_cache'):
            self._packages_table_cache = {}
            self._packages_table_items = {}  # {package_name: item_id}
        
        # Проверяем изменения
        current_packages = {pkg.get('package_name'): pkg for pkg in packages_table}
        cached_packages = self._packages_table_cache
        
        # Обновляем только измененные пакеты
        for package_name, pkg in current_packages.items():
            cached_pkg = cached_packages.get(package_name)
            
            if cached_pkg is None:
                # Новый пакет - добавляем
                self._add_package_to_table(pkg)
                self._packages_table_cache[package_name] = pkg.copy()
            else:
                # Пакет существует - проверяем изменения
                if self._package_changed(cached_pkg, pkg):
                    # Обновляем строку
                    self._update_package_in_table(package_name, pkg)
                    self._packages_table_cache[package_name] = pkg.copy()
        
        # Удаляем пакеты, которых больше нет
        for package_name in list(cached_packages.keys()):
            if package_name not in current_packages:
                # Удаляем строку
                if package_name in self._packages_table_items:
                    item_id = self._packages_table_items[package_name]
                    self.packages_tree.delete(item_id)
                    del self._packages_table_items[package_name]
                del self._packages_table_cache[package_name]
        
        # Обновляем статистику
        total_packages = len(packages_table)
        downloaded_count = sum(1 for pkg in packages_table if pkg.get('flags', {}).get('downloaded', False))
        unpacked_count = sum(1 for pkg in packages_table if pkg.get('flags', {}).get('unpacked', False))
        configured_count = sum(1 for pkg in packages_table if pkg.get('flags', {}).get('configured', False))
        
        if hasattr(self, 'packages_stats_label'):
            self.packages_stats_label.config(
                text=f"Информация: Всего пакетов: {total_packages} | "
                     f"Скачано: {downloaded_count} | "
                     f"Распаковано: {unpacked_count} | "
                     f"Настроено: {configured_count}"
            )
                    
    except Exception as e:
        pass

def _package_changed(self, old_pkg, new_pkg):
    """Проверяет, изменился ли пакет"""
    old_flags = old_pkg.get('flags', {})
    new_flags = new_pkg.get('flags', {})
    
    return (old_flags.get('downloaded') != new_flags.get('downloaded') or
            old_flags.get('unpacked') != new_flags.get('unpacked') or
            old_flags.get('configured') != new_flags.get('configured') or
            old_pkg.get('size') != new_pkg.get('size'))

def _add_package_to_table(self, pkg):
    """Добавляет пакет в таблицу"""
    package_name = pkg.get('package_name', '')
    size = pkg.get('size', '') or ''
    if not size or size.lower() == 'unknown':
        size = ''
    flags = pkg.get('flags', {})
    
    status = "Скачивание"
    if flags.get('configured'):
        status = "Настроен"
    elif flags.get('unpacked'):
        status = "Распакован"
    elif flags.get('downloaded'):
        status = "Скачан"
    
    item_id = self.packages_tree.insert("", self.tk.END, values=(
        package_name,
        size,
        status,
        "[OK]" if flags.get('downloaded') else "",
        "[OK]" if flags.get('unpacked') else "",
        "[OK]" if flags.get('configured') else ""
    ))
    
    self._packages_table_items[package_name] = item_id

def _update_package_in_table(self, package_name, pkg):
    """Обновляет строку пакета в таблице"""
    if package_name not in self._packages_table_items:
        self._add_package_to_table(pkg)
        return
    
    item_id = self._packages_table_items[package_name]
    size = pkg.get('size', '') or ''
    if not size or size.lower() == 'unknown':
        size = ''
    flags = pkg.get('flags', {})
    
    status = "Скачивание"
    if flags.get('configured'):
        status = "Настроен"
    elif flags.get('unpacked'):
        status = "Распакован"
    elif flags.get('downloaded'):
        status = "Скачан"
    
    # Обновляем значения
    self.packages_tree.set(item_id, "size", size)
    self.packages_tree.set(item_id, "status", status)
    self.packages_tree.set(item_id, "downloaded", "[OK]" if flags.get('downloaded') else "")
    self.packages_tree.set(item_id, "unpacked", "[OK]" if flags.get('unpacked') else "")
    self.packages_tree.set(item_id, "configured", "[OK]" if flags.get('configured') else "")
```

#### Критерии успеха

- ✅ Таблица обновляется с адаптивными интервалами
- ✅ Инкрементальное обновление работает (только измененные строки)
- ✅ Кэширование работает корректно
- ✅ При неактивной вкладке обновления происходят реже

---

### Этап 4: Оптимизация мониторинга процессов

**Приоритет:** Средний  
**Время:** 1.5-2 часа  
**Риск:** Средний  
**Зависимости:** Этап 1

#### Задачи

1. Адаптивные интервалы обновления
2. Кэширование информации о процессах
3. Инкрементальное обновление строк
4. Оптимизация сбора данных

#### Изменения в коде

**Файл:** `FSA-AstraInstall.py`  
**Класс:** `AutomationGUI`  
**Метод:** `_auto_refresh_processes_monitor()` и `_refresh_processes_monitor()`

**ИЗМЕНИТЬ строки 22246-22277:**

```python
def _auto_refresh_processes_monitor(self):
    """Автоматическое обновление таблицы процессов"""
    if not hasattr(self, 'processes_tree'):
        return
    
    # Проверяем, активна ли вкладка мониторинга
    is_monitor_active = self.is_tab_active(self.monitoring_tab_index)
    
    if is_monitor_active:
        # Вкладка активна - обновляем каждые 500мс (быстро)
        self._refresh_processes_monitor()
        self.root.after(500, self._auto_refresh_processes_monitor)
    else:
        # Вкладка неактивна - обновляем каждые 1-2 секунды
        self._refresh_processes_monitor()
        self.root.after(2000, self._auto_refresh_processes_monitor)
```

**ИЗМЕНИТЬ метод `_refresh_processes_monitor()` (строки 21923-22244):**

Добавить кэширование и инкрементальное обновление:

```python
def _refresh_processes_monitor(self):
    """Обновление таблицы процессов (инкрементальное)"""
    if not hasattr(self, 'processes_tree'):
        return
    
    # Защита от частых вызовов
    if not hasattr(self, '_last_processes_refresh'):
        self._last_processes_refresh = 0
    
    current_time = time.time()
    min_interval = 0.5
    if current_time - self._last_processes_refresh < min_interval:
        return
    
    self._last_processes_refresh = current_time
    
    try:
        # Инициализируем кэш, если его нет
        if not hasattr(self, '_processes_cache'):
            self._processes_cache = {}  # {pid: {'pid': pid, 'name': name, ...}}
            self._processes_items = {}  # {pid: item_id}
        
        # Получаем текущие процессы
        app_processes, total_cpu = self.process_monitor._get_app_processes_cached()
        
        if _global_activity_tracker:
            active_operations = _global_activity_tracker.get_active_operations()
        else:
            active_operations = []
        
        install_processes = self._get_running_installation_processes()
        wine_processes = self._get_wine_processes()
        
        universal_runner_processes = []
        if hasattr(self, 'universal_runner') and self.universal_runner:
            universal_runner_processes = self.universal_runner.get_running_processes()
        
        logger_threads = self._get_logger_threads_info()
        system_threads = self._get_all_system_threads_info()
        
        filesystem_monitor_info = None
        if hasattr(self, 'filesystem_monitor') and self.filesystem_monitor:
            filesystem_monitor_info = self.filesystem_monitor.get_process_info()
        
        # Объединяем все процессы в один список для обработки
        all_current_processes = {}
        
        # Добавляем процессы приложения
        for proc in app_processes:
            pid = proc.get('pid', '---')
            all_current_processes[pid] = {'type': 'app', 'data': proc}
        
        # Добавляем активные операции
        for op in active_operations:
            all_current_processes[f"op_{id(op)}"] = {'type': 'operation', 'data': op}
        
        # Добавляем процессы установки
        for proc in install_processes:
            pid = proc.get('pid', '---')
            all_current_processes[pid] = {'type': 'install', 'data': proc}
        
        # Добавляем процессы Wine
        for proc in wine_processes:
            pid = proc.get('pid', '---')
            all_current_processes[pid] = {'type': 'wine', 'data': proc}
        
        # ИНКРЕМЕНТАЛЬНОЕ ОБНОВЛЕНИЕ: обновляем только измененные процессы
        for process_key, process_info in all_current_processes.items():
            process_type = process_info['type']
            proc = process_info['data']
            
            cached_proc = self._processes_cache.get(process_key)
            
            if cached_proc is None:
                # Новый процесс - добавляем
                item_id = self._add_process_to_table(process_type, proc)
                if item_id:
                    self._processes_cache[process_key] = proc.copy() if isinstance(proc, dict) else proc
                    self._processes_items[process_key] = item_id
            else:
                # Процесс существует - проверяем изменения
                if self._process_changed(cached_proc, proc):
                    # Обновляем строку
                    if process_key in self._processes_items:
                        item_id = self._processes_items[process_key]
                        self._update_process_in_table(item_id, process_type, proc)
                        self._processes_cache[process_key] = proc.copy() if isinstance(proc, dict) else proc
        
        # Удаляем процессы, которых больше нет
        for process_key in list(self._processes_cache.keys()):
            if process_key not in all_current_processes:
                if process_key in self._processes_items:
                    item_id = self._processes_items[process_key]
                    self.processes_tree.delete(item_id)
                    del self._processes_items[process_key]
                del self._processes_cache[process_key]
        
        # Обновляем статус
        total_processes = len(all_current_processes)
        self.processes_status_label.config(
            text=f"Всего процессов: {total_processes} | Обновление каждые 0.5 секунды..."
        )
        
    except Exception as e:
        self.processes_status_label.config(text=f"Ошибка обновления: {str(e)}", fg='red')

def _process_changed(self, old_proc, new_proc):
    """Проверяет, изменился ли процесс"""
    if not isinstance(old_proc, dict) or not isinstance(new_proc, dict):
        return True  # Если не словари, считаем измененным
    
    return (old_proc.get('cpu', 0) != new_proc.get('cpu', 0) or
            old_proc.get('memory', 0) != new_proc.get('memory', 0) or
            old_proc.get('name', '') != new_proc.get('name', ''))

def _add_process_to_table(self, process_type, proc):
    """Добавляет процесс в таблицу"""
    # ... существующая логика добавления процесса ...
    # Возвращает item_id
    pass

def _update_process_in_table(self, item_id, process_type, proc):
    """Обновляет строку процесса в таблице"""
    # ... логика обновления значений строки ...
    pass
```

#### Критерии успеха

- ✅ Мониторинг обновляется с адаптивными интервалами
- ✅ Кэширование работает корректно
- ✅ Инкрементальное обновление работает
- ✅ При активной вкладке обновления происходят быстро (500мс)

---

### Этап 5: Оптимизация парсинга буфера

**Приоритет:** Высокий  
**Время:** 30-40 минут  
**Риск:** Низкий  
**Зависимости:** Нет

#### Задачи

1. Ограничение количества обрабатываемых строк
2. Адаптивная частота парсинга
3. Быстрый выход при отсутствии данных

#### Изменения в коде

**Файл:** `FSA-AstraInstall.py`  
**Класс:** `SystemUpdateParser`  
**Метод:** `parse_from_buffer()`

**ИЗМЕНИТЬ строки 31607-31649:**

```python
def parse_from_buffer(self):
    """
    Парсинг новых строк из RAW-буфера DualStreamLogger
    
    Читает только новые строки из буфера (начиная с _last_processed_buffer_index)
    и обрабатывает их через parse_line().
    Ограничивает количество обрабатываемых строк за раз для предотвращения блокировки GUI.
    """
    if self.is_finished:
        return
    
    # Получаем доступ к глобальному DualStreamLogger
    if '_global_dual_logger' not in globals() or not globals()['_global_dual_logger']:
        return
    
    dual_logger = globals()['_global_dual_logger']
    
    # Получаем RAW-буфер
    raw_buffer = dual_logger._raw_buffer
    
    # Получаем длину буфера (thread-safe через deque)
    current_buffer_size = len(raw_buffer)
    
    # Если нет новых данных - выходим быстро
    if current_buffer_size <= self._last_processed_buffer_index:
        return
    
    # ОПТИМИЗАЦИЯ: Ограничиваем количество обрабатываемых строк за раз
    max_lines_per_call = 100  # Максимум 100 строк за один вызов
    lines_to_process = min(
        current_buffer_size - self._last_processed_buffer_index,
        max_lines_per_call
    )
    
    # Обрабатываем только ограниченное количество строк
    end_index = self._last_processed_buffer_index + lines_to_process
    
    for i in range(self._last_processed_buffer_index, end_index):
        try:
            # Получаем строку из буфера
            line = raw_buffer[i]
            
            # Парсим через существующий метод
            self.parse_line(line)
            
        except IndexError:
            # Буфер изменился во время итерации - прекращаем
            break
        except Exception as e:
            print(f"[PARSER_ERROR] Ошибка парсинга из буфера: {e}")
    
    # Обновляем позицию (обработали только часть, остальное в следующем цикле)
    self._last_processed_buffer_index = end_index
```

#### Критерии успеха

- ✅ Парсинг обрабатывает не более 100 строк за раз
- ✅ Остальные строки обрабатываются в следующих циклах
- ✅ Быстрый выход при отсутствии новых данных

---

### Этап 6: Оптимизация `process_terminal_queue`

**Приоритет:** Критичный  
**Время:** 40-50 минут  
**Риск:** Средний  
**Зависимости:** Этап 2, Этап 5

#### Задачи

1. Адаптивные интервалы в зависимости от активности
2. Условное обновление терминала
3. Оптимизация вызовов парсера

#### Изменения в коде

**Файл:** `FSA-AstraInstall.py`  
**Класс:** `AutomationGUI`  
**Метод:** `process_terminal_queue()`

**ПРИМЕЧАНИЕ:** Большая часть изменений уже включена в Этап 2. Здесь нужно только убедиться, что все оптимизации применены корректно.

#### Критерии успеха

- ✅ Адаптивные интервалы работают корректно
- ✅ Терминал обновляется только при необходимости
- ✅ Парсер вызывается с ограничениями

---

## 📊 Структура изменений

### Файлы для изменения

1. **FSA-AstraInstall.py** - основной файл с GUI и логикой
   - Класс `AutomationGUI` - методы обновления GUI
   - Класс `DualStreamLogger` - оптимизация callback
   - Класс `SystemUpdateParser` - оптимизация парсинга

### Оценка изменений

- **Строк кода для изменения:** ~500-700 строк
- **Новых методов:** ~10-15 методов
- **Новых переменных:** ~10-15 переменных

---

## 🧪 Тестирование

### Тесты после каждого этапа

1. **Этап 1:**
   - ✅ Переключение вкладок обновляет `current_active_tab_index`
   - ✅ Метод `is_tab_active()` работает корректно

2. **Этап 2:**
   - ✅ Терминал обновляется с правильными интервалами
   - ✅ Инкрементальное обновление работает
   - ✅ Callback не вызывается при каждой записи

3. **Этап 3:**
   - ✅ Таблица пакетов обновляется инкрементально
   - ✅ Кэширование работает
   - ✅ Интервалы адаптивные

4. **Этап 4:**
   - ✅ Мониторинг процессов обновляется инкрементально
   - ✅ Кэширование работает
   - ✅ Интервалы адаптивные

5. **Этап 5:**
   - ✅ Парсинг ограничен количеством строк
   - ✅ Не блокирует GUI

6. **Этап 6:**
   - ✅ Все оптимизации работают вместе

### Финальное тестирование

1. **Тест производительности:**
   - Запустить обновление системы с включенным автообновлением
   - Запустить обновление системы с выключенным автообновлением
   - Сравнить время выполнения (должно быть примерно одинаково)

2. **Тест отзывчивости GUI:**
   - Во время обновления системы попробовать переключать вкладки
   - GUI должен оставаться отзывчивым
   - Нет "зависаний" интерфейса

3. **Тест мониторинга:**
   - Открыть вкладку мониторинга - обновления должны быть частыми (500мс)
   - Закрыть вкладку - обновления должны быть редкими (1-2 сек)
   - Данные должны оставаться актуальными

---

## ⚠️ Риски и митигация

### Риски

1. **Ошибки в инкрементальном обновлении**
   - **Риск:** Могут пропускаться изменения
   - **Митигация:** Тщательное тестирование, fallback на полную перерисовку при ошибках

2. **Проблемы с кэшированием**
   - **Риск:** Кэш может стать неактуальным
   - **Митигация:** Периодическая проверка актуальности, сброс кэша при необходимости

3. **Сложность отладки**
   - **Риск:** Инкрементальные обновления сложнее отлаживать
   - **Митигация:** Логирование изменений, возможность отключить оптимизации для отладки

4. **Производительность при большом количестве данных**
   - **Риск:** При очень большом буфере инкрементальное обновление может быть медленнее
   - **Митигация:** Ограничение размера буфера, периодическая очистка старых данных

### План отката

Если что-то пойдет не так:
1. Откатить изменения через git к предыдущему коммиту
2. Или добавить флаг для отключения оптимизаций
3. Постепенно включать оптимизации по этапам

---

## ✅ Критерии успеха

### После всех этапов

1. **Производительность:**
   - ✅ Обновление системы работает одинаково быстро при включенном и выключенном автообновлении
   - ✅ Разница во времени не более 5-10%

2. **Отзывчивость GUI:**
   - ✅ GUI остается отзывчивым во время активных операций
   - ✅ Нет "зависаний" интерфейса
   - ✅ Переключение вкладок работает плавно

3. **Мониторинг:**
   - ✅ Активные вкладки обновляются с высокой частотой
   - ✅ Неактивные вкладки обновляются редко, но данные актуальны
   - ✅ Нет накопления задач в очереди GUI

4. **Процесс APT:**
   - ✅ Процесс APT не блокируется из-за перегрузки GUI
   - ✅ Буфер stdout не заполняется
   - ✅ Обновление системы завершается успешно

---

## 📅 План выполнения

### Рекомендуемый порядок

1. **Этап 1** (30-40 мин) - Фундамент для всех остальных
2. **Этап 2** (1-1.5 часа) - Критично, влияет на процесс APT
3. **Этап 5** (30-40 мин) - Быстро, влияет на Этап 6
4. **Этап 6** (40-50 мин) - Критично, завершает оптимизацию терминала
5. **Этап 3** (1-1.5 часа) - Важно для пользовательского опыта
6. **Этап 4** (1.5-2 часа) - Улучшает мониторинг

**Общее время:** 5-7 часов работы

### Рекомендация

Выполнять поэтапно с тестированием после каждого этапа. Это позволит:
- Быстро выявлять проблемы
- Легко откатывать изменения при необходимости
- Видеть прогресс по мере реализации

---

**Дата создания плана:** 2025.12.25  
**Версия документа:** 1.0.0  
**Статус:** 📝 ПЛАН ГОТОВ К РЕАЛИЗАЦИИ

