#!/bin/bash
# Скрипт автоматического обновления FSA-AstraInstall для Linux
# Копирует файлы из сетевой папки и запускает установку
# Версия: V2.6.130 (2025.11.17)
# Компания: ООО "НПА Вира-Реалтайм"

# Пути для Linux
LINUX_ASTRA_PATH="$(dirname "$0")"  # Папка где находится скрипт

# ============================================================================
# БЛОК 0: ИНИЦИАЛИЗАЦИЯ ЛОГ-ФАЙЛА (САМОЕ НАЧАЛО!) 
# ============================================================================

# Создаем единый timestamp для всей сессии
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_DIR="$LINUX_ASTRA_PATH/Log"
mkdir -p "$LOG_DIR"

# Создаем ANALYSIS лог-файл (основной)
ANALYSIS_LOG_FILE="$LOG_DIR/astra_automation_$TIMESTAMP.log"

# Очищаем логи
#rm -rf "$LINUX_ASTRA_PATH/Log" 2>/dev/null

# Инициализируем лог-файл (только если не существует - защита от повторного создания)
if [ ! -f "$ANALYSIS_LOG_FILE" ]; then
    {
        echo "============================================================"
        echo "FSA-AstraInstall - НАЧАЛО СЕССИИ ОБНОВЛЕНИЯ"
        echo "Время запуска: $(date)"
        echo "Директория скрипта: $LINUX_ASTRA_PATH"
        echo "============================================================"
    } > "$ANALYSIS_LOG_FILE"
    
    # Исправляем права доступа для реального пользователя
    REAL_USER=$(who am i | awk '{print $1}' 2>/dev/null || echo "")
    if [ -z "$REAL_USER" ]; then
        REAL_USER=$(logname 2>/dev/null || echo "$SUDO_USER")
    fi
    if [ ! -z "$REAL_USER" ] && [ "$REAL_USER" != "root" ]; then
        chown "$REAL_USER:$REAL_USER" "$ANALYSIS_LOG_FILE" 2>/dev/null || true
        chmod 644 "$ANALYSIS_LOG_FILE" 2>/dev/null || true
    fi
fi

# Экспортируем для использования в функциях
export ANALYSIS_LOG_FILE
export TIMESTAMP

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

# Файлы для копирования в БИНАРНОМ режиме
FILES_TO_COPY_BINARY=(
    "astra_automation"      # Бинарный Python файл
    "astra_install"         # Бинарный bash файл (опционально)
    "README.md"             # Документация (обязательна)
    "WINE_INSTALL_GUIDE.md" # Документация (обязательна)
)

# Файлы для копирования в СКРИПТОВОМ режиме
FILES_TO_COPY_SCRIPT=(
    "astra_automation.py"   # Python скрипт
    "astra_install.sh"      # Bash скрипт
    "astra_update.sh"       # Bash скрипт
    "README.md"             # Документация
    "WINE_INSTALL_GUIDE.md" # Документация
)

# Выбираем нужный список в зависимости от режима
if [ "$IS_BINARY" = true ]; then
    FILES_TO_COPY=("${FILES_TO_COPY_BINARY[@]}")
else
    FILES_TO_COPY=("${FILES_TO_COPY_SCRIPT[@]}")
fi

# ============================================================================
# ФУНКЦИЯ ПОИСКА ИСПОЛНЯЕМОГО ФАЙЛА
# ============================================================================

# Функция поиска исполняемого файла (бинарный или скрипт)
find_executable() {
    local name="$1"
    local dir="${2:-$LINUX_ASTRA_PATH}"
    
    if [ "$IS_BINARY" = true ]; then
        # В бинарном режиме ищем только бинарные файлы
        if [ -f "$dir/$name" ] && [ -x "$dir/$name" ]; then
            echo "$dir/$name"
            return 0
        fi
    else
        # В скриптовом режиме ищем скрипты
        if [ -f "$dir/${name}.sh" ] && [ -x "$dir/${name}.sh" ]; then
            echo "$dir/${name}.sh"
            return 0
        fi
    fi
    
    return 1
}

# ============================================================================
# НАСТРОЙКА ИСТОЧНИКОВ ФАЙЛОВ (с приоритетами)
# ============================================================================
# Формат: "тип:параметры" - источники пробуются по порядку до первого доступного
# Если первый доступен - остальные не проверяются (для скорости)

# SMB как основной, Git как резервный
SOURCES=(
    "smb:10.10.55.77:Install:ISO/Linux/Astra:FokinSA"
    #"git:https://github.com/FoksSerg/FSA-AstraInstall:master:."
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

# Включить/выключить сохранение логов в файл (true/false)
# Установите false чтобы отключить логирование в файл
ENABLE_DEBUG_LOG=false

# Функция логирования (обновленная - записывает в единый лог-файл)
log_message() {
    local message="$1"
    local timestamp=$(date +"%H:%M:%S.%3N")
    local log_entry="[$timestamp] [UPDATE] $message"
    
    # Записываем в единый ANALYSIS лог-файл (если создан)
    if [ -f "$ANALYSIS_LOG_FILE" ]; then
        echo "$log_entry" >> "$ANALYSIS_LOG_FILE" 2>/dev/null || true
    fi
    
    # Старое поведение: выводим в stderr (сохраняем для обратной совместимости)
    echo "$message" >&2
    
    # Дублируем в старый DEBUG лог-файл (если включено)
    if [ "$ENABLE_DEBUG_LOG" = "true" ]; then
        echo "[$(date '+%H:%M:%S')] $message" >> "$DEBUG_LOG_FILE" 2>/dev/null || true
    fi
}

# Функция логирования только в файл (для отладки)
debug_log() {
    # Логируем только если включено
    if [ "$ENABLE_DEBUG_LOG" != "true" ]; then
        return 0
    fi
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
    
    # Возвращаем только размер (дата больше не используется)
    debug_log "get_smb_file_info: результат: размер=$size"
    echo "$size"
    return 0
}

# Функция сравнения файлов (только по размеру)
files_are_same() {
    local file="$1"
    local local_file="$LINUX_ASTRA_PATH/$file"
    local remote_size="$2"  # Теперь просто размер, без даты
    
    debug_log "files_are_same: проверка файла $file"
    debug_log "files_are_same: local_file=$local_file, remote_size=$remote_size"
    
    if [ ! -f "$local_file" ]; then
        debug_log "files_are_same: локальный файл не существует"
        return 1
    fi
    
    debug_log "files_are_same: remote_size=$remote_size"
    
    if [ -z "$remote_size" ] || [ "$remote_size" = "0" ]; then
        debug_log "files_are_same: размер удаленного файла пустой или 0"
        return 1
    fi
    
    local local_size=$(stat -f%z "$local_file" 2>/dev/null || stat -c%s "$local_file" 2>/dev/null || echo "0")
    debug_log "files_are_same: local_size=$local_size, remote_size=$remote_size"
    
    if [ "$local_size" != "$remote_size" ]; then
        debug_log "files_are_same: РАЗМЕРЫ НЕ СОВПАДАЮТ: локальный=$local_size, удаленный=$remote_size"
        return 1
    fi
    
    debug_log "files_are_same: ФАЙЛЫ ОДИНАКОВЫЕ (размеры совпадают) - пропускаем"
    return 0
}

# ============================================================================
# ФУНКЦИИ ДЛЯ РАБОТЫ С РАЗНЫМИ ИСТОЧНИКАМИ
# ============================================================================

# Функция получения информации о файле из Git репозитория
# Использует HEAD запрос к raw URL для получения размера файла (без использования API)
get_git_file_info() {
    local file="$1"
    local repo_url="$2"
    local branch="$3"
    local repo_path="$4"
    local full_path="${repo_path}/${file}"
    
    # Убираем ./ из начала пути, если есть
    full_path=$(echo "$full_path" | sed 's|^\./||')
    
    debug_log "get_git_file_info: file=$file, repo_url=$repo_url, branch=$branch, repo_path=$repo_path, full_path=$full_path"
    
    if echo "$repo_url" | grep -qE "(github|gitlab)"; then
        # Убираем .git из конца URL если есть
        local clean_url=$(echo "$repo_url" | sed 's|\.git$||')
        
        # Формируем raw URL для получения размера файла через HEAD запрос
        if echo "$clean_url" | grep -qE "github\.com"; then
            local raw_url=$(echo "$clean_url" | sed -E "s|https?://github\.com/([^/]+)/([^/]+)|https://raw.githubusercontent.com/\1/\2/${branch}|")
            raw_url="${raw_url}/${full_path}"
        elif echo "$clean_url" | grep -qE "gitlab\.com"; then
            local raw_url=$(echo "$clean_url" | sed -E "s|https?://gitlab\.com/([^/]+)/([^/]+)|https://gitlab.com/\1/\2/-/raw/${branch}|")
            raw_url="${raw_url}/${full_path}"
        else
            debug_log "get_git_file_info: неизвестный хостинг Git"
            echo ""
            return 1
        fi
        
        debug_log "get_git_file_info: clean_url=$clean_url, raw_url=$raw_url"
        
        # Получаем размер файла через HEAD запрос (не засчитывается в rate limit, работает быстрее)
        local head_response=$(curl -s -I "$raw_url" 2>&1)
        local curl_result=$?
        debug_log "get_git_file_info: curl HEAD result=$curl_result, response_length=${#head_response}"
        
        if [ $curl_result -eq 0 ]; then
            local content_length=$(echo "$head_response" | grep -iE "^content-length:" | awk '{print $2}' | tr -d '\r\n')
            
            if [ -n "$content_length" ] && [ "$content_length" != "0" ]; then
                debug_log "get_git_file_info: Размер файла через HEAD запрос: $content_length байт"
                echo "$content_length"
                return 0
            else
                debug_log "get_git_file_info: Content-Length не найден или равен 0"
            fi
        else
            debug_log "get_git_file_info: HEAD запрос не удался"
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
    
    # Убираем ./ из начала пути, если есть (GitHub/GitLab API не понимают такой формат)
    full_path=$(echo "$full_path" | sed 's|^\./||')
    
    debug_log "copy_git_file: file=$file, dest=$dest, repo_url=$repo_url, branch=$branch, repo_path=$repo_path, full_path=$full_path"
    
    if echo "$repo_url" | grep -qE "(github|gitlab)"; then
        # Убираем .git из конца URL если есть, для работы с raw
        local clean_url=$(echo "$repo_url" | sed 's|\.git$||')
        # Формат raw URL для GitHub: https://raw.githubusercontent.com/USER/REPO/BRANCH/PATH/TO/FILE
        # Для GitLab: https://gitlab.com/USER/REPO/-/raw/BRANCH/PATH/TO/FILE
        if echo "$clean_url" | grep -qE "github\.com"; then
            local raw_url=$(echo "$clean_url" | sed -E "s|https?://github\.com/([^/]+)/([^/]+)|https://raw.githubusercontent.com/\1/\2/${branch}|")
            raw_url="${raw_url}/${full_path}"
        elif echo "$clean_url" | grep -qE "gitlab\.com"; then
            local raw_url=$(echo "$clean_url" | sed -E "s|https?://gitlab\.com/([^/]+)/([^/]+)|https://gitlab.com/\1/\2/-/raw/${branch}|")
            raw_url="${raw_url}/${full_path}"
        else
            debug_log "copy_git_file: неизвестный хостинг Git, используем базовый URL"
            return 1
        fi
        
        debug_log "copy_git_file: clean_url=$clean_url, raw_url=$raw_url"
        
        local curl_output=$(curl -s -f -o "$dest" "$raw_url" 2>&1)
        local curl_result=$?
        debug_log "copy_git_file: curl result=$curl_result, output_length=${#curl_output}"
        if [ $curl_result -ne 0 ]; then
            debug_log "copy_git_file: curl failed, output: $curl_output"
        else
            debug_log "copy_git_file: файл успешно скопирован"
        fi
        
        return $curl_result
    fi
    
    debug_log "copy_git_file: URL не github/gitlab, копирование невозможно"
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
        
        if [ -n "$size" ]; then
            echo "$size"
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
    
    # Логируем результат
    debug_log "smbclient result: code=$copy_result"
    if [ -n "$error_output" ]; then
        debug_log "smbclient output: $error_output"
    fi
    
    # КРИТИЧНО: Проверяем вывод на ошибки авторизации ПЕРЕД проверкой кода возврата
    # smbclient может вернуть код 0 даже при ошибке авторизации
    if echo "$error_output" | grep -qiE "(NT_STATUS_LOGON_FAILURE|NT_STATUS_WRONG_PASSWORD|authentication failed|access denied|login failed)"; then
        debug_log "smbclient ОШИБКА АВТОРИЗАЦИИ в выводе (даже если код=$copy_result)"
        return 2  # Ошибка авторизации
    fi
    
    # Проверяем код возврата
    if [ $copy_result -eq 0 ]; then
        # Дополнительная проверка: файл должен существовать после копирования
        if [ -f "$dest" ] && [ -s "$dest" ]; then
            debug_log "smbclient УСПЕХ: файл скопирован и подтвержден"
            return 0
        else
            debug_log "smbclient ПРЕДУПРЕЖДЕНИЕ: код=0, но файл не найден или пуст"
            return 1  # Файл не скопировался
        fi
    else
        debug_log "smbclient ОШИБКА: код=$copy_result"
        # Логируем ошибку для отладки
        if command -v log_message >/dev/null 2>&1; then
            log_message "ОШИБКА копирования $file: $error_output"
        else
            echo "[ERROR] copy_smb_file failed for $file: $error_output" >&2
        fi
        return 1
    fi
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
            # Парсим параметры Git: URL:ветка:путь
            # URL может содержать :, поэтому используем awk для правильного парсинга
            # Формат: https://github.com/user/repo:master:.
            # Извлекаем URL (все до последних двух :), ветку (предпоследнее поле) и путь (последнее поле)
            local repo_url=$(echo "$source_params" | awk -F: '{url=""; for(i=1;i<=NF-2;i++){if(i>1)url=url":"; url=url$i}; print url}')
            local branch=$(echo "$source_params" | awk -F: '{print $(NF-1)}')
            local repo_path=$(echo "$source_params" | awk -F: '{print $NF}')
            debug_log "check_source_availability git: repo_url=$repo_url, branch=$branch, path=$repo_path"
            
            if command -v git >/dev/null 2>&1; then
                debug_log "check_source_availability git: git команда найдена"
                # Для git ls-remote добавляем .git если его нет
                local git_url="$repo_url"
                if ! echo "$git_url" | grep -qE '\.git$'; then
                    git_url="${repo_url}.git"
                fi
                debug_log "check_source_availability git: проверяем доступность через git ls-remote: $git_url"
                # Используем timeout если доступен, иначе без него (для совместимости)
                # Уменьшен таймаут до 5 секунд для ускорения
                if command -v timeout >/dev/null 2>&1; then
                    local git_output=$(timeout 5 git ls-remote --heads "$git_url" 2>&1)
                    result=$?
                else
                    # Альтернатива без timeout (для систем где timeout недоступен)
                    local git_output=$(git ls-remote --heads "$git_url" 2>&1)
                    result=$?
                fi
                debug_log "check_source_availability git: git ls-remote result=$result, output_length=${#git_output}"
                if [ $result -ne 0 ]; then
                    debug_log "check_source_availability git: git ls-remote failed, output: $git_output"
                fi
            else
                debug_log "check_source_availability git: git команда НЕ найдена, пробуем через HEAD запрос к raw URL"
                if echo "$repo_url" | grep -qE "(github|gitlab)"; then
                    # Убираем .git из конца URL если есть
                    local clean_url=$(echo "$repo_url" | sed 's|\.git$||')
                    debug_log "check_source_availability git: clean_url=$clean_url"
                    
                    # Формируем raw URL для проверки доступности (проверяем README.md как тестовый файл)
                    local test_file="README.md"
                    if echo "$clean_url" | grep -qE "github\.com"; then
                        local test_url=$(echo "$clean_url" | sed -E "s|https?://github\.com/([^/]+)/([^/]+)|https://raw.githubusercontent.com/\1/\2/${branch}/${test_file}|")
                    elif echo "$clean_url" | grep -qE "gitlab\.com"; then
                        local test_url=$(echo "$clean_url" | sed -E "s|https?://gitlab\.com/([^/]+)/([^/]+)|https://gitlab.com/\1/\2/-/raw/${branch}/${test_file}|")
                    else
                        debug_log "check_source_availability git: URL не github/gitlab"
                        result=1
                    fi
                    
                    if [ -n "$test_url" ]; then
                        debug_log "check_source_availability git: проверяем доступность через HEAD запрос: $test_url"
                        # Используем --max-time вместо timeout для совместимости (работает везде)
                        # Уменьшен таймаут до 5 секунд для ускорения
                        local curl_output=$(curl -s -I -f --max-time 5 "$test_url" 2>&1)
                        result=$?
                        debug_log "check_source_availability git: curl HEAD result=$result, output_length=${#curl_output}"
                        if [ $result -ne 0 ]; then
                            debug_log "check_source_availability git: curl HEAD failed, output: $curl_output"
                        fi
                    fi
                else
                    debug_log "check_source_availability git: URL не github/gitlab, проверка недоступна"
                    result=1
                fi
            fi
            ;;
            
        "smb")
            local server=$(echo "$source_params" | cut -d: -f1)
            # Используем timeout если доступен, иначе ping с ограничением времени
            if command -v timeout >/dev/null 2>&1; then
                timeout 1 ping -c 1 -W 0.5 "$server" >/dev/null 2>&1
                result=$?
            else
                # Альтернатива без timeout (для систем где timeout недоступен)
                ping -c 1 -W 0.5 "$server" >/dev/null 2>&1
                result=$?
            fi
            ;;
            
        "http")
            local base_url="$source_params"
            # Используем --max-time вместо timeout для совместимости
            curl -s -I -f --max-time 3 "$base_url" >/dev/null 2>&1
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
            # Парсим параметры Git: URL:ветка:путь (URL может содержать :)
            local repo_url=$(echo "$source_params" | awk -F: '{url=""; for(i=1;i<=NF-2;i++){if(i>1)url=url":"; url=url$i}; print url}')
            local branch=$(echo "$source_params" | awk -F: '{print $(NF-1)}')
            local repo_path=$(echo "$source_params" | awk -F: '{print $NF}')
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
            # Парсим параметры Git: URL:ветка:путь (URL может содержать :)
            local repo_url=$(echo "$source_params" | awk -F: '{url=""; for(i=1;i<=NF-2;i++){if(i>1)url=url":"; url=url$i}; print url}')
            local branch=$(echo "$source_params" | awk -F: '{print $(NF-1)}')
            local repo_path=$(echo "$source_params" | awk -F: '{print $NF}')
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

# Функция попытки копирования всех файлов из одного источника
try_copy_all_files_from_source() {
    local source="$1"
    local source_type=$(echo "$source" | cut -d: -f1)
    
    
    # Проверяем доступность источника
    if ! check_source_availability "$source"; then
        log_message "Источник $source_type недоступен"
        return 1
    fi
    
    # Устанавливаем источник
    local old_selected_source="$SELECTED_SOURCE"
    SELECTED_SOURCE="$source"
    
    # Для SMB: проверяем/создаем учетные данные
    local credentials_file=""
    local smb_user=""
    if [ "$source_type" = "smb" ]; then
        source_params=$(echo "$source" | cut -d: -f2-)
        smb_user=$(echo "$source_params" | cut -d: -f4)
        credentials_file="$HOME/.smbcredentials"
        
        if [ ! -f "$credentials_file" ]; then
            log_message "Файл учетных данных не найден. Создаем..."
            echo "username=${smb_user}" > "$credentials_file"
            echo "password=" >> "$credentials_file"
            chmod 600 "$credentials_file"
            
            # КРИТИЧНО: Разворачиваем окно терминала для запроса пароля
            # (окно уже должно быть свернуто при запуске скрипта)
            if command -v xdotool >/dev/null 2>&1 && [ "$SKIP_TERMINAL" != "true" ]; then
                restore_terminal_window "$TERMINAL_PID"
                # Небольшая задержка для гарантии что окно развернулось
                sleep 0.2
            fi
            
            log_message "Введите пароль для пользователя ${smb_user}:"
            read -s password
            echo "password=$password" > "$credentials_file"
            echo "username=${smb_user}" >> "$credentials_file"
            chmod 600 "$credentials_file"
            log_message "Учетные данные сохранены"
            
            # КРИТИЧНО: Сворачиваем окно терминала после ввода пароля
            if [ "$SKIP_TERMINAL" != "true" ]; then
                minimize_terminal_window "$TERMINAL_PID"
            fi
        fi
    fi
    
    # Статистика для этого источника
    local copied=0
    local skipped=0
    local failed=0
    local auth_error_occurred=false
    local max_auth_attempts=2  # Максимум 2 попытки с запросом пароля
    
    # Цикл копирования файлов (может быть повторен при ошибке авторизации)
    local auth_attempt=0
    while [ $auth_attempt -lt $max_auth_attempts ]; do
        auth_attempt=$((auth_attempt + 1))
        
        if [ $auth_attempt -gt 1 ]; then
            log_message "Повторная попытка копирования после обновления пароля (попытка $auth_attempt из $max_auth_attempts)..."
            # Сбрасываем счетчики для повторной попытки
            copied=0
            skipped=0
            failed=0
        fi
        
        auth_error_occurred=false
        
        # Пробуем скопировать все файлы
        MISSING_DOCS=()
        for file in "${FILES_TO_COPY[@]}"; do
            local file_path="$LINUX_ASTRA_PATH/$file"
            
            
            # Проверяем, нужно ли обновлять файл
            local need_update=true
            if [ -f "$file_path" ] && [ -s "$file_path" ]; then
                # Получаем информацию о файле для сравнения
                local remote_info=$(get_file_info_from_selected_source "$file")
                local info_result=$?
                
                # Если ошибка авторизации при получении информации - запоминаем и прерываем
                if [ $info_result -eq 2 ]; then
                    log_message "ОШИБКА: Ошибка авторизации при получении информации о файле $file"
                    auth_error_occurred=true
                    failed=$((failed + 1))
                    break  # Прерываем цикл по файлам
                fi
                
                if [ $info_result -eq 0 ] && [ -n "$remote_info" ]; then
                    # Сравниваем размеры
                    local local_size=$(stat -f%z "$file_path" 2>/dev/null || stat -c%s "$file_path" 2>/dev/null || echo "0")
                    if [ "$local_size" = "$remote_info" ]; then
                        log_message "Пропущен: $file (не изменился)"
                        skipped=$((skipped + 1))
                        need_update=false
                    fi
                fi
            fi
            
            # Если файл не нужно обновлять - пропускаем
            if [ "$need_update" = false ]; then
                continue
            fi
            
            # Пробуем скопировать файл
            copy_file_from_selected_source "$file" "$file_path"
            local copy_result=$?
            
            if [ $copy_result -eq 0 ]; then
                # Проверяем что файл действительно скопировался
                if [ -f "$file_path" ] && [ -s "$file_path" ]; then
                    log_message "Скопирован: $file"
                    copied=$((copied + 1))
                else
                    if [[ "$file" == "README.md" ]] || [[ "$file" == "WINE_INSTALL_GUIDE.md" ]]; then
                        MISSING_DOCS+=("$file")
                    else
                        log_message "ПРЕДУПРЕЖДЕНИЕ: Файл $file не найден после копирования"
                    fi
                    failed=$((failed + 1))
                fi
            elif [ $copy_result -eq 2 ]; then
                # Ошибка авторизации
                log_message "ОШИБКА: Ошибка авторизации при копировании $file"
                auth_error_occurred=true
                failed=$((failed + 1))
                break  # Прерываем цикл по файлам
            else
                # Файл не найден на этом источнике
                if [[ "$file" == "README.md" ]] || [[ "$file" == "WINE_INSTALL_GUIDE.md" ]]; then
                    MISSING_DOCS+=("$file")
                else
                    log_message "ПРЕДУПРЕЖДЕНИЕ: Файл $file не найден на источнике $source_type"
                fi
                failed=$((failed + 1))
            fi
        done
        
        # Объединяем предупреждения о документации
        if [ ${#MISSING_DOCS[@]} -gt 0 ]; then
            log_message "ПРЕДУПРЕЖДЕНИЕ: Файлы ${MISSING_DOCS[*]} не найдены на источнике $source_type"
        fi
        
        # Если была ошибка авторизации и это первая попытка - запрашиваем пароль
        if [ "$auth_error_occurred" = true ] && [ $auth_attempt -eq 1 ] && [ "$source_type" = "smb" ]; then
            log_message "Ошибка авторизации обнаружена. Запрашиваем пароль заново..."
            
            # КРИТИЧНО: Разворачиваем окно терминала для запроса пароля
            # (окно должно быть свернуто с момента запуска скрипта)
            if command -v xdotool >/dev/null 2>&1 && [ "$SKIP_TERMINAL" != "true" ]; then
                restore_terminal_window "$TERMINAL_PID"
                # Небольшая задержка для гарантии что окно развернулось
                sleep 0.2
            fi
            
            log_message "Введите пароль для пользователя ${smb_user}:"
            read -s password
            echo "password=$password" > "$credentials_file"
            echo "username=${smb_user}" >> "$credentials_file"
            chmod 600 "$credentials_file"
            log_message "Учетные данные обновлены"
            
            # КРИТИЧНО: Сворачиваем окно терминала после ввода пароля
            if [ "$SKIP_TERMINAL" != "true" ]; then
                minimize_terminal_window "$TERMINAL_PID"
            fi
            
            # Продолжаем цикл - попробуем еще раз
            continue
        elif [ "$auth_error_occurred" = true ]; then
            # Ошибка авторизации после запроса пароля или не SMB источник
            log_message "ОШИБКА: Ошибка авторизации сохраняется. Источник $source_type недоступен."
            break  # Выходим из цикла попыток
        else
            # Нет ошибки авторизации - выходим из цикла попыток
            break
        fi
    done
    
    # Восстанавливаем старый источник
    SELECTED_SOURCE="$old_selected_source"
    
    # Возвращаем результат
    local total_processed=$((copied + skipped))
    log_message "Статистика для источника $source_type: скопировано=$copied, пропущено=$skipped, не найдено=$failed из ${#FILES_TO_COPY[@]} файлов"
    
    # Если была ошибка авторизации после всех попыток - источник не подходит
    if [ "$auth_error_occurred" = true ]; then
        log_message "Источник $source_type не подходит: ошибка авторизации не устранена"
        return 1
    fi
    
    # Если все файлы обработаны (скопированы или пропущены) - источник подходит
    if [ $total_processed -eq ${#FILES_TO_COPY[@]} ] && [ $failed -eq 0 ]; then
        log_message "УСПЕХ: Все файлы найдены на источнике $source_type"
        return 0
    else
        log_message "Источник $source_type не подходит: не все файлы найдены (найдено: $total_processed из ${#FILES_TO_COPY[@]})"
        return 1
    fi
}

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

# Сворачиваем окно терминала (если доступен xdotool)
# НЕ сворачиваем в консольном режиме
if command -v xdotool >/dev/null 2>&1 && [ "$SKIP_TERMINAL" != "true" ]; then
    minimize_terminal_window "$TERMINAL_PID"  # Сворачиваем терминал по PID
fi

# Если передан --terminal-pid извне, используем его
if [ ! -z "$1" ] && [[ "$1" == "--terminal-pid" ]]; then
    TERMINAL_PID="$2"
    log_message "Используем переданный PID терминала: $TERMINAL_PID"
    shift 2  # Убираем --terminal-pid и значение из аргументов
fi

# Сохраняем оставшиеся аргументы для передачи в astra_install.sh
INSTALL_ARGS=("$@")

# КРИТИЧНО: Финальное сворачивание окна после всех проверок
# Это гарантирует, что окно будет свернуто даже если оно не было свернуто ранее
if command -v xdotool >/dev/null 2>&1 && [ "$SKIP_TERMINAL" != "true" ]; then
    minimize_terminal_window "$TERMINAL_PID"
fi

# ============================================================================
# ПОПЫТКА КОПИРОВАНИЯ ВСЕХ ФАЙЛОВ ИЗ ИСТОЧНИКОВ (по очереди, все файлы из одного)
# ============================================================================
log_message "Поиск источника со всеми необходимыми файлами..."

SELECTED_SOURCE=""
BEST_SOURCE=""
BEST_COUNT=0
UPDATE_SUCCESSFUL=false
COPIED_COUNT=0
SKIPPED_COUNT=0

# Пробуем каждый источник по очереди
for source in "${SOURCES[@]}"; do
    source_type=$(echo "$source" | cut -d: -f1)
    log_message "Проверка источника: $source_type"
    
    # Пробуем скопировать все файлы из этого источника
    if try_copy_all_files_from_source "$source"; then
        # Все файлы найдены на этом источнике - используем его
        SELECTED_SOURCE="$source"
        log_message "Используется источник: $source_type (все файлы найдены)"
        UPDATE_SUCCESSFUL=true
        break
    else
        # Не все файлы найдены - запоминаем лучший результат
        # Подсчитываем сколько файлов было скопировано/пропущено
        old_selected_source="$SELECTED_SOURCE"
        SELECTED_SOURCE="$source"
        
        found_count=0
        for file in "${FILES_TO_COPY[@]}"; do
            file_path="$LINUX_ASTRA_PATH/$file"
            # Проверяем есть ли файл локально (после попытки копирования)
            if [ -f "$file_path" ] && [ -s "$file_path" ]; then
                found_count=$((found_count + 1))
            fi
        done
        
        SELECTED_SOURCE="$old_selected_source"
        
        if [ $found_count -gt $BEST_COUNT ]; then
            BEST_COUNT=$found_count
            BEST_SOURCE="$source"
            log_message "Источник $source_type: найдено $found_count из ${#FILES_TO_COPY[@]} файлов (лучший результат пока)"
        fi
    fi
done

# Если не нашли источник со всеми файлами - используем лучший
if [ -z "$SELECTED_SOURCE" ] && [ -n "$BEST_SOURCE" ]; then
    log_message "Не найден источник со всеми файлами. Используем лучший: $(echo "$BEST_SOURCE" | cut -d: -f1) ($BEST_COUNT из ${#FILES_TO_COPY[@]} файлов)"
    SELECTED_SOURCE="$BEST_SOURCE"
    # Пробуем еще раз скопировать из лучшего источника
    try_copy_all_files_from_source "$BEST_SOURCE"
fi

# Если все источники недоступны или не подходят
if [ -z "$SELECTED_SOURCE" ]; then
    log_message "ПРЕДУПРЕЖДЕНИЕ: Не удалось найти подходящий источник. Продолжаем с локальными файлами (если есть)"
    SERVER_AVAILABLE=false
else
    SERVER_AVAILABLE=true
    selected_type=$(echo "$SELECTED_SOURCE" | cut -d: -f1)
    log_message "Выбранный источник: $selected_type"
fi

# ============================================================================
# ЭТАП ПРОВЕРКИ СКОПИРОВАННЫХ ФАЙЛОВ
# ============================================================================
if [ "$SERVER_AVAILABLE" = true ]; then
    sync
    sleep 0.1
    
    ALL_FILES_OK=true
    MISSING_FILES=()
    EMPTY_FILES=()
    
    for file in "${FILES_TO_COPY[@]}"; do
        file_path="$LINUX_ASTRA_PATH/$file"
        
        if [ ! -f "$file_path" ]; then
            log_message "ПРЕДУПРЕЖДЕНИЕ: Файл $file не найден после копирования"
            MISSING_FILES+=("$file")
            ALL_FILES_OK=false
            continue
        fi
        
        if [ ! -s "$file_path" ]; then
            log_message "ПРЕДУПРЕЖДЕНИЕ: Файл $file пустой (размер 0 байт)"
            EMPTY_FILES+=("$file")
            ALL_FILES_OK=false
            continue
        fi
        
        if [ ! -r "$file_path" ]; then
            log_message "ПРЕДУПРЕЖДЕНИЕ: Файл $file недоступен для чтения"
            ALL_FILES_OK=false
            continue
        fi
        
    done
    
    if [ "$ALL_FILES_OK" = false ]; then
        sync
        sleep 0.2
        
        for file in "${MISSING_FILES[@]}"; do
            file_path="$LINUX_ASTRA_PATH/$file"
            if [ -f "$file_path" ] && [ -s "$file_path" ]; then
                ALL_FILES_OK=true
            fi
        done
        
        for file in "${EMPTY_FILES[@]}"; do
            file_path="$LINUX_ASTRA_PATH/$file"
            if [ -s "$file_path" ]; then
                ALL_FILES_OK=true
            fi
        done
    fi
    
    # КРИТИЧНО: Устанавливаем права на выполнение сразу после проверки файлов
    if [ "$IS_BINARY" = true ]; then
        chmod +x "$LINUX_ASTRA_PATH/astra_install" 2>/dev/null
        chmod +x "$LINUX_ASTRA_PATH/astra_update" 2>/dev/null
        chmod +x "$LINUX_ASTRA_PATH/astra_automation" 2>/dev/null
    else
        chmod +x "$LINUX_ASTRA_PATH/astra_install.sh" 2>/dev/null
        chmod +x "$LINUX_ASTRA_PATH/astra_update.sh" 2>/dev/null
        chmod +x "$LINUX_ASTRA_PATH/astra_automation.py" 2>/dev/null
    fi
    
    # Объединяем предупреждения о недостающих файлах
    MISSING_DOCS=()
    for file in "${MISSING_FILES[@]}"; do
        if [[ "$file" == "README.md" ]] || [[ "$file" == "WINE_INSTALL_GUIDE.md" ]]; then
            MISSING_DOCS+=("$file")
        else
            log_message "ПРЕДУПРЕЖДЕНИЕ: Файл $file не найден после копирования"
        fi
    done
    
    if [ ${#MISSING_DOCS[@]} -gt 0 ]; then
        log_message "ПРЕДУПРЕЖДЕНИЕ: Файлы ${MISSING_DOCS[*]} не найдены"
    fi
    
    if [ "$ALL_FILES_OK" = false ] && [ ${#MISSING_DOCS[@]} -lt ${#MISSING_FILES[@]} ]; then
        log_message "ПРЕДУПРЕЖДЕНИЕ: Некоторые файлы имеют проблемы, но продолжаем работу"
    fi
    
    sync
    sleep 0.2
    
    if [ "$SKIP_TERMINAL" != "true" ]; then
        minimize_terminal_window "$TERMINAL_PID"
    fi
fi

# Обработка результата обновления
if [ "$UPDATE_SUCCESSFUL" = true ]; then
    log_message "Обновление завершено успешно"
else
    log_message "ПРЕДУПРЕЖДЕНИЕ: Обновление не выполнено, но продолжаем с локальными файлами (если есть)"
fi

# Проверяем наличие критических файлов (локально или после копирования)
if [ "$IS_BINARY" = true ]; then
    CRITICAL_FILES=("astra_install" "astra_automation")
else
    CRITICAL_FILES=("astra_install.sh" "astra_automation.py")
fi
CRITICAL_OK=true
MISSING_CRITICAL=()

for file in "${CRITICAL_FILES[@]}"; do
    file_path="$LINUX_ASTRA_PATH/$file"
    if [ ! -f "$file_path" ] || [ ! -s "$file_path" ]; then
        log_message "КРИТИЧЕСКАЯ ОШИБКА: Критический файл $file недоступен или пуст"
        CRITICAL_OK=false
        MISSING_CRITICAL+=("$file")
    fi
done

if [ "$CRITICAL_OK" = false ]; then
    log_message "ОШИБКА: Критические файлы не готовы. Запуск невозможен."
    echo "Ошибка Обновления"
    exit 1
fi

# КРИТИЧНО: Повторная установка прав перед запуском (на случай если они не были установлены ранее)
if [ "$IS_BINARY" = true ]; then
    chmod +x "$LINUX_ASTRA_PATH/astra_install" 2>/dev/null
    chmod +x "$LINUX_ASTRA_PATH/astra_update" 2>/dev/null
    chmod +x "$LINUX_ASTRA_PATH/astra_automation" 2>/dev/null
else
    chmod +x "$LINUX_ASTRA_PATH/astra_install.sh" 2>/dev/null
    chmod +x "$LINUX_ASTRA_PATH/astra_update.sh" 2>/dev/null
fi

# КРИТИЧНО: Финальная синхронизация перед запуском приложения
sync
sleep 0.1

# Запускаем установку
cd "$LINUX_ASTRA_PATH" 2>/dev/null

ASTRA_INSTALL=$(find_executable "astra_install")
if [ -z "$ASTRA_INSTALL" ]; then
    log_message "ОШИБКА: astra_install не найден"
    echo "Ошибка Обновления"
    exit 1
fi

if [ "$IS_BINARY" = true ]; then
    # Проверяем бинарный файл
    if [ ! -f "$ASTRA_INSTALL" ] || [ ! -s "$ASTRA_INSTALL" ]; then
        log_message "ОШИБКА: Файл astra_install пустой или поврежден"
        echo "Ошибка Обновления"
        exit 1
    fi
    
    if [ ! -x "$ASTRA_INSTALL" ]; then
        log_message "Файл astra_install не исполняемый, устанавливаем права..."
        chmod +x "$ASTRA_INSTALL" 2>/dev/null
    fi
else
    # Проверяем скрипт
    if [ ! -f "$ASTRA_INSTALL" ] || [ ! -s "$ASTRA_INSTALL" ]; then
        log_message "ОШИБКА: Файл astra_install.sh пустой или поврежден"
        echo "Ошибка Обновления"
        exit 1
    fi
    
    if [ ! -x "$ASTRA_INSTALL" ]; then
        log_message "Файл astra_install.sh не исполняемый, устанавливаем права..."
        chmod +x "$ASTRA_INSTALL" 2>/dev/null
    fi
fi

sync

log_message "Файл astra_install готов к запуску"

# КРИТИЧНО: Передаем лог-файл и timestamp в astra_install.sh
# Это обеспечивает единый лог-файл для всей сессии
if [ -f "$ANALYSIS_LOG_FILE" ] && [ -n "$TIMESTAMP" ]; then
    log_message "Передаем лог-файл в astra_install: $ANALYSIS_LOG_FILE"
    log_message "Передаем timestamp: $TIMESTAMP"
    
    # Формируем аргументы с лог-файлом в начале
    INSTALL_CMD_ARGS=(
        "--log-file" "$ANALYSIS_LOG_FILE"
        "--log-timestamp" "$TIMESTAMP"
        "--terminal-pid" "$TERMINAL_PID"
        "--windows-minimized"
    )
else
    # Fallback: работаем как раньше (без передачи лог-файла)
    log_message "Лог-файл не создан, работаем в старом режиме"
    INSTALL_CMD_ARGS=(
        "--terminal-pid" "$TERMINAL_PID"
        "--windows-minimized"
    )
fi

# Добавляем остальные аргументы
if [ ${#INSTALL_ARGS[@]} -gt 0 ]; then
    INSTALL_CMD_ARGS+=("${INSTALL_ARGS[@]}")
fi

# Проверяем, передан ли --console, и добавляем --mode console_forced
ADD_MODE=false
for arg in "${INSTALL_ARGS[@]}"; do
    if [[ "$arg" == "--console" ]]; then
        ADD_MODE=true
        break
    fi
done

if [ "$ADD_MODE" = true ]; then
    INSTALL_CMD_ARGS+=("--mode" "console_forced")
fi

# Запускаем с правильными аргументами
log_message "Запускаем: $ASTRA_INSTALL ${INSTALL_CMD_ARGS[*]}"
"$ASTRA_INSTALL" "${INSTALL_CMD_ARGS[@]}"

# ВРЕМЕННО: Завершение логирования
debug_log "=== КОНЕЦ СЕАНСА ОБНОВЛЕНИЯ ==="
debug_log "Статистика: скопировано=$COPIED_COUNT, пропущено=$SKIPPED_COUNT"
debug_log "Лог-файл сохранен: $DEBUG_LOG_FILE"
