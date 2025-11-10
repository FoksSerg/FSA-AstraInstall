#!/bin/bash
# Скрипт автоматического обновления FSA-AstraInstall для Linux
# Копирует файлы из сетевой папки и запускает установку
# Версия: V2.4.112 (2025.11.05)
# Компания: ООО "НПА Вира-Реалтайм"

# Функция логирования
log_message() {
    echo "[$(date '+%H:%M:%S')] $1"
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

# Пути для Linux
LINUX_SMB_PATH="smb://10.10.55.77/Install/ISO/Linux/Astra"
LINUX_ASTRA_PATH="$(dirname "$0")"  # Папка где находится скрипт

# Файлы для копирования
FILES_TO_COPY=(
    "astra_automation.py"
    "astra_install.sh"
    "astra_update.sh"
)

log_message "Запуск обновления FSA-AstraInstall"

# Определяем PID терминала ДО запуска с sudo
TERMINAL_PID=""

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

export TERMINAL_PID

# Проверяем, не в консольном режиме ли мы
SKIP_TERMINAL=false
for arg in "$@"; do
    if [[ "$arg" == "--console" ]]; then
        SKIP_TERMINAL=true
        break
    fi
done

# Сворачиваем окно терминала (ДО sudo, если доступен xdotool)
# НЕ сворачиваем в консольном режиме
if command -v xdotool >/dev/null 2>&1 && [ "$SKIP_TERMINAL" != "true" ]; then
    minimize_terminal_window "$TERMINAL_PID"  # Сворачиваем терминал по PID
fi

# Проверяем права root
if [ "$EUID" -ne 0 ]; then
    log_message "Запуск с правами root (передаем PID терминала через аргумент)..."
    sudo "$0" --terminal-pid "$TERMINAL_PID" "$@" 2>/dev/null
    exit $?
fi

# КРИТИЧНО: Если мы получили PID через аргумент, используем его (НЕ перезапускаем поиск!)
if [ ! -z "$1" ] && [[ "$1" == "--terminal-pid" ]]; then
    TERMINAL_PID="$2"
    log_message "Используем переданный PID терминала: $TERMINAL_PID"
    shift 2  # Убираем --terminal-pid и значение из аргументов
    
    # Проверяем, не в консольном режиме ли мы
    SKIP_TERMINAL_AFTER_SUDO=false
    for arg in "$@"; do
        if [[ "$arg" == "--console" ]]; then
            SKIP_TERMINAL_AFTER_SUDO=true
            break
        fi
    done
    
    # Сворачиваем терминал ПОСЛЕ sudo (если передан TERMINAL_PID)
    # НЕ сворачиваем в консольном режиме
    if [ "$SKIP_TERMINAL_AFTER_SUDO" != "true" ]; then
        minimize_terminal_window "$TERMINAL_PID"
    fi
fi

# Сохраняем оставшиеся аргументы для передачи в astra_install.sh
INSTALL_ARGS=("$@")

# Проверяем доступность сервера
log_message "Проверка доступности сервера 10.10.55.77..."
ping -c 1 -W 3 10.10.55.77 >/dev/null 2>&1
if [ $? -eq 0 ]; then
    log_message "Сервер доступен"
else
    log_message "ОШИБКА: Сервер 10.10.55.77 недоступен"
    echo "Ошибка Обновления"
    exit 1
fi

# Используем smbclient с сохраненными учетными данными
log_message "Подключение к SMB с учетными данными FokinSA..."

# Создаем папку назначения
mkdir -p "$LINUX_ASTRA_PATH" 2>/dev/null

# Файл с учетными данными
CREDENTIALS_FILE="$HOME/.smbcredentials"

# Проверяем, есть ли файл с учетными данными
if [ ! -f "$CREDENTIALS_FILE" ]; then
    log_message "Файл учетных данных не найден. Создаем..."
    echo "username=FokinSA" > "$CREDENTIALS_FILE"
    echo "password=" >> "$CREDENTIALS_FILE"
    chmod 600 "$CREDENTIALS_FILE"
    log_message "Введите пароль для пользователя FokinSA:"
    read -s password
    echo "password=$password" > "$CREDENTIALS_FILE"
    echo "username=FokinSA" >> "$CREDENTIALS_FILE"
    chmod 600 "$CREDENTIALS_FILE"
    log_message "Учетные данные сохранены"
    # Сворачиваем терминал после запроса пароля (НЕ в консольном режиме)
    if [ "$SKIP_TERMINAL" != "true" ]; then
        minimize_terminal_window "$TERMINAL_PID"
    fi
fi

# Копируем файлы используя сохраненные учетные данные
log_message "Копирование файлов из сети..."
for file in "${FILES_TO_COPY[@]}"; do
    log_message "Копируем: $file"
    smbclient //10.10.55.77/Install -A "$CREDENTIALS_FILE" -c "get ISO/Linux/Astra/$file $LINUX_ASTRA_PATH/$file" 2>/dev/null
    if [ $? -eq 0 ]; then
        log_message "Скопирован: $file"
    else
        log_message "ОШИБКА: Не удалось скопировать $file"
        echo "Ошибка Обновления"
        exit 1
    fi
done

log_message "Все файлы успешно скопированы!"

# Сворачиваем терминал после копирования файлов (на всякий случай)
# НЕ сворачиваем в консольном режиме
if [ "$SKIP_TERMINAL" != "true" ]; then
    minimize_terminal_window "$TERMINAL_PID"
fi

# Очищаем логи (ОТКЛЮЧЕНО для сохранения диагностики)
log_message "Очистка старых логов ОТКЛЮЧЕНА для сохранения диагностики..."
# rm -rf "$LINUX_ASTRA_PATH/Log" 2>/dev/null
log_message "Старые логи НЕ удалены (сохранены для диагностики)"

# Устанавливаем права
log_message "Установка прав на выполнение..."
chmod +x "$LINUX_ASTRA_PATH/astra_install.sh" 2>/dev/null
chmod +x "$LINUX_ASTRA_PATH/astra_update.sh" 2>/dev/null
log_message "Права установлены"

# Запускаем установку
log_message "Запуск установки..."
cd "$LINUX_ASTRA_PATH" 2>/dev/null
if [ -f "astra_install.sh" ]; then
    # Проверяем, передан ли --console, и добавляем --mode console_forced
    ADD_MODE_ARG=""
    for arg in "${INSTALL_ARGS[@]}"; do
        if [[ "$arg" == "--console" ]]; then
            ADD_MODE_ARG="--mode console_forced"
            break
        fi
    done
    
    if [ ${#INSTALL_ARGS[@]} -gt 0 ]; then
        if [ -n "$ADD_MODE_ARG" ]; then
            log_message "Запускаем: ./astra_install.sh --terminal-pid $TERMINAL_PID --windows-minimized ${INSTALL_ARGS[*]} $ADD_MODE_ARG"
            ./astra_install.sh --terminal-pid "$TERMINAL_PID" --windows-minimized "${INSTALL_ARGS[@]}" "$ADD_MODE_ARG"
        else
            log_message "Запускаем: ./astra_install.sh --terminal-pid $TERMINAL_PID --windows-minimized ${INSTALL_ARGS[*]}"
            ./astra_install.sh --terminal-pid "$TERMINAL_PID" --windows-minimized "${INSTALL_ARGS[@]}"
        fi
    else
        log_message "Запускаем: ./astra_install.sh --terminal-pid $TERMINAL_PID --windows-minimized"
        ./astra_install.sh --terminal-pid "$TERMINAL_PID" --windows-minimized
    fi
else
    log_message "ОШИБКА: Файл astra_install.sh не найден"
    echo "Ошибка Обновления"
    exit 1
fi
