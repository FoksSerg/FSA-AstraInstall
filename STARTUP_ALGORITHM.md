# Версия: V2.5.118 (2025.11.03)

# АЛГОРИТМ ГАРАНТИРОВАННОГО ЗАПУСКА FSA-AstraInstall

## 🎯 ЦЕЛЬ
Гарантированный запуск и завершение обновления системы даже на "чистом" Linux без настроенных репозиториев и GUI компонентов.

## 📋 ПРИНЦИПЫ

1. **Автоматический fallback**: GUI → CONSOLE если нет возможности запустить GUI
2. **Проверка кодов возврата**: Реальная проверка успешности операций
3. **Универсальность**: Работа с разными названиями пакетов (python3-tk, python3-tkinter, tk)
4. **Гарантия завершения**: Система ВСЕГДА обновится, даже если GUI не запустился
5. **Установка GUI после обновления**: После обновления репозиториев устанавливаем GUI пакеты

---

## 🔄 ЭТАП 1: ИНИЦИАЛИЗАЦИЯ (bash: astra_install.sh)

### 1.1. Проверка и получение прав root
```bash
if [ "$EUID" -ne 0 ]; then
    exec sudo -E bash "$0" "$@"
fi
```
**Результат:** Скрипт всегда работает с правами root

### 1.2. Синхронизация системного времени
```bash
- Проверка флага /var/run/fsa-time-synced
- timedatectl set-ntp true ИЛИ ntpdate
- Создание флага после успеха
```
**Результат:** Корректное время для работы с репозиториями

### 1.3. Настройка переменных окружения
```bash
export DEBIAN_FRONTEND=noninteractive
export DEBIAN_PRIORITY=critical
export APT_LISTCHANGES_FRONTEND=none
```
**Результат:** Подавление интерактивных запросов (уровень 1)

### 1.4. Определение переменных для dpkg
```bash
DPKG_OPTS="-o Dpkg::Options::=--force-confdef \
           -o Dpkg::Options::=--force-confold \
           -o Dpkg::Options::=--force-confmiss"
```
**Результат:** Опции для всех команд apt-get (уровень 2)

### 1.5. Проверка минимальных требований
```bash
- Python 3 установлен? (python3 --version)
- Версия Python >= 3.5?
```
**Результат:** ❌ Если Python нет → КРИТИЧЕСКАЯ ОШИБКА, выход

---

## 🔄 ЭТАП 2: ОПРЕДЕЛЕНИЕ РЕЖИМА ЗАПУСКА (bash)

### 2.1. Проверка аргументов командной строки
```bash
if [ "--console" in "$@" ]; then
    CONSOLE_MODE=true  # Принудительный консольный режим
    START_MODE="console_forced"
    → Переход к ЭТАПУ 3B
fi
```

### 2.2. Функция: Проверка наличия tkinter
```bash
check_tkinter_available() {
    if python3 -c "import tkinter" 2>/dev/null; then
        return 0  # tkinter доступен
    else
        return 1  # tkinter недоступен
    fi
}
```

### 2.3. Функция: Проверка доступности репозиториев
```bash
check_repos_available() {
    # Проверяем есть ли хоть один НЕ-cdrom репозиторий
    if grep -v "^#" /etc/apt/sources.list | \
       grep -v "cdrom:" | \
       grep "^deb" >/dev/null 2>&1; then
        return 0  # Репозитории есть
    else
        return 1  # Только cdrom или пусто
    fi
}
```

### 2.4. Функция: Поиск пакета tkinter в репозиториях
```bash
find_tkinter_package() {
    # Список возможных названий пакетов
    TKINTER_PACKAGES=("python3-tk" "python3-tkinter" "tk")
    
    for pkg in "${TKINTER_PACKAGES[@]}"; do
        if apt-cache show "$pkg" >/dev/null 2>&1; then
            echo "$pkg"  # Возвращаем первый найденный
            return 0
        fi
    done
    
    return 1  # Ни один пакет не найден
}
```

### 2.5. ЛОГИКА ВЫБОРА РЕЖИМА
```
┌─────────────────────────────────────────┐
│ Проверка: check_tkinter_available()    │
└───────────────┬─────────────────────────┘
                │
        ┌───────┴────────┐
        │                │
       ДА               НЕТ
        │                │
        ▼                ▼
    ┌───────┐    ┌──────────────────┐
    │  GUI  │    │ Проверка: repos? │
    │ READY │    └────────┬─────────┘
    └───┬───┘             │
        │         ┌───────┴────────┐
        │         │                │
        │        ДА               НЕТ
        │         │                │
        │         ▼                ▼
        │  ┌──────────────┐  ┌──────────────┐
        │  │ Есть пакет?  │  │   CONSOLE    │
        │  │find_tkinter()│  │   FORCED     │
        │  └──────┬───────┘  └──────┬───────┘
        │         │                 │
        │   ┌─────┴──────┐          │
        │   │            │          │
        │  ДА           НЕТ         │
        │   │            │          │
        │   ▼            ▼          │
        │ ┌────┐    ┌────────┐     │
        │ │GUI │    │CONSOLE │     │
        │ │+TK │    │FORCED  │     │
        │ └─┬──┘    └───┬────┘     │
        │   │           │          │
        └───┴───────────┴──────────┘
                    │
                    ▼
            [ЭТАП 3A или 3B]
```

### 2.6. Установка переменной START_MODE
```bash
START_MODE=""  # Определяет путь выполнения

if check_tkinter_available; then
    echo "[OK] tkinter найден - запуск GUI"
    START_MODE="gui_ready"
    
elif check_repos_available; then
    TKINTER_PKG=$(find_tkinter_package)
    if [ $? -eq 0 ]; then
        echo "[OK] Репозитории есть, пакет '$TKINTER_PKG' найден"
        echo "[i] Установим tkinter и запустим GUI"
        START_MODE="gui_install_first"
    else
        echo "[!] Репозитории есть, но пакет tkinter не найден"
        echo "[i] Принудительный консольный режим"
        START_MODE="console_forced"
        CONSOLE_MODE=true
    fi
else
    echo "[!] Нет рабочих репозиториев (только cdrom)"
    echo "[i] Принудительный консольный режим"
    echo "[i] После обновления системы GUI будет доступен"
    START_MODE="console_forced"
    CONSOLE_MODE=true
fi
```

---

## 🔄 ЭТАП 3A: УСТАНОВКА GUI КОМПОНЕНТОВ (если START_MODE = gui_install_first)

### 3A.1. Обновление списков пакетов
```bash
apt-get update -y 2>&1 | tee -a "$LOG_FILE"
EXIT_CODE=${PIPESTATUS[0]}
if [ $EXIT_CODE -ne 0 ]; then
    echo "[ERROR] Не удалось обновить списки пакетов (код: $EXIT_CODE)"
    echo "[i] Переключение на консольный режим"
    START_MODE="console_forced"
    CONSOLE_MODE=true
    → Переход к ЭТАПУ 3B
fi
```

### 3A.2. Функция: Установка tkinter с проверкой
```bash
install_tkinter_with_verification() {
    local TKINTER_PACKAGES=("python3-tk" "python3-tkinter" "tk")
    local INSTALLED=false
    
    for pkg in "${TKINTER_PACKAGES[@]}"; do
        echo "[TRY] Пробуем установить: $pkg"
        
        # Проверяем что пакет существует в репозиториях
        if ! apt-cache show "$pkg" >/dev/null 2>&1; then
            echo "[SKIP] Пакет $pkg не найден в репозиториях"
            continue
        fi
        
        echo "[INSTALL] Устанавливаем $pkg..."
        apt-get install -y $DPKG_OPTS "$pkg" 2>&1 | tee -a "$LOG_FILE"
        EXIT_CODE=${PIPESTATUS[0]}
        
        if [ $EXIT_CODE -eq 0 ]; then
            echo "[OK] Пакет $pkg установлен (код: 0)"
            
            # КРИТИЧНО: Проверяем что tkinter теперь импортируется
            if python3 -c "import tkinter" 2>/dev/null; then
                echo "[OK] tkinter успешно импортируется!"
                INSTALLED=true
                break
            else
                echo "[WARNING] Пакет $pkg установлен, но tkinter не импортируется"
            fi
        else
            echo "[ERROR] Не удалось установить $pkg (код: $EXIT_CODE)"
        fi
    done
    
    if [ "$INSTALLED" = true ]; then
        return 0
    else
        return 1
    fi
}
```

### 3A.3. Установка pip3 (опционально)
```bash
# pip3 не критичен для GUI, но полезен
if ! pip3 --version >/dev/null 2>&1; then
    apt-get install -y $DPKG_OPTS python3-pip 2>&1 | tee -a "$LOG_FILE"
    # Не проверяем код возврата - не критично
fi
```

### 3A.4. Исправление зависимостей
```bash
apt-get install -f -y $DPKG_OPTS 2>&1 | tee -a "$LOG_FILE"
```

### 3A.5. Финальная проверка перед запуском GUI
```bash
if ! python3 -c "import tkinter" 2>/dev/null; then
    echo "[ERROR] tkinter все еще недоступен после установки"
    echo "[i] Переключение на консольный режим"
    START_MODE="console_forced"
    CONSOLE_MODE=true
    → Переход к ЭТАПУ 3B
fi

echo "[OK] Все компоненты GUI готовы"
→ Переход к ЭТАПУ 4 (Запуск Python)
```

---

## 🔄 ЭТАП 3B: ПРОПУСК УСТАНОВКИ GUI (если START_MODE = console_forced)

```bash
echo ""
echo "[*] Консольный режим - GUI компоненты будут установлены ПОСЛЕ обновления"
echo "[i] Причина: нет рабочих репозиториев или tkinter недоступен"
echo ""
→ Переход к ЭТАПУ 4 (Запуск Python в консольном режиме)
```

---

## 🔄 ЭТАП 4: ЗАПУСК PYTHON СКРИПТА (bash)

### 4.1. Формирование аргументов
```bash
PYTHON_ARGS="--log-file $LOG_FILE"

if [ "$CONSOLE_MODE" = true ]; then
    PYTHON_ARGS="$PYTHON_ARGS --console"
fi

if [ "$DRY_RUN" = true ]; then
    PYTHON_ARGS="$PYTHON_ARGS --dry-run"
fi
```

### 4.2. Запуск в зависимости от режима
```bash
if [ "$CONSOLE_MODE" = true ]; then
    # Консольный режим - запуск в текущем терминале (синхронно)
    python3 astra_automation.py $PYTHON_ARGS
    PYTHON_EXIT_CODE=$?
    
else
    # GUI режим - запуск в фоне с автозакрытием терминала
    TERM_PID=$(ps -o ppid= -p $PPID | tr -d ' ')
    nohup python3 astra_automation.py $PYTHON_ARGS \
          --close-terminal "$TERM_PID" >/dev/null 2>&1 &
    PYTHON_EXIT_CODE=0
fi

exit $PYTHON_EXIT_CODE
```

---

## 🔄 ЭТАП 5: PYTHON - ИНИЦИАЛИЗАЦИЯ (astra_automation.py)

### 5.1. Парсинг аргументов
```python
parser = argparse.ArgumentParser()
parser.add_argument('--console', action='store_true')
parser.add_argument('--dry-run', action='store_true')
parser.add_argument('--log-file', type=str)
parser.add_argument('--close-terminal', type=str)
args = parser.parse_args()
```

### 5.2. Проверка доступности tkinter (для GUI режима)
```python
if not args.console:
    try:
        import tkinter
        gui_available = True
    except ImportError:
        print("[WARNING] GUI запрошен, но tkinter недоступен")
        print("[INFO] Автоматическое переключение на консольный режим")
        args.console = True
        gui_available = False
```

### 5.3. Выбор пути выполнения
```python
if args.console:
    → ЭТАП 6 (Консольный режим)
else:
    → ЭТАП 7 (GUI режим)
```

---

## 🔄 ЭТАП 6: PYTHON - КОНСОЛЬНЫЙ РЕЖИМ

### 6.1. Настройка репозиториев
```python
print("\n[REPOS] Настройка репозиториев...")
print("[i] Отключаем cdrom репозитории")
print("[i] Активируем только рабочие репозитории")

# Bash уже настроил репозитории, просто информируем
```

### 6.2. Обновление системы
```python
updater = SystemUpdater()

# Проверка ресурсов
if not updater.check_system_resources():
    print("[ERROR] Недостаточно ресурсов")
    sys.exit(1)

# Обновление
print("\n[UPDATE] Обновление системы...")
update_success = updater.update_system(args.dry_run)

if not update_success:
    print("[ERROR] Обновление системы завершилось с ошибками")
    sys.exit(1)
```

### 6.3. КРИТИЧНО: Установка GUI компонентов ПОСЛЕ обновления
```python
print("\n" + "="*60)
print("[POST-UPDATE] Установка GUI компонентов после обновления")
print("="*60)

# Теперь репозитории точно работают!
gui_success = install_gui_components_post_update()

if gui_success:
    print("[OK] GUI компоненты успешно установлены")
    print("[i] Теперь можно запустить GUI: ./astra_install.sh")
else:
    print("[WARNING] Не удалось установить GUI компоненты")
    print("[i] GUI может быть недоступен")
```

### 6.4. Функция установки GUI компонентов
```python
def install_gui_components_post_update():
    """Установка tkinter и pip3 после обновления системы"""
    import subprocess
    
    print("\n[GUI-INSTALL] Установка python3-tk...")
    
    # Пробуем разные названия пакетов
    tkinter_packages = ['python3-tk', 'python3-tkinter', 'tk']
    tkinter_installed = False
    
    for pkg in tkinter_packages:
        print(f"[TRY] Пробуем установить: {pkg}")
        
        # Проверяем наличие в репозиториях
        check_result = subprocess.run(
            ['apt-cache', 'show', pkg],
            capture_output=True,
            timeout=10
        )
        
        if check_result.returncode != 0:
            print(f"[SKIP] Пакет {pkg} не найден")
            continue
        
        # Устанавливаем
        install_result = subprocess.run(
            ['apt-get', 'install', '-y',
             '-o', 'Dpkg::Options::=--force-confdef',
             '-o', 'Dpkg::Options::=--force-confold',
             '-o', 'Dpkg::Options::=--force-confmiss',
             pkg],
            env={**os.environ, 
                 'DEBIAN_FRONTEND': 'noninteractive',
                 'DEBIAN_PRIORITY': 'critical',
                 'APT_LISTCHANGES_FRONTEND': 'none'},
            capture_output=True,
            timeout=300
        )
        
        if install_result.returncode == 0:
            print(f"[OK] Пакет {pkg} установлен")
            
            # Проверяем импорт
            try:
                import tkinter
                print("[OK] tkinter успешно импортируется!")
                tkinter_installed = True
                break
            except ImportError:
                print(f"[WARNING] Пакет {pkg} установлен, но tkinter не импортируется")
        else:
            print(f"[ERROR] Не удалось установить {pkg}")
    
    # Установка pip3 (не критично)
    print("\n[GUI-INSTALL] Установка python3-pip...")
    subprocess.run(
        ['apt-get', 'install', '-y',
         '-o', 'Dpkg::Options::=--force-confdef',
         '-o', 'Dpkg::Options::=--force-confold',
         '-o', 'Dpkg::Options::=--force-confmiss',
         'python3-pip'],
        env={**os.environ,
             'DEBIAN_FRONTEND': 'noninteractive',
             'DEBIAN_PRIORITY': 'critical',
             'APT_LISTCHANGES_FRONTEND': 'none'},
        capture_output=True,
        timeout=300
    )
    
    return tkinter_installed
```

### 6.5. Финальный отчет
```python
print("\n" + "="*60)
print("ОБНОВЛЕНИЕ ЗАВЕРШЕНО!")
print("="*60)
print(f"[OK] Система обновлена: {update_success}")
print(f"[OK] GUI компоненты: {gui_success}")
print("\n[NEXT] Следующие шаги:")
print("  1. Перезапустите для использования GUI: ./astra_install.sh")
print("  2. Или установите Wine: ./astra_install.sh --console (+ установка Wine)")
print("="*60)
```

---

## 🔄 ЭТАП 7: PYTHON - GUI РЕЖИМ

### 7.1. Импорт tkinter (уже проверено на ЭТАПЕ 5.2)
```python
import tkinter as tk
from tkinter import ttk
```

### 7.2. Запуск GUI
```python
gui = AutomationGUI(
    root=tk.Tk(),
    close_terminal_pid=args.close_terminal
)

# Закрытие родительского терминала через 2 секунды
if args.close_terminal:
    gui.root.after(2000, gui._close_parent_terminal)

# Центрирование окна
gui.center_window()

# Запуск главного цикла
gui.root.mainloop()
```

### 7.3. GUI работа
```
- Пользователь управляет процессом через интерфейс
- Обновление системы через GUI
- Установка Wine/Astra.IDE через GUI
- Управление репозиториями через GUI
```

---

## 📊 БЛОК-СХЕМА ПОЛНОГО АЛГОРИТМА

```
START (bash)
    ↓
[1] Инициализация
    - root права ✓
    - Синхронизация времени ✓
    - Переменные окружения ✓
    - Python 3 проверка ✓
    ↓
[2] Определение режима
    ↓
    ├─→ --console аргумент? → YES → [6] CONSOLE MODE
    │                          NO ↓
    ├─→ tkinter доступен? → YES → [7] GUI MODE
    │                       NO ↓
    ├─→ Репозитории есть? → NO → [6] CONSOLE MODE (forced)
    │                       YES ↓
    ├─→ tkinter пакет найден? → NO → [6] CONSOLE MODE (forced)
    │                           YES ↓
    │                              [3A] Установка tkinter
    │                                   ↓
    │                              tkinter работает? → NO → [6] CONSOLE
    │                                   YES ↓
    └──────────────────────────────→ [7] GUI MODE

[6] CONSOLE MODE (Python)
    ↓
    [6.1] Настройка репозиториев
    ↓
    [6.2] apt-get update
    ↓
    [6.3] apt-get dist-upgrade
    ↓
    [6.4] Установка python3-tk, pip3 (ПОСЛЕ обновления!)
    ↓
    [6.5] apt-get autoremove
    ↓
    [6.6] Финальный отчет
    ↓
    SUCCESS - Система обновлена + GUI готов

[7] GUI MODE (Python)
    ↓
    [7.1] import tkinter ✓
    ↓
    [7.2] Запуск GUI
    ↓
    [7.3] Пользователь управляет процессом
    ↓
    SUCCESS - По выбору пользователя
```

---

## ✅ ГАРАНТИИ АЛГОРИТМА

### 1. **Система ВСЕГДА обновится**
- Даже если GUI не запустился
- Даже если нет репозиториев изначально
- Даже если tkinter недоступен

### 2. **GUI будет доступен после первого запуска**
- Консольный режим обновит систему
- Консольный режим настроит репозитории
- Консольный режим установит tkinter
- Второй запуск → GUI работает

### 3. **Нет зависания на запросах**
- Уровень 1: Переменные окружения
- Уровень 2: Опции dpkg
- Уровень 3: Интерактивное распознавание (20 строк буфер)
- Уровень 4: Русский + английский паттерны

### 4. **Прозрачность процесса**
- Понятные логи на каждом шаге
- Объяснение почему выбран режим
- Информация о следующих шагах
- Коды возврата для всех критичных операций

### 5. **Универсальность**
- Работает на Debian, Ubuntu, Astra Linux, Mint
- Поддержка python3-tk, python3-tkinter, tk
- Работа с cdrom и network репозиториями
- Русский и английский интерфейсы

---

## 🔧 КЛЮЧЕВЫЕ ТЕХНИЧЕСКИЕ МОМЕНТЫ

### Проверка кода возврата через pipe
```bash
apt-get install -y package 2>&1 | tee -a "$LOG_FILE"
EXIT_CODE=${PIPESTATUS[0]}  # Код apt-get, НЕ tee!

if [ $EXIT_CODE -ne 0 ]; then
    echo "[ERROR] Установка провалилась (код: $EXIT_CODE)"
fi
```

### Проверка импорта модуля
```bash
# Bash
if python3 -c "import tkinter" 2>/dev/null; then
    echo "tkinter доступен"
fi

# Python
try:
    import tkinter
    available = True
except ImportError:
    available = False
```

### Установка с проверкой существования пакета
```bash
if apt-cache show "package-name" >/dev/null 2>&1; then
    # Пакет существует в репозиториях
    apt-get install -y package-name
else
    # Пакета нет
fi
```

### Автоматический fallback в Python
```python
if not args.console:
    try:
        import tkinter
    except ImportError:
        print("[AUTO] Переключение на консольный режим")
        args.console = True
```

---

## 📝 ПОРЯДОК РЕАЛИЗАЦИИ

1. ✅ **Создать этот документ** (STARTUP_ALGORITHM.md)
2. ⏳ **Создать снимок (коммит)** текущего состояния
3. ⏳ **Реализовать bash функции** (check_repos, find_tkinter, install_tkinter)
4. ⏳ **Реализовать логику выбора режима** в bash
5. ⏳ **Исправить проверку кодов возврата** в bash
6. ⏳ **Добавить автоматический fallback** в Python
7. ⏳ **Реализовать install_gui_components_post_update()** в Python
8. ⏳ **Тестирование на "чистом" Astra Linux**
9. ⏳ **Финальный коммит** с рабочим алгоритмом

---

## 🎯 ОЖИДАЕМЫЙ РЕЗУЛЬТАТ

**Сценарий 1: Чистый Astra Linux (только cdrom)**
```
1. Запуск: ./astra_install.sh
2. Определение: Нет репозиториев + нет tkinter → CONSOLE MODE
3. Обновление системы в консольном режиме
4. Установка GUI компонентов после обновления
5. Сообщение: "Перезапустите для GUI: ./astra_install.sh"
6. Второй запуск: GUI работает!
```

**Сценарий 2: Система с репозиториями, но без tkinter**
```
1. Запуск: ./astra_install.sh
2. Определение: Репозитории есть + пакет найден → Установка tkinter
3. Проверка: tkinter работает ✓
4. Запуск GUI режима
5. Пользователь управляет через интерфейс
```

**Сценарий 3: Полностью настроенная система**
```
1. Запуск: ./astra_install.sh
2. Определение: tkinter доступен → GUI MODE
3. Немедленный запуск GUI
4. Пользователь управляет через интерфейс
```

**Сценарий 4: Принудительный консольный режим**
```
1. Запуск: ./astra_install.sh --console
2. Игнорирование проверок tkinter
3. Консольный режим всегда
4. Обновление системы без GUI
```

---

*Документ создан: 2025-10-05*  
*Версия: 1.0*  
*Проект: FSA-AstraInstall*

