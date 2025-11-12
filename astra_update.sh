#!/bin/bash
# Скрипт автоматического обновления FSA-AstraInstall для Linux
# Копирует файлы из сетевой папки и запускает установку
# Версия: V2.5.116 (2025.11.12)
# Компания: ООО "НПА Вира-Реалтайм"

# ============================================================================
# ПАРАМЕТРЫ ПОДКЛЮЧЕНИЯ К СЕРВЕРУ (настройка)
# ============================================================================
SMB_SERVER="10.10.55.77"          # IP адрес или имя SMB сервера
SMB_SHARE="Install"                # Имя SMB шары
SMB_PATH="ISO/Linux/Astra"         # Путь к папке с файлами на сервере
SMB_USER="FokinSA"                 # Имя пользователя для подключения
# ============================================================================

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

# Универсальная функция разворачивания окна терминала (для запроса пароля)
restore_terminal_window() {
    if ! command -v xdotool >/dev/null 2>&1; then
        return 0  # xdotool недоступен, выходим тихо
    fi
    
    local terminal_pid="$1"
    
    # Если передан PID терминала, используем его
    if [ ! -z "$terminal_pid" ] && [ "$terminal_pid" != "0" ]; then
        WINDOW_IDS=$(xdotool search --pid "$terminal_pid" 2>/dev/null)
        if [ -n "$WINDOW_IDS" ]; then
            for window in $WINDOW_IDS; do
                xdotool windowactivate "$window" 2>/dev/null
                xdotool windowraise "$window" 2>/dev/null
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
                xdotool windowactivate "$window" 2>/dev/null
                xdotool windowraise "$window" 2>/dev/null
            done
        fi
    fi
}

# Пути для Linux
LINUX_SMB_PATH="smb://${SMB_SERVER}/${SMB_SHARE}/${SMB_PATH}"
LINUX_ASTRA_PATH="$(dirname "$0")"  # Папка где находится скрипт

# Файлы для копирования
FILES_TO_COPY=(
    "astra_automation.py"
    "astra_install.sh"
    "astra_update.sh"
    "README.md"
    "WINE_INSTALL_GUIDE.md"
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

# Определяем правильную переменную для пропуска терминала (после sudo используем SKIP_TERMINAL_AFTER_SUDO)
if [ ! -z "$SKIP_TERMINAL_AFTER_SUDO" ]; then
    SKIP_TERMINAL="$SKIP_TERMINAL_AFTER_SUDO"
fi

# Проверяем доступность сервера
log_message "Проверка доступности сервера ${SMB_SERVER}..."
ping -c 1 -W 3 "${SMB_SERVER}" >/dev/null 2>&1
if [ $? -eq 0 ]; then
    log_message "Сервер доступен"
    SERVER_AVAILABLE=true
else
    log_message "Сервер ${SMB_SERVER} недоступен. Продолжаем без обновления."
    SERVER_AVAILABLE=false
fi

# Инициализация флага успешности обновления
UPDATE_SUCCESSFUL=false

# Работа с обновлением только если сервер доступен
if [ "$SERVER_AVAILABLE" = true ]; then
    # Используем smbclient с сохраненными учетными данными
    log_message "Подключение к SMB с учетными данными ${SMB_USER}..."
    
    # Создаем папку назначения
    mkdir -p "$LINUX_ASTRA_PATH" 2>/dev/null
    
    # Файл с учетными данными
    CREDENTIALS_FILE="$HOME/.smbcredentials"
    
    # Проверяем, есть ли файл с учетными данными
    if [ ! -f "$CREDENTIALS_FILE" ]; then
        log_message "Файл учетных данных не найден. Создаем..."
        echo "username=${SMB_USER}" > "$CREDENTIALS_FILE"
        echo "password=" >> "$CREDENTIALS_FILE"
        chmod 600 "$CREDENTIALS_FILE"
        
        # Разворачиваем терминал для запроса пароля (НЕ в консольном режиме)
        if command -v xdotool >/dev/null 2>&1 && [ "$SKIP_TERMINAL" != "true" ]; then
            restore_terminal_window "$TERMINAL_PID"
        fi
        
        log_message "Введите пароль для пользователя ${SMB_USER}:"
        read -s password
        echo "password=$password" > "$CREDENTIALS_FILE"
        echo "username=${SMB_USER}" >> "$CREDENTIALS_FILE"
        chmod 600 "$CREDENTIALS_FILE"
        log_message "Учетные данные сохранены"
        
        # Сворачиваем терминал после запроса пароля (НЕ в консольном режиме)
        if [ "$SKIP_TERMINAL" != "true" ]; then
            minimize_terminal_window "$TERMINAL_PID"
        fi
    fi
    
    # Копируем файлы с обработкой ошибок авторизации
    log_message "Копирование файлов из сети..."
    
    # Первая попытка копирования
    COPY_SUCCESS=true
    AUTH_ERROR=false
    COPIED_COUNT=0
    
    for file in "${FILES_TO_COPY[@]}"; do
        log_message "Копируем: $file"
        # Сохраняем stderr для анализа ошибки
        ERROR_OUTPUT=$(smbclient //${SMB_SERVER}/${SMB_SHARE} -A "$CREDENTIALS_FILE" -c "get ${SMB_PATH}/$file $LINUX_ASTRA_PATH/$file" 2>&1 >/dev/null)
        COPY_RESULT=$?
        
        if [ $COPY_RESULT -eq 0 ]; then
            log_message "Скопирован: $file"
            COPIED_COUNT=$((COPIED_COUNT + 1))
        else
            # Анализируем тип ошибки
            if echo "$ERROR_OUTPUT" | grep -qiE "(NT_STATUS_LOGON_FAILURE|NT_STATUS_WRONG_PASSWORD|authentication failed|access denied|login failed)"; then
                log_message "ОШИБКА: Ошибка авторизации при копировании $file"
                AUTH_ERROR=true
                COPY_SUCCESS=false
                break  # Прерываем цикл для запроса пароля
            else
                # Файл не найден или другая ошибка - пропускаем и продолжаем
                log_message "ПРЕДУПРЕЖДЕНИЕ: Файл $file не найден или недоступен. Пропускаем."
                # Не устанавливаем COPY_SUCCESS=false, продолжаем копирование других файлов
            fi
        fi
    done
    
    # Если первая попытка неудачна из-за ошибки авторизации - запрашиваем пароль заново
    if [ "$AUTH_ERROR" = true ]; then
        log_message "Ошибка авторизации. Запрашиваем пароль заново..."
        
        # Разворачиваем терминал для запроса пароля (НЕ в консольном режиме)
        if command -v xdotool >/dev/null 2>&1 && [ "$SKIP_TERMINAL" != "true" ]; then
            restore_terminal_window "$TERMINAL_PID"
        fi
        
        log_message "Введите пароль для пользователя ${SMB_USER}:"
        read -s password
        echo "password=$password" > "$CREDENTIALS_FILE"
        echo "username=${SMB_USER}" >> "$CREDENTIALS_FILE"
        chmod 600 "$CREDENTIALS_FILE"
        log_message "Учетные данные обновлены"
        
        # Сворачиваем терминал после запроса пароля (НЕ в консольном режиме)
        if [ "$SKIP_TERMINAL" != "true" ]; then
            minimize_terminal_window "$TERMINAL_PID"
        fi
        
        # Вторая попытка копирования (только если была ошибка авторизации)
        COPY_SUCCESS=true
        AUTH_ERROR=false
        for file in "${FILES_TO_COPY[@]}"; do
            log_message "Копируем: $file (повторная попытка)"
            ERROR_OUTPUT=$(smbclient //${SMB_SERVER}/${SMB_SHARE} -A "$CREDENTIALS_FILE" -c "get ${SMB_PATH}/$file $LINUX_ASTRA_PATH/$file" 2>&1 >/dev/null)
            COPY_RESULT=$?
            
            if [ $COPY_RESULT -eq 0 ]; then
                log_message "Скопирован: $file"
                COPIED_COUNT=$((COPIED_COUNT + 1))
            else
                # При повторной попытке тоже анализируем ошибку
                if echo "$ERROR_OUTPUT" | grep -qiE "(NT_STATUS_LOGON_FAILURE|NT_STATUS_WRONG_PASSWORD|authentication failed|access denied|login failed)"; then
                    log_message "ОШИБКА: Ошибка авторизации при копировании $file (повторная попытка)"
                    AUTH_ERROR=true
                    COPY_SUCCESS=false
                else
                    log_message "ПРЕДУПРЕЖДЕНИЕ: Файл $file не найден или недоступен. Пропускаем."
                    # Продолжаем копирование других файлов
                fi
            fi
        done
    fi
    
    # Обработка результата обновления
    if [ $COPIED_COUNT -gt 0 ]; then
        log_message "Скопировано файлов: $COPIED_COUNT из ${#FILES_TO_COPY[@]}"
        if [ "$COPY_SUCCESS" = true ] && [ $COPIED_COUNT -eq ${#FILES_TO_COPY[@]} ]; then
            log_message "Все файлы успешно скопированы!"
        else
            log_message "Некоторые файлы не были скопированы, но продолжаем работу."
        fi
        UPDATE_SUCCESSFUL=true
        
        # Сворачиваем терминал после копирования файлов (на всякий случай)
        # НЕ сворачиваем в консольном режиме
        if [ "$SKIP_TERMINAL" != "true" ]; then
            minimize_terminal_window "$TERMINAL_PID"
        fi
    else
        if [ "$AUTH_ERROR" = true ]; then
            log_message "Не удалось обновить файлы из-за ошибки авторизации. Продолжаем без обновления."
        else
            log_message "Не удалось обновить файлы. Продолжаем без обновления."
        fi
        UPDATE_SUCCESSFUL=false
    fi
else
    log_message "Обновление пропущено (сервер недоступен)"
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
