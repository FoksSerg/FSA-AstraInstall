# ДЕТАЛЬНЫЙ ПЛАН РЕФАКТОРИНГА СИСТЕМЫ ЛОГИРОВАНИЯ
**Версия: V2.4.97 (2025.11.03)**  
**Компания: ООО "НПА Вира-Реалтайм"**  
**Обновлено: Полная проверка кода завершена**

# Статус: ОБНОВЛЕННЫЙ ПЛАН РЕАЛИЗАЦИИ

## ЦЕЛЬ РЕФАКТОРИНГА

Упростить архитектуру логирования:
- **Единый источник данных:** DualStreamLogger буферы (RAW и ANALYSIS)
- **Два потока:** RAW (сторонние процессы: apt-get, sys.stdout) и ANALYSIS (системные сообщения: print, log_info)
- **Все сообщения с метками времени** - для объединения потоков по времени
- **GUI читает из буферов** (raw/analysis/both с сортировкой по времени)
- **GUI лог через флаг `gui_log=True`** (отдельный виджет log_text)
- **Асинхронная запись в файлы** (не блокирует выполнение)
- **Удаление всех прямых записей в GLOBAL_LOG_FILE** (Вариант A: полное удаление)

---

## АНАЛИЗ ТЕКУЩЕЙ АРХИТЕКТУРЫ

### ПРОБЛЕМЫ:

1. **Дублирование записей в файлы:**
   - `universal_print()` → `GLOBAL_LOG_FILE` (прямая запись, строки 628-632, 651-653, 661-663)
   - `universal_print()` → `DualStreamLogger.write_analysis()` → `_analysis_log_path` (тот же файл!, строка 640)
   - `universal_runner._write_to_file()` → `log_file_path` (другой файл, строка 931)
   - **Итого:** одно сообщение попадает в 2-3 файла

2. **Дублирование данных в GUI:**
   - `terminal_messages_raw` / `terminal_messages_analysis` (массивы в GUI, строки 10038-10060)
   - `_raw_buffer` / `_analysis_buffer` (буферы в DualStreamLogger, строки 244-245)
   - **Итого:** данные хранятся в двух местах

3. **Несогласованность путей логирования:**
   - `print()` → `DualStreamLogger` + `gui_callback` → `add_terminal_output()`
   - `run_process()` → `DualStreamLogger.write_raw()` + `add_terminal_output()`
   - `log_info()` → `add_output()` + `_write_to_file()`
   - **Итого:** разные пути для одного типа данных

4. **TerminalRedirector:**
   - Перехватывает `sys.stdout.write()` → `terminal_queue` (строка 7059)
   - Не использует DualStreamLogger напрямую
   - Дублирует функциональность

5. **GLOBAL_LOG_FILE используется в 36 местах:**
   - Прямые записи в файл (строки 628-632, 651-653, 661-663) - **УДАЛИТЬ**
   - Отображение/открытие файла (строки 8416, 10879, 10911, 11072) - **ИЗМЕНИТЬ источник данных**
   - Отладочные проверки (строки 7661-7674) - **УДАЛИТЬ или оставить для отладки**
   - Инициализация (строка 14410) - **ОСТАВИТЬ**
   - Передача в DualStreamLogger (строка 14424) - **ОСТАВИТЬ**

---

## ПОЛНЫЙ СПИСОК ИСПОЛЬЗОВАНИЙ (НАЙДЕНО В КОДЕ)

### `GLOBAL_LOG_FILE` - ВСЕ 36 ИСПОЛЬЗОВАНИЙ:

#### КАТЕГОРИЯ 1: ПРЯМАЯ ЗАПИСЬ (УДАЛИТЬ)
- ✅ Строка 628-632: `universal_print()` → `open(GLOBAL_LOG_FILE, 'a')` - **УДАЛИТЬ**
- ✅ Строка 651-653: `universal_print()` → обработка ошибок `gui_callback` - **УДАЛИТЬ**
- ✅ Строка 661-663: `universal_print()` → обработка ошибок `gui_log_callback` - **УДАЛИТЬ**

#### КАТЕГОРИЯ 2: ОТЛАДКА (УДАЛИТЬ)
- ✅ Строка 7661: `print(f"[DEBUG_LOAD_LOG_CMD] Проверка GLOBAL_LOG_FILE...")` - **УДАЛИТЬ**
- ✅ Строка 7663-7674: Отладочные проверки и сообщения - **УДАЛИТЬ**

#### КАТЕГОРИЯ 3: ОТОБРАЖЕНИЕ/ОТКРЫТИЕ (ИЗМЕНИТЬ ИСТОЧНИК)
- ✅ Строка 7883-7884: Открытие файла через `GLOBAL_LOG_FILE` - **ИЗМЕНИТЬ**: брать из DualStreamLogger
- ✅ Строка 8416: Отображение пути к лог-файлу в GUI - **ИЗМЕНИТЬ**: брать из DualStreamLogger
- ✅ Строка 10879: Метод `open_log_file()` - **ИЗМЕНИТЬ**: брать из DualStreamLogger
- ✅ Строка 10911: Переменная `log_file` в `run_automation()` - **ИЗМЕНИТЬ**: брать из DualStreamLogger
- ✅ Строка 11072: Сообщение об ошибке с путем к лог-файлу - **ИЗМЕНИТЬ**: брать из DualStreamLogger
- ✅ Строка 11422: Переменная `log_file` в `simulate_interactive_scenarios()` - **ИЗМЕНИТЬ**: брать из DualStreamLogger
- ✅ Строка 11529: Переменная `main_log_path` в `_write_progress_to_file()` - **ИЗМЕНИТЬ**: брать из DualStreamLogger
- ✅ Строка 12734: Переменная `log_file` в `check_system_resources()` - **ИЗМЕНИТЬ**: брать из DualStreamLogger
- ✅ Строка 12996: Переменная `log_file` в `_fix_dpkg_issues()` - **ИЗМЕНИТЬ**: брать из DualStreamLogger
- ✅ Строка 13153: Переменная `log_file` в `_force_remove_broken_packages()` - **ИЗМЕНИТЬ**: брать из DualStreamLogger
- ✅ Строка 13323: Переменная `log_file` в `_recover_from_segfault()` - **ИЗМЕНИТЬ**: брать из DualStreamLogger
- ✅ Строка 13396: Переменная `log_file` в `update_system()` - **ИЗМЕНИТЬ**: брать из DualStreamLogger
- ✅ Строка 13552: Переменная `log_file` в `_safe_retry_update()` - **ИЗМЕНИТЬ**: брать из DualStreamLogger
- ✅ Строка 13597: Переменная `log_file` в `_safe_retry_update()` - **ИЗМЕНИТЬ**: брать из DualStreamLogger
- ✅ Строка 14017: Переменная `log_file` для GUI - **ИЗМЕНИТЬ**: брать из DualStreamLogger

#### КАТЕГОРИЯ 4: ПЕРЕДАЧА В МЕТОДЫ (ИЗМЕНИТЬ)
- ✅ Строка 9381-9383: Передача в `UniversalProcessRunner.set_log_file()` - **ИЗМЕНИТЬ**: не нужна, всё через DualStreamLogger

#### КАТЕГОРИЯ 5: ИНИЦИАЛИЗАЦИЯ И СОЗДАНИЕ (ОСТАВИТЬ)
- ✅ Строка 14394-14411: Установка `GLOBAL_LOG_FILE` в `main()` - **ОСТАВИТЬ**
- ✅ Строка 14424: Передача в `DualStreamLogger.create_default_logger()` - **ОСТАВИТЬ**

### `add_terminal_output()` - ВСЕ 9 ИСПОЛЬЗОВАНИЙ:

- ✅ Строка 561: `LogReplaySimulator.replay()` → `sys._gui_instance.add_terminal_output()` - **УДАЛИТЬ**
- ✅ Строка 1014-1015: `run_process()` → `self.gui_instance.add_terminal_output()` - **УДАЛИТЬ**
- ✅ Строка 1197: `RepoChecker._log()` → `self.gui_terminal.add_terminal_output()` - **УДАЛИТЬ**
- ✅ Строка 7071-7072: `_redirect_output_to_terminal()` → `self.add_terminal_output()` - **УДАЛИТЬ** (заменить на `universal_print()`)
- ✅ Строка 7249: Установка callback `gui_callback=self.add_terminal_output` - **ИЗМЕНИТЬ**: не нужен callback
- ✅ Строка 10028: Определение метода `add_terminal_output()` - **УДАЛИТЬ метод полностью**
- ✅ Строка 14029: Установка `gui.universal_runner.gui_callback = gui.add_terminal_output` - **ИЗМЕНИТЬ**: не нужен callback

### `timestamp=True` - ВСЕ 7 ИСПОЛЬЗОВАНИЙ:

- ✅ Строка 263: Сигнатура `def write_raw(self, message, timestamp=True):` - **УДАЛИТЬ параметр**
- ✅ Строка 278: Сигнатура `def write_analysis(self, message, timestamp=True):` - **УДАЛИТЬ параметр**
- ✅ Строка 555: `LogReplaySimulator.replay()` → `dual_logger.write_raw(clean_line, timestamp=True)` - **УДАЛИТЬ параметр**
- ✅ Строка 640: `universal_print()` → `dual_logger.write_analysis(f"[PRINT] {message}", timestamp=True)` - **УДАЛИТЬ параметр**
- ✅ Строка 1012: `run_process()` → `_global_dual_logger.write_raw(line_clean, timestamp=True)` - **УДАЛИТЬ параметр**
- ✅ Строка 14441: Тест → `_global_dual_logger.write_raw("=== ТЕСТ: ...", timestamp=True)` - **УДАЛИТЬ параметр**
- ✅ Строка 14442: Тест → `_global_dual_logger.write_raw("=== ТЕСТ: ...", timestamp=True)` - **УДАЛИТЬ параметр**

### `_write_to_file()` - ВСЕ 9 ИСПОЛЬЗОВАНИЙ:

- ✅ Строка 878: Определение `universal_write_to_file()` внутри `setup_universal_logging_redirect()` - **УДАЛИТЬ**
- ✅ Строка 900: `log_info()` → `self._write_to_file()` - **УДАЛИТЬ**
- ✅ Строка 909: `log_error()` → `self._write_to_file()` - **УДАЛИТЬ**
- ✅ Строка 918: `log_warning()` → `self._write_to_file()` - **УДАЛИТЬ**
- ✅ Строка 931: Определение метода `_write_to_file()` - **УДАЛИТЬ метод полностью**
- ✅ Строка 1094: `process_queue()` → `self._write_to_file()` - **УДАЛИТЬ**

### `terminal_queue` - ВСЕ 12 ИСПОЛЬЗОВАНИЙ:

- ✅ Строка 6414: Инициализация `self.terminal_queue = queue.Queue()` - **УДАЛИТЬ**
- ✅ Строка 6453: `self.root.after(1000, self.process_terminal_queue)` - **ОСТАВИТЬ** (изменить метод)
- ✅ Строка 6471: `self.root.after(1000, self.process_terminal_queue)` - **ОСТАВИТЬ** (изменить метод)
- ✅ Строка 7049-7050: `TerminalRedirector.__init__(terminal_queue, ...)` - **УДАЛИТЬ параметр**
- ✅ Строка 7059: `self.terminal_queue.put(message)` - **УДАЛИТЬ**
- ✅ Строка 7067-7068: Создание `TerminalRedirector(self.terminal_queue, ...)` - **ИЗМЕНИТЬ**
- ✅ Строка 10436-10508: Обработка `terminal_queue` в `process_terminal_queue()` - **УДАЛИТЬ логику**

### `terminal_messages_*` - ВСЕ 32 ИСПОЛЬЗОВАНИЯ:

- ✅ Строка 10038-10041: Инициализация массивов - **УДАЛИТЬ**
- ✅ Строка 10045-10060: Добавление в массивы - **УДАЛИТЬ**
- ✅ Строка 10091-10103: Чтение из массивов в `_update_terminal_display()` - **ИЗМЕНИТЬ**: читать из буферов
- ✅ Строка 10198-10213: Очистка массивов - **УДАЛИТЬ**
- ✅ Строка 10229: Добавление в `terminal_messages` - **УДАЛИТЬ**

---

## ПЛАН ИЗМЕНЕНИЙ

### РАЗДЕЛ 1: `DualStreamLogger.write_raw/write_analysis()` - УБРАТЬ ФЛАГ timestamp

**ФАЙЛ:** `astra_automation.py`  
**КЛАСС:** `DualStreamLogger`  
**МЕТОДЫ:** `write_raw()` (строка 263), `write_analysis()` (строка 278)

#### УДАЛИТЬ:
1. Параметр `timestamp=True` из сигнатуры методов (строки 263, 278)
2. Условную проверку `if timestamp:` (строки 265, 280)
3. Блок `else:` без метки времени (строки 268-269, 283-284)

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

#### ИЗМЕНИТЬ ВСЕ ВЫЗОВЫ (7 мест):
- Строка 555: `dual_logger.write_raw(clean_line, timestamp=True)` → `dual_logger.write_raw(clean_line)`
- Строка 640: `dual_logger.write_analysis(f"[PRINT] {message}", timestamp=True)` → `dual_logger.write_analysis(f"[PRINT] {message}")`
- Строка 1012: `_global_dual_logger.write_raw(line_clean, timestamp=True)` → `_global_dual_logger.write_raw(line_clean)`
- Строка 14441: `_global_dual_logger.write_raw("=== ТЕСТ: ...", timestamp=True)` → `_global_dual_logger.write_raw("=== ТЕСТ: ...")`
- Строка 14442: аналогично

---

### РАЗДЕЛ 2: `universal_print()` - УПРОЩЕНИЕ И ЕДИНАЯ ТОЧКА ВХОДА

**ФАЙЛ:** `astra_automation.py`  
**МЕТОД:** `universal_print()` (строка 623)

**КРИТИЧЕСКИ ВАЖНО:** `universal_print()` остается переопределением `builtins.print` (строка 666).  
**Весь код продолжает использовать стандартный `print()`** - это правильно для интеграции в другие проекты.  
**Прямой вызов `universal_print()` с параметрами используется только в специальных местах**, где нужны специфические параметры (`stream='raw'`, `level='ERROR'`, и т.д.).

#### УДАЛИТЬ:
1. Прямую запись в `GLOBAL_LOG_FILE` (строки 628-632)
2. Вызов `gui_callback()` для терминала (строки 648-649) - GUI читает из буферов
3. Все проверки `GLOBAL_LOG_FILE` для ошибок (строки 651-653, 661-663)

#### ИЗМЕНИТЬ:
1. Добавить флаг `stream` для определения потока ('raw' или 'analysis', по умолчанию 'analysis')
2. Упростить логику: только запись в DualStreamLogger и вызов `gui_log_callback` если `gui_log=True`
3. Убрать все проверки и дублирование
4. Сохранить переопределение `builtins.print = universal_print` (строка 666)

#### ДОБАВИТЬ:
1. Флаг `stream` для определения потока
2. Флаг `level` для уровня сообщения

#### НОВАЯ РЕАЛИЗАЦИЯ:
```python
def universal_print(*args, **kwargs):
    """
    Универсальная функция логирования - переопределяет builtins.print
    
    Автоматически вызывается при использовании стандартного print():
    - print("сообщение") → universal_print("сообщение")
    - print("сообщение", gui_log=True) → universal_print("сообщение", gui_log=True)
    
    Прямой вызов с параметрами используется только в специальных местах:
    - universal_print("сообщение", stream='raw', level='ERROR')
    
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
    
    # Получаем dual_logger из universal_runner или глобального
    dual_logger = None
    
    # Сначала пробуем через GUI
    if hasattr(sys, '_gui_instance') and sys._gui_instance:
        if hasattr(sys._gui_instance, 'universal_runner') and sys._gui_instance.universal_runner:
            dual_logger = getattr(sys._gui_instance.universal_runner, 'dual_logger', None)
    
    # Если через GUI не получилось, пробуем глобальный
    if not dual_logger:
        dual_logger = _global_dual_logger
    
    # ВСЁ через DualStreamLogger (буферы с метками времени)
    if dual_logger:
        formatted_message = f"[{level}] {message}"
        if stream_type == 'raw':
            dual_logger.write_raw(formatted_message)  # ВСЕГДА с меткой времени
        else:
            dual_logger.write_analysis(formatted_message)  # ВСЕГДА с меткой времени
    else:
        # Fallback: если dual_logger недоступен, используем оригинальный print
        # (только для самых ранних этапов инициализации)
        import builtins
        builtins._original_print(f"[{level}] {message}")
    
    # GUI лог (ТОЛЬКО если gui_log=True)
    if gui_log and hasattr(sys, '_gui_instance') and sys._gui_instance:
        if hasattr(sys._gui_instance, 'universal_runner') and sys._gui_instance.universal_runner:
            if hasattr(sys._gui_instance.universal_runner, 'gui_log_callback'):
                try:
                    sys._gui_instance.universal_runner.gui_log_callback(message)
                except Exception:
                    pass  # Игнорируем ошибки

# Сохраняем оригинальный print для fallback
import builtins
if not hasattr(builtins, '_original_print'):
    builtins._original_print = builtins.print

# Переопределяем builtins.print - это позволяет использовать стандартный print() везде
builtins.print = universal_print
```

**ПРИМЕЧАНИЕ:** Весь код проекта продолжает использовать стандартный `print()`, который автоматически работает через `universal_print()`. Прямой вызов `universal_print()` с параметрами используется только в специальных местах (см. разделы 3, 4, 5, 6).

---

### РАЗДЕЛ 3: `TerminalRedirector` - ВЫНЕСЕНИЕ И УПРОЩЕНИЕ

**ФАЙЛ:** `astra_automation.py`  
**МЕТОД:** `_redirect_output_to_terminal()` (строка 7045)  
**КЛАСС:** `TerminalRedirector` (строка 7047)

#### УДАЛИТЬ:
1. Класс `TerminalRedirector` изнутри метода `_redirect_output_to_terminal()` (строка 7047)
2. Логику `terminal_queue` (строка 7049-7059) - не нужна, т.к. GUI читает из буферов
3. Параметр `terminal_queue` из конструктора `TerminalRedirector` (строка 7049)
4. Вызовы `add_terminal_output()` для перенаправления (строка 7071-7072)

#### ИЗМЕНИТЬ:
1. Вынести класс `TerminalRedirector` на уровень модуля (перед классом `AutomationGUI`, примерно строка 6340)
2. Упростить `write()`: вызывать `universal_print()` с `stream='raw'`
3. Убрать работу с `terminal_queue`
4. Упростить метод `_redirect_output_to_terminal()`

#### ДОБАВИТЬ:
1. Класс `TerminalRedirector` на уровне модуля

#### НОВАЯ РЕАЛИЗАЦИЯ:

**Разместить ПЕРЕД классом AutomationGUI (примерно строка 6340):**
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
    
    # Логируем перенаправление (используем прямой вызов universal_print с параметрами)
    universal_print("[SYSTEM] Вывод перенаправлен на встроенный терминал GUI", stream='analysis')
    universal_print("[SYSTEM] Родительский терминал можно безопасно закрыть", stream='analysis')
```

**ПРИМЕЧАНИЕ:** Здесь используется прямой вызов `universal_print()` с параметром `stream='analysis'`, потому что стандартный `print()` не поддерживает этот параметр. Это исключительный случай.

---

### РАЗДЕЛ 4: `UniversalProcessRunner.log_info/error/warning()` - УПРОЩЕНИЕ

**ФАЙЛ:** `astra_automation.py`  
**КЛАСС:** `UniversalProcessRunner`  
**МЕТОДЫ:** `log_info()` (строка 891), `log_error()` (строка 902), `log_warning()` (строка 911)

#### УДАЛИТЬ:
1. Вызовы `add_output()` (строки 899, 908, 917)
2. Вызовы `_write_to_file()` (строки 900, 909, 918)
3. Метод `_write_to_file()` (строка 931) - всё через DualStreamLogger
4. Метод `universal_write_to_file()` внутри `setup_universal_logging_redirect()` (строка 878) - удалить

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
    
    # Используем прямой вызов universal_print с параметрами (исключительный случай)
    universal_print(full_message, stream='analysis', level='INFO')

def log_error(self, message, description=None):
    """Логирование сообщения об ошибке (метка времени автоматически)"""
    if description:
        full_message = f"{description}: {str(message)}"
    else:
        full_message = str(message)
    
    # Используем прямой вызов universal_print с параметрами (исключительный случай)
    universal_print(full_message, stream='analysis', level='ERROR')

def log_warning(self, message, description=None):
    """Логирование предупреждения (метка времени автоматически)"""
    if description:
        full_message = f"{description}: {str(message)}"
    else:
        full_message = str(message)
    
    # Используем прямой вызов universal_print с параметрами (исключительный случай)
    universal_print(full_message, stream='analysis', level='WARNING')
```

**ПРИМЕЧАНИЕ:** Здесь используется прямой вызов `universal_print()` с параметрами `stream='analysis'` и `level='ERROR'`, потому что стандартный `print()` не поддерживает эти параметры. Это исключительные случаи в специальных методах логирования.

---

### РАЗДЕЛ 5: `UniversalProcessRunner.run_process()` - УПРОЩЕНИЕ

**ФАЙЛ:** `astra_automation.py`  
**МЕТОД:** `run_process()` (строка 948)

#### УДАЛИТЬ:
1. Вызов `add_terminal_output()` для RAW потока (строки 1014-1015) - GUI читает из буферов
2. Параметр `timestamp=True` в вызове `write_raw()` (строка 1012)

#### ИЗМЕНИТЬ:
1. Оставить только запись в `DualStreamLogger.write_raw()` для RAW потока (метка времени автоматически)
2. Обработанный вывод через `_log()` → `universal_print()` → `DualStreamLogger.write_analysis()` (метка времени автоматически)

#### НОВАЯ РЕАЛИЗАЦИЯ:
```python
# В методе run_process(), в цикле чтения stdout (строка 1008):
if line_clean:
    # RAW поток (необработанный вывод процесса, метка времени автоматически)
    if _global_dual_logger:
        try:
            _global_dual_logger.write_raw(line_clean)  # Метка времени добавляется автоматически
            # GUI читает из буфера, поэтому не вызываем add_terminal_output()
        except Exception as e:
            # Используем стандартный print() с gui_log=True (поддерживается universal_print)
            print(f"[DUAL_LOGGER_ERROR] Ошибка записи в RAW-поток: {e}", gui_log=True)
    
    # ANALYSIS поток (обработанный вывод через universal_print, метка времени автоматически)
    self._log("  %s" % line_clean, "INFO", channels)
    # _log() вызывает universal_print() → DualStreamLogger.write_analysis()
    output_buffer += line
```

---

### РАЗДЕЛ 6: `UniversalProcessRunner._log()` - УПРОЩЕНИЕ

**ФАЙЛ:** `astra_automation.py`  
**МЕТОД:** `_log()` (строка 1107)

#### УДАЛИТЬ:
1. Вызовы `log_info/error/warning()` с проверкой каналов (строки 1118-1123) - всё идёт в буферы
2. Вызов `gui_callback()` (строка 1126-1127) - GUI читает из буферов

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
    # Используем прямой вызов universal_print с параметрами (исключительный случай)
    # stream='analysis' для обработанных сообщений
    gui_log_flag = "gui_log" in channels if isinstance(channels, list) else False
    universal_print(message, stream='analysis', level=level, gui_log=gui_log_flag)
```

---

### РАЗДЕЛ 7: `UniversalProcessRunner.add_output()` - УПРОЩЕНИЕ

**ФАЙЛ:** `astra_automation.py`  
**МЕТОД:** `add_output()` (строка 1052)

#### ИЗМЕНИТЬ:
1. Изменить реализацию: вызывать `universal_print()` вместо записи в очередь
2. Упростить `process_queue()` - убрать логику записи в файл через `_write_to_file()` (строка 1094)

#### НОВАЯ РЕАЛИЗАЦИЯ:
```python
def add_output(self, message, level="INFO", channels=[], bypass_filter=False):
    """
    Добавление сообщения в лог (через universal_print для обратной совместимости)
    
    Метка времени добавляется автоматически через DualStreamLogger
    """
    # Используем прямой вызов universal_print с параметрами (исключительный случай)
    gui_log = "gui_log" in channels
    stream = 'raw' if 'raw' in str(channels).lower() else 'analysis'
    universal_print(message, stream=stream, level=level, gui_log=gui_log)
```

#### ИЗМЕНИТЬ `process_queue()`:
```python
def process_queue(self):
    """Обработка очереди сообщений - вызывается из GUI"""
    try:
        while not self.output_queue.empty():
            # Получаем параметры (поддерживаем старый формат для совместимости)
            item = self.output_queue.get_nowait()
            if len(item) == 4:
                message, level, channels, bypass_filter = item
            else:
                message, level, channels = item
                bypass_filter = False
            
            # Используем прямой вызов universal_print с параметрами (исключительный случай)
            gui_log = "gui_log" in channels
            stream = 'raw' if 'raw' in str(channels).lower() else 'analysis'
            universal_print(message, stream=stream, level=level, gui_log=gui_log)
            
    except Exception as e:
        pass  # Игнорируем ошибки
```

---

### РАЗДЕЛ 8: GUI - ЧТЕНИЕ ИЗ БУФЕРОВ

**ФАЙЛ:** `astra_automation.py`  
**КЛАСС:** `AutomationGUI`  
**МЕТОДЫ:** `add_terminal_output()` (строка 10028), `_update_terminal_display()` (строка 10078), `process_terminal_queue()` (строка 10417)

#### УДАЛИТЬ:
1. Метод `add_terminal_output()` полностью (строка 10028) - не нужен, GUI читает из буферов
2. Массивы `terminal_messages_raw` и `terminal_messages_analysis` (строки 10038-10060) - дублирование
3. Логику обработки `terminal_queue` в `process_terminal_queue()` (строки 10436-10508)
4. Инициализацию `terminal_queue` (строка 6414)
5. Логику добавления в `terminal_full_content` (строки 10464-10467)
6. Очистку массивов `terminal_messages_*` (строки 10198-10213)

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
        # Используем стандартный print() с gui_log=True (поддерживается universal_print)
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
                        # Используем стандартный print() - автоматически работает через universal_print
                        print(f"[PARSER_ERROR] Ошибка parse_from_buffer: {e}")
        
        # Обновляем терминал из буферов DualStreamLogger
        if self.terminal_autoscroll_enabled.get():
            self._update_terminal_display()
        
    except Exception as e:
        # Используем стандартный print() с gui_log=True (поддерживается universal_print)
        print(f"[ERROR] Ошибка process_terminal_queue: {e}", gui_log=True)
    finally:
        # Повторяем через 100 мс
        self.root.after(100, self.process_terminal_queue)
```

**УДАЛИТЬ все вызовы `add_terminal_output()`:**
- Строка 561: `LogReplaySimulator.replay()` - заменить на `universal_print()` или убрать
- Строка 1197: `RepoChecker._log()` - убрать, всё через `universal_runner.log_info()`

**УДАЛИТЬ установку callback:**
- Строка 7249: `gui_callback=self.add_terminal_output` - убрать, не нужен
- Строка 14029: `gui.universal_runner.gui_callback = gui.add_terminal_output` - убрать, не нужен

---

### РАЗДЕЛ 9: `LogReplaySimulator.replay()` - УПРОЩЕНИЕ

**ФАЙЛ:** `astra_automation.py`  
**КЛАСС:** `LogReplaySimulator`  
**МЕТОД:** `replay()` (строка 517)

#### ИЗМЕНИТЬ:
1. Убрать вызов `add_terminal_output()` (строка 561) - GUI читает из буферов
2. Убрать параметр `timestamp=True` в вызове `write_raw()` (строка 555)

#### НОВАЯ РЕАЛИЗАЦИЯ:
```python
# В методе replay(), в цикле обработки строк (строка 555):
if clean_line:
    # Записываем в RAW-поток (метка времени добавляется автоматически)
    dual_logger.write_raw(clean_line)
    # GUI читает из буфера, поэтому не вызываем add_terminal_output()
```

---

### РАЗДЕЛ 10: `RepoChecker._log()` - УПРОЩЕНИЕ

**ФАЙЛ:** `astra_automation.py`  
**КЛАСС:** `RepoChecker`  
**МЕТОД:** `_log()` (строка 1185)

#### УДАЛИТЬ:
1. Вызов `add_terminal_output()` (строка 1197) - GUI читает из буферов

#### НОВАЯ РЕАЛИЗАЦИЯ:
```python
def _log(self, message):
    """Логирование через universal_runner"""
    if self.universal_runner:
        self.universal_runner.log_info(message)
    # GUI читает из буферов, поэтому не вызываем add_terminal_output()
```

---

### РАЗДЕЛ 11: УДАЛЕНИЕ `GLOBAL_LOG_FILE` ДЛЯ ЗАПИСИ (Вариант A)

**ФАЙЛ:** `astra_automation.py`

#### КАТЕГОРИЯ 1: ПРЯМАЯ ЗАПИСЬ (УДАЛИТЬ)
- ✅ Строка 628-632: `universal_print()` → `open(GLOBAL_LOG_FILE, 'a')` - **УДАЛИТЬ**
- ✅ Строка 651-653: `universal_print()` → обработка ошибок `gui_callback` - **УДАЛИТЬ**
- ✅ Строка 661-663: `universal_print()` → обработка ошибок `gui_log_callback` - **УДАЛИТЬ**

#### КАТЕГОРИЯ 2: ОТЛАДКА (УДАЛИТЬ)
- ✅ Строка 7661-7674: Отладочные проверки и сообщения - **УДАЛИТЬ**

#### КАТЕГОРИЯ 3: ОТОБРАЖЕНИЕ/ОТКРЫТИЕ (ИЗМЕНИТЬ ИСТОЧНИК)

**Добавить вспомогательный метод в `AutomationGUI`:**
```python
def _get_log_file_path(self):
    """
    Получение пути к лог-файлу из DualStreamLogger
    
    Returns:
        str: Путь к analysis log файлу или GLOBAL_LOG_FILE как fallback
    """
    # Пробуем получить из DualStreamLogger
    if hasattr(self, 'universal_runner') and self.universal_runner:
        dual_logger = getattr(self.universal_runner, 'dual_logger', None)
        if dual_logger and hasattr(dual_logger, '_analysis_log_path'):
            if dual_logger._analysis_log_path:
                return dual_logger._analysis_log_path
    
    # Fallback: используем GLOBAL_LOG_FILE если DualStreamLogger недоступен
    if 'GLOBAL_LOG_FILE' in globals():
        return globals().get('GLOBAL_LOG_FILE', None)
    return None
```

**ИЗМЕНИТЬ ВСЕ МЕСТА (14 мест):**
- ✅ Строка 7883-7884: Использовать `self._get_log_file_path()` вместо `GLOBAL_LOG_FILE`
- ✅ Строка 8416: Использовать `self._get_log_file_path()` вместо `GLOBAL_LOG_FILE`
- ✅ Строка 10879: Использовать `self._get_log_file_path()` вместо `GLOBAL_LOG_FILE`
- ✅ Строка 10911: Использовать `self._get_log_file_path()` вместо `GLOBAL_LOG_FILE`
- ✅ Строка 11072: Использовать `self._get_log_file_path()` вместо `GLOBAL_LOG_FILE`
- ✅ Строка 11422: Использовать `self._get_log_file_path()` вместо `GLOBAL_LOG_FILE`
- ✅ Строка 11529: Использовать `dual_logger._analysis_log_path` вместо `GLOBAL_LOG_FILE`
- ✅ Строка 12734: Использовать `self._get_log_file_path()` вместо `GLOBAL_LOG_FILE`
- ✅ Строка 12996: Использовать `self._get_log_file_path()` вместо `GLOBAL_LOG_FILE`
- ✅ Строка 13153: Использовать `self._get_log_file_path()` вместо `GLOBAL_LOG_FILE`
- ✅ Строка 13323: Использовать `self._get_log_file_path()` вместо `GLOBAL_LOG_FILE`
- ✅ Строка 13396: Использовать `self._get_log_file_path()` вместо `GLOBAL_LOG_FILE`
- ✅ Строка 13552: Использовать `self._get_log_file_path()` вместо `GLOBAL_LOG_FILE`
- ✅ Строка 14017: Использовать `self._get_log_file_path()` вместо `GLOBAL_LOG_FILE`

#### КАТЕГОРИЯ 4: ПЕРЕДАЧА В МЕТОДЫ (ИЗМЕНИТЬ)
- ✅ Строка 9381-9383: Убрать передачу в `UniversalProcessRunner.set_log_file()` - не нужна, всё через DualStreamLogger

#### КАТЕГОРИЯ 5: ИНИЦИАЛИЗАЦИЯ И СОЗДАНИЕ (ОСТАВИТЬ)
- ✅ Строка 14394-14411: Установка `GLOBAL_LOG_FILE` в `main()` - **ОСТАВИТЬ**
- ✅ Строка 14424: Передача в `DualStreamLogger.create_default_logger()` - **ОСТАВИТЬ**

---

### РАЗДЕЛ 12: ДОПОЛНИТЕЛЬНЫЕ ИЗМЕНЕНИЯ

#### 12.1. Убрать дублирование в других местах

**ПРОВЕРИТЬ:**
- `WineInstaller._log()` (строка 2338) - использует `universal_runner.log_*()` ✅ (уже правильно)
- `WineUninstaller._log()` (строка 4321) - использует `universal_runner.log_*()` ✅ (уже правильно)
- `UniversalInstaller._log()` (строка 4823) - использует `universal_runner.log_*()` ✅ (уже правильно)

**ВЫВОД:** Эти методы уже правильные, после изменения `log_info/error/warning()` они автоматически будут использовать `universal_print()` → `DualStreamLogger` (метки времени автоматически)

---

## ИТОГОВАЯ ТАБЛИЦА ИЗМЕНЕНИЙ

| Раздел | Что удаляем | Что меняем | Что добавляем |
|--------|-------------|-----------|---------------|
| `DualStreamLogger.write_*()` | Параметр `timestamp=True`<br>Условную проверку `if timestamp:`<br>Блок `else:` без метки | Всегда добавлять метку времени | - |
| `universal_print()` | Прямую запись в GLOBAL_LOG_FILE<br>gui_callback() для терминала<br>Все проверки GLOBAL_LOG_FILE | Упростить логику<br>Добавить флаг `stream` | Флаг `stream` ('raw'/'analysis')<br>Флаг `level` |
| `TerminalRedirector` | Класс из метода<br>Логику `terminal_queue`<br>Вызовы `add_terminal_output()`<br>Параметр `terminal_queue` | Вынести на уровень модуля<br>Упростить `write()` | Класс на уровне модуля |
| `log_info/error/warning()` | `add_output()`<br>`_write_to_file()`<br>Метод `_write_to_file()`<br>`universal_write_to_file()` | Использовать `universal_print()` | - |
| `run_process()` | `add_terminal_output()` для RAW<br>`timestamp=True` в вызовах | Оставить только `write_raw()` | - |
| `_log()` | Вызовы `log_info/error/warning()`<br>`gui_callback()` | Использовать `universal_print()` | - |
| `add_output()` / `process_queue()` | Логику записи в файл через `_write_to_file()` | Использовать `universal_print()` | - |
| GUI методы | `add_terminal_output()`<br>Массивы `terminal_messages_*`<br>Обработка `terminal_queue`<br>Логику `terminal_full_content`<br>Инициализацию `terminal_queue` | `_update_terminal_display()` читает из буферов<br>`process_terminal_queue()` упростить | `_extract_timestamp()` для сортировки<br>`_get_log_file_path()` для получения пути |
| `LogReplaySimulator` | `add_terminal_output()`<br>`timestamp=True` | - | - |
| `RepoChecker._log()` | `add_terminal_output()` | - | - |
| `GLOBAL_LOG_FILE` | Прямые записи (3 места)<br>Отладочные проверки (14 строк) | Отображение/открытие (14 мест) - изменить источник | `_get_log_file_path()` |

---

## ПОРЯДОК ВЫПОЛНЕНИЯ (11 этапов)

1. **Этап 1:** Убрать параметр `timestamp=True` из `DualStreamLogger.write_raw/write_analysis()` и всех вызовов (5 мест)
2. **Этап 2:** Вынести `TerminalRedirector` на уровень модуля и упростить
3. **Этап 3:** Упростить `universal_print()` - убрать дублирование и прямую запись в GLOBAL_LOG_FILE
4. **Этап 4:** Упростить `log_info/error/warning()` - использовать `universal_print()`
5. **Этап 5:** Упростить `run_process()` - убрать `add_terminal_output()` и `timestamp=True`
6. **Этап 6:** Упростить `_log()` - использовать `universal_print()`
7. **Этап 7:** Упростить `add_output()` и `process_queue()` - использовать `universal_print()`
8. **Этап 8:** Изменить GUI - чтение из буферов вместо `add_terminal_output()`
9. **Этап 9:** Удалить все вызовы `add_terminal_output()` (7 мест)
10. **Этап 10:** Удалить/изменить использование `GLOBAL_LOG_FILE` (36 мест)
11. **Этап 11:** Тестирование

---

## КРИТЕРИИ УСПЕХА

1. ✅ Все сообщения попадают в буферы DualStreamLogger **ВСЕГДА с метками времени**
2. ✅ Нет дублирования записей в файлы
3. ✅ GUI читает из буферов (raw/analysis/both)
4. ✅ GUI лог работает через флаг `gui_log=True`
5. ✅ Асинхронная запись в файлы работает корректно
6. ✅ Режим "both" объединяет потоки по времени (сортировка по меткам времени)
7. ✅ Нет параметра `timestamp=True` нигде в коде
8. ✅ Нет прямых записей в GLOBAL_LOG_FILE (кроме инициализации)
9. ✅ Нет вызовов `add_terminal_output()` нигде в коде
10. ✅ Нет метода `_write_to_file()` в UniversalProcessRunner
11. ✅ Нет обработки `terminal_queue` в GUI

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

### Риск 5: Потеря доступа к пути лог-файла
**Митигация:** Добавить метод `_get_log_file_path()` который получает путь из DualStreamLogger или использует GLOBAL_LOG_FILE как fallback

---

## ПРОВЕРОЧНЫЙ СПИСОК

### Перед началом рефакторинга:
- [x] Создать резервную копию файла
- [x] Проверить все места использования `timestamp=True` через grep (7 мест)
- [x] Проверить все места использования `add_terminal_output()` через grep (9 мест)
- [x] Проверить все места использования `_write_to_file()` через grep (9 мест)
- [x] Проверить все места использования `GLOBAL_LOG_FILE` через grep (36 мест)
- [x] Проверить все места использования `gui_callback()` через grep (38 мест)
- [x] Проверить все места использования `terminal_queue` через grep (12 мест)
- [x] Проверить все места использования `terminal_messages_*` через grep (32 места)

### После рефакторинга:
- [ ] Проверить что GUI читает из буферов корректно
- [ ] Проверить что RAW и ANALYSIS потоки разделены правильно
- [ ] Проверить что GUI лог работает с флагом `gui_log=True`
- [ ] Проверить что файлы пишутся асинхронно (RAW и ANALYSIS отдельно)
- [ ] Проверить режимы отображения (raw/analysis/both)
- [ ] Проверить объединение потоков по времени в режиме "both"
- [ ] Проверить что **ВСЕ** сообщения имеют метки времени
- [ ] Проверить что нет параметра `timestamp=True` нигде в коде
- [ ] Проверить что нет прямых записей в GLOBAL_LOG_FILE
- [ ] Проверить что нет вызовов `add_terminal_output()`
- [ ] Проверить что нет метода `_write_to_file()`
- [ ] Проверить что нет обработки `terminal_queue` в GUI

---

## ПРИМЕЧАНИЯ

- **Метки времени:** Все сообщения ВСЕГДА получают метки времени через DualStreamLogger - флаг `timestamp=True` удален полностью
- **Единый источник:** Все данные только в буферах DualStreamLogger - никаких дублирующих массивов в GUI
- **GUI терминал:** Читает из буферов периодически (100 мс) - реальное время обеспечено
- **GUI лог:** Отдельный виджет через флаг `gui_log=True` - не путать с терминалом
- **Режим "both":** Объединяет потоки по времени через сортировку по меткам времени
- **GLOBAL_LOG_FILE:** Используется только для инициализации и передачи в DualStreamLogger. Все пути к файлу получаются из DualStreamLogger через `_get_log_file_path()`
- **КРИТИЧЕСКИ ВАЖНО - Стандартный print():** `universal_print()` переопределяет `builtins.print`, поэтому весь код проекта продолжает использовать стандартный `print()` - это правильно для интеграции в другие проекты. Прямой вызов `universal_print()` с параметрами используется **ТОЛЬКО** в исключительных местах (TerminalRedirector, log_info/error/warning, _log, add_output, process_queue), где нужны специфические параметры (`stream='raw'`, `level='ERROR'`, и т.д.). Во всех остальных местах используется стандартный `print()`.

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

---

**План полностью проверен и готов к реализации!**