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
    
    for pkg in "${TKINTER_PACKAGES[@]}"; do
        if apt-cache show "$pkg" >/dev/null 2>&1; then
            echo "$pkg"  # Возвращаем первый найденный пакет
            return 0
        fi
    done
    
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
        
        # Устанавливаем с проверкой кода возврата
        apt-get install -y $DPKG_OPTS "$pkg" 2>&1 | tee -a "$LOG_FILE"
        local EXIT_CODE=${PIPESTATUS[0]}
        
        if [ $EXIT_CODE -eq 0 ]; then
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
export DEBIAN_PRIORITY=critical
export APT_LISTCHANGES_FRONTEND=none
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
# БЛОК 4: ОПРЕДЕЛЕНИЕ РЕЖИМА ЗАПУСКА (УМНАЯ ЛОГИКА)
# ============================================================

else
    echo ""
    echo "[*] Определяем оптимальный режим запуска..."
    log_message "Начинаем определение режима запуска"
    
    # Переменная для выбора режима
    START_MODE=""
    
    # Проверка 1: Есть ли tkinter?
    echo "   [?] Проверяем доступность tkinter..."
    if check_tkinter_available; then
        echo "   [OK] tkinter найден и работает"
        log_message "tkinter доступен - можно запускать GUI"
        START_MODE="gui_ready"
    else
        echo "   [!] tkinter не найден"
        log_message "tkinter недоступен - требуется анализ"
        
        # Проверка 2: Есть ли рабочие репозитории?
        echo "   [?] Проверяем доступность репозиториев..."
        if check_repos_available; then
            echo "   [OK] Рабочие репозитории найдены"
            log_message "Рабочие репозитории доступны"
            
            # Проверка 3: Есть ли пакет tkinter в репозиториях?
            echo "   [?] Ищем пакет tkinter в репозиториях..."
            TKINTER_PKG=$(find_tkinter_package)
            if [ $? -eq 0 ]; then
                echo "   [OK] Найден пакет: $TKINTER_PKG"
                log_message "Пакет tkinter найден в репозиториях: $TKINTER_PKG"
                START_MODE="gui_install_first"
            else
                echo "   [!] Пакет tkinter не найден в репозиториях"
                log_message "Пакет tkinter не найден - принудительный консольный режим"
                START_MODE="console_forced"
            fi
        else
            echo "   [!] Нет рабочих репозиториев (только cdrom или пусто)"
            log_message "Нет рабочих репозиториев - принудительный консольный режим"
            START_MODE="console_forced"
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
        
        apt-get update -y 2>&1 | tee -a "$LOG_FILE"
        UPDATE_EXIT_CODE=${PIPESTATUS[0]}
        
        if [ $UPDATE_EXIT_CODE -eq 0 ]; then
            echo "   [OK] Список пакетов обновлен (код: 0)"
            log_message "Список пакетов обновлен успешно (код: 0)"
        else
            echo "   [ERROR] Ошибка обновления списка пакетов (код: $UPDATE_EXIT_CODE)"
            log_message "ОШИБКА: Не удалось обновить списки пакетов (код: $UPDATE_EXIT_CODE)"
            echo "   [i] Переключение на консольный режим"
            log_message "Переключение на консольный режим из-за ошибки apt-get update"
            START_MODE="console_forced"
            CONSOLE_MODE=true
        fi
        
        # Продолжаем только если update успешен
        if [ "$START_MODE" = "gui_install_first" ]; then
            # Устанавливаем tkinter с проверкой
            if install_tkinter_with_verification; then
                echo "   [OK] tkinter установлен и работает"
                log_message "tkinter установлен и проверен"
            else
                echo "   [ERROR] Не удалось установить рабочий tkinter"
                echo "   [i] Переключение на консольный режим"
                log_message "Переключение на консольный режим - tkinter не установлен"
                START_MODE="console_forced"
                CONSOLE_MODE=true
            fi
            
            # Устанавливаем pip3 (не критично для GUI)
            if ! pip3 --version >/dev/null 2>&1; then
                echo ""
                echo "   [#] Устанавливаем pip3..."
                log_message "Устанавливаем pip3"
                apt-get install -y $DPKG_OPTS python3-pip 2>&1 | tee -a "$LOG_FILE"
                PIP_EXIT_CODE=${PIPESTATUS[0]}
                if [ $PIP_EXIT_CODE -eq 0 ]; then
                    echo "     [OK] pip3 установлен (код: 0)"
                    log_message "pip3 установлен успешно (код: 0)"
                else
                    echo "     [WARNING] Не удалось установить pip3 (код: $PIP_EXIT_CODE)"
                    log_message "ПРЕДУПРЕЖДЕНИЕ: Не удалось установить pip3 (код: $PIP_EXIT_CODE)"
                fi
            fi
            
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
    fi
    
    # Финальная проверка перед запуском GUI
    if [ "$START_MODE" = "gui_ready" ] || [ "$START_MODE" = "gui_install_first" ]; then
        echo ""
        echo "[?] Финальная проверка перед запуском GUI..."
        log_message "Финальная проверка компонентов перед запуском GUI"
        
        if ! check_tkinter_available; then
            echo "   [ERROR] tkinter все еще недоступен!"
            echo "   [i] Переключение на консольный режим"
            log_message "КРИТИЧЕСКАЯ ОШИБКА: tkinter недоступен после установки"
            START_MODE="console_forced"
            CONSOLE_MODE=true
        else
            echo "   [OK] tkinter работает - готовы к запуску GUI"
            log_message "Финальная проверка: tkinter работает, GUI готов"
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
    log_message "Подготовка компонентов завершена. Режим: $START_MODE"
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