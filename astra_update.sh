#!/bin/bash
# Скрипт автоматического обновления FSA-AstraInstall для Linux
# Копирует файлы из сетевой папки и запускает установку
# Версия: V2.2.58 (2025.10.15)

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

# Проверяем права root
if [ "$EUID" -ne 0 ]; then
    log_message "Запуск с правами root..."
    sudo "$0" "$@" 2>/dev/null
    exit $?
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

# Очищаем логи
log_message "Очистка старых логов..."
rm -rf "$LINUX_ASTRA_PATH/Log" 2>/dev/null
rm -f "$LINUX_ASTRA_PATH/astra_automation_*.log" 2>/dev/null
rm -f "$LINUX_ASTRA_PATH/progress_table.txt" 2>/dev/null
log_message "Старые логи удалены"

# Устанавливаем права
log_message "Установка прав на выполнение..."
chmod +x "$LINUX_ASTRA_PATH/astra_install.sh" 2>/dev/null
chmod +x "$LINUX_ASTRA_PATH/astra_update.sh" 2>/dev/null
log_message "Права установлены"

# Запускаем установку
log_message "Запуск установки..."
cd "$LINUX_ASTRA_PATH" 2>/dev/null
if [ -f "astra_install.sh" ]; then
    log_message "Запускаем: ./astra_install.sh"
    ./astra_install.sh
else
    log_message "ОШИБКА: Файл astra_install.sh не найден"
    echo "Ошибка Обновления"
    exit 1
fi
