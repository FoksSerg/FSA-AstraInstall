#!/bin/bash
# ГЛАВНЫЙ СКРИПТ: Автоматическая установка и запуск GUI

# ============================================================
# БЛОК 1: ИНИЦИАЛИЗАЦИЯ ЛОГОВ И ФУНКЦИЙ
# ============================================================

# Создаем лог файл рядом с запускающим файлом
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="$SCRIPT_DIR/astra_automation_$TIMESTAMP.log"

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
        echo "   ⚠️ Компакт-диск: $(echo "$repo_line" | awk '{print $2}') - отключаем"
        log_message "Компакт-диск репозиторий отключен: $(echo "$repo_line" | awk '{print $2}')"
        rm -f "$test_file"
        return 1  # Возвращаем 1 чтобы репозиторий был отключен
    fi

    if apt-get update -o Dir::Etc::sourcelist="$test_file" -o Dir::Etc::sourceparts="-" -o APT::Get::List-Cleanup="0" &>/dev/null; then
        echo "   ✅ Рабочий: $(echo "$repo_line" | awk '{print $2}')"
        log_message "Репозиторий рабочий: $(echo "$repo_line" | awk '{print $2}')"
        rm -f "$test_file"
        return 0
    else
        echo "   ❌ Не доступен: $(echo "$repo_line" | awk '{print $2}')"
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
            echo "📋 Режим: КОНСОЛЬНЫЙ (без GUI)"
            log_message "Включен консольный режим (--console)"
            ;;
        --dry-run)
            DRY_RUN=true
            echo "📋 Режим: ТЕСТИРОВАНИЕ (dry-run)"
            log_message "Включен режим тестирования (--dry-run)"
            ;;
        *)
            echo "⚠️ Неизвестный аргумент: $arg"
            log_message "Неизвестный аргумент: $arg"
            ;;
    esac
done

# Проверяем права root
if [ "$EUID" -ne 0 ]; then
    echo "❌ Требуются права root для установки пакетов"
    log_message "ОШИБКА: Требуются права root для установки пакетов"
    echo "Запустите: sudo bash astra_install.sh"
    exit 1
fi

log_message "Проверка прав root: OK (запущено с правами root)"

# Настраиваем переменные окружения для автоматических ответов
export DEBIAN_FRONTEND=noninteractive
log_message "Настроены переменные окружения для автоматических ответов"

echo "🔍 Проверяем систему..."
log_message "Начинаем проверку системы"

# Проверяем версию Astra Linux
if [ -f /etc/astra_version ]; then
    ASTRA_VERSION=$(cat /etc/astra_version)
    echo "   📋 Версия Astra Linux: $ASTRA_VERSION"
    log_message "Версия Astra Linux: $ASTRA_VERSION"
else
    echo "   ⚠️ Не удалось определить версию Astra Linux"
    log_message "Не удалось определить версию Astra Linux"
fi

# Проверяем Python
PYTHON3_VERSION=$(python3 --version 2>/dev/null || echo 'не найден')
echo "   📋 Python 3: $PYTHON3_VERSION"
log_message "Python 3: $PYTHON3_VERSION"

# ============================================================
# БЛОК 3: КОНСОЛЬНЫЙ РЕЖИМ
# ============================================================

if [ "$CONSOLE_MODE" = true ]; then
    echo ""
    echo "🔧 Консольный режим - используем уже имеющийся Python 3"
    log_message "Консольный режим - используем уже имеющийся Python 3"
    
    # Настраиваем репозитории
    echo ""
    echo "🎉 Консольный режим - сначала настраиваем репозитории!"
    log_message "Консольный режим - сначала настраиваем репозитории"
    
    echo "🔧 Настраиваем репозитории для консольного режима..."
    log_message "Настраиваем репозитории для консольного режима"
    
    echo "   🔍 Проверяем существующие репозитории..."
    log_message "Начинаем проверку существующих репозиториев"
    
    if [ "$DRY_RUN" = true ]; then
        echo "   ⚠️ РЕЖИМ ТЕСТИРОВАНИЯ: репозитории НЕ изменяются (только симуляция)"
        log_message "РЕЖИМ ТЕСТИРОВАНИЯ: репозитории НЕ изменяются (только симуляция)"
        
        echo "   📋 Будет создан backup: /etc/apt/sources.list.backup"
        echo "   📋 Будет проверена доступность всех репозиториев"
        echo "   📋 Нерабочие репозитории будут закомментированы"
        echo "   📋 Рабочие репозитории останутся активными"
        
        ACTIVATED_COUNT=0
        DEACTIVATED_COUNT=0
        
        while IFS= read -r line; do
            if [[ "$line" =~ ^#?deb ]]; then
                if [[ "$line" == \#* ]]; then
                    clean_line="${line#\#}"
                    clean_line="$(echo "$clean_line" | sed 's/^[[:space:]]*//')"
                    if check_single_repo "$clean_line"; then
                        ACTIVATED_COUNT=$((ACTIVATED_COUNT + 1))
                        echo "   ✅ Будет активирован: $(echo "$clean_line" | awk '{print $2}')"
                    else
                        DEACTIVATED_COUNT=$((DEACTIVATED_COUNT + 1))
                        echo "   ❌ Останется неактивным: $(echo "$clean_line" | awk '{print $2}')"
                    fi
                else
                    if check_single_repo "$line"; then
                        ACTIVATED_COUNT=$((ACTIVATED_COUNT + 1))
                        echo "   ✅ Останется активным: $(echo "$line" | awk '{print $2}')"
                    else
                        DEACTIVATED_COUNT=$((DEACTIVATED_COUNT + 1))
                        echo "   ❌ Будет деактивирован: $(echo "$line" | awk '{print $2}')"
                    fi
                fi
            fi
        done < /etc/apt/sources.list
        
        echo "   📊 Статистика (симуляция): $ACTIVATED_COUNT рабочих, $DEACTIVATED_COUNT нерабочих"
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
        
        echo "   ✅ Репозитории настроены: $ACTIVATED_COUNT рабочих, $DEACTIVATED_COUNT нерабочих"
        log_message "Репозитории настроены: $ACTIVATED_COUNT рабочих, $DEACTIVATED_COUNT нерабочих"
    fi
    
    echo ""
    echo "🎉 Консольный режим готов!"
    log_message "Консольный режим готов"
    
# ============================================================
# БЛОК 4: GUI РЕЖИМ
# ============================================================

else
    echo ""
    echo "🔧 Проверяем компоненты для GUI..."
    log_message "Начинаем проверку компонентов для GUI"
    
    NEED_TKINTER=false
    NEED_PIP=false
    NEED_PYTHON3=false
    
    if ! python3 --version >/dev/null 2>&1; then
        echo "   ❌ Python 3 не найден"
        log_message "Python 3 не найден - требуется установка"
        NEED_PYTHON3=true
    else
        echo "   ✅ Python 3 найден"
        log_message "Python 3 найден - OK"
    fi
    
    if ! python3 -c "import tkinter" >/dev/null 2>&1; then
        echo "   ❌ Tkinter не найден"
        log_message "Tkinter не найден - требуется установка"
        NEED_TKINTER=true
    else
        echo "   ✅ Tkinter найден"
        log_message "Tkinter найден - OK"
    fi
    
    if ! pip3 --version >/dev/null 2>&1; then
        echo "   ❌ pip3 не найден"
        log_message "pip3 не найден - требуется установка"
        NEED_PIP=true
    else
        echo "   ✅ pip3 найден"
        log_message "pip3 найден - OK"
    fi
    
    # Если что-то нужно установить
    if [ "$NEED_PYTHON3" = true ] || [ "$NEED_TKINTER" = true ] || [ "$NEED_PIP" = true ]; then
        echo ""
        echo "📦 Устанавливаем недостающие компоненты..."
        log_message "Начинаем установку недостающих компонентов"
        
        echo ""
        echo "🔄 Обновляем список пакетов..."
        log_message "Начинаем обновление списка пакетов (apt-get update)"
        
        if apt-get update -y 2>&1 | tee -a "$LOG_FILE"; then
            echo "   ✅ Список пакетов обновлен"
            log_message "Список пакетов обновлен успешно"
        else
            echo "   ⚠️ Ошибка обновления списка пакетов, но продолжаем"
            log_message "Ошибка обновления списка пакетов, но продолжаем"
        fi
        
        if [ "$NEED_PYTHON3" = true ]; then
            echo "   📥 Устанавливаем Python 3..."
            log_message "Устанавливаем Python 3"
            if apt-get install -y python3 2>&1 | tee -a "$LOG_FILE"; then
                echo "     ✅ Python 3 установлен"
                log_message "Python 3 установлен успешно"
            else
                echo "     ❌ Не удалось установить Python 3"
                log_message "ОШИБКА: Не удалось установить Python 3"
            fi
        fi
        
        if [ "$NEED_TKINTER" = true ]; then
            echo "   📥 Устанавливаем Tkinter..."
            log_message "Устанавливаем Tkinter"
            if apt-get install -y python3-tk 2>&1 | tee -a "$LOG_FILE"; then
                echo "     ✅ python3-tk установлен"
                log_message "python3-tk установлен успешно"
            else
                echo "     ❌ Не удалось установить python3-tk"
                log_message "ОШИБКА: Не удалось установить python3-tk"
            fi
        fi
        
        if [ "$NEED_PIP" = true ]; then
            echo "   📥 Устанавливаем pip3..."
            log_message "Устанавливаем pip3"
            if apt-get install -y python3-pip 2>&1 | tee -a "$LOG_FILE"; then
                echo "     ✅ python3-pip установлен"
                log_message "python3-pip установлен успешно"
            else
                echo "     ❌ Не удалось установить python3-pip"
                log_message "ОШИБКА: Не удалось установить python3-pip"
            fi
        fi
        
        echo ""
        echo "🔧 Исправляем зависимости..."
        log_message "Исправляем зависимости (apt-get install -f)"
        if apt-get install -f -y 2>&1 | tee -a "$LOG_FILE"; then
            echo "   ✅ Зависимости исправлены"
            log_message "Зависимости исправлены успешно"
        else
            echo "   ⚠️ Ошибка исправления зависимостей, но продолжаем"
            log_message "Ошибка исправления зависимостей, но продолжаем"
        fi
    fi
    
    echo ""
    echo "🧪 Проверяем результат..."
    log_message "Начинаем финальную проверку установленных компонентов"
    
    echo "   📋 Python 3: $(python3 --version 2>/dev/null || echo 'не работает')"
    echo "   📋 Tkinter: $(python3 -c 'import tkinter; print("работает")' 2>/dev/null || echo 'не работает')"
    echo "   📋 pip3: $(pip3 --version 2>/dev/null || echo 'не работает')"
    log_message "Финальная проверка: Python 3: $(python3 --version 2>/dev/null || echo 'не работает')"
    log_message "Финальная проверка: Tkinter: $(python3 -c 'import tkinter; print("работает")' 2>/dev/null || echo 'не работает')"
    log_message "Финальная проверка: pip3: $(pip3 --version 2>/dev/null || echo 'не работает')"
    
    echo ""
    echo "🎉 Установка завершена!"
    log_message "Установка компонентов завершена"
fi

# ============================================================
# БЛОК 5: ЗАПУСК PYTHON СКРИПТА
# ============================================================

echo ""
if [ "$CONSOLE_MODE" = true ]; then
    echo "🚀 Запускаем консольный режим..."
    log_message "Запускаем консольный режим"
else
    echo "🚀 Запускаем графический интерфейс..."
    log_message "Запускаем графический интерфейс"
fi

log_message "Передаем управление Python скрипту: astra-automation.py"
log_message "Лог файл: $LOG_FILE"

if python3 --version >/dev/null 2>&1; then
    echo "   📋 Используем Python 3: $(python3 --version)"
    log_message "Используем Python 3: $(python3 --version)"
    python3 astra-automation.py --log-file "$LOG_FILE" "$@"
    PYTHON_EXIT_CODE=$?
else
    echo "   ❌ Python 3 не найден!"
    log_message "ОШИБКА: Python 3 не найден"
    exit 1
fi

log_message "Python скрипт завершен с кодом: $PYTHON_EXIT_CODE"
exit $PYTHON_EXIT_CODE