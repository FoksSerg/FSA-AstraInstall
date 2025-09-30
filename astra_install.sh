#!/bin/bash
# ГЛАВНЫЙ СКРИПТ: Автоматическая установка и запуск GUI

# ============================================================
# БЛОК 1: ИНИЦИАЛИЗАЦИЯ ЛОГОВ И ФУНКЦИЙ
# ============================================================

# Создаем лог файл рядом с запускающим файлом
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_DIR="$SCRIPT_DIR/Log"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/astra_automation_$TIMESTAMP.log"

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

# Инициализируем лог файл
echo "============================================================" > "$LOG_FILE"
echo "ASTRA AUTOMATION - НАЧАЛО СЕССИИ" >> "$LOG_FILE"
echo "Время запуска: $(date)" >> "$LOG_FILE"
echo "Директория скрипта: $SCRIPT_DIR" >> "$LOG_FILE"
echo "Аргументы командной строки: $*" >> "$LOG_FILE"
echo "============================================================" >> "$LOG_FILE"

echo "============================================================"
echo "ASTRA AUTOMATION - АВТОМАТИЧЕСКАЯ УСТАНОВКА И ЗАПУСК"
echo "============================================================"
log_message "Начинаем выполнение astra_install.sh"

# ============================================================
# БЛОК 2: ОБРАБОТКА АРГУМЕНТОВ И ПРОВЕРКИ
# ============================================================

# Обрабатываем аргументы командной строки
CONSOLE_MODE=false
DRY_RUN=false

for arg in "$@"; do
    case $arg in
        --console)
            CONSOLE_MODE=true
            echo "[i] Режим: КОНСОЛЬНЫЙ (без GUI)"
            log_message "Включен консольный режим (--console)"
            ;;
        --dry-run)
            DRY_RUN=true
            echo "[i] Режим: ТЕСТИРОВАНИЕ (dry-run)"
            log_message "Включен режим тестирования (--dry-run)"
            ;;
        *)
            echo "[!] Неизвестный аргумент: $arg"
            log_message "Неизвестный аргумент: $arg"
            ;;
    esac
done

# Проверяем права root и автоматически перезапускаемся через sudo если нужно
if [ "$EUID" -ne 0 ]; then
    echo "[i] Требуются права root. Перезапуск через sudo..."
    log_message "Перезапуск скрипта с правами root через sudo"
    # Перезапускаем себя с sudo, передавая все аргументы
    exec sudo -E bash "$0" "$@"
    exit $?
fi

log_message "Проверка прав root: OK (запущено с правами root)"

# Синхронизация системного времени (один раз за сеанс)
TIME_SYNC_FLAG="/var/run/fsa-time-synced"

if [ -f "$TIME_SYNC_FLAG" ]; then
    echo "[i] Время уже синхронизировано в этом сеансе"
    log_message "Синхронизация времени пропущена (уже выполнена в текущем сеансе)"
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
log_message "Настроены переменные окружения для автоматических ответов"

echo "[?] Проверяем систему..."
log_message "Начинаем проверку системы"

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
# БЛОК 3: КОНСОЛЬНЫЙ РЕЖИМ
# ============================================================

if [ "$CONSOLE_MODE" = true ]; then
    echo ""
    echo "[*] Консольный режим - используем уже имеющийся Python 3"
    log_message "Консольный режим - используем уже имеющийся Python 3"
    
    # Настраиваем репозитории
    echo ""
    echo "[+] Консольный режим - сначала настраиваем репозитории!"
    log_message "Консольный режим - сначала настраиваем репозитории"
    
    echo "[*] Настраиваем репозитории для консольного режима..."
    log_message "Настраиваем репозитории для консольного режима"
    
    echo "   [?] Проверяем существующие репозитории..."
    log_message "Начинаем проверку существующих репозиториев"
    
    if [ "$DRY_RUN" = true ]; then
        echo "   [!] РЕЖИМ ТЕСТИРОВАНИЯ: репозитории НЕ изменяются (только симуляция)"
        log_message "РЕЖИМ ТЕСТИРОВАНИЯ: репозитории НЕ изменяются (только симуляция)"
        
        echo "   [i] Будет создан backup: /etc/apt/sources.list.backup"
        echo "   [i] Будет проверена доступность всех репозиториев"
        echo "   [i] Нерабочие репозитории будут закомментированы"
        echo "   [i] Рабочие репозитории останутся активными"
        
        ACTIVATED_COUNT=0
        DEACTIVATED_COUNT=0
        
        while IFS= read -r line; do
            if [[ "$line" =~ ^#?deb ]]; then
                if [[ "$line" == \#* ]]; then
                    clean_line="${line#\#}"
                    clean_line="$(echo "$clean_line" | sed 's/^[[:space:]]*//')"
                    if check_single_repo "$clean_line"; then
                        ACTIVATED_COUNT=$((ACTIVATED_COUNT + 1))
                        echo "   [OK] Будет активирован: $(echo "$clean_line" | awk '{print $2}')"
                    else
                        DEACTIVATED_COUNT=$((DEACTIVATED_COUNT + 1))
                        echo "   [ERR] Останется неактивным: $(echo "$clean_line" | awk '{print $2}')"
                    fi
                else
                    if check_single_repo "$line"; then
                        ACTIVATED_COUNT=$((ACTIVATED_COUNT + 1))
                        echo "   [OK] Останется активным: $(echo "$line" | awk '{print $2}')"
                    else
                        DEACTIVATED_COUNT=$((DEACTIVATED_COUNT + 1))
                        echo "   [ERR] Будет деактивирован: $(echo "$line" | awk '{print $2}')"
                    fi
                fi
            fi
        done < /etc/apt/sources.list
        
        echo "   [i] Статистика (симуляция): $ACTIVATED_COUNT рабочих, $DEACTIVATED_COUNT нерабочих"
        log_message "Статистика (симуляция): $ACTIVATED_COUNT рабочих, $DEACTIVATED_COUNT нерабочих"
    else
        # Реальный режим - изменяем репозитории
        cp /etc/apt/sources.list /etc/apt/sources.list.backup
        log_message "Создан backup репозиториев: /etc/apt/sources.list.backup"
        
        TEMP_FILE=$(mktemp)
        echo "# Системные репозитории - автоматически настроены (консольный режим)" > "$TEMP_FILE"
        
        ACTIVATED_COUNT=0
        DEACTIVATED_COUNT=0
        
        while IFS= read -r line; do
            if [[ "$line" =~ ^#?deb ]]; then
                if [[ "$line" == \#* ]]; then
                    clean_line="${line#\#}"
                    clean_line="$(echo "$clean_line" | sed 's/^[[:space:]]*//')"
                    if check_single_repo "$clean_line"; then
                        echo "$clean_line" >> "$TEMP_FILE"
                        ACTIVATED_COUNT=$((ACTIVATED_COUNT + 1))
                        log_message "Активирован репозиторий: $(echo "$clean_line" | awk '{print $2}')"
                    else
                        echo "$line" >> "$TEMP_FILE"
                        DEACTIVATED_COUNT=$((DEACTIVATED_COUNT + 1))
                        log_message "Оставлен неактивным репозиторий: $(echo "$clean_line" | awk '{print $2}')"
                    fi
                else
                    if check_single_repo "$line"; then
                        echo "$line" >> "$TEMP_FILE"
                        ACTIVATED_COUNT=$((ACTIVATED_COUNT + 1))
                        log_message "Оставлен активным репозиторий: $(echo "$line" | awk '{print $2}')"
                    else
                        echo "# $line" >> "$TEMP_FILE"
                        DEACTIVATED_COUNT=$((DEACTIVATED_COUNT + 1))
                        log_message "Деактивирован репозиторий: $(echo "$line" | awk '{print $2}')"
                    fi
                fi
            else
                echo "$line" >> "$TEMP_FILE"
            fi
        done < /etc/apt/sources.list
        
        UNIQUE_TEMP_FILE=$(mktemp)
        awk '!seen[$0]++' "$TEMP_FILE" > "$UNIQUE_TEMP_FILE"
        mv "$UNIQUE_TEMP_FILE" "$TEMP_FILE"
        
        cp "$TEMP_FILE" /etc/apt/sources.list
        rm -f "$TEMP_FILE"
        
        echo "   [OK] Репозитории настроены: $ACTIVATED_COUNT рабочих, $DEACTIVATED_COUNT нерабочих"
        log_message "Репозитории настроены: $ACTIVATED_COUNT рабочих, $DEACTIVATED_COUNT нерабочих"
    fi
    
    echo ""
    echo "[+] Консольный режим готов!"
    log_message "Консольный режим готов"
    
# ============================================================
# БЛОК 4: GUI РЕЖИМ
# ============================================================

else
    echo ""
    echo "[*] Проверяем компоненты для GUI..."
    log_message "Начинаем проверку компонентов для GUI"
    
    NEED_TKINTER=false
    NEED_PIP=false
    NEED_PYTHON3=false
    
    if ! python3 --version >/dev/null 2>&1; then
        echo "   [ERR] Python 3 не найден"
        log_message "Python 3 не найден - требуется установка"
        NEED_PYTHON3=true
    else
        echo "   [OK] Python 3 найден"
        log_message "Python 3 найден - OK"
    fi
    
    if ! python3 -c "import tkinter" >/dev/null 2>&1; then
        echo "   [ERR] Tkinter не найден"
        log_message "Tkinter не найден - требуется установка"
        NEED_TKINTER=true
    else
        echo "   [OK] Tkinter найден"
        log_message "Tkinter найден - OK"
    fi
    
    if ! pip3 --version >/dev/null 2>&1; then
        echo "   [ERR] pip3 не найден"
        log_message "pip3 не найден - требуется установка"
        NEED_PIP=true
    else
        echo "   [OK] pip3 найден"
        log_message "pip3 найден - OK"
    fi
    
    # Если что-то нужно установить
    if [ "$NEED_PYTHON3" = true ] || [ "$NEED_TKINTER" = true ] || [ "$NEED_PIP" = true ]; then
        echo ""
        echo "[#] Устанавливаем недостающие компоненты..."
        log_message "Начинаем установку недостающих компонентов"
        
        echo ""
        echo "[~] Обновляем список пакетов..."
        log_message "Начинаем обновление списка пакетов (apt-get update)"
        
        if apt-get update -y 2>&1 | tee -a "$LOG_FILE"; then
            echo "   [OK] Список пакетов обновлен"
            log_message "Список пакетов обновлен успешно"
        else
            echo "   [!] Ошибка обновления списка пакетов, но продолжаем"
            log_message "Ошибка обновления списка пакетов, но продолжаем"
        fi
        
        if [ "$NEED_PYTHON3" = true ]; then
            echo "   [#] Устанавливаем Python 3..."
            log_message "Устанавливаем Python 3"
            if apt-get install -y python3 2>&1 | tee -a "$LOG_FILE"; then
                echo "     [OK] Python 3 установлен"
                log_message "Python 3 установлен успешно"
            else
                echo "     [ERR] Не удалось установить Python 3"
                log_message "ОШИБКА: Не удалось установить Python 3"
            fi
        fi
        
        if [ "$NEED_TKINTER" = true ]; then
            echo "   [#] Устанавливаем Tkinter..."
            log_message "Устанавливаем Tkinter"
            if apt-get install -y python3-tk 2>&1 | tee -a "$LOG_FILE"; then
                echo "     [OK] python3-tk установлен"
                log_message "python3-tk установлен успешно"
            else
                echo "     [ERR] Не удалось установить python3-tk"
                log_message "ОШИБКА: Не удалось установить python3-tk"
            fi
        fi
        
        if [ "$NEED_PIP" = true ]; then
            echo "   [#] Устанавливаем pip3..."
            log_message "Устанавливаем pip3"
            if apt-get install -y python3-pip 2>&1 | tee -a "$LOG_FILE"; then
                echo "     [OK] python3-pip установлен"
                log_message "python3-pip установлен успешно"
            else
                echo "     [ERR] Не удалось установить python3-pip"
                log_message "ОШИБКА: Не удалось установить python3-pip"
            fi
        fi
        
        echo ""
        echo "[*] Исправляем зависимости..."
        log_message "Исправляем зависимости (apt-get install -f)"
        if apt-get install -f -y 2>&1 | tee -a "$LOG_FILE"; then
            echo "   [OK] Зависимости исправлены"
            log_message "Зависимости исправлены успешно"
        else
            echo "   [!] Ошибка исправления зависимостей, но продолжаем"
            log_message "Ошибка исправления зависимостей, но продолжаем"
        fi
    fi
    
    echo ""
    echo "[?] Проверяем результат..."
    log_message "Начинаем финальную проверку установленных компонентов"
    
    echo "   [i] Python 3: $(python3 --version 2>/dev/null || echo 'не работает')"
    echo "   [i] Tkinter: $(python3 -c 'import tkinter; print("работает")' 2>/dev/null || echo 'не работает')"
    echo "   [i] pip3: $(pip3 --version 2>/dev/null || echo 'не работает')"
    log_message "Финальная проверка: Python 3: $(python3 --version 2>/dev/null || echo 'не работает')"
    log_message "Финальная проверка: Tkinter: $(python3 -c 'import tkinter; print("работает")' 2>/dev/null || echo 'не работает')"
    log_message "Финальная проверка: pip3: $(pip3 --version 2>/dev/null || echo 'не работает')"
    
    echo ""
    echo "[+] Установка завершена!"
    log_message "Установка компонентов завершена"
fi

# ============================================================
# БЛОК 5: ЗАПУСК PYTHON СКРИПТА
# ============================================================

echo ""
if [ "$CONSOLE_MODE" = true ]; then
    echo "[>] Запускаем консольный режим..."
    log_message "Запускаем консольный режим"
else
    echo "[>] Запускаем графический интерфейс..."
    log_message "Запускаем графический интерфейс"
fi

log_message "Передаем управление Python скрипту: astra-automation.py"
log_message "Лог файл: $LOG_FILE"

if python3 --version >/dev/null 2>&1; then
    echo "   [i] Используем Python 3: $(python3 --version)"
    log_message "Используем Python 3: $(python3 --version)"
    
    if [ "$CONSOLE_MODE" = true ]; then
        # Консольный режим - запускаем в текущем терминале
        python3 astra-automation.py --log-file "$LOG_FILE" "$@"
        PYTHON_EXIT_CODE=$?
    else
        # GUI режим - запускаем в фоне и передаем PID терминала для закрытия
        echo "   [i] GUI запускается в фоновом режиме"
        echo "   [i] Окно терминала закроется автоматически после запуска GUI"
        log_message "GUI запускается в фоновом режиме (детачится от терминала)"
        
        # Получаем PID родительского терминала (процесс окна терминала, не bash скрипта)
        # $PPID - это PID родителя текущего скрипта, нужен родитель родителя
        TERM_PID=$(ps -o ppid= -p $PPID | tr -d ' ')
        log_message "PID bash скрипта: $PPID"
        log_message "PID окна терминала: $TERM_PID"
        
        # Запускаем GUI с передачей PID терминала для автозакрытия
        nohup python3 astra-automation.py --log-file "$LOG_FILE" --close-terminal "$TERM_PID" "$@" >/dev/null 2>&1 &
        PYTHON_PID=$!
        
        echo "   [OK] GUI запущен (PID: $PYTHON_PID)"
        echo "   [i] Терминал закроется автоматически после полного запуска GUI"
        log_message "GUI запущен в фоновом режиме (PID: $PYTHON_PID)"
        log_message "GUI закроет терминал (PID: $TERM_PID) после полного запуска"
        
        PYTHON_EXIT_CODE=0
    fi
else
    echo "   [ERR] Python 3 не найден!"
    log_message "ОШИБКА: Python 3 не найден"
    exit 1
fi

log_message "Bash скрипт завершен с кодом: $PYTHON_EXIT_CODE"
exit $PYTHON_EXIT_CODE