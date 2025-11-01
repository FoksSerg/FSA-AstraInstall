# ДЕТАЛЬНЫЙ ПЛАН РЕФАКТОРИНГА СИСТЕМЫ ЛОГИРОВАНИЯ
**Версия: V2.4.96 (2025.10.31)**
**Компания: ООО "НПА Вира-Реалтайм"**

# Статус: ПЛАН РЕАЛИЗАЦИИ

## ЦЕЛЬ РЕФАКТОРИНГА

Упростить архитектуру логирования:
- **Единый источник данных:** DualStreamLogger буферы (RAW и ANALYSIS)
- **Два потока:** RAW (сторонние процессы: apt-get, sys.stdout) и ANALYSIS (системные сообщения: print, log_info)
- **Все сообщения с метками времени** - для объединения потоков по времени
- **GUI читает из буферов** (raw/analysis/both с сортировкой по времени)
- **GUI лог через флаг `gui_log=True`** (отдельный виджет log_text)
- **Асинхронная запись в файлы** (не блокирует выполнение)

---

## АНАЛИЗ ТЕКУЩЕЙ АРХИТЕКТУРЫ

### ПРОБЛЕМЫ:

1. **Дублирование записей в файлы:**
   - `universal_print()` → `GLOBAL_LOG_FILE` (прямая запись, строка 641)
   - `universal_print()` → `DualStreamLogger.write_analysis()` → `_analysis_log_path` (тот же файл!, строка 651)
   - `universal_runner._write_to_file()` → `log_file_path` (другой файл, строка 942)
   - **Итого:** одно сообщение попадает в 2-3 файла

2. **Дублирование данных в GUI:**
   - `terminal_messages_raw` / `terminal_messages_analysis` (массивы в GUI, строки 10083-10098)
   - `_raw_buffer` / `_analysis_buffer` (буферы в DualStreamLogger, строки 255-256)
   - **Итого:** данные хранятся в двух местах

3. **Несогласованность путей логирования:**
   - `print()` → `DualStreamLogger` + `gui_callback` → `add_terminal_output()`
   - `run_process()` → `DualStreamLogger.write_raw()` + `add_terminal_output()`
   - `log_info()` → `add_output()` + `_write_to_file()`
   - **Итого:** разные пути для одного типа данных

4. **TerminalRedirector:**
   - Перехватывает `sys.stdout.write()` → `terminal_queue` (строка 7070)
   - Не использует DualStreamLogger напрямую
   - Дублирует функциональность

---

## ПЛАН ИЗМЕНЕНИЙ

### РАЗДЕЛ 1: `DualStreamLogger.write_raw/write_analysis()` - УБРАТЬ ФЛАГ timestamp

**ФАЙЛ:** `astra_automation.py`  
**КЛАСС:** `DualStreamLogger`  
**МЕТОДЫ:** `write_raw()` (строка 274), `write_analysis()` (строка 289)

#### УДАЛИТЬ:
1. Параметр `timestamp=True` из сигнатуры методов
2. Условную проверку `if timestamp:` (строки 276, 291)
3. Блок `else:` без метки времени (строки 279-280, 294-295)

#### ИЗМЕНИТЬ:
1. Всегда добавлять метку времени (убрать условие)
2. Упростить логику: всегда форматировать с timestamp

#### НОВАЯ РЕАЛИЗАЦИЯ:
```python
def write_raw(self, message):
    """Записать сообщение в RAW-поток (всегда с меткой времени)"""
    timestamp_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    formatted_message = "[%s] %s" % (timestamp_str, message)
    
    with self._raw_lock:
        self._raw_buffer.append(formatted_message)
    
    # Асинхронная запись в файл (если включено)
    if self._file_writer_running and self._raw_log_path:
        self._file_queue.put(('raw', formatted_message))

def write_analysis(self, message):
    """Записать сообщение в ANALYSIS-поток (всегда с меткой времени)"""
    timestamp_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    formatted_message = "[%s] %s" % (timestamp_str, message)
    
    with self._analysis_lock:
        self._analysis_buffer.append(formatted_message)
    
    # Асинхронная запись в файл (если включено)
    if self._file_writer_running and self._analysis_log_path:
        self._file_queue.put(('analysis', formatted_message))
```

#### ИЗМЕНИТЬ ВСЕ ВЫЗОВЫ:
- `write_raw(..., timestamp=True)` → `write_raw(...)`
- `write_analysis(..., timestamp=True)` → `write_analysis(...)`

**Места изменений:**
- Строка 566: `dual_logger.write_raw(clean_line, timestamp=True)` → `dual_logger.write_raw(clean_line)`
- Строка 651: `dual_logger.write_analysis(f"[PRINT] {message}", timestamp=True)` → `dual_logger.write_analysis(f"[PRINT] {message}")`
- Строка 1023: `_global_dual_logger.write_raw(line_clean, timestamp=True)` → `_global_dual_logger.write_raw(line_clean)`
- Строка 14452: `_global_dual_logger.write_raw("=== ТЕСТ: ...", timestamp=True)` → `_global_dual_logger.write_raw("=== ТЕСТ: ...")`
- Строка 14453: аналогично

---

### РАЗДЕЛ 2: `universal_print()` - УПРОЩЕНИЕ И ЕДИНАЯ ТОЧКА ВХОДА

**ФАЙЛ:** `astra_automation.py`  
**МЕТОД:** `universal_print()` (строка 634)

#### УДАЛИТЬ:
1. Прямую запись в `GLOBAL_LOG_FILE` (строки 639-642)
2. Вызов `gui_callback()` для терминала (строки 655-664) - GUI читает из буферов
3. Дублирование в `DualStreamLogger` с префиксом `[PRINT]` (строки 644-653)
4. Все проверки `GLOBAL_LOG_FILE` для ошибок (строки 662-664, 672-674)

#### ИЗМЕНИТЬ:
1. Добавить флаг `stream` для определения потока ('raw' или 'analysis', по умолчанию 'analysis')
2. Упростить логику: только запись в DualStreamLogger и вызов `gui_log_callback` если `gui_log=True`
3. Убрать все проверки и дублирование

#### ДОБАВИТЬ:
1. Флаг `stream` для определения потока
2. Флаг `level` для уровня сообщения

#### НОВАЯ РЕАЛИЗАЦИЯ:
```python
def universal_print(*args, **kwargs):
    """
    Универсальная функция логирования - ЕДИНСТВЕННЫЙ путь в буферы DualStreamLogger
    
    Флаги:
    - stream='analysis'|'raw' - поток (по умолчанию 'analysis')
    - gui_log=True|False - отображать в GUI логе (по умолчанию False)
    - level='INFO'|'ERROR'|'WARNING'|'DEBUG' - уровень (по умолчанию 'INFO')
    
    ВСЕ сообщения ВСЕГДА с метками времени (через DualStreamLogger)
    """
    message = ' '.join(str(arg) for arg in args)
    
    # Флаги
    stream_type = kwargs.pop('stream', 'analysis')  # 'analysis' или 'raw'
    gui_log = kwargs.pop('gui_log', False)
    level = kwargs.pop('level', 'INFO')
    
    # Получаем dual_logger из universal_runner
    dual_logger = None
    if hasattr(sys, '_gui_instance') and sys._gui_instance:
        if hasattr(sys._gui_instance, 'universal_runner') and sys._gui_instance.universal_runner:
            dual_logger = getattr(sys._gui_instance.universal_runner, 'dual_logger', None)
    
    # ВСЁ через DualStreamLogger (буферы с метками времени)
    if dual_logger:
        formatted_message = f"[{level}] {message}"
        if stream_type == 'raw':
            dual_logger.write_raw(formatted_message)  # ВСЕГДА с меткой времени
        else:
            dual_logger.write_analysis(formatted_message)  # ВСЕГДА с меткой времени
    else:
        # Fallback: если dual_logger недоступен, используем прямой print
        # (только для самых ранних этапов инициализации)
        _original_print(f"[{level}] {message}")
    
    # GUI лог (ТОЛЬКО если gui_log=True)
    if gui_log and hasattr(sys, '_gui_instance') and sys._gui_instance:
        if hasattr(sys._gui_instance, 'universal_runner') and sys._gui_instance.universal_runner:
            if hasattr(sys._gui_instance.universal_runner, 'gui_log_callback'):
                try:
                    sys._gui_instance.universal_runner.gui_log_callback(message)
                except Exception:
                    pass  # Игнорируем ошибки
```

---

### РАЗДЕЛ 3: `TerminalRedirector` - ВЫНЕСЕНИЕ И УПРОЩЕНИЕ

**ФАЙЛ:** `astra_automation.py`  
**МЕТОД:** `_redirect_output_to_terminal()` (строка 7056)  
**КЛАСС:** `TerminalRedirector` (строка 7066)

#### УДАЛИТЬ:
1. Класс `TerminalRedirector` изнутри метода `_redirect_output_to_terminal()` (вынести на уровень модуля)
2. Логику `terminal_queue` (строка 7070) - не нужна, т.к. GUI читает из буферов
3. Вызовы `add_terminal_output()` для перенаправления (строки 7082-7083)
4. Логику получения `universal_print_func` из модуля (строки 7058-7064)
5. Параметр `universal_print_func` из конструктора `TerminalRedirector` (строка 7068)

#### ИЗМЕНИТЬ:
1. Вынести класс `TerminalRedirector` на уровень модуля (перед классом `AutomationGUI`, примерно строка 6358)
2. Упростить `write()`: вызывать `universal_print()` с `stream='raw'`
3. Убрать работу с `terminal_queue`
4. Упростить метод `_redirect_output_to_terminal()`

#### ДОБАВИТЬ:
1. Класс `TerminalRedirector` на уровне модуля

#### НОВАЯ РЕАЛИЗАЦИЯ:

**Разместить ПЕРЕД классом AutomationGUI (примерно строка 6358):**
```python
# ============================================================================
# TERMINALREDIRECTOR - ПЕРЕНАПРАВЛЕНИЕ sys.stdout/stderr В RAW ПОТОК
# ============================================================================
class TerminalRedirector:
    """
    Перехват sys.stdout/stderr для перенаправления в RAW поток DualStreamLogger
    
    Все сообщения автоматически получают метки времени через DualStreamLogger
    """
    
    def __init__(self, stream_name):
        """
        Args:
            stream_name: "stdout" или "stderr"
        """
        self.stream_name = stream_name
    
    def write(self, message):
        """Запись в RAW поток через universal_print"""
        if message.strip():
            # Добавляем префикс для stderr
            if self.stream_name == "stderr":
                message = f"[STDERR] {message}"
            
            # ВСЁ через universal_print в RAW поток (метка времени добавляется автоматически)
            universal_print(message.strip(), stream='raw', level='INFO')
    
    def flush(self):
        """Не требуется для GUI"""
        pass
```

**Изменить метод `_redirect_output_to_terminal()`:**
```python
def _redirect_output_to_terminal(self):
    """Перенаправление stdout и stderr на встроенный терминал GUI"""
    # Перенаправляем stdout и stderr
    sys.stdout = TerminalRedirector("stdout")
    sys.stderr = TerminalRedirector("stderr")
    
    # Логируем перенаправление (через universal_print, метка времени автоматически)
    print("[SYSTEM] Вывод перенаправлен на встроенный терминал GUI", stream='analysis')
    print("[SYSTEM] Родительский терминал можно безопасно закрыть", stream='analysis')
```

---

### РАЗДЕЛ 4: `UniversalProcessRunner.log_info/error/warning()` - УПРОЩЕНИЕ

**ФАЙЛ:** `astra_automation.py`  
**КЛАСС:** `UniversalProcessRunner`  
**МЕТОДЫ:** `log_info()` (строка 902), `log_error()` (строка 913), `log_warning()` (строка 922)

#### УДАЛИТЬ:
1. Вызовы `add_output()` (строки 910, 919, 928)
2. Вызовы `_write_to_file()` (строки 911, 920, 929)
3. Метод `_write_to_file()` (строка 942) - всё через DualStreamLogger

#### ИЗМЕНИТЬ:
1. Упростить методы: вызывать `universal_print()` с соответствующим уровнем
2. Убрать дублирование путей записи
3. Все сообщения автоматически получат метки времени через DualStreamLogger

#### НОВАЯ РЕАЛИЗАЦИЯ:
```python
def log_info(self, message, description=None, extra_info=None):
    """Логирование информационного сообщения (метка времени автоматически)"""
    if description and extra_info is not None:
        full_message = f"{description}: {str(message)} (доп.инфо: {extra_info})"
    elif description:
        full_message = f"{description}: {str(message)}"
    else:
        full_message = str(message)
    
    # ВСЁ через universal_print → DualStreamLogger (метка времени автоматически)
    universal_print(full_message, stream='analysis', level='INFO')

def log_error(self, message, description=None):
    """Логирование сообщения об ошибке (метка времени автоматически)"""
    if description:
        full_message = f"{description}: {str(message)}"
    else:
        full_message = str(message)
    
    # ВСЁ через universal_print → DualStreamLogger (метка времени автоматически)
    universal_print(full_message, stream='analysis', level='ERROR')

def log_warning(self, message, description=None):
    """Логирование предупреждения (метка времени автоматически)"""
    if description:
        full_message = f"{description}: {str(message)}"
    else:
        full_message = str(message)
    
    # ВСЁ через universal_print → DualStreamLogger (метка времени автоматически)
    universal_print(full_message, stream='analysis', level='WARNING')
```

---

### РАЗДЕЛ 5: `UniversalProcessRunner.run_process()` - УПРОЩЕНИЕ

**ФАЙЛ:** `astra_automation.py`  
**МЕТОД:** `run_process()` (строка 959)

#### УДАЛИТЬ:
1. Вызов `add_terminal_output()` для RAW потока (строка 1026) - GUI читает из буферов
2. Логику добавления в GUI терминал напрямую

#### ИЗМЕНИТЬ:
1. Оставить только запись в `DualStreamLogger.write_raw()` для RAW потока (метка времени автоматически)
2. Обработанный вывод через `_log()` → `universal_print()` → `DualStreamLogger.write_analysis()` (метка времени автоматически)

#### НОВАЯ РЕАЛИЗАЦИЯ:
```python
# В методе run_process(), в цикле чтения stdout (строка 1019):
if line_clean:
    # RAW поток (необработанный вывод процесса, метка времени автоматически)
    if _global_dual_logger:
        try:
            _global_dual_logger.write_raw(line_clean)  # Метка времени добавляется автоматически
            # GUI читает из буфера, поэтому не вызываем add_terminal_output()
        except Exception as e:
            print(f"[DUAL_LOGGER_ERROR] Ошибка записи в RAW-поток: {e}", gui_log=True)
    
    # ANALYSIS поток (обработанный вывод через universal_print, метка времени автоматически)
    self._log("  %s" % line_clean, "INFO", channels)
    # _log() вызывает universal_print() → DualStreamLogger.write_analysis()
    output_buffer += line
```

---

### РАЗДЕЛ 6: `UniversalProcessRunner._log()` - УПРОЩЕНИЕ

**ФАЙЛ:** `astra_automation.py`  
**МЕТОД:** `_log()` (строка 1118)

#### УДАЛИТЬ:
1. Вызовы `log_info/error/warning()` с проверкой каналов (строки 1128-1134) - всё идёт в буферы
2. Вызов `gui_callback()` (строка 1138) - GUI читает из буферов

#### ИЗМЕНИТЬ:
1. Упростить: вызывать `universal_print()` с нужным уровнем и потоком
2. Убрать проверку каналов - всё идёт через DualStreamLogger (метка времени автоматически)

#### НОВАЯ РЕАЛИЗАЦИЯ:
```python
def _log(self, message, level="INFO", channels=["file", "terminal"]):
    """
    Универсальное логирование - всё через universal_print
    
    Args:
        message: Текст сообщения
        level: Уровень сообщения ("INFO", "ERROR", "WARNING")
        channels: Игнорируется (для обратной совместимости)
    
    Метка времени добавляется автоматически через DualStreamLogger
    """
    # ВСЁ через universal_print → DualStreamLogger (метка времени автоматически)
    # stream='analysis' для обработанных сообщений
    gui_log_flag = "gui_log" in channels if isinstance(channels, list) else False
    universal_print(message, stream='analysis', level=level, gui_log=gui_log_flag)
```

---

### РАЗДЕЛ 7: `UniversalProcessRunner.add_output()` - УПРОЩЕНИЕ (ОПЦИОНАЛЬНО)

**ФАЙЛ:** `astra_automation.py`  
**МЕТОД:** `add_output()` (строка 1063)

#### АНАЛИЗ:
- Используется в `process_queue()` для обработки очереди
- Может использоваться в других местах

#### РЕШЕНИЕ:
1. Оставить метод для обратной совместимости
2. Изменить реализацию: вызывать `universal_print()` вместо записи в очередь
3. Упростить `process_queue()` - не нужна, т.к. всё через буферы

#### ИЗМЕНИТЬ:
```python
def add_output(self, message, level="INFO", channels=[], bypass_filter=False):
    """
    Добавление сообщения в лог (через universal_print для обратной совместимости)
    
    Метка времени добавляется автоматически через DualStreamLogger
    """
    gui_log = "gui_log" in channels
    stream = 'raw' if 'raw' in str(channels).lower() else 'analysis'
    universal_print(message, stream=stream, level=level, gui_log=gui_log)
```

---

### РАЗДЕЛ 8: GUI - ЧТЕНИЕ ИЗ БУФЕРОВ

**ФАЙЛ:** `astra_automation.py`  
**КЛАСС:** `AutomationGUI`  
**МЕТОДЫ:** `add_terminal_output()` (строка 10073), `_update_terminal_display()` (строка 10089), `process_terminal_queue()` (строка 10462)

#### УДАЛИТЬ:
1. Метод `add_terminal_output()` - не нужен, GUI читает из буферов
2. Массивы `terminal_messages_raw` и `terminal_messages_analysis` (строки 10083-10098) - дублирование
3. Логику обработки `terminal_queue` в `process_terminal_queue()` (строки 10479-10526)
4. Все вызовы `add_terminal_output()` из других мест
5. Логику добавления в `terminal_full_content` (строки 10474-10478)

#### ИЗМЕНИТЬ:
1. Метод `_update_terminal_display()` - читать из буферов DualStreamLogger
2. Метод `process_terminal_queue()` - только чтение из буферов и обновление GUI
3. Убрать обработку `terminal_queue` - не нужна

#### ДОБАВИТЬ:
1. Метод `_extract_timestamp()` - извлечение времени из сообщения для сортировки

#### НОВАЯ РЕАЛИЗАЦИЯ:

**Добавить новый метод:**
```python
def _extract_timestamp(self, message):
    """
    Извлечение timestamp из сообщения для сортировки
    
    Формат сообщения: "[2024-01-01 12:00:00.123] [LEVEL] message"
    """
    try:
        if message.startswith('[') and '] ' in message:
            timestamp_str = message.split('] ', 1)[0][1:]  # Убираем первую '['
            # Парсим timestamp
            import datetime
            return datetime.datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S.%f")
    except Exception:
        pass
    # Если не удалось извлечь - возвращаем минимальное время для сортировки
    import datetime
    return datetime.datetime.min
```

**Изменить `_update_terminal_display()`:**
```python
def _update_terminal_display(self):
    """Обновление терминала из буферов DualStreamLogger"""
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
            self._updating_terminal = False
            return
        
        # Режим отображения
        mode = getattr(self, 'terminal_stream_mode', None)
        if mode:
            mode_value = mode.get()
            
            if mode_value == "raw":
                # Только RAW поток
                messages = dual_logger.get_raw_buffer()
                
            elif mode_value == "analysis":
                # Только ANALYSIS поток
                messages = dual_logger.get_analysis_buffer()
                
            elif mode_value == "both":
                # Объединяем оба потока ПО ВРЕМЕНИ
                raw_messages = dual_logger.get_raw_buffer()
                analysis_messages = dual_logger.get_analysis_buffer()
                
                # Объединяем и сортируем по времени (метки времени уже есть в каждом сообщении)
                all_messages = raw_messages + analysis_messages
                all_messages.sort(key=lambda x: self._extract_timestamp(x))
                
                messages = all_messages
            else:
                messages = []
        else:
            # Fallback: используем analysis по умолчанию
            messages = dual_logger.get_analysis_buffer()
        
        if not messages:
            self._updating_terminal = False
            return
        
        # Применяем поисковый фильтр
        search_text = self.terminal_search_var.get().lower()
        if search_text:
            messages = [msg for msg in messages if search_text in msg.lower()]
        
        # Обновляем терминал
        self.terminal_text.config(state=self.tk.NORMAL)
        self.terminal_text.delete(1.0, self.tk.END)
        
        # Добавляем все сообщения (метки времени уже есть в каждом сообщении)
        for message in messages:
            self.terminal_text.insert(self.tk.END, message + "\n")
        
        # Прокрутка в конец (если автопрокрутка включена)
        if self.terminal_autoscroll_enabled.get():
            self.terminal_text.see(self.tk.END)
        
        self.terminal_text.config(state=self.tk.DISABLED)
        
        self._updating_terminal = False
        
    except Exception as e:
        print(f"[ERROR] Ошибка обновления терминала: {e}", gui_log=True)
        if hasattr(self, '_updating_terminal'):
            self._updating_terminal = False
```

**Изменить `process_terminal_queue()`:**
```python
def process_terminal_queue(self):
    """Обработка очереди сообщений и обновление терминала из буферов"""
    try:
        # Обрабатываем очередь UniversalProcessRunner (для обратной совместимости)
        if hasattr(self, 'universal_runner') and self.universal_runner:
            self.universal_runner.process_queue()
        
        # Парсер читает из RAW-буфера
        if hasattr(self, 'system_updater') and self.system_updater:
            if hasattr(self.system_updater, 'system_update_parser'):
                parser = self.system_updater.system_update_parser
                if parser and hasattr(parser, 'parse_from_buffer'):
                    try:
                        parser.parse_from_buffer()
                    except Exception as e:
                        print(f"[PARSER_ERROR] Ошибка parse_from_buffer: {e}")
        
        # Обновляем терминал из буферов DualStreamLogger
        if self.terminal_autoscroll_enabled.get():
            self._update_terminal_display()
        
    except Exception as e:
        print(f"[ERROR] Ошибка process_terminal_queue: {e}", gui_log=True)
    finally:
        # Повторяем через 100 мс
        self.root.after(100, self.process_terminal_queue)
```

**УДАЛИТЬ метод `add_terminal_output()` полностью** - не используется, GUI читает из буферов

---

### РАЗДЕЛ 9: ДОПОЛНИТЕЛЬНЫЕ ИЗМЕНЕНИЯ

#### 9.1. Убрать дублирование в других местах

**ФАЙЛ:** `astra_automation.py`  
**МЕСТО:** Различные классы, которые используют `_log()` методы

**ПРОВЕРИТЬ:**
- `RepoChecker._log()` (строка 1196) - использует `universal_runner.log_info()` ✅ (уже правильно)
- `WineInstaller._log()` (строка 2349) - использует `universal_runner.log_*()` ✅ (уже правильно)
- `WineUninstaller._log()` (строка 4332) - использует `universal_runner.log_*()` ✅ (уже правильно)
- `UniversalInstaller._log()` (строка 4834) - использует `universal_runner.log_*()` ✅ (уже правильно)

**ВЫВОД:** Эти методы уже правильные, после изменения `log_info/error/warning()` они автоматически будут использовать `universal_print()` → `DualStreamLogger` (метки времени автоматически)

#### 9.2. Убрать прямую запись в GLOBAL_LOG_FILE

**ФАЙЛ:** `astra_automation.py`  
**МЕСТО:** Все места, где используется `GLOBAL_LOG_FILE` напрямую

**ПРОВЕРИТЬ через grep:**
- Все вызовы `open(GLOBAL_LOG_FILE, ...)` - должны быть удалены или заменены

#### 9.3. Убрать вызовы `_write_to_file()` напрямую

**ФАЙЛ:** `astra_automation.py`  
**МЕТОД:** `_write_to_file()` (строка 942)

**ДЕЙСТВИЕ:**
- Удалить метод полностью
- Проверить все места использования через grep
- Заменить на `universal_print()` → `DualStreamLogger`

#### 9.4. Убрать все вызовы `add_terminal_output()`

**ФАЙЛ:** `astra_automation.py`  
**МЕТОД:** `add_terminal_output()` (строка 10073)

**ДЕЙСТВИЕ:**
- Удалить метод полностью
- Найти все вызовы через grep
- Удалить все вызовы (GUI читает из буферов)

#### 9.5. Убрать все вызовы с `timestamp=True`

**ФАЙЛ:** `astra_automation.py`  
**МЕСТО:** Все вызовы `write_raw()` и `write_analysis()`

**ДЕЙСТВИЕ:**
- Найти все вызовы через grep: `timestamp=True`
- Удалить параметр из всех вызовов

---

## ИТОГОВАЯ ТАБЛИЦА ИЗМЕНЕНИЙ

| Раздел | Что удаляем | Что меняем | Что добавляем |
|--------|-------------|-----------|---------------|
| `DualStreamLogger.write_*()` | Параметр `timestamp=True`<br>Условную проверку `if timestamp:`<br>Блок `else:` без метки | Всегда добавлять метку времени | - |
| `universal_print()` | Прямую запись в GLOBAL_LOG_FILE<br>gui_callback() для терминала<br>Дублирование DualStreamLogger<br>Все проверки GLOBAL_LOG_FILE | Упростить логику<br>Добавить флаг `stream` | Флаг `stream` ('raw'/'analysis')<br>Флаг `level` |
| `TerminalRedirector` | Класс из метода<br>Логику `terminal_queue`<br>Вызовы `add_terminal_output()`<br>Логику получения `universal_print_func` | Вынести на уровень модуля<br>Упростить `write()` | Класс на уровне модуля |
| `log_info/error/warning()` | `add_output()`<br>`_write_to_file()`<br>Метод `_write_to_file()` | Использовать `universal_print()` | - |
| `run_process()` | `add_terminal_output()` для RAW<br>`timestamp=True` в вызовах | Оставить только `write_raw()` | - |
| `_log()` | Вызовы `log_info/error/warning()`<br>`gui_callback()` | Использовать `universal_print()` | - |
| GUI методы | `add_terminal_output()`<br>Массивы `terminal_messages_*`<br>Обработка `terminal_queue`<br>Логику `terminal_full_content` | `_update_terminal_display()` читает из буферов<br>`process_terminal_queue()` упростить | `_extract_timestamp()` для сортировки |

---

## ПОРЯДОК ВЫПОЛНЕНИЯ

1. **Этап 1:** Убрать параметр `timestamp=True` из `DualStreamLogger.write_raw/write_analysis()` и всех вызовов
2. **Этап 2:** Вынести `TerminalRedirector` на уровень модуля и упростить
3. **Этап 3:** Упростить `universal_print()` - убрать дублирование
4. **Этап 4:** Упростить `log_info/error/warning()` - использовать `universal_print()`
5. **Этап 5:** Упростить `run_process()` - убрать `add_terminal_output()` и `timestamp=True`
6. **Этап 6:** Упростить `_log()` - использовать `universal_print()`
7. **Этап 7:** Изменить GUI - чтение из буферов вместо `add_terminal_output()`
8. **Этап 8:** Удалить неиспользуемые методы и массивы
9. **Этап 9:** Удалить метод `_write_to_file()` и все его вызовы
10. **Этап 10:** Тестирование

---

## КРИТЕРИИ УСПЕХА

1. ✅ Все сообщения попадают в буферы DualStreamLogger **ВСЕГДА с метками времени**
2. ✅ Нет дублирования записей в файлы
3. ✅ GUI читает из буферов (raw/analysis/both)
4. ✅ GUI лог работает через флаг `gui_log=True`
5. ✅ Асинхронная запись в файлы работает корректно
6. ✅ Режим "both" объединяет потоки по времени (сортировка по меткам времени)
7. ✅ Нет параметра `timestamp=True` нигде в коде

---

## РИСКИ И МИТИГАЦИЯ

### Риск 1: Потеря реального времени в GUI
**Митигация:** GUI обновляется каждые 100 мс из буферов - достаточно быстро для восприятия

### Риск 2: Потеря сообщений при падении приложения
**Митигация:** Буферы пишутся в файлы асинхронно (каждую секунду или 50 строк)

### Риск 3: Проблемы с сортировкой по времени
**Митигация:** Все сообщения в буферах уже имеют метки времени в едином формате `[YYYY-MM-DD HH:MM:SS.mmm]`

### Риск 4: Нарушение обратной совместимости
**Митигация:** Оставить методы-обертки (`add_output()`) для обратной совместимости, но они будут использовать `universal_print()`

---

## ПРОВЕРОЧНЫЙ СПИСОК

### Перед началом рефакторинга:
- [ ] Создать резервную копию файла
- [ ] Проверить все места использования `timestamp=True` через grep
- [ ] Проверить все места использования `add_terminal_output()` через grep
- [ ] Проверить все места использования `_write_to_file()` через grep
- [ ] Проверить все места использования `GLOBAL_LOG_FILE` через grep
- [ ] Проверить все места использования `gui_callback()` через grep

### После рефакторинга:
- [ ] Проверить что GUI читает из буферов корректно
- [ ] Проверить что RAW и ANALYSIS потоки разделены правильно
- [ ] Проверить что GUI лог работает с флагом `gui_log=True`
- [ ] Проверить что файлы пишутся асинхронно (RAW и ANALYSIS отдельно)
- [ ] Проверить режимы отображения (raw/analysis/both)
- [ ] Проверить объединение потоков по времени в режиме "both"
- [ ] Проверить что **ВСЕ** сообщения имеют метки времени
- [ ] Проверить что нет параметра `timestamp=True` нигде в коде

---

## ПРИМЕЧАНИЯ

- **Метки времени:** Все сообщения ВСЕГДА получают метки времени через DualStreamLogger - флаг `timestamp=True` удален полностью
- **Единый источник:** Все данные только в буферах DualStreamLogger - никаких дублирующих массивов в GUI
- **GUI терминал:** Читает из буферов периодически (100 мс) - реальное время обеспечено
- **GUI лог:** Отдельный виджет через флаг `gui_log=True` - не путать с терминалом
- **Режим "both":** Объединяет потоки по времени через сортировку по меткам времени

---

## ТЕКУЩАЯ АРХИТЕКТУРА (для справки)

### Источники:
- `print()` → `universal_print()` → ANALYSIS поток
- `sys.stdout.write()` → `TerminalRedirector` → RAW поток
- `log_info/error/warning()` → ANALYSIS поток
- `run_process()` → RAW (необработанный) + ANALYSIS (обработанный)

### Буферы:
- `_raw_buffer` → RAW файл (apt_raw_*.log)
- `_analysis_buffer` → ANALYSIS файл (astra_automation_*.log)

### GUI:
- Терминал: читает из буферов (raw/analysis/both)
- Лог: через `gui_log=True` (отдельный виджет)

