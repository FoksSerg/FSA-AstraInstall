#!/bin/bash
# ГЛАВНЫЙ СКРИПТ: Автоматическая установка и запуск GUI
# Версия: V2.6.132 (2025.11.17)
# Компания: ООО "НПА Вира-Реалтайм"

# ============================================================
# БЛОК 1: ИНИЦИАЛИЗАЦИЯ ЛОГОВ И ФУНКЦИЙ
# ============================================================

# Версия скрипта
SCRIPT_VERSION="V2.6.132 (2025.11.16)"

# Создаем лог файл рядом с запускающим файлом
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ============================================================================
# ОПРЕДЕЛЕНИЕ РЕЖИМА РАБОТЫ (БИНАРНЫЙ ИЛИ СКРИПТОВЫЙ)
# ============================================================================

# Определяем тип запуска: бинарный или скрипт
SCRIPT_NAME=$(basename "$0")
if [[ "$SCRIPT_NAME" == *.sh ]]; then
    IS_BINARY=false
else
    IS_BINARY=true
fi

# ============================================================================
# ФУНКЦИЯ ПОИСКА PYTHON ФАЙЛА
# ============================================================================

# Функция поиска Python скрипта или бинарного файла
find_python_executable() {
    local name="$1"
    local dir="${2:-$SCRIPT_DIR}"
    
    if [ "$IS_BINARY" = true ]; then
        # В бинарном режиме ищем только бинарный файл
        if [ -f "$dir/$name" ] && [ -x "$dir/$name" ]; then
            echo "$dir/$name"
            return 0
        fi
    else
        # В скриптовом режиме ищем Python скрипт
        if [ -f "$dir/${name}.py" ] && command -v python3 >/dev/null 2>&1; then
            echo "python3 $dir/${name}.py"
            return 0
        fi
    fi
    
    return 1
}

# Универсальная функция сворачивания окна терминала (работает до и после sudo)
minimize_terminal_window() {
    if ! command -v xdotool >/dev/null 2>&1; then
        return 0  # xdotool недоступен, выходим тихо
    fi
    
    local terminal_pid="$1"
    
    # Если передан PID терминала, используем его
    if [ ! -z "$terminal_pid" ] && [ "$terminal_pid" != "0" ]; then
        WINDOW_IDS=$(xdotool search --pid "$terminal_pid" 2>/dev/null)
        if [ -n "$WINDOW_IDS" ]; then
            for window in $WINDOW_IDS; do
                xdotool windowminimize "$window" 2>/dev/null
            done
            return 0
        fi
    fi
    
    # Fallback: пробуем найти терминал через PPID
    local term_pid=$(ps -o ppid= -p $$ | tr -d ' ' 2>/dev/null)
    if [ ! -z "$term_pid" ] && [ "$term_pid" != "0" ]; then
        WINDOW_IDS=$(xdotool search --pid "$term_pid" 2>/dev/null)
        if [ -n "$WINDOW_IDS" ]; then
            for window in $WINDOW_IDS; do
                xdotool windowminimize "$window" 2>/dev/null
            done
        fi
    fi
}

# КРИТИЧНО: Сворачиваем окно терминала МГНОВЕННО (до всех выводов)
# Выполняем только при первом запуске (до перезапуска через sudo)
if [ "$EUID" -ne 0 ] && command -v xdotool >/dev/null 2>&1; then
    # Проверяем аргументы - не сворачиваем в консольном режиме
    SKIP_TERMINAL=false
    for arg in "$@"; do
        if [[ "$arg" == "--console" ]]; then
            SKIP_TERMINAL=true
            break
        fi
    done
    
    # Сворачиваем окно терминала (всегда, кроме консольного режима)
    if [ "$SKIP_TERMINAL" != "true" ]; then
        minimize_terminal_window ""  # Пробуем найти автоматически
    fi
fi

# КРИТИЧНО: Принудительно переходим в каталог скрипта
# Это решает проблему запуска из ярлыка на рабочем столе
echo "FSA-AstraInstall Automation $SCRIPT_VERSION"
echo "Переходим в каталог скрипта: $SCRIPT_DIR"
cd "$SCRIPT_DIR" || {
    echo "ОШИБКА: Не удалось перейти в каталог скрипта: $SCRIPT_DIR"
    exit 1
}
echo "Текущий каталог: $(pwd)"

# Проверяем наличие основных файлов
if [ "$IS_BINARY" = true ]; then
    if [ ! -f "$SCRIPT_DIR/astra_automation" ] || [ ! -x "$SCRIPT_DIR/astra_automation" ]; then
        echo "ОШИБКА: Файл astra_automation не найден в каталоге: $SCRIPT_DIR"
        echo "Список файлов в каталоге:"
        ls -la
        exit 1
    fi
else
    if [ ! -f "$SCRIPT_DIR/astra_automation.py" ]; then
        echo "ОШИБКА: Файл astra_automation.py не найден в каталоге: $SCRIPT_DIR"
        echo "Список файлов в каталоге:"
        ls -la
        exit 1
    fi
fi

# ============================================================================
# БЛОК 0: ИНИЦИАЛИЗАЦИЯ ЛОГ-ФАЙЛА (ПЕРЕД ВСЕМ!)
# ============================================================================

# КРИТИЧНО: Проверяем передан ли --log-file ПЕРЕД созданием нового
LOG_FILE_PASSED=""
LOG_TIMESTAMP_PASSED=""
TERMINAL_PID_ARG=""

# КРИТИЧНО: Проверяем переменные окружения (если перезапустились через sudo)
if [ -n "$FSA_LOG_FILE" ]; then
    LOG_FILE_PASSED="$FSA_LOG_FILE"
fi
if [ -n "$FSA_LOG_TIMESTAMP" ]; then
    LOG_TIMESTAMP_PASSED="$FSA_LOG_TIMESTAMP"
fi
if [ -n "$FSA_TERMINAL_PID" ]; then
    TERMINAL_PID_ARG="$FSA_TERMINAL_PID"
fi

# Обрабатываем аргументы (--log-file, --log-timestamp, --terminal-pid)
# КРИТИЧНО: Если уже восстановлены из переменных окружения, пропускаем обработку
if [ -z "$LOG_FILE_PASSED" ] && [ -z "$LOG_TIMESTAMP_PASSED" ] && [ -z "$TERMINAL_PID_ARG" ]; then
    i=1
    while [ $i -le $# ]; do
        # КРИТИЧНО: Используем eval для косвенной подстановки аргументов
        eval "arg=\${$i}"
        if [[ "$arg" == "--log-file" ]] && [ $((i+1)) -le $# ]; then
            next_idx=$((i+1))
            eval "LOG_FILE_PASSED=\${$next_idx}"
            i=$((i+2))
            continue
        elif [[ "$arg" == "--log-timestamp" ]] && [ $((i+1)) -le $# ]; then
            next_idx=$((i+1))
            eval "LOG_TIMESTAMP_PASSED=\${$next_idx}"
            i=$((i+2))
            continue
        elif [[ "$arg" == "--terminal-pid" ]] && [ $((i+1)) -le $# ]; then
            next_idx=$((i+1))
            eval "TERMINAL_PID_ARG=\${$next_idx}"
            i=$((i+2))
            continue
        elif [[ "$arg" == --terminal-pid=* ]]; then
            TERMINAL_PID_ARG="${arg#*=}"
            i=$((i+1))
            continue
        fi
        i=$((i+1))
    done
fi

# Если передан --log-file - используем его
if [ -n "$LOG_FILE_PASSED" ]; then
    # КРИТИЧНО: Преобразуем относительный путь в абсолютный
    if [[ "$LOG_FILE_PASSED" != /* ]]; then
        # Относительный путь - делаем абсолютным относительно SCRIPT_DIR
        LOG_FILE_PASSED="$SCRIPT_DIR/$LOG_FILE_PASSED"
        # Убираем двойные слеши и ./ в начале
        LOG_FILE_PASSED=$(echo "$LOG_FILE_PASSED" | sed 's|/\./|/|g' | sed 's|^\./||' | sed 's|//|/|g')
    fi
    
    if [ -f "$LOG_FILE_PASSED" ]; then
        LOG_FILE="$LOG_FILE_PASSED"
        LOG_DIR="$(dirname "$LOG_FILE")"
        
        # Извлекаем timestamp из имени файла, если не передан
        if [ -z "$LOG_TIMESTAMP_PASSED" ]; then
            TIMESTAMP=$(echo "$LOG_FILE" | grep -oE '[0-9]{8}_[0-9]{6}' | head -1)
        else
            TIMESTAMP="$LOG_TIMESTAMP_PASSED"
        fi
        
        # КРИТИЧНО: Проверяем, не был ли уже добавлен разделитель (при перезапуске через sudo)
        # Проверяем переменную окружения или последние строки файла
        if [ -z "$FSA_LOG_INITIALIZED" ]; then
            # Проверяем последние строки файла на наличие разделителя
            if ! tail -n 10 "$LOG_FILE" | grep -q "ASTRA INSTALL - НАЧАЛО УСТАНОВКИ"; then
                # Добавляем разделитель (НЕ пересоздаем файл!)
                {
                    echo ""
                    echo "============================================================"
                    echo "ASTRA INSTALL - НАЧАЛО УСТАНОВКИ"
                    echo "Время запуска: $(date)"
                    echo "Директория скрипта: $SCRIPT_DIR"
                    echo "============================================================"
                } >> "$LOG_FILE"
                
                # Устанавливаем флаг в переменной окружения для предотвращения повторного добавления
                export FSA_LOG_INITIALIZED="1"
            fi
        fi
        
        # Исправляем права доступа
        REAL_USER=$(who am i | awk '{print $1}' 2>/dev/null || echo "")
        if [ -z "$REAL_USER" ]; then
            REAL_USER=$(logname 2>/dev/null || echo "$SUDO_USER")
        fi
        if [ ! -z "$REAL_USER" ] && [ "$REAL_USER" != "root" ]; then
            chown "$REAL_USER:$REAL_USER" "$LOG_FILE" 2>/dev/null || true
            chmod 644 "$LOG_FILE" 2>/dev/null || true
        fi
    else
        # Файл не найден - создаем новый (fallback)
        echo "[WARNING] Переданный лог-файл не найден: $LOG_FILE_PASSED, создаем новый" >&2
        LOG_FILE_PASSED=""
    fi
fi

# Если LOG_FILE_PASSED пуст или файл не найден - создаем новый
if [ -z "$LOG_FILE_PASSED" ] || [ ! -f "$LOG_FILE" ]; then
    # СТАРОЕ ПОВЕДЕНИЕ: создаем новый лог-файл (как было раньше)
    TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    LOG_DIR="$SCRIPT_DIR/Log"
    mkdir -p "$LOG_DIR"
    LOG_FILE="$LOG_DIR/astra_automation_$TIMESTAMP.log"
    
    # Инициализируем лог-файл (как было раньше)
    echo "============================================================" > "$LOG_FILE"
    echo "ASTRA AUTOMATION - НАЧАЛО СЕССИИ" >> "$LOG_FILE"
    echo "Время запуска: $(date)" >> "$LOG_FILE"
    echo "Директория скрипта: $SCRIPT_DIR" >> "$LOG_FILE"
    echo "============================================================" >> "$LOG_FILE"
    
    # Исправляем права доступа (как было раньше)
    if [ -d "$LOG_DIR" ]; then
        REAL_USER=$(who am i | awk '{print $1}')
        if [ -z "$REAL_USER" ]; then
            REAL_USER=$(logname 2>/dev/null || echo "$SUDO_USER")
        fi
        
        if [ ! -z "$REAL_USER" ]; then
            chown -R "$REAL_USER:$REAL_USER" "$LOG_DIR" 2>/dev/null
            chmod -R 755 "$LOG_DIR" 2>/dev/null
            echo "[i] Установлены права доступа для пользователя: $REAL_USER"
        fi
    fi
fi

# Экспортируем для использования в функциях
export LOG_FILE
export TIMESTAMP

# Функция логирования
log_message() {
    local message="$1"
    local timestamp=$(date +"%H:%M:%S.%3N")
    echo "[$timestamp] [BASH] $message" >> "$LOG_FILE"
    echo "$message"  # Также выводим в консоль
}

# Функция проверки одного репозитория
check_single_repo() {
    local repo_line="$1"
    local test_file=$(mktemp)
    echo "$repo_line" > "$test_file"

    # Автоматически отключаем компакт-диск репозитории
    if [[ "$repo_line" =~ cdrom: ]]; then
        echo "   [!] Компакт-диск: $(echo "$repo_line" | awk '{print $2}') - отключаем"
        log_message "Компакт-диск репозиторий отключен: $(echo "$repo_line" | awk '{print $2}')"
        rm -f "$test_file"
        return 1  # Возвращаем 1 чтобы репозиторий был отключен
    fi

    if apt-get update -o Dir::Etc::sourcelist="$test_file" -o Dir::Etc::sourceparts="-" -o APT::Get::List-Cleanup="0" &>/dev/null; then
        echo "   [OK] Рабочий: $(echo "$repo_line" | awk '{print $2}')"
        log_message "Репозиторий рабочий: $(echo "$repo_line" | awk '{print $2}')"
        rm -f "$test_file"
        return 0
    else
        echo "   [ERR] Не доступен: $(echo "$repo_line" | awk '{print $2}')"
        log_message "Репозиторий не доступен: $(echo "$repo_line" | awk '{print $2}')"
        rm -f "$test_file"
        return 1
    fi
}

# Функция проверки доступности tkinter
check_tkinter_available() {
    if python3 -c "import tkinter" 2>/dev/null; then
        return 0  # tkinter доступен
    else
        return 1  # tkinter недоступен
    fi
}

# Функция проверки доступности репозиториев (не-cdrom)
check_repos_available() {
    # Проверяем есть ли хоть один НЕ-cdrom и НЕ-закомментированный репозиторий
    if grep -v "^#" /etc/apt/sources.list 2>/dev/null | grep -v "cdrom:" | grep "^deb" >/dev/null 2>&1; then
        return 0  # Репозитории есть
    else
        return 1  # Только cdrom или пусто
    fi
}

# Функция поиска пакета tkinter в репозиториях
find_tkinter_package() {
    # Список возможных названий пакетов tkinter
    local TKINTER_PACKAGES=("python3-tk" "python3-tkinter" "tk")
    
    log_message "Поиск пакетов tkinter в репозиториях"
    
    for pkg in "${TKINTER_PACKAGES[@]}"; do
        if apt-cache show "$pkg" >/dev/null 2>&1; then
            log_message "Пакет $pkg найден в репозиториях"
            echo "$pkg"  # Возвращаем первый найденный пакет
            return 0
        else
            log_message "Пакет $pkg не найден в репозиториях"
        fi
    done
    
    log_message "Ни один пакет tkinter не найден в репозиториях"
    return 1  # Ни один пакет не найден в репозиториях
}

# Функция установки tkinter с проверкой
install_tkinter_with_verification() {
    local TKINTER_PACKAGES=("python3-tk" "python3-tkinter" "tk")
    local INSTALLED=false
    
    echo ""
    echo "[#] Установка tkinter..."
    log_message "Начинаем установку tkinter с проверкой"
    
    for pkg in "${TKINTER_PACKAGES[@]}"; do
        echo "   [TRY] Пробуем установить: $pkg"
        log_message "Пробуем установить пакет: $pkg"
        
        # Проверяем что пакет существует в репозиториях
        if ! apt-cache show "$pkg" >/dev/null 2>&1; then
            echo "   [SKIP] Пакет $pkg не найден в репозиториях"
            log_message "Пакет $pkg не найден в репозиториях"
            continue
        fi
        
        echo "   [INSTALL] Устанавливаем $pkg..."
        log_message "Устанавливаем пакет $pkg"
        
        # Устанавливаем с максимально агрессивными опциями автоматического подтверждения
        # Используем yes "Y" для автоматического ответа "Y" на все запросы dpkg (обновляем конфигурации)
        yes "Y" | apt-get install -y $DPKG_OPTS "$pkg" 2>&1 | tee -a "$LOG_FILE"
        local EXIT_CODE=${PIPESTATUS[0]}
        
        # Игнорируем код 141 (SIGPIPE) от yes команды - это нормально
        if [ $EXIT_CODE -eq 0 ] || [ $EXIT_CODE -eq 141 ]; then
            echo "   [OK] Пакет $pkg установлен (код возврата: 0)"
            log_message "Пакет $pkg установлен успешно (код: 0)"
            
            # КРИТИЧНО: Проверяем что tkinter теперь импортируется
            if python3 -c "import tkinter" 2>/dev/null; then
                echo "   [OK] tkinter успешно импортируется!"
                log_message "tkinter успешно импортируется после установки $pkg"
                INSTALLED=true
                break
            else
                echo "   [WARNING] Пакет $pkg установлен, но tkinter не импортируется"
                log_message "ПРЕДУПРЕЖДЕНИЕ: Пакет $pkg установлен, но tkinter не работает"
            fi
        else
            echo "   [ERROR] Не удалось установить $pkg (код возврата: $EXIT_CODE)"
            log_message "ОШИБКА: Не удалось установить $pkg (код: $EXIT_CODE)"
        fi
    done
    
    if [ "$INSTALLED" = true ]; then
        echo "   [OK] tkinter успешно установлен и работает"
        log_message "tkinter успешно установлен и работает"
        return 0
    else
        echo "   [ERROR] Не удалось установить рабочий tkinter"
        log_message "ОШИБКА: Не удалось установить рабочий tkinter"
        return 1
    fi
}

# Инициализируем лог файл (если еще не инициализирован)
if [ -z "$LOG_FILE" ] || [ ! -f "$LOG_FILE" ]; then
    echo "============================================================" > "$LOG_FILE"
    echo "ASTRA AUTOMATION - НАЧАЛО СЕССИИ" >> "$LOG_FILE"
    echo "Время запуска: $(date)" >> "$LOG_FILE"
    echo "Директория скрипта: $SCRIPT_DIR" >> "$LOG_FILE"
    echo "============================================================" >> "$LOG_FILE"
fi

echo "============================================================"
echo "ASTRA AUTOMATION - АВТОМАТИЧЕСКАЯ УСТАНОВКА И ЗАПУСК"
echo "============================================================"

# ============================================================
# БЛОК 2: ОБРАБОТКА АРГУМЕНТОВ И ПРОВЕРКИ
# ============================================================

# Обрабатываем аргументы командной строки
CONSOLE_MODE=false
DRY_RUN=false
# КРИТИЧНО: НЕ сбрасываем TERMINAL_PID_ARG, если он уже установлен выше!
# TERMINAL_PID_ARG уже может быть установлен из переменной окружения или из аргументов
START_MODE_ARG=""
SKIP_NEXT_ARG=false  # Флаг для пропуска следующего аргумента (значение --log-file, --log-timestamp или --terminal-pid)

for arg in "$@"; do
    # КРИТИЧНО: Пропускаем значение --log-file, --log-timestamp или --terminal-pid
    if [ "$SKIP_NEXT_ARG" = true ]; then
        SKIP_NEXT_ARG=false
        continue
    fi
    
    case $arg in
        --log-file|--log-timestamp|--terminal-pid)
            # КРИТИЧНО: Пропускаем эти аргументы - они уже обработаны выше
            # Следующий аргумент - значение, пропускаем его тоже
            SKIP_NEXT_ARG=true
            ;;
        --windows-minimized)
            # Окна уже свернуты, пропускаем сворачивание
            ;;
        --console)
            CONSOLE_MODE=true
            echo "[i] Режим: КОНСОЛЬНЫЙ (без GUI)"
            ;;
        --dry-run)
            DRY_RUN=true
            echo "[i] Режим: ТЕСТИРОВАНИЕ (dry-run)"
            ;;
        --mode)
            # Следующий аргумент - режим запуска
            shift
            START_MODE_ARG="$1"
            ;;
        --terminal-pid=*)
            # Обрабатываем --terminal-pid=value
            TERMINAL_PID_ARG="${arg#*=}"
            ;;
        *)
            # Игнорируем неизвестные аргументы (уже обработаны выше)
            ;;
    esac
done

# КРИТИЧНО: Если получен PID терминала через аргумент, используем его
if [ ! -z "$TERMINAL_PID_ARG" ]; then
    TERMINAL_PID="$TERMINAL_PID_ARG"
    
    # Сворачиваем терминал ПОСЛЕ sudo (если передан TERMINAL_PID)
    if [ "$EUID" -eq 0 ] && command -v xdotool >/dev/null 2>&1; then
        SKIP_TERMINAL=false
        for arg in "$@"; do
            if [[ "$arg" == "--console" ]]; then
                SKIP_TERMINAL=true
                break
            fi
        done
        
        if [ "$SKIP_TERMINAL" != "true" ]; then
            minimize_terminal_window "$TERMINAL_PID"  # Используем переданный PID
        fi
    fi
fi

# Проверяем права root и автоматически перезапускаемся через sudo если нужно
if [ "$EUID" -ne 0 ]; then
    echo "[i] Требуются права root. Перезапуск через sudo..."
    log_message "Перезапуск скрипта с правами root через sudo"
    
    # КРИТИЧНО: Сохраняем --log-file, --log-timestamp и --terminal-pid в переменных окружения
    # чтобы они не потерялись при перезапуске через sudo
    if [ -n "$LOG_FILE_PASSED" ]; then
        export FSA_LOG_FILE="$LOG_FILE_PASSED"
    fi
    if [ -n "$LOG_TIMESTAMP_PASSED" ]; then
        export FSA_LOG_TIMESTAMP="$LOG_TIMESTAMP_PASSED"
    fi
    if [ -n "$TERMINAL_PID_ARG" ]; then
        export FSA_TERMINAL_PID="$TERMINAL_PID_ARG"
    fi
    # КРИТИЧНО: Передаем флаг инициализации лог-файла
    if [ -n "$FSA_LOG_INITIALIZED" ]; then
        export FSA_LOG_INITIALIZED="$FSA_LOG_INITIALIZED"
    fi
    
    # Перезапускаем себя с sudo, передавая все аргументы и переменные окружения
    if [ ! -z "$DISPLAY" ]; then
        exec sudo -E env DISPLAY="$DISPLAY" XAUTHORITY="${XAUTHORITY:-$HOME/.Xauthority}" FSA_WINDOWS_MINIMIZED="$FSA_WINDOWS_MINIMIZED" FSA_LOG_FILE="${FSA_LOG_FILE:-}" FSA_LOG_TIMESTAMP="${FSA_LOG_TIMESTAMP:-}" FSA_TERMINAL_PID="${FSA_TERMINAL_PID:-}" FSA_LOG_INITIALIZED="${FSA_LOG_INITIALIZED:-}" bash "$0" "$@"
    else
        exec sudo -E env FSA_WINDOWS_MINIMIZED="$FSA_WINDOWS_MINIMIZED" FSA_LOG_FILE="${FSA_LOG_FILE:-}" FSA_LOG_TIMESTAMP="${FSA_LOG_TIMESTAMP:-}" FSA_TERMINAL_PID="${FSA_TERMINAL_PID:-}" FSA_LOG_INITIALIZED="${FSA_LOG_INITIALIZED:-}" bash "$0" "$@"
    fi
    exit $?
fi

log_message "Проверка прав root: OK (запущено с правами root)"

# Синхронизация системного времени (один раз за сеанс)
TIME_SYNC_FLAG="/tmp/fsa-time-synced"

if [ -f "$TIME_SYNC_FLAG" ]; then
    echo "[i] Время уже синхронизировано в этом сеансе"
else
    echo "[~] Синхронизация системного времени..."
    log_message "Выполняется синхронизация времени (первый запуск после загрузки)"
    
    # Пробуем разные методы синхронизации времени
    TIME_SYNCED=false
    
    # Метод 1: timedatectl (systemd)
    if command -v timedatectl >/dev/null 2>&1; then
        if timedatectl set-ntp true 2>/dev/null; then
            echo "   [OK] Время синхронизировано через NTP (timedatectl)"
            log_message "Время синхронизировано через timedatectl"
            TIME_SYNCED=true
        fi
    fi
    
    # Метод 2: ntpdate (если первый не сработал)
    if [ "$TIME_SYNCED" = false ] && command -v ntpdate >/dev/null 2>&1; then
        if ntpdate -s time.nist.gov 2>/dev/null || ntpdate -s pool.ntp.org 2>/dev/null; then
            echo "   [OK] Время синхронизировано через NTP (ntpdate)"
            log_message "Время синхронизировано через ntpdate"
            TIME_SYNCED=true
        fi
    fi
    
    # Создаем флаг успешной синхронизации
    if [ "$TIME_SYNCED" = true ]; then
        echo "$(date '+%Y-%m-%d %H:%M:%S')" > "$TIME_SYNC_FLAG"
        log_message "Флаг синхронизации создан: $TIME_SYNC_FLAG"
    else
        echo "   [!] Не удалось синхронизировать время (продолжаем работу)"
        log_message "Предупреждение: синхронизация времени не выполнена"
    fi
fi

# Настраиваем переменные окружения для автоматических ответов
export DEBIAN_FRONTEND=noninteractive
export DEBIAN_PRIORITY=critical
export APT_LISTCHANGES_FRONTEND=none

# Опции dpkg для автоматического обновления конфигураций
DPKG_OPTS="-o Dpkg::Options::=--force-confdef -o Dpkg::Options::=--force-confnew -o Dpkg::Options::=--force-confmiss"


echo "[?] Проверяем систему..."

# Проверяем версию Astra Linux
if [ -f /etc/astra_version ]; then
    ASTRA_VERSION=$(cat /etc/astra_version)
    echo "   [i] Версия Astra Linux: $ASTRA_VERSION"
    log_message "Версия Astra Linux: $ASTRA_VERSION"
else
    echo "   [!] Не удалось определить версию Astra Linux"
    log_message "Не удалось определить версию Astra Linux"
fi

# Проверяем Python
PYTHON3_VERSION=$(python3 --version 2>/dev/null || echo 'не найден')
echo "   [i] Python 3: $PYTHON3_VERSION"
log_message "Python 3: $PYTHON3_VERSION"

# ============================================================
# БЛОК 3: ОПРЕДЕЛЕНИЕ РЕЖИМА ЗАПУСКА (УМНАЯ ЛОГИКА)
# ============================================================

if [ "$CONSOLE_MODE" = false ]; then
    echo ""
    echo "[*] Определяем оптимальный режим запуска..."
    
    # Переменная для выбора режима
    START_MODE=""
    
    # СНАЧАЛА настраиваем репозитории, если их нет
    echo "   [?] Проверяем доступность репозиториев..."
    if ! check_repos_available; then
        echo "   [!] Нет рабочих репозиториев (только cdrom или пусто)"
        log_message "Нет рабочих репозиториев - настраиваем через Python"
        
        echo "   [#] Настраиваем репозитории через Python..."
        log_message "Вызываем Python для настройки репозиториев с лог-файлом: $LOG_FILE"
        
        ASTRA_AUTOMATION_REPOS=$(find_python_executable "astra_automation")
        if [ -z "$ASTRA_AUTOMATION_REPOS" ]; then
            log_message "ОШИБКА: astra_automation не найден для настройки репозиториев"
            exit 1
        fi
        
        $ASTRA_AUTOMATION_REPOS --log-file "$LOG_FILE" --setup-repos 2>&1 | tee -a "$LOG_FILE"
        REPOS_EXIT_CODE=${PIPESTATUS[0]}
        
        if [ $REPOS_EXIT_CODE -eq 0 ]; then
            echo "   [OK] Репозитории настроены успешно"
            log_message "Репозитории настроены через Python"
            
            # КРИТИЧНО: Обновляем список пакетов после настройки репозиториев
            echo "   [#] Обновляем список пакетов после настройки репозиториев..."
            log_message "Обновляем список пакетов после настройки репозиториев"
            
            yes "Y" | apt-get update -y 2>&1 | tee -a "$LOG_FILE"
            UPDATE_EXIT_CODE=${PIPESTATUS[0]}
            
            if [ $UPDATE_EXIT_CODE -eq 0 ]; then
                echo "   [OK] Список пакетов обновлен после настройки репозиториев"
                log_message "Список пакетов обновлен успешно после настройки репозиториев"
            else
                echo "   [WARNING] Ошибка обновления списка пакетов (код: $UPDATE_EXIT_CODE)"
                log_message "ПРЕДУПРЕЖДЕНИЕ: Ошибка обновления списка пакетов (код: $UPDATE_EXIT_CODE)"
                echo "   [i] Продолжаем работу - возможно список уже актуален"
                log_message "Продолжаем работу несмотря на ошибку обновления списка пакетов"
            fi
        else
            echo "   [ERROR] Ошибка настройки репозиториев (код: $REPOS_EXIT_CODE)"
            log_message "ОШИБКА: Не удалось настроить репозитории (код: $REPOS_EXIT_CODE)"
            echo "   [i] Переключение на консольный режим"
            log_message "Переключение на консольный режим из-за ошибки настройки репозиториев"
            START_MODE="console_forced"
            CONSOLE_MODE=true
        fi
    else
        echo "   [OK] Рабочие репозитории уже настроены"
    fi
    
    # Теперь определяем режим на основе доступности tkinter
    if [ -z "$START_MODE" ]; then  # Если режим еще не определен
        echo "   [?] Проверяем доступность tkinter..."
        if check_tkinter_available; then
            echo "   [OK] tkinter найден и работает"
            START_MODE="gui_ready"
        else
            echo "   [!] tkinter не найден"
            log_message "tkinter недоступен - требуется установка"
            
            # Проверяем есть ли пакет tkinter в репозиториях
            echo "   [?] Ищем пакет tkinter в репозиториях..."
            log_message "Поиск пакета tkinter в репозиториях"
            
            TKINTER_PKG=$(find_tkinter_package)
            TKINTER_FOUND=$?
            
            log_message "Результат поиска tkinter: код=$TKINTER_FOUND, пакет='$TKINTER_PKG'"
            
            if [ $TKINTER_FOUND -eq 0 ]; then
                echo "   [OK] Найден пакет: $TKINTER_PKG"
                log_message "Пакет tkinter найден в репозиториях: $TKINTER_PKG"
                START_MODE="gui_install_first"
            else
                echo "   [!] Пакет tkinter не найден в репозиториях"
                log_message "Пакет tkinter не найден - принудительный консольный режим"
                START_MODE="console_forced"
                CONSOLE_MODE=true
            fi
        fi
    fi
    
    # Вывод итогового решения
    echo ""
    echo "============================================================"
    case $START_MODE in
        gui_ready)
            echo "[MODE] GUI РЕЖИМ - все компоненты готовы"
            echo "[i] tkinter доступен, запускаем графический интерфейс"
            log_message "Режим: GUI_READY - немедленный запуск GUI"
            ;;
        gui_install_first)
            echo "[MODE] GUI РЕЖИМ - установка tkinter"
            echo "[i] Репозитории доступны, установим tkinter и запустим GUI"
            log_message "Режим: GUI_INSTALL_FIRST - установка tkinter перед запуском"
            ;;
        console_forced)
            echo "[MODE] КОНСОЛЬНЫЙ РЕЖИМ (принудительный)"
            echo "[!] Причина: нет репозиториев или tkinter недоступен"
            echo "[i] Система будет обновлена в консольном режиме"
            echo "[i] GUI компоненты будут установлены ПОСЛЕ обновления"
            echo "[i] После завершения запустите снова для GUI"
            log_message "Режим: CONSOLE_FORCED - нет возможности запустить GUI"
            CONSOLE_MODE=true
            ;;
    esac
    echo "============================================================"
    echo ""
    
    # Если нужно установить tkinter - делаем это
    if [ "$START_MODE" = "gui_install_first" ]; then
        echo "[#] Устанавливаем компоненты для GUI..."
        log_message "Начинаем установку GUI компонентов"
        
        echo ""
        echo "[~] Обновляем список пакетов..."
        log_message "Начинаем обновление списка пакетов (apt-get update)"
        
        yes "Y" | apt-get update -y 2>&1 | tee -a "$LOG_FILE"
        UPDATE_EXIT_CODE=${PIPESTATUS[0]}
        
        # Игнорируем код 141 (SIGPIPE) от yes команды
        if [ $UPDATE_EXIT_CODE -eq 0 ] || [ $UPDATE_EXIT_CODE -eq 141 ]; then
            echo "   [OK] Список пакетов обновлен (код: 0)"
            log_message "Список пакетов обновлен успешно (код: 0)"
        else
            echo "   [WARNING] Ошибка обновления списка пакетов (код: $UPDATE_EXIT_CODE)"
            log_message "ПРЕДУПРЕЖДЕНИЕ: Ошибка обновления списка пакетов (код: $UPDATE_EXIT_CODE)"
            echo "   [i] Продолжаем работу - возможно список уже актуален"
            log_message "Продолжаем работу несмотря на ошибку обновления списка пакетов"
        fi
        
        # НЕ переключаемся в консольный режим из-за ошибки apt-get update!
        # Продолжаем установку GUI компонентов
        
        # Устанавливаем tkinter с проверкой
        if install_tkinter_with_verification; then
            echo "   [OK] tkinter установлен и работает"
            log_message "tkinter установлен и проверен"
            
            # Устанавливаем дополнительные компоненты для GUI
            echo ""
            echo "[#] Установка дополнительных компонентов для GUI..."
            yes "Y" | apt-get install -y python3-psutil wmctrl xdotool expect $DPKG_OPTS 2>&1 | tee -a "$LOG_FILE"
            COMPONENTS_EXIT_CODE=${PIPESTATUS[0]}
            
            if [ $COMPONENTS_EXIT_CODE -eq 0 ] || [ $COMPONENTS_EXIT_CODE -eq 141 ]; then
                echo "   [OK] Дополнительные компоненты установлены (код: $COMPONENTS_EXIT_CODE)"
                log_message "psutil, wmctrl, xdotool, expect установлены успешно"
            else
                echo "   [WARNING] Некоторые компоненты не установлены (код: $COMPONENTS_EXIT_CODE)"
                log_message "ПРЕДУПРЕЖДЕНИЕ: Некоторые компоненты не установлены, функциональность может быть ограничена"
            fi
            
            # КРИТИЧНО: Меняем режим на gui_ready и СБРАСЫВАЕМ CONSOLE_MODE
            START_MODE="gui_ready"
            CONSOLE_MODE=false
            echo "   [i] Режим изменен на: gui_ready"
            echo "   [i] CONSOLE_MODE сброшен в: false"
            log_message "Режим изменен на gui_ready после установки tkinter, CONSOLE_MODE сброшен"
        else
            echo "   [ERROR] Не удалось установить рабочий tkinter"
            echo "   [i] Переключение на консольный режим"
            log_message "Переключение на консольный режим - tkinter не установлен"
            START_MODE="console_forced"
            CONSOLE_MODE=true
        fi
        
        # Пропускаем установку pip3 для экономии места и времени
        # pip3 не критичен для работы GUI
        echo "     [SKIP] Пропускаем установку pip3 (не критично для GUI)"
        log_message "Пропускаем установку pip3 (не критично для GUI)"
        
        # Исправляем зависимости
        echo ""
        echo "   [*] Исправляем зависимости..."
        log_message "Исправляем зависимости (apt-get install -f)"
        apt-get install -f -y $DPKG_OPTS 2>&1 | tee -a "$LOG_FILE"
        FIX_EXIT_CODE=${PIPESTATUS[0]}
        if [ $FIX_EXIT_CODE -eq 0 ]; then
            echo "   [OK] Зависимости исправлены (код: 0)"
            log_message "Зависимости исправлены успешно (код: 0)"
        else
            echo "   [WARNING] Ошибка исправления зависимостей (код: $FIX_EXIT_CODE)"
            log_message "ПРЕДУПРЕЖДЕНИЕ: Ошибка исправления зависимостей (код: $FIX_EXIT_CODE)"
        fi
    fi
    
    # Финальная проверка перед запуском GUI
    if [ "$START_MODE" = "gui_ready" ] || [ "$START_MODE" = "gui_install_first" ]; then
        echo ""
        echo "[?] Финальная проверка перед запуском GUI..."
        
        if ! check_tkinter_available; then
            echo "   [ERROR] tkinter все еще недоступен!"
            echo "   [i] Переключение на консольный режим"
            log_message "КРИТИЧЕСКАЯ ОШИБКА: tkinter недоступен после установки"
            START_MODE="console_forced"
            CONSOLE_MODE=true
        else
            echo "   [OK] tkinter работает - готовы к запуску GUI"
            echo "   [i] CONSOLE_MODE установлен в: false"
            CONSOLE_MODE=false
        fi
    fi
fi

echo ""
echo "[?] Статус компонентов:"
echo "   [i] Python 3: $(python3 --version 2>/dev/null || echo 'не работает')"
echo "   [i] Tkinter: $(python3 -c 'import tkinter; print("работает")' 2>/dev/null || echo 'не работает')"
echo "   [i] pip3: $(pip3 --version 2>/dev/null || echo 'не работает')"
log_message "Статус: Python=$(python3 --version 2>/dev/null || echo 'N/A'), Tkinter=$(python3 -c 'import tkinter; print("OK")' 2>/dev/null || echo 'N/A'), pip3=$(pip3 --version 2>/dev/null || echo 'N/A')"

echo ""
echo "[+] Подготовка завершена!"

# ============================================================
# БЛОК 4: ЗАПУСК PYTHON СКРИПТА
# ============================================================

echo ""
echo "[INFO] Финальные параметры запуска:"
echo "   [i] CONSOLE_MODE: $CONSOLE_MODE"
echo "   [i] START_MODE: $START_MODE"

# Устанавливаем START_MODE для консольного режима
# Если режим передан через аргумент --mode, используем его
if [ -n "$START_MODE_ARG" ]; then
    START_MODE="$START_MODE_ARG"
    log_message "Используем START_MODE из аргумента: $START_MODE"
elif [ "$CONSOLE_MODE" = true ] && [ -z "$START_MODE" ]; then
    # Если режим не передан, но включен консольный режим, устанавливаем по умолчанию
    START_MODE="console_forced"
    log_message "Установлен START_MODE=console_forced для консольного режима"
fi

if [ "$CONSOLE_MODE" = true ]; then
    echo "[>] Консольный режим - обновление системы..."
    log_message "Запускаем консольный режим"
    
    # Устанавливаем psutil для мониторинга системы в консольном режиме
    echo ""
    echo "[#] Установка psutil для мониторинга системы..."
    yes "Y" | apt-get install -y python3-psutil $DPKG_OPTS 2>&1 | tee -a "$LOG_FILE"
    PSUTIL_EXIT_CODE=${PIPESTATUS[0]}
    
    if [ $PSUTIL_EXIT_CODE -eq 0 ] || [ $PSUTIL_EXIT_CODE -eq 141 ]; then
        echo "   [OK] psutil установлен (код: $PSUTIL_EXIT_CODE)"
        log_message "psutil установлен успешно в консольном режиме"
    else
        echo "   [WARNING] psutil не установлен (код: $PSUTIL_EXIT_CODE)"
        log_message "ПРЕДУПРЕЖДЕНИЕ: psutil не установлен, мониторинг будет ограничен"
    fi
    
    echo ""
    echo "[*] Запуск Python скрипта в консольном режиме..."
    log_message "Запускаем Python с флагом --console"
else
    echo "[>] Запускаем графический интерфейс..."
fi

log_message "FSA-AstraInstall Automation $SCRIPT_VERSION"

# В бинарном режиме не нужен Python - бинарник уже содержит интерпретатор
if [ "$IS_BINARY" = true ] || python3 --version >/dev/null 2>&1; then
    if [ "$IS_BINARY" = false ]; then
        echo "   [i] Используем Python 3: $(python3 --version)"
    else
        echo "   [i] Бинарный режим - Python интерпретатор встроен"
        log_message "Бинарный режим - Python интерпретатор встроен"
    fi
    
    if [ "$CONSOLE_MODE" = true ]; then
        # Консольный режим - запускаем в текущем терминале
        ASTRA_AUTOMATION=$(find_python_executable "astra_automation")
        if [ -z "$ASTRA_AUTOMATION" ]; then
            log_message "ОШИБКА: astra_automation не найден"
            exit 1
        fi
        
        # КРИТИЧНО: Передаем лог-файл и timestamp в astra_automation.py
        if [ -n "$TIMESTAMP" ]; then
            $ASTRA_AUTOMATION --log-file "$LOG_FILE" --log-timestamp "$TIMESTAMP" --console --mode "$START_MODE" "$@"
        else
            $ASTRA_AUTOMATION --log-file "$LOG_FILE" --console --mode "$START_MODE" "$@"
        fi
        PYTHON_EXIT_CODE=$?
    else
        # GUI режим - запускаем в фоне и передаем PID терминала для закрытия
        echo "   [i] GUI запускается в фоновом режиме"
        echo "   [i] Окно терминала закроется автоматически после запуска GUI"
        # Получаем PID родительского терминала (процесс окна терминала, не bash скрипта)
        # $PPID - это PID родителя текущего скрипта, нужен родитель родителя
        # АЛГОРИТМ ОПРЕДЕЛЕНИЯ PID ТЕРМИНАЛА С ПРОВЕРКОЙ
        
        # КРИТИЧНО: Проверяем переданный PID терминала из astra_update.sh
        if [ -z "$TERMINAL_PID" ]; then
            log_message "Переданный PID терминала не найден, используем алгоритм поиска"
            
            # Список методов определения PID (по приоритету)
            methods=(
                "ps -o ppid= -p \$PPID | tr -d ' '"                                  # Метод 1 - РАБОТАЕТ НА 1.7.8
                "ps -o ppid= -p \$(ps -o ppid= -p \$PPID | tr -d ' ') | tr -d ' '"  # Метод 2 - РАБОТАЕТ НА 1.8.3
                "\$PPID"                                                             # Метод 3 - простой fallback
                "ps -o ppid= -p \$\$ | tr -d ' '"                                   # Метод 4 - альтернатива
                "pstree -p \$\$ | grep -o '([0-9]*)' | tail -1 | tr -d '()'"        # Метод 5 - если pstree доступен
                "ps -o pid,ppid,comm -p \$\$ | tail -1 | awk '{print \$2}'"         # Метод 6 - awk fallback
            )
            
            # Проверяем каждый метод по очереди
            for i in "${!methods[@]}"; do
                method="${methods[$i]}"
                # Проверяем каждый метод
                candidate_pid=$(eval "$method" 2>/dev/null)
                
                # Проверяем существование и тип процесса
                if [ ! -z "$candidate_pid" ] && kill -0 "$candidate_pid" 2>/dev/null; then
                    process_name=$(ps -o comm= -p "$candidate_pid" 2>/dev/null)
                    
                    # Проверяем что это терминал
                    if [[ "$process_name" =~ (fly-term|gnome-terminal|xterm|konsole|terminator) ]]; then
                        TERMINAL_PID="$candidate_pid"
                        break  # ВЫХОДИМ ИЗ ЦИКЛА!
                    fi
                fi
            done
            
            # Fallback если ничего не найдено
            if [ -z "$TERMINAL_PID" ]; then
                TERMINAL_PID=$(ps -o ppid= -p $PPID | tr -d ' ')
            fi
        fi  # Закрываем блок if [ -z "$TERMINAL_PID" ]
        
        # Запускаем GUI с передачей PID терминала для автозакрытия
        ASTRA_AUTOMATION=$(find_python_executable "astra_automation")
        if [ -z "$ASTRA_AUTOMATION" ]; then
            log_message "ОШИБКА: astra_automation не найден"
            exit 1
        fi
        
        # КРИТИЧНО: Передаем лог-файл и timestamp в astra_automation.py (GUI режим)
        # Проверяем что TERMINAL_PID валидный перед передачей
        if [ -n "$TIMESTAMP" ]; then
            # Запускаем команду (может быть "python3 file.py" или "./file")
            if [ "$IS_BINARY" = true ]; then
                # Бинарный режим - просто путь к файлу
                if [ -n "$TERMINAL_PID" ] && [[ "$TERMINAL_PID" =~ ^[0-9]+$ ]]; then
                    nohup "$ASTRA_AUTOMATION" --log-file "$LOG_FILE" --log-timestamp "$TIMESTAMP" --close-terminal "$TERMINAL_PID" --mode "$START_MODE" "$@" >/dev/null 2>&1 &
                else
                    nohup "$ASTRA_AUTOMATION" --log-file "$LOG_FILE" --log-timestamp "$TIMESTAMP" --mode "$START_MODE" "$@" >/dev/null 2>&1 &
                fi
            else
                # Скриптовый режим - команда с python3
                if [ -n "$TERMINAL_PID" ] && [[ "$TERMINAL_PID" =~ ^[0-9]+$ ]]; then
                    nohup bash -c "$ASTRA_AUTOMATION --log-file \"$LOG_FILE\" --log-timestamp \"$TIMESTAMP\" --close-terminal \"$TERMINAL_PID\" --mode \"$START_MODE\" $*" >/dev/null 2>&1 &
                else
                    nohup bash -c "$ASTRA_AUTOMATION --log-file \"$LOG_FILE\" --log-timestamp \"$TIMESTAMP\" --mode \"$START_MODE\" $*" >/dev/null 2>&1 &
                fi
            fi
        else
            # Fallback: без timestamp (старое поведение)
            if [ "$IS_BINARY" = true ]; then
                # Бинарный режим - просто путь к файлу
                if [ -n "$TERMINAL_PID" ] && [[ "$TERMINAL_PID" =~ ^[0-9]+$ ]]; then
                    nohup "$ASTRA_AUTOMATION" --log-file "$LOG_FILE" --close-terminal "$TERMINAL_PID" --mode "$START_MODE" "$@" >/dev/null 2>&1 &
                else
                    nohup "$ASTRA_AUTOMATION" --log-file "$LOG_FILE" --mode "$START_MODE" "$@" >/dev/null 2>&1 &
                fi
            else
                # Скриптовый режим - команда с python3
                if [ -n "$TERMINAL_PID" ] && [[ "$TERMINAL_PID" =~ ^[0-9]+$ ]]; then
                    nohup bash -c "$ASTRA_AUTOMATION --log-file \"$LOG_FILE\" --close-terminal \"$TERMINAL_PID\" --mode \"$START_MODE\" $*" >/dev/null 2>&1 &
                else
                    nohup bash -c "$ASTRA_AUTOMATION --log-file \"$LOG_FILE\" --mode \"$START_MODE\" $*" >/dev/null 2>&1 &
                fi
            fi
        fi
        PYTHON_PID=$!
        log_message "GUI запущен в фоновом режиме (PID: $PYTHON_PID)"
        PYTHON_EXIT_CODE=0
    fi
else
    if [ "$IS_BINARY" = false ]; then
        echo "   [ERR] Python 3 не найден!"
        log_message "ОШИБКА: Python 3 не найден"
        exit 1
    else
        # В бинарном режиме Python не нужен
        echo "   [i] Бинарный режим - Python не требуется"
        log_message "Бинарный режим - Python не требуется"
    fi
fi

log_message "Bash скрипт завершен с кодом: $PYTHON_EXIT_CODE"
exit $PYTHON_EXIT_CODE
