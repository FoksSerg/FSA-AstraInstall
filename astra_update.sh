#!/bin/bash
# Скрипт автоматического обновления FSA-AstraInstall для Linux
# Копирует файлы из сетевой папки и запускает установку
# Версия: V2.4.99 (2025.10.30)
# Компания: ООО "НПА Вира-Реалтайм"

# Сворачиваем все окна включая терминал в самом начале работы
if command -v xdotool >/dev/null 2>&1; then
    xdotool key Super+d 2>/dev/null 
fi

# Функция логирования
log_message() {
    echo "[$(date '+%H:%M:%S')] $1"
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
fi

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
    log_message "Запускаем: ./astra_install.sh --terminal-pid $TERMINAL_PID --windows-minimized"
    ./astra_install.sh --terminal-pid "$TERMINAL_PID" --windows-minimized
else
    log_message "ОШИБКА: Файл astra_install.sh не найден"
    echo "Ошибка Обновления"
    exit 1
fi
