#!/bin/bash
# Скрипт автоматического обновления FSA-AstraInstall для Linux
# Копирует файлы из сетевой папки и запускает установку
# Версия: V2.5.118 (2025.11.12)
# Компания: ООО "НПА Вира-Реалтайм"

# ============================================================================
# НАСТРОЙКА ИСТОЧНИКОВ ФАЙЛОВ (с приоритетами)
# ============================================================================
# Формат: "тип:параметры" - источники пробуются по порядку до первого доступного
# Если первый доступен - остальные не проверяются (для скорости)

# SMB как основной, Git как резервный
SOURCES=(
    "smb:10.10.55.77:Install:ISO/Linux/Astra:FokinSA"
    "git:https://github.com/FoksSerg/FSA-AstraInstall:master:."
)

# Пример: Только SMB
# SOURCES=(
#     "smb:10.10.55.77:Install:ISO/Linux/Astra:FokinSA"
# )

# Пример: Git как основной, SMB как резервный
# SOURCES=(
#     "git:https://github.com/FoksSerg/FSA-AstraInstall:master:."
#     "smb:10.10.55.77:Install:ISO/Linux/Astra:FokinSA"
# )

# Формат параметров для каждого типа:
# - smb:  сервер:шара:путь:пользователь
# - git:  URL_репозитория:ветка:путь_в_репозитории
# - http: базовый_URL
# ============================================================================

# ВРЕМЕННО: Лог-файл для аналитики
DEBUG_LOG_FILE="$(dirname "$0")/astra_update_debug.log"

# Функция логирования
log_message() {
    local message="[$(date '+%H:%M:%S')] $1"
    # Выводим в stderr, чтобы не попадало в результат команд подстановки
    echo "$message" >&2
    # ВРЕМЕННО: Дублируем в лог-файл
    echo "$message" >> "$DEBUG_LOG_FILE" 2>/dev/null || true
}

# Функция логирования только в файл (для отладки)
debug_log() {
    local message="[$(date '+%H:%M:%S')] [DEBUG] $1"
    echo "$message" >> "$DEBUG_LOG_FILE" 2>/dev/null || true
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

# ============================================================================
# ФУНКЦИИ ДЛЯ ПРОВЕРКИ И СРАВНЕНИЯ ФАЙЛОВ
# ============================================================================

# Функция получения информации о файле на SMB сервере (размер и дата)
get_smb_file_info() {
    local file="$1"
    local server="$2"
    local share="$3"
    local path="$4"
    local user="$5"
    local smb_path="${path}/${file}"
    
    # Используем существующий файл с учетными данными
    local credentials_file="$HOME/.smbcredentials"
    
    # Получаем информацию о файле через smbclient ls
    debug_log "get_smb_file_info: запрос информации для $file, путь=$smb_path"
    local ls_output=$(smbclient //${server}/${share} -A "$credentials_file" -c "ls \"$smb_path\"" 2>&1)
    local ls_result=$?
    debug_log "get_smb_file_info: ls_result=$ls_result, output_length=${#ls_output}"
    
    # Проверяем на ошибки авторизации
    if echo "$ls_output" | grep -qiE "(NT_STATUS_LOGON_FAILURE|NT_STATUS_WRONG_PASSWORD|authentication failed|access denied|login failed)"; then
        echo ""
        return 2  # Ошибка авторизации
    fi
    
    if [ $ls_result -ne 0 ]; then
        echo ""
        return 1  # Файл не найден или другая ошибка
    fi
    
    # Парсим вывод ls
    debug_log "get_smb_file_info: парсинг вывода ls"
    local size=$(echo "$ls_output" | grep -oE '[0-9]{4,}' | head -1)
    debug_log "get_smb_file_info: размер (первая попытка): $size"
    
    if [ -z "$size" ]; then
        # Пробуем альтернативный способ - ищем размер в другом формате
        size=$(echo "$ls_output" | grep -oE '[0-9]+' | head -1)
        debug_log "get_smb_file_info: размер (альтернативная попытка): $size"
        if [ -z "$size" ]; then
            debug_log "get_smb_file_info: ОШИБКА - не удалось извлечь размер из вывода: $ls_output"
            echo ""
            return 1  # Не удалось извлечь размер
        fi
    fi
    
    # Извлекаем дату и время
    debug_log "get_smb_file_info: извлечение даты"
    local date_time=$(echo "$ls_output" | grep -oE '[A-Z][a-z]{2}\s+[A-Z][a-z]{2}\s+[0-9]{1,2}\s+[0-9]{2}:[0-9]{2}:[0-9]{2}\s+[0-9]{4}' | head -1)
    debug_log "get_smb_file_info: дата (формат 1): $date_time"
    
    if [ -z "$date_time" ]; then
        date_time=$(echo "$ls_output" | grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}\s+[0-9]{2}:[0-9]{2}:[0-9]{2}' | head -1)
        debug_log "get_smb_file_info: дата (формат 2): $date_time"
    fi
    
    if [ -z "$date_time" ]; then
        date_time=$(echo "$ls_output" | grep -oE '[A-Z][a-z]{2}\s+[A-Z][a-z]{2}\s+[0-9]{1,2}\s+[0-9]{4}' | head -1)
        debug_log "get_smb_file_info: дата (формат 3): $date_time"
    fi
    
    local result="${size}|${date_time}"
    debug_log "get_smb_file_info: результат: $result"
    echo "$result"
    return 0
}

# Функция конвертации даты SMB в Unix timestamp (независимо от часового пояса)
smb_date_to_timestamp() {
    local date_str="$1"
    
    if [ -z "$date_str" ]; then
        echo "0"
        return 1
    fi
    
    # Формат 1: "Mon Nov 12 10:30:45 2025"
    if echo "$date_str" | grep -qE '^[A-Z][a-z]{2}\s+[A-Z][a-z]{2}\s+[0-9]{1,2}\s+[0-9]{2}:[0-9]{2}:[0-9]{2}\s+[0-9]{4}'; then
        local timestamp=$(date -u -d "$date_str" +%s 2>/dev/null || date -ujf "%a %b %d %H:%M:%S %Y" "$date_str" +%s 2>/dev/null)
        if [ -n "$timestamp" ] && [ "$timestamp" != "0" ]; then
            echo "$timestamp"
            return 0
        fi
    fi
    
    # Формат 2: "2025-11-12 10:30:45"
    if echo "$date_str" | grep -qE '^[0-9]{4}-[0-9]{2}-[0-9]{2}\s+[0-9]{2}:[0-9]{2}:[0-9]{2}'; then
        local timestamp=$(date -u -d "$date_str" +%s 2>/dev/null || date -ujf "%Y-%m-%d %H:%M:%S" "$date_str" +%s 2>/dev/null)
        if [ -n "$timestamp" ] && [ "$timestamp" != "0" ]; then
            echo "$timestamp"
            return 0
        fi
    fi
    
    # Формат 3: "Mon Nov 12 2025" (без времени)
    if echo "$date_str" | grep -qE '^[A-Z][a-z]{2}\s+[A-Z][a-z]{2}\s+[0-9]{1,2}\s+[0-9]{4}'; then
        local timestamp=$(date -u -d "$date_str 00:00:00" +%s 2>/dev/null || date -ujf "%a %b %d %Y" "$date_str" +%s 2>/dev/null)
        if [ -n "$timestamp" ] && [ "$timestamp" != "0" ]; then
            echo "$timestamp"
            return 0
        fi
    fi
    
    echo "0"
    return 1
}

# Функция сравнения файлов (размер и дата модификации)
files_are_same() {
    local file="$1"
    local local_file="$LINUX_ASTRA_PATH/$file"
    local smb_info="$2"
    
    debug_log "files_are_same: проверка файла $file"
    debug_log "files_are_same: local_file=$local_file, smb_info=$smb_info"
    
    if [ ! -f "$local_file" ]; then
        debug_log "files_are_same: локальный файл не существует"
        return 1
    fi
    
    local smb_size=$(echo "$smb_info" | cut -d'|' -f1)
    local smb_date=$(echo "$smb_info" | cut -d'|' -f2)
    
    debug_log "files_are_same: smb_size=$smb_size, smb_date=$smb_date"
    
    if [ -z "$smb_size" ] || [ "$smb_size" = "0" ]; then
        debug_log "files_are_same: размер SMB пустой или 0"
        return 1
    fi
    
    local local_size=$(stat -f%z "$local_file" 2>/dev/null || stat -c%s "$local_file" 2>/dev/null || echo "0")
    debug_log "files_are_same: local_size=$local_size, smb_size=$smb_size"
    
    if [ "$local_size" != "$smb_size" ]; then
        debug_log "files_are_same: РАЗМЕРЫ НЕ СОВПАДАЮТ: локальный=$local_size, SMB=$smb_size"
        return 1
    fi
    
    debug_log "files_are_same: размеры совпадают, проверяем дату"
    
    if [ -n "$smb_date" ]; then
        local smb_timestamp=$(smb_date_to_timestamp "$smb_date")
        local local_timestamp=$(stat -f%m "$local_file" 2>/dev/null || stat -c%Y "$local_file" 2>/dev/null || echo "0")
        
        debug_log "files_are_same: smb_timestamp=$smb_timestamp, local_timestamp=$local_timestamp"
        debug_log "files_are_same: smb_date=$smb_date"
        
        if [ "$smb_timestamp" = "0" ] || [ "$smb_timestamp" = "" ]; then
            debug_log "files_are_same: не удалось распарсить дату SMB, считаем файлы одинаковыми по размеру"
            return 0
        fi
        
        local diff=$((local_timestamp - smb_timestamp))
        local abs_diff=${diff#-}
        debug_log "files_are_same: разница во времени: $diff секунд (абсолютная: $abs_diff)"
        
        # ПРОБЛЕМА: SMB возвращает дату в UTC, а локальный файл - в локальном часовом поясе
        # Разница может быть до 12 часов (43200 секунд) из-за разных часовых поясов
        # Решение: если разница меньше 12 часов (43200 секунд) - считаем файлы одинаковыми
        # Это компенсирует разницу часовых поясов между сервером и клиентом
        if [ $abs_diff -gt 43200 ]; then
            # Разница больше 12 часов - файлы действительно разные
            debug_log "files_are_same: ДАТЫ НЕ СОВПАДАЮТ: разница=$abs_diff секунд (больше 12 часов)"
            return 1
        else
            # Разница меньше 12 часов - скорее всего это разница часовых поясов
            debug_log "files_are_same: даты совпадают (разница=$abs_diff секунд, вероятно разница часовых поясов)"
        fi
    else
        debug_log "files_are_same: дата SMB пустая, считаем файлы одинаковыми по размеру"
    fi
    
    debug_log "files_are_same: ФАЙЛЫ ОДИНАКОВЫЕ - пропускаем"
    return 0
}

# ============================================================================
# ФУНКЦИИ ДЛЯ РАБОТЫ С РАЗНЫМИ ИСТОЧНИКАМИ
# ============================================================================

# Функция получения информации о файле из Git репозитория
get_git_file_info() {
    local file="$1"
    local repo_url="$2"
    local branch="$3"
    local repo_path="$4"
    local full_path="${repo_path}/${file}"
    
    if echo "$repo_url" | grep -qE "(github|gitlab)"; then
        # Убираем .git из конца URL если есть, для работы с API
        local clean_url=$(echo "$repo_url" | sed 's|\.git$||')
        local api_url=$(echo "$clean_url" | sed -E 's|https?://(github\.com|gitlab\.com)/([^/]+)/([^/]+)|https://api.\1/repos/\2/\3/contents|')
        
        local api_response=$(curl -s "${api_url}/${full_path}?ref=${branch}" 2>/dev/null)
        
        if [ $? -eq 0 ] && [ -n "$api_response" ]; then
            local size=$(echo "$api_response" | grep -oE '"size"[[:space:]]*:[[:space:]]*[0-9]+' | grep -oE '[0-9]+' | head -1)
            
            local commit_url=$(echo "$clean_url" | sed -E 's|https?://(github\.com|gitlab\.com)/([^/]+)/([^/]+)|https://api.\1/repos/\2/\3/commits|')
            local commit_info=$(curl -s "${commit_url}?path=${full_path}&sha=${branch}&per_page=1" 2>/dev/null)
            local date=$(echo "$commit_info" | grep -oE '"date"[[:space:]]*:[[:space:]]*"[^"]+"' | head -1 | sed 's/.*"date"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/')
            
            if [ -n "$size" ]; then
                echo "${size}|${date}"
                return 0
            fi
        fi
    fi
    
    echo ""
    return 1
}

# Функция копирования файла из Git репозитория
copy_git_file() {
    local file="$1"
    local dest="$2"
    local repo_url="$3"
    local branch="$4"
    local repo_path="$5"
    local full_path="${repo_path}/${file}"
    
    if echo "$repo_url" | grep -qE "(github|gitlab)"; then
        # Убираем .git из конца URL если есть, для работы с raw
        local clean_url=$(echo "$repo_url" | sed 's|\.git$||')
        local raw_url=$(echo "$clean_url" | sed -E 's|https?://(github\.com|gitlab\.com)/([^/]+)/([^/]+)|https://raw.\1/\2/\3/${branch}|')
        raw_url="${raw_url}/${full_path}"
        
        if curl -s -f -o "$dest" "$raw_url" 2>/dev/null; then
            return 0
        fi
    fi
    
    return 1
}

# Функция получения информации о файле через HTTP/HTTPS
get_http_file_info() {
    local file="$1"
    local base_url="$2"
    local file_url="${base_url}/${file}"
    
    local headers=$(curl -s -I "$file_url" 2>/dev/null)
    
    if [ $? -ne 0 ]; then
        echo ""
        return 1
    fi
    
    if echo "$headers" | grep -qE "HTTP/[0-9.]+ 200"; then
        local size=$(echo "$headers" | grep -i "Content-Length:" | awk '{print $2}' | tr -d '\r')
        local date=$(echo "$headers" | grep -i "Last-Modified:" | cut -d: -f2- | sed 's/^ *//' | tr -d '\r')
        
        if [ -z "$date" ]; then
            date=$(date -u +"%a, %d %b %Y %H:%M:%S GMT")
        fi
        
        if [ -n "$size" ]; then
            echo "${size}|${date}"
            return 0
        fi
    fi
    
    echo ""
    return 1
}

# Функция копирования файла через HTTP/HTTPS
copy_http_file() {
    local file="$1"
    local dest="$2"
    local base_url="$3"
    local file_url="${base_url}/${file}"
    
    if curl -s -f -o "$dest" "$file_url" 2>/dev/null; then
        return 0
    fi
    
    return 1
}

# Функция копирования файла из SMB
copy_smb_file() {
    local file="$1"
    local dest="$2"
    local server="$3"
    local share="$4"
    local path="$5"
    local user="$6"
    local smb_path="${path}/${file}"
    
    local credentials_file="$HOME/.smbcredentials"
    
    # Используем тот же формат команды, что и в старой версии (без кавычек в пути)
    # Старая версия: get ${SMB_PATH}/$file $LINUX_ASTRA_PATH/$file
    # Формируем команду точно как в старой версии
    local smb_cmd="get ${smb_path} ${dest}"
    debug_log "copy_smb_file: file=$file, smb_path=$smb_path, dest=$dest"
    debug_log "copy_smb_file: server=$server, share=$share, credentials_file=$credentials_file"
    debug_log "smbclient command: smbclient //${server}/${share} -A $credentials_file -c \"$smb_cmd\""
    
    # Выполняем команду и сохраняем вывод
    local error_output=$(smbclient //${server}/${share} -A "$credentials_file" -c "$smb_cmd" 2>&1)
    local copy_result=$?
    
    # Логируем результат (всегда, даже если успешно)
    debug_log "smbclient result: code=$copy_result"
    if [ -n "$error_output" ]; then
        debug_log "smbclient output: $error_output"
    fi
    if [ $copy_result -eq 0 ]; then
        debug_log "smbclient УСПЕХ: файл скопирован"
        
        # ВАЖНО: smbclient не сохраняет дату модификации файла при копировании
        # Нужно установить дату модификации локального файла равной дате файла на SMB сервере
        # Для этого получаем информацию о файле и устанавливаем дату через touch
        local smb_info=$(get_smb_file_info "$file" "$server" "$share" "$path" "$user")
        if [ $? -eq 0 ] && [ -n "$smb_info" ]; then
            local smb_date=$(echo "$smb_info" | cut -d'|' -f2)
            if [ -n "$smb_date" ]; then
                # Устанавливаем дату модификации локального файла равной дате файла на SMB
                # Используем touch -d для установки даты в формате "Tue Nov 11 02:23:24 2025"
                if touch -d "$smb_date" "$dest" 2>/dev/null; then
                    debug_log "Дата модификации установлена: $smb_date"
                else
                    # Альтернативный способ: конвертируем дату в timestamp и используем touch -t
                    local smb_timestamp=$(smb_date_to_timestamp "$smb_date")
                    if [ "$smb_timestamp" != "0" ] && [ -n "$smb_timestamp" ]; then
                        # Конвертируем timestamp в формат для touch -t: [[CC]YY]MMDDhhmm[.ss]
                        local touch_date=$(date -u -d "@$smb_timestamp" +"%Y%m%d%H%M.%S" 2>/dev/null || date -ujf "%s" "$smb_timestamp" +"%Y%m%d%H%M.%S" 2>/dev/null)
                        if [ -n "$touch_date" ]; then
                            if touch -t "$touch_date" "$dest" 2>/dev/null; then
                                debug_log "Дата модификации установлена через touch -t: $touch_date (timestamp: $smb_timestamp)"
                            else
                                debug_log "ПРЕДУПРЕЖДЕНИЕ: Не удалось установить дату модификации через touch -t"
                            fi
                        fi
                    else
                        debug_log "ПРЕДУПРЕЖДЕНИЕ: Не удалось конвертировать дату SMB в timestamp"
                    fi
                fi
            fi
        fi
    else
        debug_log "smbclient ОШИБКА: код=$copy_result"
    fi
    
    if [ $copy_result -eq 0 ]; then
        return 0
    fi
    
    # Логируем ошибку для отладки (только если не авторизация)
    if ! echo "$error_output" | grep -qiE "(NT_STATUS_LOGON_FAILURE|NT_STATUS_WRONG_PASSWORD|authentication failed|access denied|login failed)"; then
        # Это не ошибка авторизации - логируем детали через log_message (если доступна)
        if command -v log_message >/dev/null 2>&1; then
            log_message "ОШИБКА копирования $file: $error_output"
        else
            echo "[ERROR] copy_smb_file failed for $file: $error_output" >&2
        fi
    fi
    
    if echo "$error_output" | grep -qiE "(NT_STATUS_LOGON_FAILURE|NT_STATUS_WRONG_PASSWORD|authentication failed|access denied|login failed)"; then
        return 2
    fi
    
    return 1
}

# ============================================================================
# ФУНКЦИИ ПРОВЕРКИ ДОСТУПНОСТИ ИСТОЧНИКОВ
# ============================================================================

check_source_availability() {
    local source="$1"
    local source_type=$(echo "$source" | cut -d: -f1)
    local source_params=$(echo "$source" | cut -d: -f2-)
    
    local result=1
    
    case "$source_type" in
        "git")
            local repo_url=$(echo "$source_params" | cut -d: -f1)
            
            if command -v git >/dev/null 2>&1; then
                # Для git ls-remote добавляем .git если его нет
                local git_url="$repo_url"
                if ! echo "$git_url" | grep -qE '\.git$'; then
                    git_url="${repo_url}.git"
                fi
                timeout 3 git ls-remote --heads "$git_url" >/dev/null 2>&1
                result=$?
            else
                if echo "$repo_url" | grep -qE "(github|gitlab)"; then
                    # Убираем .git из конца URL если есть, для работы с API
                    local clean_url=$(echo "$repo_url" | sed 's|\.git$||')
                    local api_url=$(echo "$clean_url" | sed -E 's|https?://(github\.com|gitlab\.com)/([^/]+)/([^/]+)|https://api.\1/repos/\2/\3|')
                    timeout 3 curl -s -f "$api_url" >/dev/null 2>&1
                    result=$?
                fi
            fi
            ;;
            
        "smb")
            local server=$(echo "$source_params" | cut -d: -f1)
            timeout 1 ping -c 1 -W 0.5 "$server" >/dev/null 2>&1
            result=$?
            ;;
            
        "http")
            local base_url="$source_params"
            timeout 3 curl -s -I -f "$base_url" >/dev/null 2>&1
            result=$?
            ;;
    esac
    
    return $result
}

SELECTED_SOURCE=""

determine_available_source() {
    for source in "${SOURCES[@]}"; do
        local source_type=$(echo "$source" | cut -d: -f1)
        log_message "Проверка доступности источника: $source_type..."
        
        if check_source_availability "$source"; then
            log_message "Источник доступен: $source_type"
            # КРИТИЧНО: Выводим только источник в stdout
            echo "$source"
            return 0
        else
            log_message "Источник недоступен: $source_type, пробуем следующий..."
        fi
    done
    
    log_message "ОШИБКА: Все источники недоступны"
    echo ""
    return 1
}

get_file_info_from_selected_source() {
    local file="$1"
    
    if [ -z "$SELECTED_SOURCE" ]; then
        echo ""
        return 1
    fi
    
    local source_type=$(echo "$SELECTED_SOURCE" | cut -d: -f1)
    local source_params=$(echo "$SELECTED_SOURCE" | cut -d: -f2-)
    
    case "$source_type" in
        "git")
            local repo_url=$(echo "$source_params" | cut -d: -f1)
            local branch=$(echo "$source_params" | cut -d: -f2)
            local repo_path=$(echo "$source_params" | cut -d: -f3)
            get_git_file_info "$file" "$repo_url" "$branch" "$repo_path"
            ;;
            
        "smb")
            local server=$(echo "$source_params" | cut -d: -f1)
            local share=$(echo "$source_params" | cut -d: -f2)
            local path=$(echo "$source_params" | cut -d: -f3)
            local user=$(echo "$source_params" | cut -d: -f4)
            get_smb_file_info "$file" "$server" "$share" "$path" "$user"
            ;;
            
        "http")
            local base_url="$source_params"
            get_http_file_info "$file" "$base_url"
            ;;
            
        *)
            echo ""
            return 1
            ;;
    esac
}

copy_file_from_selected_source() {
    local file="$1"
    local dest="$2"
    
    if [ -z "$SELECTED_SOURCE" ]; then
        return 1
    fi
    
    local source_type=$(echo "$SELECTED_SOURCE" | cut -d: -f1)
    local source_params=$(echo "$SELECTED_SOURCE" | cut -d: -f2-)
    
    case "$source_type" in
        "git")
            local repo_url=$(echo "$source_params" | cut -d: -f1)
            local branch=$(echo "$source_params" | cut -d: -f2)
            local repo_path=$(echo "$source_params" | cut -d: -f3)
            copy_git_file "$file" "$dest" "$repo_url" "$branch" "$repo_path"
            ;;
            
        "smb")
            local server=$(echo "$source_params" | cut -d: -f1)
            local share=$(echo "$source_params" | cut -d: -f2)
            local path=$(echo "$source_params" | cut -d: -f3)
            local user=$(echo "$source_params" | cut -d: -f4)
            debug_log "copy_file_from_selected_source: file=$file, dest=$dest"
            debug_log "SMB params: server=$server, share=$share, path=$path, user=$user"
            copy_smb_file "$file" "$dest" "$server" "$share" "$path" "$user"
            ;;
            
        "http")
            local base_url="$source_params"
            copy_http_file "$file" "$dest" "$base_url"
            ;;
            
        *)
            return 1
            ;;
    esac
}

# Пути для Linux
LINUX_ASTRA_PATH="$(dirname "$0")"  # Папка где находится скрипт

# Файлы для копирования
FILES_TO_COPY=(
    "astra_automation.py"
    "astra_install.sh"
    "astra_update.sh"
    "README.md"
    "WINE_INSTALL_GUIDE.md"
)

# ВРЕМЕННО: Инициализация лог-файла для аналитики
log_message "Запуск обновления FSA-AstraInstall"
debug_log "=== НАЧАЛО СЕАНСА ОБНОВЛЕНИЯ ==="
debug_log "Версия скрипта: V2.5.117"
debug_log "Дата: $(date '+%Y-%m-%d %H:%M:%S')"
debug_log "Путь скрипта: $(dirname "$0")"
debug_log "Пользователь: $(whoami)"
debug_log "PID: $$"

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

# ============================================================================
# ОПРЕДЕЛЕНИЕ ДОСТУПНОГО ИСТОЧНИКА (один раз в начале)
# ============================================================================
log_message "Определение доступного источника файлов..."

# Получаем источник (log_message теперь выводит в stderr, так что stdout чистый)
SELECTED_SOURCE=$(determine_available_source)
debug_log "SELECTED_SOURCE: $SELECTED_SOURCE"

if [ -z "$SELECTED_SOURCE" ]; then
    log_message "ОШИБКА: Все источники недоступны. Продолжаем без обновления."
    log_message "Проверьте доступность сети и настройки источников в скрипте"
    debug_log "ОШИБКА: Все источники недоступны"
    SERVER_AVAILABLE=false
else
    selected_type=$(echo "$SELECTED_SOURCE" | cut -d: -f1)
    log_message "Используется источник: $selected_type"
    log_message "Выбранный источник: $SELECTED_SOURCE"
    debug_log "Выбран источник: $selected_type, полный путь: $SELECTED_SOURCE"
    SERVER_AVAILABLE=true
fi
# ============================================================================

# Инициализация флага успешности обновления
UPDATE_SUCCESSFUL=false

# Работа с обновлением только если источник доступен
if [ "$SERVER_AVAILABLE" = true ]; then
    # Для SMB: создаем файл с учетными данными (если нужно)
    if echo "$SELECTED_SOURCE" | grep -q "^smb:"; then
        source_params=$(echo "$SELECTED_SOURCE" | cut -d: -f2-)
        smb_user=$(echo "$source_params" | cut -d: -f4)
        
        log_message "Подключение к SMB с учетными данными ${smb_user}..."
        
        mkdir -p "$LINUX_ASTRA_PATH" 2>/dev/null
        
        CREDENTIALS_FILE="$HOME/.smbcredentials"
        
        if [ ! -f "$CREDENTIALS_FILE" ]; then
            log_message "Файл учетных данных не найден. Создаем..."
            echo "username=${smb_user}" > "$CREDENTIALS_FILE"
            echo "password=" >> "$CREDENTIALS_FILE"
            chmod 600 "$CREDENTIALS_FILE"
            
            if command -v xdotool >/dev/null 2>&1 && [ "$SKIP_TERMINAL" != "true" ]; then
                restore_terminal_window "$TERMINAL_PID"
            fi
            
            log_message "Введите пароль для пользователя ${smb_user}:"
            read -s password
            echo "password=$password" > "$CREDENTIALS_FILE"
            echo "username=${smb_user}" >> "$CREDENTIALS_FILE"
            chmod 600 "$CREDENTIALS_FILE"
            log_message "Учетные данные сохранены"
            
            if [ "$SKIP_TERMINAL" != "true" ]; then
                minimize_terminal_window "$TERMINAL_PID"
            fi
        fi
    fi
    
    # Копируем файлы с обработкой ошибок авторизации и проверкой изменений
    log_message "Проверка и копирование файлов из сети..."
    
    # Первая попытка копирования
    COPY_SUCCESS=true
    AUTH_ERROR=false
    COPIED_COUNT=0
    SKIPPED_COUNT=0
    
    for file in "${FILES_TO_COPY[@]}"; do
        log_message "Проверяем: $file"
        
        # Получаем информацию о файле (только из выбранного источника)
        debug_log "Попытка получить информацию о файле: $file"
        SMB_INFO=$(get_file_info_from_selected_source "$file")
        SMB_INFO_RESULT=$?
        debug_log "get_file_info_from_selected_source result: code=$SMB_INFO_RESULT, info=$SMB_INFO"
        
        # Детальное логирование результата получения информации
        if [ $SMB_INFO_RESULT -eq 0 ]; then
            if [ -n "$SMB_INFO" ]; then
                SMB_SIZE=$(echo "$SMB_INFO" | cut -d'|' -f1)
                log_message "Информация о файле получена: размер $SMB_SIZE байт"
                debug_log "Информация о файле получена: размер=$SMB_SIZE, полная_инфо=$SMB_INFO"
            else
                log_message "ПРЕДУПРЕЖДЕНИЕ: Информация о файле пустая"
                debug_log "ПРЕДУПРЕЖДЕНИЕ: Информация о файле пустая"
            fi
        else
            log_message "ПРЕДУПРЕЖДЕНИЕ: Не удалось получить информацию о файле $file из источника"
            debug_log "ПРЕДУПРЕЖДЕНИЕ: Не удалось получить информацию, код=$SMB_INFO_RESULT"
        fi
        
        # Проверяем нужно ли копировать (только если информация доступна)
        # Если информация недоступна - просто пытаемся скопировать (как в старой версии)
        if [ $SMB_INFO_RESULT -eq 0 ] && [ -n "$SMB_INFO" ]; then
            # Информация доступна - проверяем, нужно ли копировать (оптимизация)
            if files_are_same "$file" "$SMB_INFO"; then
                log_message "Пропущен: $file (не изменился - размер и дата совпадают)"
                SKIPPED_COUNT=$((SKIPPED_COUNT + 1))
                continue
            else
                # Файл изменился - копируем
                SMB_SIZE=$(echo "$SMB_INFO" | cut -d'|' -f1)
                log_message "Копируем: $file (изменен, размер: $SMB_SIZE байт)"
            fi
        else
            # Информация недоступна - просто пытаемся скопировать (как в старой версии)
            # Проверка информации - это только оптимизация, не обязательное условие
            log_message "Копируем: $file (проверка информации недоступна, копируем напрямую)"
        fi
        
        # Копируем файл (только из выбранного источника)
        log_message "Попытка копирования: $file -> $LINUX_ASTRA_PATH/$file"
        debug_log "Начало копирования: file=$file, dest=$LINUX_ASTRA_PATH/$file"
        debug_log "Локальный файл существует: $([ -f "$LINUX_ASTRA_PATH/$file" ] && echo "да" || echo "нет")"
        copy_file_from_selected_source "$file" "$LINUX_ASTRA_PATH/$file"
        COPY_RESULT=$?
        debug_log "copy_file_from_selected_source завершена: код=$COPY_RESULT"
        
        if [ $COPY_RESULT -eq 0 ]; then
            log_message "Скопирован: $file"
            debug_log "УСПЕХ: Файл $file скопирован успешно"
            # Проверяем, что файл действительно скопировался
            if [ -f "$LINUX_ASTRA_PATH/$file" ]; then
                local file_size=$(stat -f%z "$LINUX_ASTRA_PATH/$file" 2>/dev/null || stat -c%s "$LINUX_ASTRA_PATH/$file" 2>/dev/null || echo "unknown")
                debug_log "Файл подтвержден: размер=$file_size байт"
            else
                debug_log "ОШИБКА: Файл не найден после копирования!"
            fi
            COPIED_COUNT=$((COPIED_COUNT + 1))
        elif [ $COPY_RESULT -eq 2 ]; then
            # Ошибка авторизации SMB
            log_message "ОШИБКА: Ошибка авторизации при копировании $file"
            debug_log "ОШИБКА АВТОРИЗАЦИИ: код=$COPY_RESULT, файл=$file"
            AUTH_ERROR=true
            COPY_SUCCESS=false
            break
        else
            log_message "ПРЕДУПРЕЖДЕНИЕ: Файл $file не найден или недоступен. Код ошибки: $COPY_RESULT"
            debug_log "ОШИБКА КОПИРОВАНИЯ: код=$COPY_RESULT, файл=$file"
            # Пробуем вывести детали ошибки, если доступны
            if [ -n "$SELECTED_SOURCE" ]; then
                source_type=$(echo "$SELECTED_SOURCE" | cut -d: -f1)
                log_message "Источник: $source_type, путь: $(echo "$SELECTED_SOURCE" | cut -d: -f2- | cut -d: -f3)"
                debug_log "Источник: $source_type, полный=$SELECTED_SOURCE"
            fi
        fi
    done
    
    # Логируем статистику первой попытки
    log_message "Статистика: скопировано $COPIED_COUNT, пропущено $SKIPPED_COUNT из ${#FILES_TO_COPY[@]} файлов"
    
    # Если первая попытка неудачна из-за ошибки авторизации - запрашиваем пароль заново
    if [ "$AUTH_ERROR" = true ]; then
        log_message "Ошибка авторизации. Запрашиваем пароль заново..."
        
        if echo "$SELECTED_SOURCE" | grep -q "^smb:"; then
            source_params=$(echo "$SELECTED_SOURCE" | cut -d: -f2-)
            smb_user=$(echo "$source_params" | cut -d: -f4)
            
            if command -v xdotool >/dev/null 2>&1 && [ "$SKIP_TERMINAL" != "true" ]; then
                restore_terminal_window "$TERMINAL_PID"
            fi
            
            log_message "Введите пароль для пользователя ${smb_user}:"
            read -s password
            echo "password=$password" > "$CREDENTIALS_FILE"
            echo "username=${smb_user}" >> "$CREDENTIALS_FILE"
            chmod 600 "$CREDENTIALS_FILE"
            log_message "Учетные данные обновлены"
            
            if [ "$SKIP_TERMINAL" != "true" ]; then
                minimize_terminal_window "$TERMINAL_PID"
            fi
            
            # Вторая попытка копирования
            COPY_SUCCESS=true
            AUTH_ERROR=false
            SKIPPED_COUNT=0
            
            for file in "${FILES_TO_COPY[@]}"; do
                log_message "Проверяем: $file (повторная попытка)"
                
                SMB_INFO=$(get_file_info_from_selected_source "$file")
                SMB_INFO_RESULT=$?
                
                if [ $SMB_INFO_RESULT -eq 0 ] && files_are_same "$file" "$SMB_INFO"; then
                    log_message "Пропущен: $file (не изменился - размер и дата совпадают)"
                    SKIPPED_COUNT=$((SKIPPED_COUNT + 1))
                    continue
                fi
                
                if [ $SMB_INFO_RESULT -eq 0 ]; then
                    SMB_SIZE=$(echo "$SMB_INFO" | cut -d'|' -f1)
                    log_message "Копируем: $file (повторная попытка, изменен или новый, размер: $SMB_SIZE байт)"
                else
                    log_message "Копируем: $file (повторная попытка, информация недоступна)"
                fi
                
                copy_file_from_selected_source "$file" "$LINUX_ASTRA_PATH/$file"
                COPY_RESULT=$?
                
                if [ $COPY_RESULT -eq 0 ]; then
                    log_message "Скопирован: $file"
                    COPIED_COUNT=$((COPIED_COUNT + 1))
                elif [ $COPY_RESULT -eq 2 ]; then
                    log_message "ОШИБКА: Ошибка авторизации при копировании $file (повторная попытка)"
                    AUTH_ERROR=true
                    COPY_SUCCESS=false
                else
                    log_message "ПРЕДУПРЕЖДЕНИЕ: Файл $file не найден или недоступен. Пропускаем."
                fi
            done
            
            log_message "Статистика (повторная попытка): скопировано $COPIED_COUNT, пропущено $SKIPPED_COUNT"
        fi
    fi
    
    # ============================================================================
    # ЭТАП ПРОВЕРКИ СКОПИРОВАННЫХ ФАЙЛОВ
    # ============================================================================
    if [ $COPIED_COUNT -gt 0 ]; then
        log_message "Проверка скопированных файлов..."
        
        log_message "Синхронизация файловой системы..."
        sync
        sleep 0.3
        
        ALL_FILES_OK=true
        MISSING_FILES=()
        EMPTY_FILES=()
        
        for file in "${FILES_TO_COPY[@]}"; do
            file_path="$LINUX_ASTRA_PATH/$file"
            
            if [ ! -f "$file_path" ]; then
                log_message "ОШИБКА: Файл $file не найден после копирования"
                MISSING_FILES+=("$file")
                ALL_FILES_OK=false
                continue
            fi
            
            if [ ! -s "$file_path" ]; then
                log_message "ОШИБКА: Файл $file пустой (размер 0 байт)"
                EMPTY_FILES+=("$file")
                ALL_FILES_OK=false
                continue
            fi
            
            if [ ! -r "$file_path" ]; then
                log_message "ОШИБКА: Файл $file недоступен для чтения"
                ALL_FILES_OK=false
                continue
            fi
            
            file_size=$(stat -f%z "$file_path" 2>/dev/null || stat -c%s "$file_path" 2>/dev/null || echo "unknown")
            log_message "Проверен: $file (размер: $file_size байт)"
        done
        
        if [ "$ALL_FILES_OK" = false ]; then
            log_message "Обнаружены проблемы с файлами. Повторная синхронизация..."
            sync
            sleep 1
            
            for file in "${MISSING_FILES[@]}"; do
                file_path="$LINUX_ASTRA_PATH/$file"
                if [ -f "$file_path" ] && [ -s "$file_path" ]; then
                    log_message "Файл $file теперь доступен"
                    ALL_FILES_OK=true
                fi
            done
            
            for file in "${EMPTY_FILES[@]}"; do
                file_path="$LINUX_ASTRA_PATH/$file"
                if [ -s "$file_path" ]; then
                    log_message "Файл $file больше не пустой"
                    ALL_FILES_OK=true
                fi
            done
        fi
        
        CRITICAL_FILES=("astra_install.sh" "astra_automation.py")
        CRITICAL_OK=true
        
        for file in "${CRITICAL_FILES[@]}"; do
            file_path="$LINUX_ASTRA_PATH/$file"
            if [ ! -f "$file_path" ] || [ ! -s "$file_path" ]; then
                log_message "КРИТИЧЕСКАЯ ОШИБКА: Критический файл $file недоступен или пуст"
                CRITICAL_OK=false
            fi
        done
        
        if [ "$CRITICAL_OK" = false ]; then
            log_message "ОШИБКА: Критические файлы не готовы. Запуск невозможен."
        fi
        
        if [ "$ALL_FILES_OK" = true ]; then
            log_message "Все файлы успешно проверены и готовы к использованию"
        else
            log_message "ПРЕДУПРЕЖДЕНИЕ: Некоторые файлы имеют проблемы, но продолжаем работу"
        fi
        
        log_message "Проверка файлов завершена"
    fi
    # ============================================================================
    
    # Обработка результата обновления
    if [ $COPIED_COUNT -gt 0 ]; then
        log_message "Скопировано файлов: $COPIED_COUNT из ${#FILES_TO_COPY[@]}"
        if [ "$COPY_SUCCESS" = true ] && [ $COPIED_COUNT -eq ${#FILES_TO_COPY[@]} ]; then
            log_message "Все файлы успешно скопированы!"
        else
            log_message "Некоторые файлы не были скопированы, но продолжаем работу."
        fi
        UPDATE_SUCCESSFUL=true
        
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
    log_message "Обновление пропущено (все источники недоступны)"
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

# Финальная проверка перед запуском
log_message "Финальная проверка перед запуском..."
if [ -f "astra_install.sh" ]; then
    if [ ! -s "astra_install.sh" ]; then
        log_message "ОШИБКА: Файл astra_install.sh пустой или поврежден"
        echo "Ошибка Обновления"
        exit 1
    fi
    
    if [ ! -x "astra_install.sh" ]; then
        log_message "Файл astra_install.sh не исполняемый, устанавливаем права..."
        chmod +x "astra_install.sh" 2>/dev/null
    fi
    
    sync
    
    log_message "Файл astra_install.sh готов к запуску"
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
    debug_log "КРИТИЧЕСКАЯ ОШИБКА: Файл astra_install.sh не найден"
    debug_log "Проверка существования: $([ -f "$LINUX_ASTRA_PATH/astra_install.sh" ] && echo "файл существует" || echo "файл НЕ существует")"
    debug_log "Содержимое директории: $(ls -la "$LINUX_ASTRA_PATH" 2>&1 | head -10)"
    echo "Ошибка Обновления"
    exit 1
fi

# ВРЕМЕННО: Завершение логирования
debug_log "=== КОНЕЦ СЕАНСА ОБНОВЛЕНИЯ ==="
debug_log "Статистика: скопировано=$COPIED_COUNT, пропущено=$SKIPPED_COUNT"
debug_log "Лог-файл сохранен: $DEBUG_LOG_FILE"
